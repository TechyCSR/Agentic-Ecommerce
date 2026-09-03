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

    # Set when the order arrives from the shopping agent. Unique, so replaying
    # the same sync (a retry, a duplicate webhook) can never create a second
    # order for the same purchase.
    agent_order_id = db.Column(db.String(255), nullable=True, unique=True, index=True)
    # The agent's buyer identifier — a Clerk user id, not a UUID in this DB,
    # which is why it doesn't reuse user_id.
    buyer_ref = db.Column(db.String(255), nullable=True, index=True)
    placed_at = db.Column(db.DateTime(timezone=True), nullable=True)

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

    def latest_payment(self):
        return self.payments[-1] if self.payments else None

    def to_dict(self, include_items=True, include_payments=True):
        latest = self.latest_payment()
        data = {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "merchant_id": str(self.merchant_id),
            "store_id": str(self.store_id),
            "agent_order_id": self.agent_order_id,
            "buyer_ref": self.buyer_ref,
            "status": self.status.value if self.status else None,
            "payment_status": latest.status.value if latest and latest.status else None,
            "currency": self.currency,
            "subtotal_amount": self.subtotal_amount,
            "tax_amount": self.tax_amount,
            "total_amount": self.total_amount,
            "item_count": len(self.items or []),
            "placed_at": self.placed_at.isoformat() if self.placed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_items:
            data["items"] = [i.to_dict() for i in self.items]
        if include_payments:
            data["payments"] = [p.to_dict() for p in self.payments]
        return data
