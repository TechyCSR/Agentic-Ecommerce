from flask import Blueprint, g, request

from app.middleware.clerk_auth import require_auth
from app.services import order_service
from app.utils.exceptions import ValidationError
from app.utils.pagination import build_meta, paginate_params
from app.utils.responses import success

bp = Blueprint("orders", __name__, url_prefix="/api/v1")


@bp.route("/orders", methods=["GET"])
@require_auth
def list_orders():
    limit, offset = paginate_params(request.args)
    status = request.args.get("status")
    orders, total = order_service.list_orders_for_merchant(
        g.current_user, status=status, limit=limit, offset=offset
    )
    return success(
        [o.to_dict(include_items=False) for o in orders],
        meta=build_meta(total, limit, offset),
    )


@bp.route("/orders/stats", methods=["GET"])
@require_auth
def order_stats():
    return success(order_service.order_stats(g.current_user))


@bp.route("/orders/<uuid:order_id>", methods=["GET"])
@require_auth
def get_order(order_id):
    order = order_service.get_order_for_merchant(g.current_user, order_id)
    return success(order.to_dict())


@bp.route("/orders/<uuid:order_id>/fulfillment", methods=["PATCH"])
@require_auth
def update_fulfillment(order_id):
    body = request.get_json(silent=True) or {}
    status = body.get("status")
    if not status:
        raise ValidationError("status is required")
    order = order_service.update_fulfillment_status(g.current_user, order_id, status)
    return success(order.to_dict())


@bp.route("/payments", methods=["GET"])
@require_auth
def list_payments():
    limit, offset = paginate_params(request.args)
    payments, total = order_service.list_payments_for_merchant(
        g.current_user, limit=limit, offset=offset
    )
    return success(payments, meta=build_meta(total, limit, offset))
