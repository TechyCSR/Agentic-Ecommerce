"""Razorpay webhooks — the authoritative source of payment status.

Browser-side verification is the fast path, but it only runs if the buyer's
tab is still open. This endpoint is the backstop: Razorpay calls it
server-to-server, so a payment that completes after the buyer closes the page
still confirms the order.

Authentication is the signature, not Clerk — Razorpay has no user session.
Per Razorpay's spec the signature is HMAC-SHA256 over the **raw request
body**, keyed with the **webhook secret** (a different value from the API key
secret).
"""

import hashlib
import hmac
import threading

from flask import Blueprint, current_app, request

from app.extensions import db
from app.models import Order, Payment
from app.models.enums import PaymentStatus
from app.services import audit_service, payment_service, telegram_service
from app.utils.responses import success

bp = Blueprint("webhooks", __name__, url_prefix="/api/v1/webhooks")

CONFIRMING_EVENTS = {"payment.captured", "order.paid"}
FAILING_EVENTS = {"payment.failed"}


def _signature_is_valid(raw_body: bytes, signature: str | None) -> bool:
    secret = current_app.config.get("RAZORPAY_WEBHOOK_SECRET") or ""
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@bp.route("/razorpay", methods=["POST"])
def razorpay_webhook():
    # Read the raw bytes before anything parses them — re-serializing JSON
    # would change the payload and break the signature.
    raw_body = request.get_data()
    signature = request.headers.get("X-Razorpay-Signature")

    if not _signature_is_valid(raw_body, signature):
        audit_service.log_event(
            action="PAYMENT_WEBHOOK_REJECTED",
            metadata={"reason": "invalid_signature", "has_signature": bool(signature)},
        )
        # 200 on purpose: an unauthenticated caller learns nothing, and
        # Razorpay isn't asked to retry something we will never accept.
        return success({"received": True}, status=200)

    payload = request.get_json(silent=True) or {}
    event = payload.get("event")
    entity = (
        (payload.get("payload") or {}).get("payment", {}).get("entity")
        or (payload.get("payload") or {}).get("order", {}).get("entity")
        or {}
    )
    provider_order_id = entity.get("order_id") or entity.get("id")
    provider_payment_id = entity.get("id") if entity.get("order_id") else None

    audit_service.log_event(
        action="PAYMENT_WEBHOOK_RECEIVED",
        metadata={
            "event": event,
            "provider_order_id": provider_order_id,
            "provider_payment_id": provider_payment_id,
        },
    )

    payment = (
        Payment.query.filter_by(provider_order_id=provider_order_id).first()
        if provider_order_id
        else None
    )
    if payment is None:
        # Not an order of ours (or not created yet) — acknowledge and move on.
        return success({"received": True, "matched": False})

    order = Order.query.get(payment.order_id)

    if event in CONFIRMING_EVENTS:
        if payment.status == PaymentStatus.PAID:
            return success({"received": True, "already_confirmed": True})
        payment_service.confirm_payment_from_webhook(
            order, payment, provider_payment_id or payment.provider_payment_id
        )
        return success({"received": True, "confirmed": True})

    if event in FAILING_EVENTS and payment.status != PaymentStatus.PAID:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = (
            entity.get("error_description") or "Payment failed (reported by Razorpay)"
        )
        db.session.commit()
        audit_service.log_event(
            action="PAYMENT_FAILED",
            resource_id=order.id if order else None,
            session_id=order.session_id if order else None,
            buyer_clerk_user_id=payment.buyer_clerk_user_id,
            metadata={"source": "webhook", "reason": payment.failure_reason},
        )

    return success({"received": True})


@bp.route("/telegram", methods=["POST"])
def telegram_webhook():
    """Telegram delivers updates here.

    Authenticated by the secret token Telegram echoes back in a header (set
    when the webhook is registered), not by Clerk — Telegram has no user
    session. Work happens on a background thread so this returns instantly:
    an agent turn can take many seconds, and a slow 200 makes Telegram retry
    and duplicate the reply.
    """
    expected = current_app.config.get("TELEGRAM_WEBHOOK_SECRET") or ""
    provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token") or ""
    if not expected or not hmac.compare_digest(expected, provided):
        audit_service.log_event(
            action="TELEGRAM_WEBHOOK_REJECTED",
            metadata={"reason": "invalid_secret_token"},
        )
        return success({"ok": True})

    update = request.get_json(silent=True) or {}
    threading.Thread(
        target=telegram_service.process_update,
        args=(current_app._get_current_object(), update),
        daemon=True,
    ).start()
    return success({"ok": True})
