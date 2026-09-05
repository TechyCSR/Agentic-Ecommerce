"""Public catalog highlights, for the parts of the UI a signed-out visitor sees.

The landing page and the chat's opening screen both need to talk about the
real catalog — how many products there are, which shelves are worth
suggesting — and neither should require a session to do it. Everything here
is aggregate and non-identifying: counts and category names, never a buyer's
data.
"""

from flask import Blueprint

from app.services import catalog_client
from app.utils.responses import success

bp = Blueprint("catalog", __name__, url_prefix="/api/v1/catalog")

# Shelves too generic to make an interesting opening suggestion.
_SKIP_AS_STARTER = {"Electronics", "Fashion", "Grocery", "Home & Kitchen"}

# The shelves the landing page shows off. Chosen because they photograph
# well and are recognisably real, which is the point being made.
_SHOWCASE_CATEGORIES = ["Smartphones", "Laptops", "Audio", "Footwear", "Watches", "Snacks"]


@bp.route("/highlights", methods=["GET"])
def highlights():
    """Categories with live counts, plus totals worth stating on a landing page.

    Degrades to an empty payload rather than an error: the marketing copy
    around it should still render if the merchant service is briefly away.
    """
    try:
        facets = catalog_client.get_facets()
    except Exception:  # noqa: BLE001 — a marketing page must not 500 on this
        return success({"categories": [], "brands": [], "product_count": 0})

    categories = facets.get("categories") or []
    brands = facets.get("brands") or []

    starters = [
        c for c in categories
        if c["name"] not in _SKIP_AS_STARTER and c.get("product_count", 0) >= 5
    ]

    return success(
        {
            "showcase": _showcase(),
            "categories": categories,
            "starter_categories": [c["name"] for c in starters[:12]],
            "brands": [b["name"] for b in brands[:24]],
            # Categories overlap (a product sits in a leaf and its parent), so
            # the totals are reported from the merchant's own counts rather
            # than summed here, which would double-count.
            "category_count": len(categories),
            "brand_count": len(brands),
        }
    )


def _showcase(per_category: int = 1) -> list[dict]:
    """A few real products, for the landing page's shelf.

    Deliberately the live catalog rather than stock imagery: the page claims
    the agent only ever shows real stock, so its own hero should be held to
    that too.
    """
    picked = []
    for category in _SHOWCASE_CATEGORIES:
        try:
            products, _ = catalog_client.search_catalog(
                category=category, in_stock=True, limit=per_category
            )
        except Exception:  # noqa: BLE001 — a missing shelf just means one fewer card
            continue
        for product in products:
            image = next(
                (i["url"] for i in (product.get("images") or []) if i.get("is_primary")),
                None,
            )
            variant = (product.get("variants") or [None])[0]
            if not image or not variant:
                continue
            picked.append(
                {
                    "name": product["name"],
                    "brand": product.get("brand"),
                    "category": product.get("category") or category,
                    "image_url": image,
                    "price": (variant.get("price") or {}).get("amount"),
                    "currency": (variant.get("price") or {}).get("currency") or "INR",
                }
            )
    return picked
