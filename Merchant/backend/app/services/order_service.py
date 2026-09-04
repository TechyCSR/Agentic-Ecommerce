"""Orders received from an authorized shopping agent, and the merchant's
view of them.

Two properties matter most here:

* **Idempotent.** Sync is keyed on `agent_order_id`. A retry, a duplicated
  webhook, or a re-sent request returns the existing order instead of
  creating a second one or double-decrementing stock.
* **Server-resolved.** Nothing about a product, price, merchant or store is
  taken from the request body. Every line is re-read from this database, and
  the merchant/store are derived from the products themselves — the agent's
  API client is platform-wide with `merchant_id = NULL`, so it could not
  supply them even if we wanted it to.
"""

from datetime import datetime, timezone

from sqlalchemy import func

from app.extensions import db
from app.models import Order, OrderItem, Payment, Product, ProductVariant
from app.models.enums import (
    FULFILLMENT_FLOW,
    OrderStatus,
    PaymentProvider,
    PaymentStatus,
    ProductStatus,
)
from app.services import (
    audit_service,
    merchant_service,
    product_service,
    reservation_service,
)
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationError


def _resolve_line(line: dict):
    """Re-reads one requested line from this database. Returns
    (variant, product, quantity)."""
    variant_id = line.get("variant_id")
    quantity = int(line.get("quantity") or 1)
    if not variant_id:
        raise ValidationError("Each item needs a variant_id")
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1")

    variant = ProductVariant.query.get(variant_id)
    if variant is None:
        raise NotFoundError(f"Variant {variant_id} not found", code="VARIANT_NOT_FOUND")

    product = Product.query.get(variant.product_id)
    if product is None or product.status != ProductStatus.ACTIVE:
        raise ValidationError(
            f"Product for variant {variant_id} is not available", code="PRODUCT_NOT_AVAILABLE"
        )

    return variant, product, quantity


def create_order_from_agent(payload: dict, api_client_id=None):
    """Registers a paid order that the agent has already collected money for.

    Returns (orders, created) — a list because one agent cart can span
    several stores, and a Merchant order belongs to exactly one.
    """
    agent_order_id = (payload.get("agent_order_id") or "").strip()
    if not agent_order_id:
        raise ValidationError("agent_order_id is required")

    existing = Order.query.filter_by(agent_order_id=agent_order_id).all()
    if existing:
        # Already synced — return what we have rather than duplicating it.
        return existing, False

    items = payload.get("items") or []
    if not items:
        raise ValidationError("An order needs at least one item")

    buyer_ref = payload.get("buyer_ref")
    currency = payload.get("currency") or "INR"
    payment = payload.get("payment") or {}

    resolved = [_resolve_line(line) for line in items]

    # One Merchant order per store, since Order carries a single store_id.
    by_store: dict = {}
    for variant, product, quantity in resolved:
        by_store.setdefault(product.store_id, []).append((variant, product, quantity))

    now = datetime.now(timezone.utc)
    orders = []

    for store_id, store_lines in by_store.items():
        merchant_id = store_lines[0][1].store.merchant_id
        order = Order(
            merchant_id=merchant_id,
            store_id=store_id,
            agent_order_id=agent_order_id if len(by_store) == 1 else f"{agent_order_id}:{store_id}",
            buyer_ref=buyer_ref,
            status=OrderStatus.PAID,
            currency=currency,
            placed_at=now,
        )
        db.session.add(order)
        db.session.flush()  # need order.id for items and the movement reference

        subtotal = 0
        for variant, product, quantity in store_lines:
            # Price comes from this database, never from the request.
            unit_price = variant.price
            line_total = unit_price * quantity
            subtotal += line_total

            db.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_variant_id=variant.id,
                    product_name_snapshot=product.name,
                    quantity=quantity,
                    unit_price_amount=unit_price,
                    total_amount=line_total,
                )
            )

            try:
                product_service.adjust_stock_internal(
                    variant,
                    -quantity,
                    reason="ORDER_PLACED",
                    reference_type="ORDER",
                    reference_id=order.id,
                    commit=False,
                )
            except ValidationError as exc:
                # The last unit went to someone else between checkout and
                # payment. Say so distinctly: the caller has already charged
                # this buyer and must refund rather than retry forever.
                db.session.rollback()
                raise ValidationError(
                    f"'{product.name}' sold out before this order could be placed.",
                    code="INSUFFICIENT_STOCK",
                ) from exc

        order.subtotal_amount = subtotal
        order.total_amount = subtotal

        db.session.add(
            Payment(
                order_id=order.id,
                provider=PaymentProvider.RAZORPAY,
                provider_order_id=payment.get("provider_order_id"),
                provider_payment_id=payment.get("provider_payment_id"),
                amount=subtotal,
                currency=currency,
                status=PaymentStatus.CAPTURED,
            )
        )
        orders.append(order)

    # The hold this order was protecting has now become a real decrement.
    # Settling it in the same transaction is what stops the units being
    # subtracted twice — once as "held", once as "sold".
    consumed = reservation_service.consume(agent_order_id, commit=False)

    db.session.commit()

    for order in orders:
        audit_service.log_event(
            actor_type="AGENT",
            actor_id=api_client_id,
            merchant_id=order.merchant_id,
            resource_type="ORDER",
            resource_id=order.id,
            action="ORDER_RECEIVED_FROM_AGENT",
            metadata={
                "agent_order_id": order.agent_order_id,
                "buyer_ref": buyer_ref,
                "total_amount": order.total_amount,
                "currency": order.currency,
                "item_count": len(order.items),
                "reservations_consumed": consumed,
            },
        )

    return orders, True


def cancel_order_from_agent(agent_order_id: str, reason: str = None, api_client_id=None):
    """Cancels a synced order and puts its stock back.

    Refused once the goods are on their way — an order that has shipped can't
    be unshipped, and silently restoring stock for it would corrupt the
    merchant's inventory.
    """
    orders = get_by_agent_order_id(agent_order_id)
    if not orders:
        # Nothing was ever placed, but a priced checkout may still be sitting
        # on stock. Free it rather than making the next buyer wait out the TTL.
        if reservation_service.release(agent_order_id, "ORDER_CANCELLED", api_client_id):
            return []
        raise NotFoundError("Order not found", code="ORDER_NOT_FOUND")

    shipped = [o for o in orders if o.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED)]
    if shipped:
        raise ValidationError(
            "This order has already shipped and can no longer be cancelled.",
            code="ORDER_ALREADY_SHIPPED",
        )

    cancelled = []
    for order in orders:
        if order.status == OrderStatus.CANCELLED:
            cancelled.append(order)
            continue

        for item in order.items:
            variant = ProductVariant.query.get(item.product_variant_id)
            if variant is None:
                continue
            product_service.adjust_stock_internal(
                variant,
                item.quantity,  # positive: the reservation goes back
                reason="ORDER_CANCELLED",
                reference_type="ORDER",
                reference_id=order.id,
                commit=False,
            )

        order.status = OrderStatus.CANCELLED
        cancelled.append(order)

    db.session.commit()

    for order in cancelled:
        audit_service.log_event(
            actor_type="AGENT",
            actor_id=api_client_id,
            merchant_id=order.merchant_id,
            resource_type="ORDER",
            resource_id=order.id,
            action="ORDER_CANCELLED",
            metadata={"agent_order_id": agent_order_id, "reason": reason,
                      "stock_restored": True},
        )
    return cancelled


def get_by_agent_order_id(agent_order_id: str):
    return Order.query.filter(
        (Order.agent_order_id == agent_order_id)
        | (Order.agent_order_id.like(f"{agent_order_id}:%"))
    ).all()


# ---- Merchant-facing ----


def list_orders_for_merchant(user, status=None, limit=20, offset=0):
    merchant = merchant_service.get_merchant_for_user(user)
    query = Order.query.filter_by(merchant_id=merchant.id)
    if status:
        query = query.filter(Order.status == status)
    total = query.count()
    orders = query.order_by(Order.created_at.desc()).limit(limit).offset(offset).all()
    return orders, total


def get_order_for_merchant(user, order_id) -> Order:
    order = Order.query.get(order_id)
    if order is None:
        raise NotFoundError("Order not found", code="ORDER_NOT_FOUND")
    if order.merchant_id != merchant_service.get_merchant_for_user(user).id:
        raise ForbiddenError("You do not have access to this order", code="ORDER_FORBIDDEN")
    return order


def update_fulfillment_status(user, order_id, status: str) -> Order:
    order = get_order_for_merchant(user, order_id)

    if status not in FULFILLMENT_FLOW:
        raise ValidationError(
            f"Status must be one of: {', '.join(FULFILLMENT_FLOW)}",
            code="INVALID_FULFILLMENT_STATUS",
        )
    if order.status == OrderStatus.CANCELLED:
        raise ValidationError("A cancelled order can't be fulfilled", code="ORDER_CANCELLED")
    if order.status in (OrderStatus.DRAFT, OrderStatus.PAYMENT_FAILED):
        raise ValidationError(
            "Only a paid order can be fulfilled", code="ORDER_NOT_PAID"
        )

    previous = order.status.value if order.status else None
    order.status = OrderStatus(status)
    db.session.commit()

    audit_service.log_event(
        actor_type="MERCHANT",
        actor_id=user.id,
        merchant_id=order.merchant_id,
        resource_type="ORDER",
        resource_id=order.id,
        action="ORDER_FULFILLMENT_UPDATED",
        metadata={"from": previous, "to": status},
    )
    return order


def order_stats(user) -> dict:
    """Counts and revenue for the merchant dashboard."""
    merchant_id = merchant_service.get_merchant_for_user(user).id

    total_orders = Order.query.filter_by(merchant_id=merchant_id).count()

    paid_states = [
        OrderStatus.PAID,
        OrderStatus.CONFIRMED,
        OrderStatus.PACKED,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
    ]
    revenue = (
        db.session.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.merchant_id == merchant_id, Order.status.in_(paid_states))
        .scalar()
    )
    awaiting = Order.query.filter(
        Order.merchant_id == merchant_id,
        Order.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.PACKED]),
    ).count()
    delivered = Order.query.filter_by(
        merchant_id=merchant_id, status=OrderStatus.DELIVERED
    ).count()

    return {
        "total_orders": total_orders,
        "revenue_amount": int(revenue or 0),
        "currency": "INR",
        "awaiting_fulfillment": awaiting,
        "delivered": delivered,
    }


def list_payments_for_merchant(user, limit=20, offset=0):
    query = (
        db.session.query(Payment, Order)
        .join(Order, Payment.order_id == Order.id)
        .filter(Order.merchant_id == merchant_service.get_merchant_for_user(user).id)
    )
    total = query.count()
    rows = query.order_by(Payment.created_at.desc()).limit(limit).offset(offset).all()
    return [
        {**payment.to_dict(), "order": order.to_dict(include_items=False, include_payments=False)}
        for payment, order in rows
    ], total
