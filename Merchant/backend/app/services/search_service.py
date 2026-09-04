from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from app.models import Category, Product, ProductVariant, Store
from app.models.enums import ProductStatus


def _matching_category_ids(term: str) -> set:
    """Category ids a shopper's word should reach.

    Three things a plain `name ILIKE %term%` got wrong:

    * **Reverse containment.** A buyer (or the agent) says "Wireless Mouse";
      the category is "Mouse". `%Wireless Mouse%` never matches "Mouse", so
      a real product looked out of stock.
    * **Parent categories.** "Fashion" is a parent of Men/Women/Kids and has
      no products of its own, so filtering by it returned nothing.
    * **Singular/plural.** "laptop" vs the "Laptops" category.

    The taxonomy is small (tens of rows), so this matches in Python where the
    rules stay readable, rather than in increasingly baroque SQL.
    """
    term = (term or "").strip().lower()
    if not term:
        return set()

    categories = Category.query.all()
    by_id = {c.id: c for c in categories}

    def alike(name: str) -> bool:
        name = (name or "").lower()
        if not name:
            return False
        if name in term or term in name:
            return True
        # Tolerate simple plurals in either direction.
        return name.rstrip("s") == term.rstrip("s")

    matched = {c.id for c in categories if alike(c.name) or alike(c.slug)}

    # A parent stands for everything beneath it.
    frontier = list(matched)
    while frontier:
        children = [c.id for c in categories if c.parent_id in frontier and c.id not in matched]
        matched.update(children)
        frontier = children

    return {cid for cid in matched if cid in by_id}


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
        category_ids = _matching_category_ids(filters["category"])
        if not category_ids:
            # An unknown category shouldn't silently return the whole catalog.
            return [], 0
        query = query.filter(
            Product.categories.any(Category.id.in_(category_ids))
        )

    if filters.get("q"):
        term = f"%{filters['q']}%"
        conditions = [
            Product.name.ilike(term),
            Product.description.ilike(term),
            Product.short_description.ilike(term),
            Product.brand.ilike(term),
        ]
        # Free text should also reach a product through its category, so
        # "laptop" finds the AeroBook even though the word never appears in
        # its name or description.
        q_category_ids = _matching_category_ids(filters["q"])
        if q_category_ids:
            conditions.append(Product.categories.any(Category.id.in_(q_category_ids)))
        query = query.filter(or_(*conditions))

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
        query.options(
            selectinload(Product.variants),
            selectinload(Product.images),
            selectinload(Product.categories),
            selectinload(Product.store).selectinload(Store.merchant),
        )
        .order_by(Product.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return products, total
