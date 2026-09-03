from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentProvider, PaymentStatus


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """One payment attempt against an order.

    A retry creates a new row rather than mutating the old one, so every
    attempt stays on the record (Phase 3 requires previous attempts to be
    recorded, and the audit trail to be able to point at a specific one).
    """

    __tablename__ = "payments"

    order_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("orders.id"), nullable=False, index=True
    )
    buyer_clerk_user_id = db.Column(db.String(255), nullable=False, index=True)

    provider = db.Column(
        SAEnum(PaymentProvider, name="payment_provider"),
        nullable=False,
        default=PaymentProvider.RAZORPAY,
    )

    provider_order_id = db.Column(db.String(255), nullable=True, index=True)
    provider_payment_id = db.Column(db.String(255), nullable=True)

    amount = db.Column(db.Integer, nullable=False, default=0)
    currency = db.Column(db.String(10), nullable=False, default="INR")

    status = db.Column(
        SAEnum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.CREATED,
        index=True,
    )

    # How the buyer actually paid, read back from Razorpay after verification
    # (card / upi / netbanking / wallet) plus a safe descriptor like the card
    # network + last4 or the bank name. No full instrument data is ever stored.
    method = db.Column(db.String(40), nullable=True)
    method_detail = db.Column(db.String(120), nullable=True)

    failure_reason = db.Column(db.Text, nullable=True)
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)

    order = db.relationship("Order", back_populates="payments")

    def to_dict(self):
        return {
            "id": str(self.id),
            "order_id": str(self.order_id),
            "provider": self.provider.value if self.provider else None,
            # Provider order id is safe to expose (the client needs it to open
            # checkout); the payment id identifies the transaction on a
            # receipt. No card/instrument data is ever stored or returned.
            "provider_order_id": self.provider_order_id,
            "provider_payment_id": self.provider_payment_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status.value if self.status else None,
            "method": self.method,
            "method_detail": self.method_detail,
            "failure_reason": self.failure_reason,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
