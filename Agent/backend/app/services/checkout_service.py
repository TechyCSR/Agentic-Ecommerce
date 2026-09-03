"""Checkout: turn a session's cart into an order priced by the backend.

Nothing about money comes from the client. Every line is re-validated
against the live Merchant catalog at checkout time (product active and
agent-searchable, variant present, stock sufficient) and re-priced from
that response, so a stale cart snapshot or a tampered request can't set
the amount that gets charged.
"""

from datetime import datetime, timezone

from flask import current_app

from app.extensions import db
from app.models import Order, SelectedProduct
from app.models.enums import OrderStatus, PaymentStatus, SelectionStatus
from app.services import address_service, audit_service, catalog_client, chat_service
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationError


def _format_amount(paise: int, currency: str = "INR") -> str:
    """Smallest-unit integer -> a string a buyer reads, e.g. 8999900 -> ₹89,999."""
    symbol = "₹" if currency == "INR" else f"{currency} "
    major = paise / 100
    return f"{symbol}{major:,.0f}" if major == int(major) else f"{symbol}{major:,.2f}"


def _validate_line(buyer_id: str, session_id, item: SelectedProduct) -> dict:
    """Re-checks one cart line against the catalog and returns a priced snapshot."""
    try:
        product = catalog_client.get_product(str(item.product_id))
    except catalog_client.CatalogError as exc:
        audit_service.log_event(
            action="TOOL_FAILURE",
            session_id=session_id,
            buyer_clerk_user_id=buyer_id,
            metadata={"tool": "get_product_details", "context": "checkout", "error": str(exc)},
        )
        raise ValidationError(
            "Unable to verify your items right now. Please try again.",
            code="CATALOG_UNAVAILABLE",
        ) from exc

    if product is None or product.get("agent_searchable") is False:
        raise ValidationError(
            f"'{item.product_name_snapshot}' is no longer available.",
            code="PRODUCT_NOT_AVAILABLE",
        )

    variant = next(
        (v for v in product.get("variants", []) if v.get("variant_id") == str(item.variant_id)),
        None,
    )
    if variant is None:
        raise ValidationError(
            f"The selected option for '{product['name']}' is no longer available.",
            code="VARIANT_NOT_AVAILABLE",
        )

    quantity = int(item.quantity or 1)
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1.", code="INVALID_QUANTITY")

    stock = variant.get("stock_quantity") or 0
    if variant.get("availability") != "IN_STOCK" or stock < quantity:
        raise ValidationError(
            f"'{product['name']}' doesn't have enough stock for the quantity you selected.",
            code="OUT_OF_STOCK",
        )

    audit_service.log_event(
        action="PRODUCT_VALIDATED",
        session_id=session_id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "product_id": str(item.product_id),
            "variant_id": str(item.variant_id),
            "quantity": quantity,
            "stock_available": stock,
        },
    )

    # Price comes from this fresh catalog response, never from the cart row.
    price = variant.get("price") or {}
    unit_amount = int(price.get("amount") or 0)
    currency = price.get("currency") or "INR"

    audit_service.log_event(
        action="PRICE_VALIDATED",
        session_id=session_id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "product_id": str(item.product_id),
            "variant_id": str(item.variant_id),
            "cart_price_snapshot": item.price_amount_snapshot,
            "validated_unit_price": unit_amount,
            "currency": currency,
            "price_changed": unit_amount != item.price_amount_snapshot,
        },
    )

    images = product.get("images") or []
    primary_image = next((i["url"] for i in images if i.get("is_primary")), None)
    if not primary_image and images:
        primary_image = images[0].get("url")

    return {
        "product_id": str(item.product_id),
        "variant_id": str(item.variant_id),
        "product_name": product["name"],
        "variant_name": variant.get("name"),
        "merchant_name": (product.get("merchant") or {}).get("name"),
        "image_url": primary_image,
        "quantity": quantity,
        "unit_price": {"amount": unit_amount, "currency": currency},
        "line_total": {"amount": unit_amount * quantity, "currency": currency},
    }


def create_checkout(buyer_id: str, session_id) -> Order:
    session = chat_service.get_session_for_buyer(buyer_id, session_id)

    cart_items = (
        SelectedProduct.query.filter_by(session_id=session.id, status=SelectionStatus.SELECTED)
        .order_by(SelectedProduct.created_at.asc())
        .all()
    )
    if not cart_items:
        raise ValidationError("Your cart is empty.", code="CART_EMPTY")

    audit_service.log_event(
        action="CHECKOUT_STARTED",
        session_id=session.id,
        buyer_clerk_user_id=buyer_id,
        metadata={"item_count": len(cart_items)},
    )

    lines = [_validate_line(buyer_id, session.id, item) for item in cart_items]

    currencies = {line["unit_price"]["currency"] for line in lines}
    if len(currencies) > 1:
        raise ValidationError(
            "Your cart mixes currencies, which can't be checked out together.",
            code="MIXED_CURRENCIES",
        )

    amount_total = sum(line["line_total"]["amount"] for line in lines)
    if amount_total <= 0:
        raise ValidationError("This order has no payable amount.", code="INVALID_AMOUNT")

    # Fail here, with a number the buyer can act on, rather than letting
    # Razorpay reject the payment after they've already clicked Pay.
    max_amount = current_app.config.get("MAX_ORDER_AMOUNT") or 0
    if max_amount and amount_total > max_amount:
        audit_service.log_event(
            action="CHECKOUT_REJECTED",
            session_id=session.id,
            buyer_clerk_user_id=buyer_id,
            metadata={
                "reason": "amount_over_limit",
                "amount": amount_total,
                "limit": max_amount,
            },
        )
        raise ValidationError(
            f"This order comes to {_format_amount(amount_total)}, which is above the "
            f"{_format_amount(max_amount)} payment limit currently supported. "
            "Please remove an item or reduce the quantity.",
            code="AMOUNT_OVER_LIMIT",
        )

    # A physical order needs somewhere to go. Asking here — before any money
    # is authorized — keeps the failure cheap and explainable.
    address = address_service.get_default(buyer_id)
    if address is None:
        audit_service.log_event(
            action="CHECKOUT_REJECTED",
            session_id=session.id,
            buyer_clerk_user_id=buyer_id,
            metadata={"reason": "no_delivery_address"},
        )
        raise ValidationError(
            "I need a delivery address before placing this order. Add one and "
            "I'll get it ready.",
            code="ADDRESS_REQUIRED",
        )

    order = Order(
        session_id=session.id,
        buyer_clerk_user_id=buyer_id,
        items=lines,
        amount_total=amount_total,
        currency=currencies.pop(),
        status=OrderStatus.CREATED,
        shipping_address=address.to_dict(),
    )
    db.session.add(order)
    db.session.commit()

    audit_service.log_event(
        action="ORDER_CREATED",
        resource_id=order.id,
        session_id=session.id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "order_id": str(order.id),
            "amount": order.amount_total,
            "currency": order.currency,
            "item_count": len(lines),
            "status": order.status.value,
        },
    )
    return order


def get_order_for_buyer(buyer_id: str, order_id) -> Order:
    order = Order.query.get(order_id)
    if order is None:
        raise NotFoundError("Order not found.", code="ORDER_NOT_FOUND")
    if order.buyer_clerk_user_id != buyer_id:
        raise ForbiddenError("You do not have access to this order.", code="ORDER_FORBIDDEN")
    return order


def list_orders(buyer_id: str, session_id=None) -> list[Order]:
    query = Order.query.filter_by(buyer_clerk_user_id=buyer_id)
    if session_id is not None:
        query = query.filter_by(session_id=session_id)
    return query.order_by(Order.created_at.desc()).all()


def build_receipt(buyer_id: str, order: Order) -> dict:
    """Receipt data for a paid order. Only ever built from verified state."""
    payment = next(
        (p for p in order.payments if p.status == PaymentStatus.PAID),
        None,
    )
    if payment is None:
        raise ValidationError(
            "A receipt is available once payment has been verified.",
            code="PAYMENT_NOT_VERIFIED",
        )

    audit_service.log_event(
        action="RECEIPT_GENERATED",
        resource_id=order.id,
        session_id=order.session_id,
        buyer_clerk_user_id=buyer_id,
        metadata={"order_id": str(order.id), "payment_id": str(payment.id)},
    )

    return {
        "order_id": str(order.id),
        "items": order.items or [],
        "total": {"amount": order.amount_total, "currency": order.currency},
        "order_status": order.status.value if order.status else None,
        "payment_status": payment.status.value if payment.status else None,
        "payment_id": payment.provider_payment_id,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def sync_order_to_merchant(order: Order) -> bool:
    """Registers a paid order with the Merchant service so the seller sees it.

    Never raises: by the time this runs the buyer has been charged, so a
    Merchant-side failure must not unwind a confirmed order. It records
    MERCHANT_SYNC_FAILED and leaves the order retryable instead.
    """
    if order.merchant_synced_at:
        return True

    payment = next((p for p in order.payments if p.status == PaymentStatus.PAID), None)
    payload = {
        "agent_order_id": str(order.id),
        "buyer_ref": order.buyer_clerk_user_id,
        "currency": order.currency,
        "items": [
            {"variant_id": item["variant_id"], "quantity": item["quantity"]}
            for item in (order.items or [])
        ],
        "payment": {
            "provider_order_id": payment.provider_order_id if payment else None,
            "provider_payment_id": payment.provider_payment_id if payment else None,
        },
    }

    try:
        data = catalog_client.create_order(payload)
    except Exception as exc:  # noqa: BLE001 — a paid order must never be rolled back by a sync failure
        audit_service.log_event(
            action="MERCHANT_SYNC_FAILED",
            resource_id=order.id,
            session_id=order.session_id,
            buyer_clerk_user_id=order.buyer_clerk_user_id,
            metadata={"order_id": str(order.id), "error": str(exc)[:500]},
        )
        return False

    order.merchant_order_ids = [o["id"] for o in data.get("orders", [])]
    order.merchant_synced_at = datetime.now(timezone.utc)
    db.session.commit()

    audit_service.log_event(
        action="MERCHANT_SYNC_SUCCEEDED",
        resource_id=order.id,
        session_id=order.session_id,
        buyer_clerk_user_id=order.buyer_clerk_user_id,
        metadata={
            "order_id": str(order.id),
            "merchant_order_ids": order.merchant_order_ids,
            "already_existed": not data.get("created", True),
        },
    )
    return True


def get_fulfillment_status(order: Order) -> str | None:
    """Reads the merchant's fulfillment status back, for "where is my order?".
    Returns None when unsynced or unreachable — never raises into a chat turn."""
    if not order.merchant_synced_at:
        return None
    try:
        data = catalog_client.get_merchant_order(str(order.id))
    except Exception:  # noqa: BLE001 — a status lookup must not break the reply
        return None
    if not data or not data.get("orders"):
        return None
    # One cart can span stores; report the least-advanced status so the buyer
    # isn't told "delivered" while part of the order is still being packed.
    statuses = [o.get("status") for o in data["orders"] if o.get("status")]
    for stage in ("PAID", "CONFIRMED", "PACKED", "SHIPPED", "DELIVERED"):
        if stage in statuses:
            return stage
    return statuses[0] if statuses else None


def clear_cart_for_order(order: Order) -> None:
    """Marks the cart lines that became this order as superseded, so a
    confirmed order can't be silently checked out a second time."""
    SelectedProduct.query.filter_by(
        session_id=order.session_id, status=SelectionStatus.SELECTED
    ).update({"status": SelectionStatus.SUPERSEDED})
    db.session.commit()


def cancel_order(buyer_id: str, order) -> tuple[bool, str]:
    """Cancels a buyer's own order, refunding it if it was paid.

    Bounded deliberately: only the buyer's own order, only while the merchant
    hasn't shipped it, and any refund is for exactly what was captured. The
    merchant is told first — if they refuse (already shipped), nothing is
    cancelled and no money moves.
    """
    from app.services import payment_service

    if order.status == OrderStatus.CANCELLED:
        return False, "That order is already cancelled."

    fulfillment = get_fulfillment_status(order)
    if fulfillment in ("SHIPPED", "DELIVERED"):
        audit_service.log_event(
            action="ORDER_CANCEL_REFUSED",
            resource_id=order.id,
            session_id=order.session_id,
            buyer_clerk_user_id=buyer_id,
            metadata={"order_id": str(order.id), "reason": "already_" + fulfillment.lower()},
        )
        return False, (
            f"That order has already been {fulfillment.lower()}, so it can't be "
            "cancelled here. Ask about a return instead."
        )

    # Ask the merchant first: they own fulfillment and stock, and they are the
    # authority on whether it's too late.
    if order.merchant_synced_at:
        try:
            catalog_client.cancel_merchant_order(str(order.id), "buyer_cancelled")
        except Exception as exc:  # noqa: BLE001 — surfaced to the buyer, never a traceback
            audit_service.log_event(
                action="ORDER_CANCEL_REFUSED",
                resource_id=order.id,
                session_id=order.session_id,
                buyer_clerk_user_id=buyer_id,
                metadata={"order_id": str(order.id), "error": str(exc)[:300]},
            )
            return False, (
                "The store couldn't cancel that order right now — it may already "
                "be on its way. Please try again shortly."
            )

    payment = next((p for p in order.payments if p.status == PaymentStatus.PAID), None)

    order.status = OrderStatus.CANCELLED
    db.session.commit()

    audit_service.log_event(
        action="ORDER_CANCELLED",
        resource_id=order.id,
        session_id=order.session_id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "order_id": str(order.id),
            "amount": order.amount_total,
            "currency": order.currency,
            "was_paid": payment is not None,
        },
    )

    if payment is None:
        return True, "Your order is cancelled. Nothing was charged."

    refunded, message = payment_service.refund_payment(order, payment, "buyer_cancelled")
    if refunded:
        return True, f"Your order is cancelled. {message}"
    # The refund helper's failure text already explains the cancellation.
    return True, message


def reorder_into_cart(buyer_id: str, order, session_id) -> tuple[int, list]:
    """Puts a past order's items back in the cart, re-validating each one.

    Anything now unavailable or out of stock is skipped and named, rather
    than silently dropped or added at a stale price.
    """
    from app.services import selection_service

    added, skipped = 0, []
    for item in order.items or []:
        try:
            selection_service.add_to_cart(
                buyer_id, session_id, item["product_id"], item["variant_id"],
                int(item.get("quantity") or 1),
            )
            added += 1
        except Exception:  # noqa: BLE001 — one unavailable line shouldn't stop the rest
            skipped.append(item.get("product_name"))
    return added, skipped
