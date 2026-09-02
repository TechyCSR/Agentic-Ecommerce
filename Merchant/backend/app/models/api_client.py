from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ApiClientStatus, ApiClientType


class ApiClient(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "api_clients"

    merchant_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("merchants.id"), nullable=True, index=True
    )

    name = db.Column(db.String(255), nullable=False)
    client_type = db.Column(
        SAEnum(ApiClientType, name="api_client_type"),
        nullable=False,
        default=ApiClientType.AUTHORIZED_AGENT,
    )

    api_key_hash = db.Column(db.String(255), nullable=False, unique=True)
    api_key_prefix = db.Column(db.String(40), nullable=False)
    api_key_last4 = db.Column(db.String(10), nullable=False)

    status = db.Column(
        SAEnum(ApiClientStatus, name="api_client_status"),
        nullable=False,
        default=ApiClientStatus.ACTIVE,
        index=True,
    )

    last_used_at = db.Column(db.DateTime(timezone=True), nullable=True)

    merchant = db.relationship("Merchant", back_populates="api_clients")
    scopes = db.relationship(
        "ApiClientScope", back_populates="api_client", cascade="all, delete-orphan"
    )

    @property
    def masked_key(self):
        return f"{self.api_key_prefix}{'*' * 16}{self.api_key_last4}"

    def to_dict(self):
        return {
            "id": str(self.id),
            "merchant_id": str(self.merchant_id) if self.merchant_id else None,
            "name": self.name,
            "client_type": self.client_type.value if self.client_type else None,
            "masked_key": self.masked_key,
            "status": self.status.value if self.status else None,
            "scopes": [s.scope for s in self.scopes],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
        }


class ApiClientScope(UUIDPrimaryKeyMixin, db.Model):
    __tablename__ = "api_client_scopes"

    api_client_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("api_clients.id"),
        nullable=False,
        index=True,
    )
    scope = db.Column(db.String(100), nullable=False)

    api_client = db.relationship("ApiClient", back_populates="scopes")

    __table_args__ = (
        db.UniqueConstraint(
            "api_client_id", "scope", name="uq_api_client_scopes_client_scope"
        ),
    )
