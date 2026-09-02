from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import UUIDPrimaryKeyMixin, utcnow


class ProductImage(UUIDPrimaryKeyMixin, db.Model):
    __tablename__ = "product_images"

    product_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("products.id"), nullable=False, index=True
    )

    image_url = db.Column(db.String(2048), nullable=False)
    cloudinary_public_id = db.Column(db.String(500), nullable=True)
    alt_text = db.Column(db.String(255), nullable=True)

    position = db.Column(db.Integer, nullable=False, default=0)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    product = db.relationship("Product", back_populates="images")

    def to_dict(self):
        return {
            "id": str(self.id),
            "product_id": str(self.product_id),
            "url": self.image_url,
            "image_url": self.image_url,
            "cloudinary_public_id": self.cloudinary_public_id,
            "alt_text": self.alt_text,
            "position": self.position,
            "is_primary": self.is_primary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
