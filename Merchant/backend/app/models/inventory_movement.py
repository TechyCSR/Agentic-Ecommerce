from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import UUIDPrimaryKeyMixin, utcnow


class InventoryMovement(UUIDPrimaryKeyMixin, db.Model):
    __tablename__ = "inventory_movements"

    product_variant_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("product_variants.id"),
        nullable=False,
        index=True,
    )

    quantity_change = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=True)

    reference_type = db.Column(db.String(100), nullable=True)
    reference_id = db.Column(UUID(as_uuid=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    product_variant = db.relationship(
        "ProductVariant", back_populates="inventory_movements"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "product_variant_id": str(self.product_variant_id),
            "quantity_change": self.quantity_change,
            "reason": self.reason,
            "reference_type": self.reference_type,
            "reference_id": str(self.reference_id) if self.reference_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
