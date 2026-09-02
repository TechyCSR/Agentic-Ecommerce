"""Sole gateway to product data — every call goes through Merchant Phase 1's
existing agent-readable catalog API (central API key, catalog:read +
product:read scopes). This service never touches product tables directly.
"""

import requests
from flask import current_app


class CatalogError(Exception):
    """Raised when the Merchant agent API can't be reached or errors."""


def _headers():
    api_key = current_app.config.get("MERCHANT_AGENT_API_KEY")
    return {"Authorization": f"Bearer {api_key}"}


def _base_url():
    return current_app.config.get("MERCHANT_AGENT_API_URL", "").rstrip("/")


def search_catalog(
    *,
    q=None,
    category=None,
    brand=None,
    min_price=None,
    max_price=None,
    in_stock=None,
    limit=10,
    offset=0,
):
    params = {"limit": limit, "offset": offset}
    if q:
        params["q"] = q
    if category:
        params["category"] = category
    if brand:
        params["brand"] = brand
    if min_price is not None:
        params["min_price"] = min_price
    if max_price is not None:
        params["max_price"] = max_price
    if in_stock is not None:
        params["in_stock"] = "true" if in_stock else "false"

    try:
        resp = requests.get(
            f"{_base_url()}/api/v1/agent/catalog/search",
            headers=_headers(),
            params=params,
            timeout=10,
        )
    except requests.RequestException as exc:
        raise CatalogError(f"Catalog search request failed: {exc}") from exc

    if resp.status_code != 200:
        raise CatalogError(f"Catalog search failed with status {resp.status_code}")

    body = resp.json()
    if not body.get("success"):
        raise CatalogError(body.get("error", {}).get("message", "Catalog search failed"))

    return body["data"], body.get("meta", {})


def get_product(product_id: str):
    """Returns the agent-readable product dict, or None if not found /
    not active / not agent-searchable (matching the Merchant API's 404)."""
    try:
        resp = requests.get(
            f"{_base_url()}/api/v1/agent/products/{product_id}",
            headers=_headers(),
            timeout=10,
        )
    except requests.RequestException as exc:
        raise CatalogError(f"Product lookup request failed: {exc}") from exc

    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise CatalogError(f"Product lookup failed with status {resp.status_code}")

    body = resp.json()
    if not body.get("success"):
        raise CatalogError(body.get("error", {}).get("message", "Product lookup failed"))

    return body["data"]
