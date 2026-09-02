from sqlalchemy import Enum as SAEnum

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    clerk_user_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(120), nullable=True)
    last_name = db.Column(db.String(120), nullable=True)
    profile_image_url = db.Column(db.String(1024), nullable=True)
    role = db.Column(
        SAEnum(UserRole, name="user_role"), nullable=False, default=UserRole.MERCHANT
    )

    merchants = db.relationship(
        "Merchant", back_populates="owner", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "clerk_user_id": self.clerk_user_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "profile_image_url": self.profile_image_url,
            "role": self.role.value if self.role else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
