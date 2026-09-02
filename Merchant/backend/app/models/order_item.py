from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import UUIDPrimaryKeyMixin


class OrderItem(UUIDPrimaryKeyMixin, db.Model):
    __tablename__ = "order_items"

    order_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("orders.id"), nullable=False, index=True
    )

    product_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("products.id"), nullable=True
    )
    product_variant_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("product_variants.id"), nullable=True
    )

    # Snapshots so historical orders remain accurate if the product changes later.
    product_name_snapshot = db.Column(db.String(255), nullable=False)

    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price_amount = db.Column(db.Integer, nullable=False, default=0)
    total_amount = db.Column(db.Integer, nullable=False, default=0)

    order = db.relationship("Order", back_populates="items")

    def to_dict(self):
        return {
            "id": str(self.id),
            "order_id": str(self.order_id),
            "product_id": str(self.product_id) if self.product_id else None,
            "product_variant_id": (
                str(self.product_variant_id) if self.product_variant_id else None
            ),
            "product_name_snapshot": self.product_name_snapshot,
            "quantity": self.quantity,
            "unit_price_amount": self.unit_price_amount,
            "total_amount": self.total_amount,
        }
