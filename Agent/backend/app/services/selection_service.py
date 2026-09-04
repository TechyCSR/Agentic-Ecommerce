"""Cart: add/update/remove items, validated fresh against the Merchant
catalog API on every write. Price/stock/product info is never trusted from
the request or from anything cached earlier in the conversation — only from
a live catalog_client.get_product() call made here, server-side.

A cart line can never exceed what is actually buyable. The catalog's
`stock_quantity` is already net of other buyers' checkout holds, so the
ceiling here is real availability, not shelf count. Asking for more than
that is capped to the ceiling and reported back rather than silently
accepted — a cart that can't survive checkout is worse than a smaller one.
"""

from app.extensions import db
from app.models import SelectedProduct
from app.models.enums import SelectionStatus
from app.services import audit_service, catalog_client, chat_service
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationError


def _primary_image(product: dict) -> str | None:
    images = product.get("images") or []
    primary = next((i["url"] for i in images if i.get("is_primary")), None)
    return primary or (images[0].get("url") if images else None)


def _verify_variant(product_id: str, variant_id: str) -> tuple[dict, dict]:
    try:
        product = catalog_client.get_product(product_id)
    except catalog_client.CatalogError as exc:
        raise ValidationError(
            "Unable to verify this product right now. Please try again.",
            code="CATALOG_UNAVAILABLE",
        ) from exc

    if product is None:
        raise NotFoundError(
            "This product is no longer available.", code="PRODUCT_NOT_AVAILABLE"
        )

    variant = next(
        (v for v in product.get("variants", []) if v.get("variant_id") == variant_id),
        None,
    )
    if variant is None:
        raise NotFoundError("This variant is no longer available.", code="VARIANT_NOT_AVAILABLE")

    if variant.get("availability") != "IN_STOCK" or not variant.get("stock_quantity"):
        raise ValidationError("This variant is currently out of stock.", code="OUT_OF_STOCK")

    return product, variant


def _available(variant: dict) -> int:
    """Units this buyer could actually get right now — the merchant reports
    this net of stock other buyers are holding mid-checkout."""
    return max(0, int(variant.get("stock_quantity") or 0))


def _annotate(item, requested: int, granted: int, available: int):
    """Records that a quantity was trimmed, so the caller can say so.

    Plain instance attributes, not columns: this describes what just
    happened to one request, not a fact about the cart line.
    """
    item.requested_quantity = requested
    item.stock_limited = granted < requested
    item.available_stock = available
    return item


def add_to_cart(buyer_id: str, session_id: str, product_id: str, variant_id: str, quantity: int = 1):
    session = chat_service.get_session_for_buyer(buyer_id, session_id)

    try:
        product, variant = _verify_variant(product_id, variant_id)
    except (ValidationError, NotFoundError) as exc:
        audit_service.log_event(
            action="TOOL_FAILURE",
            session_id=session.id,
            buyer_clerk_user_id=buyer_id,
            metadata={"tool": "get_product_details", "error": str(exc), "context": "cart_add"},
        )
        raise

    existing = SelectedProduct.query.filter_by(
        session_id=session.id,
        product_id=product["product_id"],
        variant_id=variant["variant_id"],
        status=SelectionStatus.SELECTED,
    ).first()

    price = variant.get("price") or {}
    available = _available(variant)

    # "Add 2 more" means two on top of what is already there, so the ceiling
    # applies to the resulting total — not to this request in isolation.
    already = existing.quantity if existing else 0
    requested = already + max(int(quantity), 1)
    granted = min(requested, available)

    if granted <= already:
        raise ValidationError(
            f"Your cart already has all {available} available of "
            f"'{product['name']}' — there aren't any more to add.",
            code="INSUFFICIENT_STOCK",
        )

    if existing:
        existing.quantity = granted
        db.session.commit()
        item = existing
    else:
        item = SelectedProduct(
            session_id=session.id,
            buyer_clerk_user_id=buyer_id,
            product_id=product["product_id"],
            variant_id=variant["variant_id"],
            product_name_snapshot=product["name"],
            variant_name_snapshot=variant["name"],
            merchant_name_snapshot=(product.get("merchant") or {}).get("name"),
            price_amount_snapshot=price.get("amount", 0),
            currency_snapshot=price.get("currency", "INR"),
            image_url_snapshot=_primary_image(product),
            quantity=granted,
            status=SelectionStatus.SELECTED,
        )
        db.session.add(item)
        db.session.commit()

    audit_service.log_event(
        action="PRODUCT_SELECTED",
        resource_id=item.id,
        session_id=session.id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "product_id": str(product["product_id"]),
            "variant_id": str(variant["variant_id"]),
            "quantity": item.quantity,
            "requested_quantity": requested,
            "stock_limited": granted < requested,
            "available_stock": available,
            "price": price,
        },
    )
    return _annotate(item, requested, granted, available)


def update_quantity(buyer_id: str, session_id: str, selection_id: str, quantity: int):
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1.", code="INVALID_QUANTITY")

    session = chat_service.get_session_for_buyer(buyer_id, session_id)
    item = SelectedProduct.query.get(selection_id)
    if item is None or item.session_id != session.id or item.status != SelectionStatus.SELECTED:
        raise NotFoundError("Cart item not found.", code="CART_ITEM_NOT_FOUND")
    if item.buyer_clerk_user_id != buyer_id:
        raise ForbiddenError("You do not have access to this cart item.", code="CART_ITEM_FORBIDDEN")

    # Re-verify stock before honoring a bumped-up quantity — never trust the
    # client's number against unchecked availability.
    _, variant = _verify_variant(str(item.product_id), str(item.variant_id))

    available = _available(variant)
    granted = min(quantity, available)

    item.quantity = granted
    db.session.commit()

    audit_service.log_event(
        action="CART_QUANTITY_UPDATED",
        resource_id=item.id,
        session_id=session.id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "product_id": str(item.product_id),
            "variant_id": str(item.variant_id),
            "quantity": granted,
            "requested_quantity": quantity,
            "stock_limited": granted < quantity,
            "available_stock": available,
        },
    )
    return _annotate(item, quantity, granted, available)


def remove_from_cart(buyer_id: str, session_id: str, selection_id: str):
    session = chat_service.get_session_for_buyer(buyer_id, session_id)
    item = SelectedProduct.query.get(selection_id)
    if item is None or item.session_id != session.id or item.status != SelectionStatus.SELECTED:
        raise NotFoundError("Cart item not found.", code="CART_ITEM_NOT_FOUND")
    if item.buyer_clerk_user_id != buyer_id:
        raise ForbiddenError("You do not have access to this cart item.", code="CART_ITEM_FORBIDDEN")

    item.status = SelectionStatus.REMOVED
    db.session.commit()

    audit_service.log_event(
        action="PRODUCT_REMOVED",
        resource_id=item.id,
        session_id=session.id,
        buyer_clerk_user_id=buyer_id,
        metadata={"product_id": str(item.product_id), "variant_id": str(item.variant_id)},
    )
    return item


def get_cart(buyer_id: str, session_id: str) -> dict:
    session = chat_service.get_session_for_buyer(buyer_id, session_id)
    items = (
        SelectedProduct.query.filter_by(session_id=session.id, status=SelectionStatus.SELECTED)
        .order_by(SelectedProduct.created_at.asc())
        .all()
    )
    total_amount = sum(i.price_amount_snapshot * i.quantity for i in items)
    currency = items[0].currency_snapshot if items else "INR"
    return {
        "items": [i.to_dict() for i in items],
        "total": {"amount": total_amount, "currency": currency},
    }
