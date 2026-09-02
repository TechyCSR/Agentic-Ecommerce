"""Buy Now: validate product + variant + stock fresh against the Merchant
catalog API, then save the selection. Price/stock/product info is never
trusted from the request — only from a live catalog_client.get_product()
call made here, server-side.
"""

from app.extensions import db
from app.models import SelectedProduct
from app.models.enums import SelectionStatus
from app.services import audit_service, catalog_client, chat_service
from app.utils.exceptions import NotFoundError, ValidationError


def select_product(buyer_id: str, session_id: str, product_id: str, variant_id: str):
    session = chat_service.get_session_for_buyer(buyer_id, session_id)

    try:
        product = catalog_client.get_product(product_id)
    except catalog_client.CatalogError as exc:
        audit_service.log_event(
            action="TOOL_FAILURE",
            session_id=session.id,
            buyer_clerk_user_id=buyer_id,
            metadata={"tool": "get_product_details", "error": str(exc), "context": "select"},
        )
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

    # Supersede any prior active selection for this session
    SelectedProduct.query.filter_by(
        session_id=session.id, status=SelectionStatus.SELECTED
    ).update({"status": SelectionStatus.SUPERSEDED})

    price = variant.get("price") or {}
    selection = SelectedProduct(
        session_id=session.id,
        buyer_clerk_user_id=buyer_id,
        product_id=product["product_id"],
        variant_id=variant["variant_id"],
        product_name_snapshot=product["name"],
        variant_name_snapshot=variant["name"],
        merchant_name_snapshot=(product.get("merchant") or {}).get("name"),
        price_amount_snapshot=price.get("amount", 0),
        currency_snapshot=price.get("currency", "INR"),
        status=SelectionStatus.SELECTED,
    )
    db.session.add(selection)
    db.session.commit()

    audit_service.log_event(
        action="PRODUCT_SELECTED",
        resource_id=selection.id,
        session_id=session.id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "product_id": str(product["product_id"]),
            "variant_id": str(variant["variant_id"]),
            "price": price,
        },
    )
    return selection


def get_active_selection(buyer_id: str, session_id: str):
    session = chat_service.get_session_for_buyer(buyer_id, session_id)
    return (
        SelectedProduct.query.filter_by(
            session_id=session.id, status=SelectionStatus.SELECTED
        )
        .order_by(SelectedProduct.created_at.desc())
        .first()
    )
