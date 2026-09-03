from flask import Blueprint, g, request

from app.middleware.clerk_auth import require_auth
from app.services import checkout_service, payment_service
from app.utils.exceptions import ValidationError
from app.utils.responses import success

bp = Blueprint("checkout", __name__, url_prefix="/api/v1")


@bp.route("/chat/sessions/<uuid:session_id>/checkout", methods=["POST"])
@require_auth
def create_checkout(session_id):
    """Validates the session's cart against the live catalog and prices the
    order server-side. No amount is accepted from the request."""
    order = checkout_service.create_checkout(g.buyer_id, session_id)
    return success(order.to_dict(), status=201)


@bp.route("/orders", methods=["GET"])
@require_auth
def list_orders():
    session_id = request.args.get("session_id")
    orders = checkout_service.list_orders(g.buyer_id, session_id)
    return success([o.to_dict() for o in orders])


@bp.route("/orders/<uuid:order_id>", methods=["GET"])
@require_auth
def get_order(order_id):
    order = checkout_service.get_order_for_buyer(g.buyer_id, order_id)
    return success(order.to_dict())


@bp.route("/orders/<uuid:order_id>/authorize", methods=["POST"])
@require_auth
def authorize_payment(order_id):
    """The explicit "Pay ₹X" action. Creates the Razorpay order and returns
    the public key id only — the secret stays server-side."""
    body = request.get_json(silent=True) or {}
    checkout = payment_service.authorize_and_create_payment(
        g.buyer_id, order_id, is_retry=bool(body.get("retry"))
    )
    return success(checkout, status=201)


@bp.route("/orders/<uuid:order_id>/verify", methods=["POST"])
@require_auth
def verify_payment(order_id):
    body = request.get_json(silent=True) or {}
    provider_order_id = body.get("razorpay_order_id")
    provider_payment_id = body.get("razorpay_payment_id")
    signature = body.get("razorpay_signature")
    if not provider_order_id or not provider_payment_id or not signature:
        raise ValidationError(
            "razorpay_order_id, razorpay_payment_id and razorpay_signature are required"
        )

    order, payment = payment_service.verify_payment(
        g.buyer_id, order_id, provider_order_id, provider_payment_id, signature
    )
    return success({"order": order.to_dict(), "payment": payment.to_dict()})


@bp.route("/orders/<uuid:order_id>/failed", methods=["POST"])
@require_auth
def record_failure(order_id):
    body = request.get_json(silent=True) or {}
    order, payment = payment_service.record_unsuccessful_attempt(
        g.buyer_id,
        order_id,
        body.get("razorpay_order_id"),
        cancelled=bool(body.get("cancelled")),
        reason=body.get("reason"),
    )
    return success({"order": order.to_dict(), "payment": payment.to_dict() if payment else None})


@bp.route("/orders/<uuid:order_id>/receipt", methods=["GET"])
@require_auth
def get_receipt(order_id):
    order = checkout_service.get_order_for_buyer(g.buyer_id, order_id)
    return success(checkout_service.build_receipt(g.buyer_id, order))
