"""A timed hold on stock, taken when an agent prices a checkout.

Reservations are **logical**: `product_variants.stock_quantity` keeps meaning
"units physically on hand" and is only moved by a real order or a merchant
adjustment. What a hold does is subtract from what everyone *else* can be
offered:

    available = stock_quantity - SUM(held, unexpired, someone else's)

That keeps the merchant's own inventory view honest while closing the window
between "the agent quoted a price" and "the buyer finished paying" — the
window that previously let two buyers pay for the same last unit.

Expiry is enforced by reading, not by a job: every availability query filters
on `expires_at`, so a hold whose buyer walked away stops blocking stock at
the exact second it lapses, whether or not anything swept it.
"""

from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ReservationStatus


class StockReservation(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "stock_reservations"
    __table_args__ = (
        # One hold per variant per agent order, so re-pricing the same
        # checkout updates the hold instead of stacking a second one.
        db.UniqueConstraint(
            "agent_order_id", "product_variant_id", name="uq_reservation_order_variant"
        ),
    )

    # The buyer-side order this hold belongs to. Not a foreign key: the order
    # lives in the Agent service's database, and this service never sees it.
    agent_order_id = db.Column(db.String(255), nullable=False, index=True)

    product_variant_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    quantity = db.Column(db.Integer, nullable=False, default=1)

    status = db.Column(
        SAEnum(ReservationStatus, name="reservation_status"),
        nullable=False,
        default=ReservationStatus.HELD,
        index=True,
    )

    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    settled_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Which authorized agent took the hold, for the audit trail.
    api_client_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("api_clients.id"), nullable=True
    )

    product_variant = db.relationship("ProductVariant")

    def to_dict(self):
        return {
            "id": str(self.id),
            "agent_order_id": self.agent_order_id,
            "variant_id": str(self.product_variant_id),
            "quantity": self.quantity,
            "status": self.status.value if self.status else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
        }
