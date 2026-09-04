import re

from sqlalchemy import and_, case, or_
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Category, Product, ProductVariant, Store
from app.models.category import product_categories
from app.models.enums import ProductStatus


def _singular(word: str) -> str:
    """Crude but predictable: enough for "laptop" vs "Laptops"."""
    if len(word) > 3 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("es") and not word.endswith("ses"):
        return word[:-2]
    if len(word) > 2 and word.endswith("s"):
        return word[:-1]
    return word


def _words(text: str) -> set:
    """Meaningful whole words, singularised. Drops one-letter fragments so
    the possessive in "Men's Clothing" doesn't become a token of its own."""
    return {
        _singular(w) for w in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(w) > 1
    }


def _singular(word: str) -> str:
    """Crude but predictable: enough for "laptop" vs the "Laptops" category."""
    if len(word) > 3 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("es") and not word.endswith("ses"):
        return word[:-2]
    if len(word) > 2 and word.endswith("s"):
        return word[:-1]
    return word


def _words(text: str) -> set:
    """Whole words, singularised. One-letter fragments are dropped so the
    possessive in "Men's Clothing" doesn't become a token of its own."""
    return {
        _singular(w) for w in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(w) > 1
    }


def _matching_category_ids(term: str) -> set:
    """Category ids a named category should reach.

    This resolves a category the caller *names*; it does not guess one from
    prose. Matching is on whole words, because plain substring containment
    silently rotted as the catalog grew: "car" matched Hair **Care**, Skin
    **Care** and Oral **Care**, so a question about cars returned shampoo.
    "art" matched Sm**art**phones and "men" matched Wo**men**.

    Two directions are allowed, both word-exact:
    * the named term contains the category ("wireless mouse" -> Mouse)
    * the category contains the named term ("men" -> Men's Clothing)

    A parent stands for everything beneath it, so "Electronics" reaches every
    leaf under it even though it holds no products of its own.
    """
    term_words = _words(term or "")
    if not term_words:
        return set()

    categories = Category.query.all()

    def alike(name: str) -> bool:
        name_words = _words(name or "")
        if not name_words:
            return False
        return name_words <= term_words or term_words <= name_words

    matched = {
        c.id for c in categories
        if alike(c.name) or alike((c.slug or "").replace("-", " "))
    }

    frontier = list(matched)
    while frontier:
        children = [c.id for c in categories if c.parent_id in frontier and c.id not in matched]
        matched.update(children)
        frontier = children

    return matched


def category_exists(term: str) -> bool:
    """Whether a named category resolves to anything at all — so a caller can
    tell "we don't stock that" apart from "nothing matched your filters"."""
    return bool(_matching_category_ids(term))


def catalog_facets(limit_brands: int = 60) -> dict:
    """What the catalog actually contains: categories with counts, and the
    brands worth naming.

    This exists so the agent can ground a query in real values instead of
    inventing a category and getting an empty result that reads to the buyer
    as "we don't sell that".
    """
    from sqlalchemy import func

    rows = (
        db.session.query(Category.name, func.count(Product.id))
        .select_from(Category)
        .join(product_categories, product_categories.c.category_id == Category.id)
        .join(Product, Product.id == product_categories.c.product_id)
        .filter(Product.status == ProductStatus.ACTIVE, Product.is_agent_searchable.is_(True))
        .group_by(Category.name)
        .order_by(func.count(Product.id).desc())
        .all()
    )
    brands = (
        db.session.query(Product.brand, func.count(Product.id))
        .filter(
            Product.status == ProductStatus.ACTIVE,
            Product.is_agent_searchable.is_(True),
            Product.brand.isnot(None),
        )
        .group_by(Product.brand)
        .order_by(func.count(Product.id).desc())
        .limit(limit_brands)
        .all()
    )
    return {
        "categories": [{"name": n, "product_count": c} for n, c in rows],
        "brands": [{"name": n, "product_count": c} for n, c in brands],
    }


# Words a shopper types that carry no meaning for matching. Requiring every
# word to match is right ("running shoes" shouldn't return every shoe), but
# only for words that actually describe the product.
_STOPWORDS = {
    # articles and filler
    "a", "an", "the", "some", "any", "all", "my", "me", "you", "your",
    "for", "with", "and", "or", "of", "in", "on", "at", "to", "from",
    "is", "are", "it", "that", "this", "please", "hi", "hello",
    # shopping filler that describes no product
    "new", "best", "good", "nice", "cheap", "cheapest", "top", "great",
    "show", "find", "need", "want", "looking", "look", "buy", "get",
    "suggest", "recommend", "give", "have", "having", "something",
    "anything", "under", "below", "over", "above", "between", "around",
    # words that appear in nearly every description
    "product", "products", "item", "items", "thing", "things", "stuff",
    "available", "option", "options", "range", "quality",
}


def _term_condition(term: str):
    """Everywhere one word may legitimately match a product."""
    like = f"%{term}%"
    conditions = [
        Product.name.ilike(like),
        Product.description.ilike(like),
        Product.short_description.ilike(like),
        Product.brand.ilike(like),
    ]
    # Free text should also reach a product through its category, so "laptop"
    # finds a MacBook even though the word appears in neither name nor copy.
    category_ids = _matching_category_ids(term)
    if category_ids:
        conditions.append(Product.categories.any(Category.id.in_(category_ids)))
    return or_(*conditions)


def _query_terms(raw: str) -> list[str]:
    """The words worth matching on.

    Bare numbers are dropped: "laptop under 50000" is a price filter the
    caller should pass as max_price, and matching "50000" as text finds
    nothing while making the whole query fail.
    """
    words = [w for w in re.split(r"[^\w&\']+", raw.lower()) if len(w) > 1]
    meaningful = [w for w in words if w not in _STOPWORDS and not w.isdigit()]
    return meaningful or [w for w in words if not w.isdigit()] or [raw]


def _relevance(terms: list[str]):
    """Ranks a name match above a brand match above body copy.

    Without this, results come back in creation order, so "mobile phone"
    led with a selfie stick — it mentions both words — while the actual
    phones sat further down.
    """
    score = None
    for term in terms:
        like = f"%{term}%"
        part = (
            case((Product.name.ilike(like), 8), else_=0)
            + case((Product.brand.ilike(like), 4), else_=0)
            + case((Product.short_description.ilike(like), 2), else_=0)
            + case((Product.description.ilike(like), 1), else_=0)
        )
        score = part if score is None else score + part
    return score


def _free_text_filter(terms: list[str], require_all: bool):
    """Every meaningful word, rather than the phrase as one string.

    The whole query used to go into a single ILIKE, so "mobile phone" found
    nothing while "phone" found forty-seven — the two words never appear
    adjacent in any listing.
    """
    conditions = [_term_condition(t) for t in terms]
    return and_(*conditions) if require_all else or_(*conditions)


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
        # A named brand is a constraint, not a hint. Substring matching made
        # "Apple" reach an apple-scented shampoo; anchoring to the start of
        # the brand keeps "Samsung" reaching "Samsung Electronics" without
        # reaching everything that merely mentions the word.
        brand = filters["brand"].strip()
        query = query.filter(
            or_(Product.brand.ilike(brand), Product.brand.ilike(f"{brand} %"))
        )

    if filters.get("category"):
        category_ids = _matching_category_ids(filters["category"])
        if not category_ids:
            # An unknown category shouldn't silently return the whole catalog.
            return [], 0
        query = query.filter(
            Product.categories.any(Category.id.in_(category_ids))
        )

    terms = _query_terms(filters["q"]) if filters.get("q") else []
    # Kept so the any-word retry below can rebuild from the same filters.
    base = query
    if terms:
        query = query.filter(_free_text_filter(terms, require_all=True))

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

    # A conversational query often carries a word no listing uses ("gaming
    # keyboard"). Requiring every word is the right first attempt, but only
    # widen when the caller gave no structural constraint — if they asked for
    # a category or a brand, honour it rather than quietly returning things
    # outside it.
    structural = any(filters.get(k) for k in ("category", "brand"))
    if total == 0 and len(terms) > 1 and not structural:
        query = base.filter(_free_text_filter(terms, require_all=False))
        total = query.distinct().count()

    query = query.options(
        selectinload(Product.variants),
        selectinload(Product.images),
        selectinload(Product.categories),
        selectinload(Product.store).selectinload(Store.merchant),
    )

    if not terms:
        return (
            query.order_by(Product.created_at.desc()).limit(limit).offset(offset).all(),
            total,
        )

    # The base query is DISTINCT, and Postgres requires every ORDER BY
    # expression to appear in the select list under DISTINCT — so the score
    # is selected alongside the product and dropped again here.
    score = _relevance(terms).label("relevance")
    rows = (
        query.add_columns(score)
        .order_by(score.desc(), Product.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [row[0] for row in rows], total
