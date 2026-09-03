"""Razorpay payment handling — the backend is the only source of truth.

Two rules shape this module:

1. The amount charged always comes from the stored Order, never from the
   request body, so the client cannot influence what is billed.
2. A payment becomes PAID only after this process verifies Razorpay's
   HMAC signature itself. The browser telling us "payment succeeded" is
   treated as an unverified claim until then.
"""

import hashlib
import hmac
from datetime import datetime, timezone

import razorpay
from flask import current_app

from app.extensions import db
from app.models import ChatMessage, Payment
from app.models.enums import MessageRole, OrderStatus, PaymentProvider, PaymentStatus
from app.services import audit_service, checkout_service
from app.utils.exceptions import ValidationError

# Razorpay's own limit on the receipt field.
RECEIPT_MAX_LENGTH = 40


def _client() -> razorpay.Client:
    key_id = current_app.config.get("RAZORPAY_KEY_ID")
    key_secret = current_app.config.get("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise ValidationError(
            "Payments aren't configured right now. Please try again later.",
            code="PAYMENTS_UNAVAILABLE",
        )
    return razorpay.Client(auth=(key_id, key_secret))


def _terminal(status: PaymentStatus) -> bool:
    return status in (PaymentStatus.PAID, PaymentStatus.FAILED, PaymentStatus.CANCELLED)


def authorize_and_create_payment(buyer_id: str, order_id, is_retry: bool = False) -> dict:
    """Called only from an explicit user action ("Pay ₹X" / "Try again").

    Creates a Razorpay order for the stored amount and returns just enough
    for the browser to open Checkout — key id, provider order id, amount.
    The key secret never leaves this process.
    """
    order = checkout_service.get_order_for_buyer(buyer_id, order_id)

    if order.status == OrderStatus.CONFIRMED:
        raise ValidationError("This order is already paid.", code="ORDER_ALREADY_CONFIRMED")
    if order.status == OrderStatus.CANCELLED:
        raise ValidationError("This order was cancelled.", code="ORDER_CANCELLED")

    existing = order.latest_payment()
    if existing and existing.status == PaymentStatus.PAID:
        raise ValidationError("This order is already paid.", code="ORDER_ALREADY_CONFIRMED")

    if is_retry:
        audit_service.log_event(
            action="PAYMENT_RETRY_REQUESTED",
            resource_id=order.id,
            session_id=order.session_id,
            buyer_clerk_user_id=buyer_id,
            metadata={
                "order_id": str(order.id),
                "previous_attempts": len(order.payments),
                "amount": order.amount_total,
                "currency": order.currency,
            },
        )

    # Recorded before contacting Razorpay: this is the user's explicit
    # consent to be charged this specific amount.
    audit_service.log_event(
        action="USER_PAYMENT_AUTHORIZED",
        resource_id=order.id,
        session_id=order.session_id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "order_id": str(order.id),
            "amount": order.amount_total,
            "currency": order.currency,
        },
    )

    client = _client()
    try:
        provider_order = client.order.create(
            {
                "amount": order.amount_total,
                "currency": order.currency,
                "receipt": str(order.id)[:RECEIPT_MAX_LENGTH],
                "notes": {"order_id": str(order.id), "buyer": buyer_id},
            }
        )
    except Exception as exc:  # noqa: BLE001 — provider/network failure must not 500 the checkout
        audit_service.log_event(
            action="PAYMENT_FAILED",
            resource_id=order.id,
            session_id=order.session_id,
            buyer_clerk_user_id=buyer_id,
            metadata={
                "order_id": str(order.id),
                "stage": "razorpay_order_create",
                "error": str(exc),
            },
        )
        raise ValidationError(
            "We couldn't start the payment right now. Please try again.",
            code="PAYMENT_INIT_FAILED",
        ) from exc

    payment = Payment(
        order_id=order.id,
        buyer_clerk_user_id=buyer_id,
        provider=PaymentProvider.RAZORPAY,
        provider_order_id=provider_order.get("id"),
        amount=order.amount_total,
        currency=order.currency,
        status=PaymentStatus.PENDING,
    )
    db.session.add(payment)
    db.session.commit()

    audit_service.log_event(
        action="RAZORPAY_ORDER_CREATED",
        resource_id=order.id,
        session_id=order.session_id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "order_id": str(order.id),
            "payment_id": str(payment.id),
            "provider_order_id": payment.provider_order_id,
            "amount": payment.amount,
            "currency": payment.currency,
        },
    )

    return {
        "payment_id": str(payment.id),
        "provider_order_id": payment.provider_order_id,
        "amount": payment.amount,
        "currency": payment.currency,
        "key_id": current_app.config["RAZORPAY_KEY_ID"],
        "order": order.to_dict(),
    }


def _signature_is_valid(provider_order_id: str, provider_payment_id: str, signature: str) -> bool:
    """Razorpay's documented check: HMAC-SHA256 of "<order_id>|<payment_id>"
    keyed with the secret, compared in constant time."""
    secret = current_app.config.get("RAZORPAY_KEY_SECRET") or ""
    if not secret or not signature:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{provider_order_id}|{provider_payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_payment(
    buyer_id: str,
    order_id,
    provider_order_id: str,
    provider_payment_id: str,
    signature: str,
):
    order = checkout_service.get_order_for_buyer(buyer_id, order_id)

    payment = next(
        (p for p in order.payments if p.provider_order_id == provider_order_id),
        None,
    )
    if payment is None:
        raise ValidationError(
            "We couldn't match that payment to this order.", code="PAYMENT_NOT_FOUND"
        )

    if payment.status == PaymentStatus.PAID:
        # Idempotent: a duplicated callback shouldn't double-confirm or error.
        return order, payment

    audit_service.log_event(
        action="PAYMENT_ATTEMPTED",
        resource_id=order.id,
        session_id=order.session_id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "order_id": str(order.id),
            "payment_id": str(payment.id),
            "provider_order_id": provider_order_id,
            "provider_payment_id": provider_payment_id,
        },
    )

    if not _signature_is_valid(provider_order_id, provider_payment_id, signature):
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = "Signature verification failed"
        db.session.commit()
        audit_service.log_event(
            action="PAYMENT_FAILED",
            resource_id=order.id,
            session_id=order.session_id,
            buyer_clerk_user_id=buyer_id,
            metadata={
                "order_id": str(order.id),
                "payment_id": str(payment.id),
                "reason": "signature_verification_failed",
                "provider_payment_id": provider_payment_id,
            },
        )
        raise ValidationError(
            "We couldn't verify this payment. No payment has been recorded as successful.",
            code="PAYMENT_VERIFICATION_FAILED",
        )

    _mark_paid_and_confirm(order, payment, provider_payment_id, source="browser")

    checkout_service.clear_cart_for_order(order)

    # Tell the seller, and tell the buyer's own conversation. Both are
    # best-effort on purpose — the payment is already verified and must stand
    # regardless of what either of these does.
    checkout_service.sync_order_to_merchant(order)
    _post_order_confirmation_to_chat(order, payment)

    return order, payment


def _describe_method(entity: dict) -> tuple[str | None, str | None]:
    """Turns Razorpay's payment entity into a method plus a safe descriptor.

    Only non-sensitive fragments are kept — network and last4, bank or wallet
    name, or a UPI handle. Never a full instrument number.
    """
    method = entity.get("method")
    detail = None
    if method == "card":
        card = entity.get("card") or {}
        bits = [card.get("network"), card.get("last4") and f"•••• {card['last4']}"]
        detail = " ".join(b for b in bits if b) or None
    elif method == "upi":
        detail = entity.get("vpa")
    elif method == "netbanking":
        detail = entity.get("bank")
    elif method == "wallet":
        detail = entity.get("wallet")
    return method, detail


def _fetch_payment_method(payment, provider_payment_id):
    """Reads back how the payment was actually made. Best-effort: a failure
    here must never affect an already-verified payment."""
    if not provider_payment_id:
        return
    try:
        entity = _client().payment.fetch(provider_payment_id)
    except Exception:  # noqa: BLE001 — cosmetic detail, never worth failing a payment over
        return
    method, detail = _describe_method(entity or {})
    if method:
        payment.method = method
        payment.method_detail = detail


def _mark_paid_and_confirm(order, payment, provider_payment_id, source: str):
    """The single place a payment becomes PAID and an order CONFIRMED.

    Shared by browser verification and the Razorpay webhook so the two can
    never diverge — whichever arrives first does the work, and the other
    finds it already done.
    """
    payment.provider_payment_id = provider_payment_id
    payment.status = PaymentStatus.PAID
    payment.paid_at = datetime.now(timezone.utc)
    _fetch_payment_method(payment, provider_payment_id)

    order.status = OrderStatus.CONFIRMED
    order.confirmed_at = datetime.now(timezone.utc)
    db.session.commit()

    audit_service.log_event(
        action="PAYMENT_VERIFIED",
        resource_id=order.id,
        session_id=order.session_id,
        buyer_clerk_user_id=order.buyer_clerk_user_id,
        metadata={
            "order_id": str(order.id),
            "payment_id": str(payment.id),
            "provider_payment_id": provider_payment_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status.value,
            "method": payment.method,
            "source": source,
        },
    )
    audit_service.log_event(
        action="ORDER_CONFIRMED",
        resource_id=order.id,
        session_id=order.session_id,
        buyer_clerk_user_id=order.buyer_clerk_user_id,
        metadata={
            "order_id": str(order.id),
            "amount": order.amount_total,
            "currency": order.currency,
            "status": order.status.value,
            "source": source,
        },
    )


def confirm_payment_from_webhook(order, payment, provider_payment_id):
    """Webhook entry point. Razorpay's own call already proves the payment,
    so there's no client signature to check here — the request itself was
    authenticated by its webhook signature before reaching this."""
    _mark_paid_and_confirm(order, payment, provider_payment_id, source="webhook")
    checkout_service.clear_cart_for_order(order)
    checkout_service.sync_order_to_merchant(order)
    _post_order_confirmation_to_chat(order, payment)
    return order, payment


def _post_order_confirmation_to_chat(order, payment):
    """Writes the confirmation into the chat session as a real assistant
    message, so the agent knows an order exists without being asked and the
    buyer sees it in the conversation they bought from."""
    if not order.session_id:
        return
    try:
        lines = ", ".join(
            f"{i.get('quantity')} x {i.get('product_name')}" for i in (order.items or [])
        )
        amount = order.amount_total / 100
        symbol = "₹" if order.currency == "INR" else f"{order.currency} "
        text = (
            f"✅ **Payment verified — your order is confirmed.**\n\n"
            f"- **Order ID:** `{order.id}`\n"
            f"- **Items:** {lines}\n"
            f"- **Amount paid:** {symbol}{amount:,.0f}\n"
            f"- **Payment status:** PAID\n"
            f"- **Order status:** CONFIRMED\n"
        )
        if payment and payment.provider_payment_id:
            text += f"- **Payment ID:** `{payment.provider_payment_id}`\n"
        text += "\nAsk me any time if you'd like to check its status."

        db.session.add(
            ChatMessage(
                session_id=order.session_id,
                role=MessageRole.ASSISTANT,
                content=text,
                suggested_replies=[
                    "Where is my order?",
                    "Show my order details",
                    "Find me something else",
                ],
            )
        )
        db.session.commit()
    except Exception as exc:  # noqa: BLE001 — a chat write must never affect a verified payment
        db.session.rollback()
        audit_service.log_event(
            action="ORDER_CHAT_NOTICE_FAILED",
            resource_id=order.id,
            session_id=order.session_id,
            buyer_clerk_user_id=order.buyer_clerk_user_id,
            metadata={"error": str(exc)[:300]},
        )


def record_unsuccessful_attempt(
    buyer_id: str,
    order_id,
    provider_order_id: str | None,
    cancelled: bool,
    reason: str | None = None,
):
    """Records a dismissed or failed checkout. Never marks anything paid."""
    order = checkout_service.get_order_for_buyer(buyer_id, order_id)

    payment = None
    if provider_order_id:
        payment = next(
            (p for p in order.payments if p.provider_order_id == provider_order_id), None
        )
    if payment is None:
        payment = order.latest_payment()

    if payment is None or _terminal(payment.status):
        return order, payment

    payment.status = PaymentStatus.CANCELLED if cancelled else PaymentStatus.FAILED
    payment.failure_reason = reason or ("Cancelled by user" if cancelled else "Payment failed")
    db.session.commit()

    audit_service.log_event(
        action="PAYMENT_CANCELLED" if cancelled else "PAYMENT_FAILED",
        resource_id=order.id,
        session_id=order.session_id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "order_id": str(order.id),
            "payment_id": str(payment.id),
            "provider_order_id": payment.provider_order_id,
            "reason": payment.failure_reason,
            "status": payment.status.value,
        },
    )
    return order, payment
