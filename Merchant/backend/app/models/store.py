from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import StoreStatus


class Store(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "stores"

    merchant_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("merchants.id"), nullable=False, index=True
    )

    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)

    description = db.Column(db.Text, nullable=True)

    currency = db.Column(db.String(10), nullable=False, default="INR")
    country = db.Column(db.String(100), nullable=True)

    status = db.Column(
        SAEnum(StoreStatus, name="store_status"),
        nullable=False,
        default=StoreStatus.ACTIVE,
    )

    merchant = db.relationship("Merchant", back_populates="stores")
    products = db.relationship(
        "Product", back_populates="store", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "merchant_id": str(self.merchant_id),
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "currency": self.currency,
            "country": self.country,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
