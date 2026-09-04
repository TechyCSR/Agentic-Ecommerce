from flask import Blueprint, g, request

from app.middleware.api_key_auth import require_scopes
from app.models.enums import ApiScope
from app.services import (
    audit_service,
    order_service,
    product_service,
    reservation_service,
    search_service,
)
from app.utils.agent_format import product_to_agent_dict
from app.utils.exceptions import NotFoundError
from app.utils.pagination import build_meta, paginate_params
from app.utils.responses import success
from app.utils.search_filters import parse_search_filters

bp = Blueprint("agent", __name__, url_prefix="/api/v1/agent")


@bp.route("/catalog/search", methods=["GET"])
@require_scopes(ApiScope.CATALOG_READ.value)
def agent_search():
    limit, offset = paginate_params(request.args)
    filters = parse_search_filters(request.args)

    products, total = search_service.search_products(
        filters, limit, offset, require_agent_searchable=True
    )

    # What other buyers are holding mid-checkout, so the agent is never shown
    # stock it can't actually have. One query for the whole page.
    held = reservation_service.held_for_products(
        products, exclude_agent_order_id=request.args.get("for_order")
    )

    audit_service.log_event(
        actor_type="AGENT",
        actor_id=g.api_client.id,
        merchant_id=g.api_client.merchant_id,
        resource_type="CATALOG",
        action="CATALOG_SEARCHED",
        metadata={"filters": filters, "client": g.api_client.name},
    )

    return success(
        [product_to_agent_dict(p, held) for p in products],
        meta=build_meta(total, limit, offset),
    )


@bp.route("/products/<uuid:product_id>", methods=["GET"])
@require_scopes(ApiScope.PRODUCT_READ.value)
def agent_get_product(product_id):
    product = product_service.get_product_or_404(product_id)

    audit_service.log_event(
        actor_type="AGENT",
        actor_id=g.api_client.id,
        merchant_id=g.api_client.merchant_id,
        resource_type="PRODUCT",
        resource_id=product.id,
        action="PRODUCT_VIEWED",
        metadata={"client": g.api_client.name},
    )

    if product.status.value != "ACTIVE" or not product.is_agent_searchable:
        from app.utils.exceptions import NotFoundError

        raise NotFoundError("Product not found", code="PRODUCT_NOT_FOUND")

    held = reservation_service.held_for_products(
        [product], exclude_agent_order_id=request.args.get("for_order")
    )
    return success(product_to_agent_dict(product, held))


@bp.route("/orders", methods=["POST"])
@require_scopes(ApiScope.CHECKOUT_CREATE.value)
def agent_create_order():
    """Registers an order the agent has already collected payment for.

    Idempotent on `agent_order_id`, and everything about price/merchant/store
    is resolved from this database — the body only says which variants and
    how many.
    """
    payload = request.get_json(silent=True) or {}
    orders, created = order_service.create_order_from_agent(payload, g.api_client.id)
    return success(
        {
            "created": created,
            "orders": [o.to_dict() for o in orders],
        },
        status=201 if created else 200,
    )


@bp.route("/orders/<agent_order_id>", methods=["GET"])
@require_scopes(ApiScope.CHECKOUT_CREATE.value)
def agent_get_order(agent_order_id):
    """Lets the buyer's agent read fulfillment status back for "where is my
    order?" — read-only."""
    orders = order_service.get_by_agent_order_id(agent_order_id)
    if not orders:
        raise NotFoundError("Order not found", code="ORDER_NOT_FOUND")
    return success({"orders": [o.to_dict() for o in orders]})


@bp.route("/orders/<agent_order_id>/cancel", methods=["POST"])
@require_scopes(ApiScope.CHECKOUT_CREATE.value)
def agent_cancel_order(agent_order_id):
    """Cancels a synced order and restores its stock. Refused once shipped."""
    payload = request.get_json(silent=True) or {}
    orders = order_service.cancel_order_from_agent(
        agent_order_id, payload.get("reason"), g.api_client.id
    )
    return success({"cancelled": [o.to_dict(include_items=False) for o in orders]})


@bp.route("/reservations", methods=["POST"])
@require_scopes(ApiScope.CHECKOUT_CREATE.value)
def agent_reserve_stock():
    """Holds stock for a checkout the agent has just priced.

    This is what closes the oversell window: between pricing and payment the
    buyer is slow, and without a hold a second buyer could be quoted the same
    last unit and charged for it. The hold expires on its own, so an
    abandoned checkout never strands inventory.

    Idempotent on `agent_order_id` — re-posting re-prices the hold against
    the current cart and restarts the clock.
    """
    payload = request.get_json(silent=True) or {}
    result = reservation_service.reserve(
        payload.get("agent_order_id"),
        payload.get("items"),
        api_client_id=g.api_client.id,
        ttl_minutes=payload.get("ttl_minutes"),
    )
    return success(result, status=201)


@bp.route("/reservations/<agent_order_id>", methods=["GET"])
@require_scopes(ApiScope.CHECKOUT_CREATE.value)
def agent_get_reservation(agent_order_id):
    """What is still held for an order, and for how much longer."""
    result = reservation_service.get_reservation(agent_order_id)
    if result is None:
        return success({"agent_order_id": agent_order_id, "reservations": [], "held": False})
    return success({**result, "held": True})


@bp.route("/reservations/<agent_order_id>", methods=["DELETE"])
@require_scopes(ApiScope.CHECKOUT_CREATE.value)
def agent_release_stock(agent_order_id):
    """Gives held stock back early — the buyer cancelled or changed the cart.

    Never an error when there is nothing held: the hold may have already
    expired, and a release that arrives late should still read as success.
    """
    payload = request.get_json(silent=True) or {}
    released = reservation_service.release(
        agent_order_id,
        payload.get("reason") or "RELEASED_BY_AGENT",
        api_client_id=g.api_client.id,
    )
    return success({"agent_order_id": agent_order_id, "released": released})
