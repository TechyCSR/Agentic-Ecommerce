"""Timed stock holds, so two buyers can't pay for the same last unit.

The oversell window this closes is real and was measured in production: the
agent validates stock when it prices a checkout, but the buyer then spends
anywhere from seconds to minutes inside Razorpay. Without a hold, nothing
stopped a second buyer from being quoted — and charged for — the same unit,
leaving the loser of the race paid-up and unfulfillable.

Two properties keep this safe:

* **Atomic.** Checking availability and writing the hold happen inside one
  transaction with the variant rows locked, so concurrent reservations for
  the same variant serialize instead of both seeing the same free stock.
* **Self-releasing.** A hold carries an expiry and every read filters on it.
  An abandoned checkout frees its stock on its own; nothing depends on a
  cron job having run, or on the agent remembering to call release.
"""

import uuid
from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import func

from app.extensions import db
from app.models import Product, ProductVariant, StockReservation
from app.models.enums import ProductStatus, ReservationStatus
from app.services import audit_service
from app.utils.exceptions import NotFoundError, ValidationError

DEFAULT_TTL_MINUTES = 15
MAX_TTL_MINUTES = 60


def _now():
    return datetime.now(timezone.utc)


def _ttl_minutes(requested=None) -> int:
    """Bounded so a caller can shorten a hold but never sit on stock forever."""
    default = current_app.config.get("STOCK_RESERVATION_TTL_MINUTES") or DEFAULT_TTL_MINUTES
    try:
        minutes = int(requested) if requested else int(default)
    except (TypeError, ValueError):
        minutes = int(default)
    return max(1, min(minutes, MAX_TTL_MINUTES))


# ---- Availability ----


def held_quantities(variant_ids, exclude_agent_order_id=None) -> dict:
    """How many units of each variant are currently held by someone else.

    Expired holds are excluded by the query itself, which is what makes
    expiry correct without a sweeper.
    """
    if not variant_ids:
        return {}

    query = (
        db.session.query(
            StockReservation.product_variant_id,
            func.coalesce(func.sum(StockReservation.quantity), 0),
        )
        .filter(
            StockReservation.product_variant_id.in_(list(variant_ids)),
            StockReservation.status == ReservationStatus.HELD,
            StockReservation.expires_at > _now(),
        )
        .group_by(StockReservation.product_variant_id)
    )
    if exclude_agent_order_id:
        query = query.filter(StockReservation.agent_order_id != exclude_agent_order_id)

    return {variant_id: int(total or 0) for variant_id, total in query.all()}


def held_for_products(products, exclude_agent_order_id=None) -> dict:
    """Held counts for every variant of the given products, in one query —
    search returns a page of products and must not fan out per variant."""
    variant_ids = [v.id for product in products for v in product.variants]
    return held_quantities(variant_ids, exclude_agent_order_id)


def available_quantity(variant, exclude_agent_order_id=None) -> int:
    held = held_quantities([variant.id], exclude_agent_order_id).get(variant.id, 0)
    return max(0, (variant.stock_quantity or 0) - held)


# ---- Lifecycle ----


def sweep_expired(reason="EXPIRED") -> int:
    """Settles lapsed holds so the table reads as the truth rather than as a
    pile of rows the availability query happens to ignore.

    Purely cosmetic for correctness — reads already discount expired holds —
    but it gives the audit trail a moment where the stock came back.
    """
    stale = StockReservation.query.filter(
        StockReservation.status == ReservationStatus.HELD,
        StockReservation.expires_at <= _now(),
    ).all()
    if not stale:
        return 0

    by_order: dict = {}
    for reservation in stale:
        reservation.status = ReservationStatus.RELEASED
        reservation.settled_at = _now()
        by_order.setdefault(reservation.agent_order_id, 0)
        by_order[reservation.agent_order_id] += reservation.quantity
    db.session.commit()

    for agent_order_id, units in by_order.items():
        audit_service.log_event(
            actor_type="SYSTEM",
            resource_type="STOCK_RESERVATION",
            action="STOCK_RESERVATION_EXPIRED",
            metadata={
                "agent_order_id": agent_order_id,
                "units_released": units,
                "reason": reason,
            },
        )
    return len(stale)


def _lock_variants(variant_ids) -> dict:
    """Loads the variants, locked where the database can lock them.

    The lock is what makes "check then hold" atomic under concurrency.
    SQLite (tests) has no row locks and no concurrency to protect against,
    so it is skipped there rather than failing on the syntax.
    """
    query = ProductVariant.query.filter(ProductVariant.id.in_(list(variant_ids)))
    if db.session.get_bind().dialect.name == "postgresql":
        query = query.with_for_update()
    return {variant.id: variant for variant in query.all()}


def reserve(agent_order_id: str, items, api_client_id=None, ttl_minutes=None) -> dict:
    """Holds stock for one agent order. Idempotent, and safe to repeat.

    Re-reserving the same `agent_order_id` re-prices the hold against the
    current cart: quantities are updated, lines the buyer dropped are
    released, and the clock restarts. That is what makes "ask for the Pay
    button again" cheap — the buyer keeps their place in the queue rather
    than losing the hold and racing for it afresh.
    """
    agent_order_id = (agent_order_id or "").strip()
    if not agent_order_id:
        raise ValidationError("agent_order_id is required")

    wanted: dict = {}
    for line in items or []:
        variant_id = _as_uuid(line.get("variant_id"))
        if variant_id is None:
            raise ValidationError("Each item needs a valid variant_id")
        quantity = int(line.get("quantity") or 1)
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1")
        wanted[variant_id] = wanted.get(variant_id, 0) + quantity

    if not wanted:
        raise ValidationError("A reservation needs at least one item")

    # Tidy lapsed holds first, so this reservation is measured against — and
    # audited alongside — an accurate picture of what is actually spoken for.
    sweep_expired()

    existing = StockReservation.query.filter_by(agent_order_id=agent_order_id).all()
    if any(r.status == ReservationStatus.CONSUMED for r in existing):
        raise ValidationError(
            "This order has already been placed and its stock consumed.",
            code="RESERVATION_ALREADY_CONSUMED",
        )

    variants = _lock_variants(wanted.keys())
    held_by_others = held_quantities(wanted.keys(), exclude_agent_order_id=agent_order_id)

    expires_at = _now() + timedelta(minutes=_ttl_minutes(ttl_minutes))
    by_variant = {str(r.product_variant_id): r for r in existing}
    reservations = []

    for variant_id, quantity in wanted.items():
        variant = variants.get(variant_id)
        if variant is None:
            db.session.rollback()
            raise NotFoundError(f"Variant {variant_id} not found", code="VARIANT_NOT_FOUND")

        product = Product.query.get(variant.product_id)
        if product is None or product.status != ProductStatus.ACTIVE:
            db.session.rollback()
            raise ValidationError(
                f"Product for variant {variant_id} is not available",
                code="PRODUCT_NOT_AVAILABLE",
            )

        available = (variant.stock_quantity or 0) - held_by_others.get(variant.id, 0)
        if available < quantity:
            db.session.rollback()
            raise ValidationError(
                f"Only {max(0, available)} left of '{product.name}' — "
                f"{quantity} isn't available right now.",
                code="INSUFFICIENT_STOCK",
            )

        reservation = by_variant.pop(str(variant_id), None)
        if reservation is None:
            reservation = StockReservation(
                agent_order_id=agent_order_id,
                product_variant_id=variant.id,
                api_client_id=api_client_id,
            )
            db.session.add(reservation)
        reservation.quantity = quantity
        reservation.status = ReservationStatus.HELD
        reservation.expires_at = expires_at
        reservation.settled_at = None
        reservations.append(reservation)

    # Anything this order held last time but no longer wants goes back now,
    # rather than sitting on stock until it expires.
    for dropped in by_variant.values():
        if dropped.status == ReservationStatus.HELD:
            dropped.status = ReservationStatus.RELEASED
            dropped.settled_at = _now()

    db.session.commit()

    audit_service.log_event(
        actor_type="AGENT",
        actor_id=api_client_id,
        resource_type="STOCK_RESERVATION",
        action="STOCK_RESERVED",
        metadata={
            "agent_order_id": agent_order_id,
            "expires_at": expires_at.isoformat(),
            "items": [
                {"variant_id": str(r.product_variant_id), "quantity": r.quantity}
                for r in reservations
            ],
        },
    )

    return {
        "agent_order_id": agent_order_id,
        "expires_at": expires_at.isoformat(),
        "ttl_seconds": int((expires_at - _now()).total_seconds()),
        "reservations": [r.to_dict() for r in reservations],
    }


def release(agent_order_id: str, reason="RELEASED", api_client_id=None) -> int:
    """Gives held stock back early — the buyer cancelled or walked away.

    Never an error if there is nothing to release: the hold may have already
    expired, or the caller may simply be being tidy.
    """
    held = StockReservation.query.filter_by(
        agent_order_id=agent_order_id, status=ReservationStatus.HELD
    ).all()
    if not held:
        return 0

    for reservation in held:
        reservation.status = ReservationStatus.RELEASED
        reservation.settled_at = _now()
    db.session.commit()

    audit_service.log_event(
        actor_type="AGENT",
        actor_id=api_client_id,
        resource_type="STOCK_RESERVATION",
        action="STOCK_RELEASED",
        metadata={
            "agent_order_id": agent_order_id,
            "reason": reason,
            "units_released": sum(r.quantity for r in held),
        },
    )
    return len(held)


def consume(agent_order_id: str, order_id=None, commit=True) -> int:
    """Settles the hold because the order it was protecting is now real.

    Called from order creation, where the physical `stock_quantity` decrement
    happens. Both must land together: the hold has to stop counting at the
    same instant the stock actually leaves, or the units are subtracted
    twice and the variant looks emptier than it is.
    """
    held = StockReservation.query.filter_by(
        agent_order_id=agent_order_id, status=ReservationStatus.HELD
    ).all()
    for reservation in held:
        reservation.status = ReservationStatus.CONSUMED
        reservation.settled_at = _now()
    if commit and held:
        db.session.commit()
    return len(held)


def get_reservation(agent_order_id: str) -> dict | None:
    """What is currently held for an order, for the agent to read back."""
    held = StockReservation.query.filter_by(
        agent_order_id=agent_order_id, status=ReservationStatus.HELD
    ).filter(StockReservation.expires_at > _now()).all()
    if not held:
        return None
    expires_at = min(r.expires_at for r in held)
    return {
        "agent_order_id": agent_order_id,
        "expires_at": expires_at.isoformat(),
        "ttl_seconds": max(0, int((expires_at - _now()).total_seconds())),
        "reservations": [r.to_dict() for r in held],
    }


def _as_uuid(value):
    """Variant ids arrive as strings over HTTP. Returns None rather than
    raising, so a malformed id becomes a clean 400 instead of a 500."""
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
