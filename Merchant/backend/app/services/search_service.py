from sqlalchemy import or_

from app.models import Category, Product, ProductVariant, Store
from app.models.enums import ProductStatus


def search_products(filters, limit, offset, require_agent_searchable=False):
    query = (
        Product.query.join(Store, Product.store_id == Store.id)
        .filter(Product.status == ProductStatus.ACTIVE)
        .distinct()
    )

    if require_agent_searchable:
        query = query.filter(Product.is_agent_searchable.is_(True))

    if filters.get("merchant_id"):
        query = query.filter(Store.merchant_id == filters["merchant_id"])

    if filters.get("store_id"):
        query = query.filter(Product.store_id == filters["store_id"])

    if filters.get("brand"):
        query = query.filter(Product.brand.ilike(f"%{filters['brand']}%"))

    if filters.get("category"):
        query = query.join(Product.categories).filter(
            or_(
                Category.name.ilike(f"%{filters['category']}%"),
                Category.slug.ilike(f"%{filters['category']}%"),
            )
        )

    if filters.get("q"):
        term = f"%{filters['q']}%"
        query = query.filter(
            or_(
                Product.name.ilike(term),
                Product.description.ilike(term),
                Product.short_description.ilike(term),
                Product.brand.ilike(term),
            )
        )

    needs_variant_join = any(
        filters.get(key) is not None
        for key in ("min_price", "max_price", "currency", "in_stock")
    )
    if needs_variant_join:
        query = query.join(ProductVariant, ProductVariant.product_id == Product.id)

        if filters.get("min_price") is not None:
            query = query.filter(ProductVariant.price >= filters["min_price"])
        if filters.get("max_price") is not None:
            query = query.filter(ProductVariant.price <= filters["max_price"])
        if filters.get("currency"):
            query = query.filter(ProductVariant.currency == filters["currency"])
        if filters.get("in_stock"):
            query = query.filter(ProductVariant.stock_quantity > 0)

    total = query.distinct().count()
    products = (
        query.order_by(Product.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return products, total
