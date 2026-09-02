from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import VariantStatus


class ProductVariant(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "product_variants"

    product_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("products.id"), nullable=False, index=True
    )

    sku = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)

    # Stored in the smallest currency unit (e.g. paise for INR).
    price = db.Column(db.Integer, nullable=False, default=0)
    currency = db.Column(db.String(10), nullable=False, default="INR")
    compare_at_price = db.Column(db.Integer, nullable=True)

    stock_quantity = db.Column(db.Integer, nullable=False, default=0)

    status = db.Column(
        SAEnum(VariantStatus, name="variant_status"),
        nullable=False,
        default=VariantStatus.ACTIVE,
    )

    product = db.relationship("Product", back_populates="variants")
    inventory_movements = db.relationship(
        "InventoryMovement",
        back_populates="product_variant",
        cascade="all, delete-orphan",
    )

    @property
    def availability(self):
        if self.status.value == "DISCONTINUED":
            return "DISCONTINUED"
        if self.stock_quantity and self.stock_quantity > 0:
            return "IN_STOCK"
        return "OUT_OF_STOCK"

    def to_dict(self):
        return {
            "id": str(self.id),
            "variant_id": str(self.id),
            "product_id": str(self.product_id),
            "sku": self.sku,
            "name": self.name,
            "price": self.price,
            "currency": self.currency,
            "compare_at_price": self.compare_at_price,
            "stock_quantity": self.stock_quantity,
            "status": self.status.value if self.status else None,
            "availability": self.availability,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
