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


@bp.route("/orders/<uuid:order_id>/sync", methods=["POST"])
@require_auth
def resync_order(order_id):
    """Retries registering a paid order with the merchant, for the case where
    the automatic sync at confirmation time failed."""
    order = checkout_service.get_order_for_buyer(g.buyer_id, order_id)
    synced = checkout_service.sync_order_to_merchant(order)
    return success({"synced": synced, "order": order.to_dict()})


# Actions that move money or change what a buyer owes. Kept explicit rather
# than dumping the whole audit table: the point is to show that every money
# action is attributable, bounded and gated.
MONEY_TRAIL_ACTIONS = [
    "CHECKOUT_STARTED",
    "PRODUCT_VALIDATED",
    "PRICE_VALIDATED",
    "ORDER_CREATED",
    "CHECKOUT_REJECTED",
    "USER_PAYMENT_AUTHORIZED",
    "RAZORPAY_ORDER_CREATED",
    "PAYMENT_ATTEMPTED",
    "PAYMENT_VERIFIED",
    "PAYMENT_FAILED",
    "PAYMENT_CANCELLED",
    "PAYMENT_RETRY_REQUESTED",
    "PAYMENT_WEBHOOK_RECEIVED",
    "ORDER_CONFIRMED",
    "RECEIPT_GENERATED",
    "MERCHANT_SYNC_SUCCEEDED",
    "MERCHANT_SYNC_FAILED",
]


@bp.route("/audit", methods=["GET"])
@require_auth
def money_trail():
    """The buyer's own audit trail of money actions.

    Scoped to the caller: an audit row is only returned when its metadata
    carries this buyer's id, so one account can never read another's trail.
    """
    from app.models import AuditEvent

    limit = min(int(request.args.get("limit") or 50), 200)
    order_id = request.args.get("order_id")

    query = AuditEvent.query.filter(
        AuditEvent.action.in_(MONEY_TRAIL_ACTIONS),
        AuditEvent.metadata_json["buyer_clerk_user_id"].astext == g.buyer_id,
    )
    if order_id:
        query = query.filter(AuditEvent.metadata_json["order_id"].astext == order_id)

    events = query.order_by(AuditEvent.created_at.desc()).limit(limit).all()
    return success(
        [
            {
                "id": str(e.id),
                "action": e.action,
                "order_id": (e.metadata_json or {}).get("order_id"),
                "amount": (e.metadata_json or {}).get("amount"),
                "currency": (e.metadata_json or {}).get("currency"),
                "status": (e.metadata_json or {}).get("status"),
                "reason": (e.metadata_json or {}).get("reason")
                or (e.metadata_json or {}).get("error"),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
    )
