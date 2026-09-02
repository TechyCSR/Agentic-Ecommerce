from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentProvider, PaymentStatus


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "payments"

    order_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("orders.id"), nullable=False, index=True
    )

    provider = db.Column(
        SAEnum(PaymentProvider, name="payment_provider"),
        nullable=False,
        default=PaymentProvider.RAZORPAY,
    )

    provider_order_id = db.Column(db.String(255), nullable=True)
    provider_payment_id = db.Column(db.String(255), nullable=True)

    amount = db.Column(db.Integer, nullable=False, default=0)
    currency = db.Column(db.String(10), nullable=False, default="INR")

    status = db.Column(
        SAEnum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.CREATED,
        index=True,
    )

    order = db.relationship("Order", back_populates="payments")

    def to_dict(self):
        return {
            "id": str(self.id),
            "order_id": str(self.order_id),
            "provider": self.provider.value if self.provider else None,
            "provider_order_id": self.provider_order_id,
            "provider_payment_id": self.provider_payment_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
