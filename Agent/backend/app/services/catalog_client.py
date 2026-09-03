"""Sole gateway to the Merchant service — catalog reads and order
registration both go through its agent API with the central API key
(catalog:read + product:read + checkout:create). This service never touches
Merchant's tables directly.
"""

import requests
from flask import current_app


# Merchant search measures 6.5-7.7s in production (the app and its database
# sit in different regions), so 10s left almost no headroom before a
# legitimate query looked like an outage to the buyer.
REQUEST_TIMEOUT = 25


class CatalogError(Exception):
    """Raised when the Merchant agent API can't be reached or errors."""


class MerchantSyncError(Exception):
    """Raised when registering an order with the Merchant service fails.

    Kept distinct from CatalogError because the caller treats it very
    differently: by sync time the buyer has already paid, so this must never
    unwind the order — only be recorded and retried.
    """


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
            timeout=REQUEST_TIMEOUT,
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
            timeout=REQUEST_TIMEOUT,
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


def create_order(payload: dict) -> dict:
    """Registers a paid order with the Merchant service.

    Idempotent on the Merchant side via `agent_order_id`, so a retry after a
    timeout is safe and will not create a duplicate order or decrement stock
    twice.
    """
    try:
        resp = requests.post(
            f"{_base_url()}/api/v1/agent/orders",
            headers={**_headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise MerchantSyncError(f"Order sync request failed: {exc}") from exc

    if resp.status_code not in (200, 201):
        raise MerchantSyncError(
            f"Order sync failed with status {resp.status_code}: {resp.text[:200]}"
        )

    body = resp.json()
    if not body.get("success"):
        raise MerchantSyncError(body.get("error", {}).get("message", "Order sync failed"))

    return body["data"]


def get_merchant_order(agent_order_id: str):
    """Reads fulfillment status back from the Merchant service, so the agent
    can answer "where is my order?". Returns None if it hasn't synced."""
    try:
        resp = requests.get(
            f"{_base_url()}/api/v1/agent/orders/{agent_order_id}",
            headers=_headers(),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise MerchantSyncError(f"Order lookup request failed: {exc}") from exc

    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise MerchantSyncError(f"Order lookup failed with status {resp.status_code}")

    body = resp.json()
    if not body.get("success"):
        return None
    return body["data"]


def cancel_merchant_order(agent_order_id: str, reason: str | None = None) -> dict:
    """Asks the Merchant service to cancel a synced order and restore stock."""
    try:
        resp = requests.post(
            f"{_base_url()}/api/v1/agent/orders/{agent_order_id}/cancel",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"reason": reason},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise MerchantSyncError(f"Cancel request failed: {exc}") from exc

    body = resp.json() if resp.content else {}
    if resp.status_code != 200 or not body.get("success"):
        raise MerchantSyncError(
            (body.get("error") or {}).get("message") or f"Cancel failed ({resp.status_code})"
        )
    return body["data"]


def list_categories() -> list:
    """Category names, so the agent can answer "what do you sell?"."""
    try:
        resp = requests.get(f"{_base_url()}/api/v1/categories", timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        raise CatalogError(f"Category lookup failed: {exc}") from exc
    if resp.status_code != 200:
        raise CatalogError(f"Category lookup failed with status {resp.status_code}")
    body = resp.json()
    return body.get("data") or []
