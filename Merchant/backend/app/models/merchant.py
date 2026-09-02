from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import MerchantStatus


class Merchant(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "merchants"

    owner_user_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False, index=True
    )

    business_name = db.Column(db.String(255), nullable=False)
    legal_name = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)

    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    website_url = db.Column(db.String(1024), nullable=True)

    status = db.Column(
        SAEnum(MerchantStatus, name="merchant_status"),
        nullable=False,
        default=MerchantStatus.ACTIVE,
    )

    owner = db.relationship("User", back_populates="merchants")
    stores = db.relationship(
        "Store", back_populates="merchant", cascade="all, delete-orphan"
    )
    api_clients = db.relationship(
        "ApiClient", back_populates="merchant", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "owner_user_id": str(self.owner_user_id),
            "business_name": self.business_name,
            "legal_name": self.legal_name,
            "description": self.description,
            "email": self.email,
            "phone": self.phone,
            "website_url": self.website_url,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
