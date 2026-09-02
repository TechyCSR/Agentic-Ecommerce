from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import UUIDPrimaryKeyMixin, utcnow
from app.models.enums import SelectionStatus


class SelectedProduct(UUIDPrimaryKeyMixin, db.Model):
    __tablename__ = "selected_products"

    session_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("chat_sessions.id"), nullable=False, index=True
    )
    buyer_clerk_user_id = db.Column(db.String(255), nullable=False, index=True)

    product_id = db.Column(UUID(as_uuid=True), nullable=False)
    variant_id = db.Column(UUID(as_uuid=True), nullable=False)

    # Snapshots taken at selection time, validated fresh against the
    # Merchant catalog API — never trusted from the client.
    product_name_snapshot = db.Column(db.String(255), nullable=False)
    variant_name_snapshot = db.Column(db.String(255), nullable=False)
    merchant_name_snapshot = db.Column(db.String(255), nullable=True)
    price_amount_snapshot = db.Column(db.Integer, nullable=False)
    currency_snapshot = db.Column(db.String(10), nullable=False)

    status = db.Column(
        SAEnum(SelectionStatus, name="selection_status"),
        nullable=False,
        default=SelectionStatus.SELECTED,
    )

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    session = db.relationship("ChatSession", back_populates="selections")

    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "product_id": str(self.product_id),
            "variant_id": str(self.variant_id),
            "product_name": self.product_name_snapshot,
            "variant_name": self.variant_name_snapshot,
            "merchant_name": self.merchant_name_snapshot,
            "price": {
                "amount": self.price_amount_snapshot,
                "currency": self.currency_snapshot,
            },
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
