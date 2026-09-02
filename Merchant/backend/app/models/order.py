from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import OrderStatus


class Order(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "orders"

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=True)
    merchant_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("merchants.id"), nullable=False, index=True
    )
    store_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("stores.id"), nullable=False, index=True
    )

    status = db.Column(
        SAEnum(OrderStatus, name="order_status"),
        nullable=False,
        default=OrderStatus.DRAFT,
        index=True,
    )
    currency = db.Column(db.String(10), nullable=False, default="INR")

    subtotal_amount = db.Column(db.Integer, nullable=False, default=0)
    tax_amount = db.Column(db.Integer, nullable=False, default=0)
    total_amount = db.Column(db.Integer, nullable=False, default=0)

    items = db.relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payments = db.relationship(
        "Payment", back_populates="order", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "merchant_id": str(self.merchant_id),
            "store_id": str(self.store_id),
            "status": self.status.value if self.status else None,
            "currency": self.currency,
            "subtotal_amount": self.subtotal_amount,
            "tax_amount": self.tax_amount,
            "total_amount": self.total_amount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
