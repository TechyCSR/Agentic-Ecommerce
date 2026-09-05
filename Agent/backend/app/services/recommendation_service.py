"""What to suggest alongside what the buyer is already looking at.

Two jobs, and they are different:

* **Complements.** Things that go *with* the anchor. The previous version
  searched the anchor's own category, which returns competitors — offering
  a second phone to someone holding a phone is not a cross-sell, it is a
  reason to start the decision again.
* **Memory.** What this buyer has bought, carted and searched before, so
  the agent can pick up where they left off instead of meeting them cold
  every session.

Everything returned here comes from a live catalog lookup. Nothing is
invented, and a suggestion the catalog can't currently supply is simply not
made.
"""

from app.extensions import db
from app.models import AuditEvent, Order, SelectedProduct
from app.models.enums import OrderStatus
from app.services import catalog_client

# What genuinely goes with what, in this catalog's own vocabulary. Ordered
# by how naturally the pairing reads to a shopper, best first.
COMPLEMENTS: dict[str, list[str]] = {
    # Electronics
    "Smartphones": ["Mobile Accessories", "Audio", "Wearables"],
    "Laptops": ["Mice", "Keyboards", "Storage", "Bags", "Monitors"],
    "Tablets": ["Mobile Accessories", "Audio", "Computer Accessories"],
    "Monitors": ["Keyboards", "Mice", "Computer Accessories"],
    "Keyboards": ["Mice", "Monitors", "Computer Accessories"],
    "Mice": ["Keyboards", "Monitors", "Computer Accessories"],
    "Audio": ["Mobile Accessories", "Computer Accessories", "Storage"],
    "Wearables": ["Mobile Accessories", "Audio", "Sports Equipment"],
    "Storage": ["Computer Accessories", "Bags"],
    "Computer Accessories": ["Mice", "Keyboards", "Storage"],
    "Mobile Accessories": ["Audio", "Wearables", "Computer Accessories"],
    # Fashion
    "Men's Clothing": ["Footwear", "Watches", "Eyewear", "Bags"],
    "Women's Clothing": ["Footwear", "Bags", "Jewellery", "Watches"],
    "Footwear": ["Sports Equipment", "Bags", "Men's Clothing"],
    "Watches": ["Eyewear", "Bags", "Jewellery"],
    "Bags": ["Eyewear", "Watches", "Storage"],
    "Jewellery": ["Watches", "Women's Clothing"],
    "Eyewear": ["Watches", "Bags"],
    # Home
    "Kitchen": ["Packaged Food", "Condiments", "Home Decor"],
    "Furniture": ["Home Decor", "Kitchen"],
    "Home Decor": ["Furniture", "Kitchen"],
    # Grocery — the strongest pairings in the whole catalog
    "Snacks": ["Beverages", "Dairy", "Breakfast"],
    "Beverages": ["Snacks", "Breakfast"],
    "Breakfast": ["Dairy", "Beverages", "Condiments"],
    "Dairy": ["Breakfast", "Snacks"],
    "Condiments": ["Packaged Food", "Kitchen", "Snacks"],
    "Packaged Food": ["Condiments", "Kitchen", "Snacks"],
    # Personal care
    "Hair Care": ["Bath & Body", "Skin Care"],
    "Skin Care": ["Bath & Body", "Makeup", "Fragrances"],
    "Bath & Body": ["Hair Care", "Skin Care", "Oral Care"],
    "Makeup": ["Skin Care", "Fragrances"],
    "Fragrances": ["Bath & Body", "Makeup"],
    "Oral Care": ["Bath & Body"],
    "Sports Equipment": ["Footwear", "Wearables"],
}

# An add-on that costs as much as the thing it accompanies isn't an add-on.
# Anything up to about half the anchor still reads as "and this too".
ACCESSORY_PRICE_RATIO = 0.55
# When nothing fits that, the shelf is still allowed — but within reason. A
# ₹15,000 monitor alongside a ₹799 keyboard is a real pairing and a silly
# suggestion. The floor keeps cheap anchors from excluding everything.
FALLBACK_RATIO = 3
FALLBACK_FLOOR = 200_000  # ₹2,000


def complements_for(anchor: dict, limit: int = 3, max_price: int | None = None) -> list[dict]:
    """Real, in-stock products that go with the anchor.

    Walks the complementary shelves in order and stops once it has enough,
    so a laptop leads with a mouse rather than whatever happened to sort
    first across everything.
    """
    category = anchor.get("category")
    shelves = COMPLEMENTS.get(category or "", [])
    if not shelves:
        return []

    anchor_price = _anchor_price(anchor)
    budget = max_price
    if budget is None and anchor_price:
        budget = int(anchor_price * ACCESSORY_PRICE_RATIO)

    found: list[dict] = []
    seen = {anchor.get("product_id")}

    # Second pass is looser but not unbounded.
    fallback = (
        max(anchor_price * FALLBACK_RATIO, FALLBACK_FLOOR) if anchor_price else None
    )

    for shelf in shelves:
        if len(found) >= limit:
            break
        budgets = [budget, fallback] if budget else [fallback]
        for attempt_budget in dict.fromkeys(b for b in budgets if b is not None) or [None]:
            try:
                products, _ = catalog_client.search_catalog(
                    category=shelf,
                    max_price=attempt_budget,
                    in_stock=True,
                    limit=limit * 2,
                )
            except catalog_client.CatalogError:
                products = []
            fresh = [p for p in products if p.get("product_id") not in seen]
            if fresh:
                # One per shelf, so three suggestions read as three ideas
                # rather than three of the same thing.
                pick = fresh[0]
                seen.add(pick.get("product_id"))
                found.append(pick)
                break
    return found[:limit]


def _anchor_price(anchor: dict) -> int | None:
    price = anchor.get("price")
    if isinstance(price, dict):
        return price.get("amount")
    if isinstance(price, int):
        return price
    variants = anchor.get("variants") or []
    if variants:
        return (variants[0].get("price") or {}).get("amount")
    return None


def buyer_memory(buyer_id: str) -> dict:
    """What this buyer has actually done before, across every session.

    Read from real records — confirmed orders, cart adds and the searches
    they ran — rather than anything the model claimed to remember. Used to
    ground the agent, never shown back verbatim.
    """
    bought = _purchased_names(buyer_id)
    shelves = _searched_categories(buyer_id)
    brands = _searched_brands(buyer_id)
    spend = _typical_spend(buyer_id)

    return {
        "purchased": bought,
        "categories": shelves,
        "brands": brands,
        "typical_spend": spend,
        "returning": bool(bought or shelves),
    }


def _purchased_names(buyer_id: str, limit: int = 6) -> list[str]:
    orders = (
        Order.query.filter(
            Order.buyer_clerk_user_id == buyer_id,
            Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.CANCELLED]),
        )
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )
    names: list[str] = []
    for order in orders:
        for item in order.items or []:
            name = item.get("product_name")
            if name and name not in names:
                names.append(name)
    return names[:limit]


def _recent_search_params(buyer_id: str, limit: int = 40) -> list[dict]:
    events = (
        AuditEvent.query.filter(
            AuditEvent.action == "PRODUCT_SEARCH",
            AuditEvent.metadata_json["buyer_clerk_user_id"].astext == buyer_id,
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [(e.metadata_json or {}).get("params") or {} for e in events]


def _searched_categories(buyer_id: str, limit: int = 5) -> list[str]:
    ordered: list[str] = []
    for params in _recent_search_params(buyer_id):
        category = params.get("category")
        if category and category not in ordered:
            ordered.append(category)
    return ordered[:limit]


def _searched_brands(buyer_id: str, limit: int = 4) -> list[str]:
    ordered: list[str] = []
    for params in _recent_search_params(buyer_id):
        brand = params.get("brand")
        if brand and brand not in ordered:
            ordered.append(brand)
    return ordered[:limit]


def _typical_spend(buyer_id: str) -> int | None:
    """Median-ish order value, so the agent doesn't open with a ₹1.2L laptop
    for someone who has only ever bought biscuits."""
    amounts = [
        o.amount_total
        for o in Order.query.filter(
            Order.buyer_clerk_user_id == buyer_id,
            Order.status == OrderStatus.CONFIRMED,
        ).all()
        if o.amount_total
    ]
    if not amounts:
        return None
    amounts.sort()
    return amounts[len(amounts) // 2]


def cart_categories(session_id) -> list[str]:
    """Shelves already represented in this session's cart, so a suggestion
    doesn't offer more of what they have."""
    from app.models.enums import SelectionStatus

    rows = (
        db.session.query(SelectedProduct.product_name_snapshot)
        .filter_by(session_id=session_id, status=SelectionStatus.SELECTED)
        .all()
    )
    return [r[0] for r in rows if r[0]]
