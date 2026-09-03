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
from app.models import Payment
from app.models.enums import OrderStatus, PaymentProvider, PaymentStatus
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

    payment.provider_payment_id = provider_payment_id
    payment.status = PaymentStatus.PAID
    payment.paid_at = datetime.now(timezone.utc)

    order.status = OrderStatus.CONFIRMED
    order.confirmed_at = datetime.now(timezone.utc)
    db.session.commit()

    audit_service.log_event(
        action="PAYMENT_VERIFIED",
        resource_id=order.id,
        session_id=order.session_id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "order_id": str(order.id),
            "payment_id": str(payment.id),
            "provider_payment_id": provider_payment_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status.value,
        },
    )
    audit_service.log_event(
        action="ORDER_CONFIRMED",
        resource_id=order.id,
        session_id=order.session_id,
        buyer_clerk_user_id=buyer_id,
        metadata={
            "order_id": str(order.id),
            "amount": order.amount_total,
            "currency": order.currency,
            "status": order.status.value,
        },
    )

    checkout_service.clear_cart_for_order(order)
    return order, payment


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
