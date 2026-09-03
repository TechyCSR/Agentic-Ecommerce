from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import OrderStatus


class Order(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "orders"

    session_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("chat_sessions.id"), nullable=True, index=True
    )
    buyer_clerk_user_id = db.Column(db.String(255), nullable=False, index=True)

    # Line items as immutable snapshots taken at checkout time, each one
    # re-validated against the live Merchant catalog first (product active,
    # variant in stock, price current). Stored as JSONB rather than a child
    # table because they are written once and only ever read back whole —
    # same approach as chat_messages.product_cards.
    items = db.Column(JSONB, nullable=False, default=list)

    # Authoritative total, computed server-side from validated catalog
    # prices — never accepted from the client.
    amount_total = db.Column(db.Integer, nullable=False, default=0)
    currency = db.Column(db.String(10), nullable=False, default="INR")

    status = db.Column(
        SAEnum(OrderStatus, name="order_status"),
        nullable=False,
        default=OrderStatus.CREATED,
        index=True,
    )

    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Ids of the order(s) this became in the Merchant service. A list because
    # one cart can span stores, and a Merchant order belongs to exactly one.
    merchant_order_ids = db.Column(JSONB, nullable=True)
    merchant_synced_at = db.Column(db.DateTime(timezone=True), nullable=True)

    payments = db.relationship(
        "Payment",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="Payment.created_at",
    )

    def latest_payment(self):
        return self.payments[-1] if self.payments else None

    def to_dict(self, include_payments: bool = True):
        latest = self.latest_payment()
        data = {
            "id": str(self.id),
            "session_id": str(self.session_id) if self.session_id else None,
            "items": self.items or [],
            "amount_total": self.amount_total,
            "currency": self.currency,
            "total": {"amount": self.amount_total, "currency": self.currency},
            "status": self.status.value if self.status else None,
            "payment_status": latest.status.value if latest and latest.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "merchant_order_ids": self.merchant_order_ids or [],
            "merchant_synced_at": (
                self.merchant_synced_at.isoformat() if self.merchant_synced_at else None
            ),
        }
        if include_payments:
            data["payments"] = [p.to_dict() for p in self.payments]
        return data
