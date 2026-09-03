"""Checkout: turn a session's cart into an order priced by the backend.

Nothing about money comes from the client. Every line is re-validated
against the live Merchant catalog at checkout time (product active and
agent-searchable, variant present, stock sufficient) and re-priced from
that response, so a stale cart snapshot or a tampered request can't set
the amount that gets charged.
"""

from flask import current_app

from app.extensions import db
from app.models import Order, SelectedProduct
from app.models.enums import OrderStatus, PaymentStatus, SelectionStatus
from app.services import audit_service, catalog_client, chat_service
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

    order = Order(
        session_id=session.id,
        buyer_clerk_user_id=buyer_id,
        items=lines,
        amount_total=amount_total,
        currency=currencies.pop(),
        status=OrderStatus.CREATED,
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


def clear_cart_for_order(order: Order) -> None:
    """Marks the cart lines that became this order as superseded, so a
    confirmed order can't be silently checked out a second time."""
    SelectedProduct.query.filter_by(
        session_id=order.session_id, status=SelectionStatus.SELECTED
    ).update({"status": SelectionStatus.SUPERSEDED})
    db.session.commit()
