from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import InventoryMovement, Product, ProductImage, ProductVariant, Store
from app.models.enums import ProductStatus
from app.services import audit_service
from app.services.category_service import resolve_categories
from app.services.merchant_service import assert_owns_merchant
from app.services.store_service import get_store_or_404, list_stores_for_user
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.slugify import unique_slug

# Eager-load the relations to_dict() traverses so listing/reading products
# doesn't fall into an N+1 query pattern (one extra round trip per relation,
# per product, which is especially costly against a remote/serverless DB).
_PRODUCT_EAGER_OPTIONS = (
    selectinload(Product.variants),
    selectinload(Product.images),
    selectinload(Product.categories),
    selectinload(Product.store).selectinload(Store.merchant),
)


def _slug_exists_in_store(store_id):
    def check(candidate):
        return (
            Product.query.filter_by(store_id=store_id, slug=candidate).first()
            is not None
        )

    return check


def _validate_variant_payload(variant_payload):
    if not variant_payload.get("sku"):
        raise ValidationError("Variant SKU is required")
    if not variant_payload.get("name"):
        raise ValidationError("Variant name is required")
    price = variant_payload.get("price")
    if price is None or price < 0:
        raise ValidationError("Variant price must be >= 0")
    stock = variant_payload.get("stock_quantity", 0)
    if stock is not None and stock < 0:
        raise ValidationError("Stock quantity must be >= 0")
    existing = ProductVariant.query.filter_by(sku=variant_payload["sku"]).first()
    if existing:
        raise ValidationError(f"SKU '{variant_payload['sku']}' already exists")


def get_product_or_404(product_id):
    product = Product.query.options(*_PRODUCT_EAGER_OPTIONS).get(product_id)
    if not product:
        raise NotFoundError("Product not found", code="PRODUCT_NOT_FOUND")
    return product


def get_product_for_user(user, product_id):
    product = get_product_or_404(product_id)
    assert_owns_merchant(user, product.store.merchant)
    return product


def create_product(user, store_id, payload):
    store = get_store_or_404(store_id)
    assert_owns_merchant(user, store.merchant)

    name = payload.get("name")
    if not name:
        raise ValidationError("Product name is required")

    slug = unique_slug(payload.get("slug") or name, _slug_exists_in_store(store.id))

    product = Product(
        store_id=store.id,
        name=name,
        slug=slug,
        short_description=payload.get("short_description"),
        description=payload.get("description"),
        brand=payload.get("brand"),
        status=ProductStatus(payload.get("status", ProductStatus.DRAFT.value)),
        is_agent_searchable=payload.get("is_agent_searchable", True),
    )

    category_ids = payload.get("category_ids") or []
    product.categories = resolve_categories(category_ids)

    db.session.add(product)
    db.session.flush()

    for variant_payload in payload.get("variants", []):
        _validate_variant_payload(variant_payload)
        variant = ProductVariant(
            product_id=product.id,
            sku=variant_payload["sku"],
            name=variant_payload["name"],
            price=variant_payload["price"],
            currency=variant_payload.get("currency", store.currency),
            compare_at_price=variant_payload.get("compare_at_price"),
            stock_quantity=variant_payload.get("stock_quantity", 0),
        )
        db.session.add(variant)

    for idx, image_payload in enumerate(payload.get("images", [])):
        image = ProductImage(
            product_id=product.id,
            image_url=image_payload["image_url"],
            cloudinary_public_id=image_payload.get("cloudinary_public_id"),
            alt_text=image_payload.get("alt_text"),
            position=image_payload.get("position", idx),
            is_primary=image_payload.get("is_primary", idx == 0),
        )
        db.session.add(image)

    db.session.commit()

    audit_service.log_event(
        actor_type="USER",
        actor_id=user.id,
        merchant_id=store.merchant_id,
        resource_type="PRODUCT",
        resource_id=product.id,
        action="PRODUCT_CREATED",
        metadata={"name": product.name},
    )
    return product


def list_products_for_user(user, filters, limit, offset):
    stores = list_stores_for_user(user)
    store_ids = [s.id for s in stores]
    if not store_ids:
        return [], 0

    query = Product.query.filter(Product.store_id.in_(store_ids))

    if filters.get("store_id"):
        query = query.filter(Product.store_id == filters["store_id"])
    if filters.get("status"):
        query = query.filter(Product.status == ProductStatus(filters["status"]))
    if filters.get("q"):
        like = f"%{filters['q']}%"
        query = query.filter(Product.name.ilike(like))

    total = query.count()
    products = (
        query.options(*_PRODUCT_EAGER_OPTIONS)
        .order_by(Product.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return products, total


def get_product_stats_for_user(user):
    """Aggregate product/inventory counts via SQL instead of loading full
    product rows — used by the dashboard overview, which only needs totals.
    """
    stores = list_stores_for_user(user)
    store_ids = [s.id for s in stores]
    if not store_ids:
        return {
            "total_products": 0,
            "active_products": 0,
            "out_of_stock_products": 0,
            "total_inventory": 0,
        }

    total_products = Product.query.filter(Product.store_id.in_(store_ids)).count()
    active_products = Product.query.filter(
        Product.store_id.in_(store_ids), Product.status == ProductStatus.ACTIVE
    ).count()

    stock_per_product = (
        db.session.query(
            Product.id.label("product_id"),
            func.coalesce(func.sum(ProductVariant.stock_quantity), 0).label("stock"),
        )
        .outerjoin(ProductVariant, ProductVariant.product_id == Product.id)
        .filter(Product.store_id.in_(store_ids))
        .group_by(Product.id)
        .subquery()
    )
    total_inventory = db.session.query(
        func.coalesce(func.sum(stock_per_product.c.stock), 0)
    ).scalar()
    out_of_stock_products = (
        db.session.query(func.count())
        .select_from(stock_per_product)
        .filter(stock_per_product.c.stock == 0)
        .scalar()
    )

    return {
        "total_products": total_products,
        "active_products": active_products,
        "out_of_stock_products": out_of_stock_products,
        "total_inventory": int(total_inventory or 0),
    }


def update_product(user, product_id, payload):
    product = get_product_for_user(user, product_id)

    for field in [
        "name",
        "short_description",
        "description",
        "brand",
        "is_agent_searchable",
    ]:
        if field in payload and payload[field] is not None:
            setattr(product, field, payload[field])

    if payload.get("status"):
        product.status = ProductStatus(payload["status"])

    if payload.get("slug") and payload["slug"] != product.slug:
        product.slug = unique_slug(
            payload["slug"], _slug_exists_in_store(product.store_id)
        )

    if "category_ids" in payload:
        product.categories = resolve_categories(payload["category_ids"])

    db.session.commit()

    audit_service.log_event(
        actor_type="USER",
        actor_id=user.id,
        merchant_id=product.store.merchant_id,
        resource_type="PRODUCT",
        resource_id=product.id,
        action="PRODUCT_UPDATED",
        metadata=payload,
    )
    return product


def delete_product(user, product_id):
    product = get_product_for_user(user, product_id)
    merchant_id = product.store.merchant_id
    db.session.delete(product)
    db.session.commit()

    audit_service.log_event(
        actor_type="USER",
        actor_id=user.id,
        merchant_id=merchant_id,
        resource_type="PRODUCT",
        resource_id=product_id,
        action="PRODUCT_DELETED",
    )


def set_product_status(user, product_id, status: ProductStatus, action_name: str):
    product = get_product_for_user(user, product_id)
    product.status = status
    db.session.commit()

    audit_service.log_event(
        actor_type="USER",
        actor_id=user.id,
        merchant_id=product.store.merchant_id,
        resource_type="PRODUCT",
        resource_id=product.id,
        action=action_name,
    )
    return product


def archive_product(user, product_id):
    return set_product_status(
        user, product_id, ProductStatus.ARCHIVED, "PRODUCT_ARCHIVED"
    )


def activate_product(user, product_id):
    return set_product_status(
        user, product_id, ProductStatus.ACTIVE, "PRODUCT_ACTIVATED"
    )


def deactivate_product(user, product_id):
    return set_product_status(
        user, product_id, ProductStatus.INACTIVE, "PRODUCT_DEACTIVATED"
    )


# ---- Variants ----


def add_variant(user, product_id, payload):
    product = get_product_for_user(user, product_id)
    _validate_variant_payload(payload)

    variant = ProductVariant(
        product_id=product.id,
        sku=payload["sku"],
        name=payload["name"],
        price=payload["price"],
        currency=payload.get("currency", product.store.currency),
        compare_at_price=payload.get("compare_at_price"),
        stock_quantity=payload.get("stock_quantity", 0),
    )
    db.session.add(variant)
    db.session.commit()
    return variant


def get_variant_for_user(user, variant_id):
    variant = ProductVariant.query.get(variant_id)
    if not variant:
        raise NotFoundError("Variant not found", code="VARIANT_NOT_FOUND")
    assert_owns_merchant(user, variant.product.store.merchant)
    return variant


def update_variant(user, variant_id, payload):
    variant = get_variant_for_user(user, variant_id)

    if "price" in payload and payload["price"] is not None:
        if payload["price"] < 0:
            raise ValidationError("Price must be >= 0")
        variant.price = payload["price"]

    for field in ["name", "compare_at_price", "currency"]:
        if field in payload and payload[field] is not None:
            setattr(variant, field, payload[field])

    if payload.get("status"):
        from app.models.enums import VariantStatus

        variant.status = VariantStatus(payload["status"])

    if "stock_quantity" in payload and payload["stock_quantity"] is not None:
        adjust_stock(
            user,
            variant.id,
            payload["stock_quantity"] - variant.stock_quantity,
            reason="MANUAL_ADJUSTMENT",
        )

    db.session.commit()
    return variant


def delete_variant(user, variant_id):
    variant = get_variant_for_user(user, variant_id)
    db.session.delete(variant)
    db.session.commit()


def adjust_stock_internal(
    variant,
    quantity_change,
    reason="MANUAL_ADJUSTMENT",
    reference_type=None,
    reference_id=None,
    commit=True,
):
    """Applies a stock delta to an already-resolved variant.

    Split out from `adjust_stock` because that one resolves the variant
    through `get_variant_for_user`, which requires a merchant Clerk user —
    unavailable on the agent API-key path, where an incoming paid order must
    still decrement inventory. `reference_type`/`reference_id` let the
    movement point back at the order that caused it (the columns existed but
    had never been populated).
    """
    new_quantity = variant.stock_quantity + quantity_change
    if new_quantity < 0:
        raise ValidationError("Stock quantity cannot go below zero")

    variant.stock_quantity = new_quantity
    movement = InventoryMovement(
        product_variant_id=variant.id,
        quantity_change=quantity_change,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.session.add(movement)
    if commit:
        db.session.commit()
    return variant


def adjust_stock(user, variant_id, quantity_change, reason="MANUAL_ADJUSTMENT"):
    variant = get_variant_for_user(user, variant_id)
    return adjust_stock_internal(variant, quantity_change, reason)


# ---- Images ----


def add_image(user, product_id, payload):
    product = get_product_for_user(user, product_id)

    is_primary = payload.get("is_primary", False)
    if is_primary:
        for image in product.images:
            image.is_primary = False

    max_position = max([img.position for img in product.images], default=-1)

    image = ProductImage(
        product_id=product.id,
        image_url=payload["image_url"],
        cloudinary_public_id=payload.get("cloudinary_public_id"),
        alt_text=payload.get("alt_text"),
        position=payload.get("position", max_position + 1),
        is_primary=is_primary or len(product.images) == 0,
    )
    db.session.add(image)
    db.session.commit()
    return image


def delete_image(user, product_id, image_id):
    product = get_product_for_user(user, product_id)
    image = next((img for img in product.images if str(img.id) == str(image_id)), None)
    if not image:
        raise NotFoundError("Image not found", code="IMAGE_NOT_FOUND")

    was_primary = image.is_primary
    db.session.delete(image)
    db.session.flush()

    if was_primary:
        remaining = (
            ProductImage.query.filter_by(product_id=product.id)
            .order_by(ProductImage.position)
            .first()
        )
        if remaining:
            remaining.is_primary = True

    db.session.commit()


def reorder_images(user, product_id, ordered_image_ids):
    product = get_product_for_user(user, product_id)
    images_by_id = {str(img.id): img for img in product.images}

    for position, image_id in enumerate(ordered_image_ids):
        image = images_by_id.get(str(image_id))
        if image:
            image.position = position

    db.session.commit()
    return product.images


def set_primary_image(user, product_id, image_id):
    product = get_product_for_user(user, product_id)
    found = False
    for image in product.images:
        image.is_primary = str(image.id) == str(image_id)
        found = found or image.is_primary

    if not found:
        raise NotFoundError("Image not found", code="IMAGE_NOT_FOUND")

    db.session.commit()
    return product.images
