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
            "categories": categories,
            "starter_categories": [c["name"] for c in starters[:12]],
            "brands": [b["name"] for b in brands[:24]],
            # Categories overlap (a product sits in a leaf and its parent), so
            # the totals are reported from the merchant's own counts rather
            # than summed here, which would double-count.
            "product_count": _product_count(),
            "category_count": len(categories),
            "brand_count": len(brands),
        }
    )


def _product_count() -> int:
    """How many products the agent can actually see.

    Taken from a search's own total rather than by summing category counts,
    which would double-count everything sitting in both a leaf and its
    parent.
    """
    try:
        _, meta = catalog_client.search_catalog(limit=1)
        return int(meta.get("total") or 0)
    except Exception:  # noqa: BLE001 — the copy reads fine without a number
        return 0
