from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.extensions import db
from app.models.base import UUIDPrimaryKeyMixin, utcnow


class AuditEvent(UUIDPrimaryKeyMixin, db.Model):
    __tablename__ = "audit_events"

    actor_type = db.Column(db.String(50), nullable=False)
    actor_id = db.Column(UUID(as_uuid=True), nullable=True)

    merchant_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("merchants.id"), nullable=True, index=True
    )

    resource_type = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(UUID(as_uuid=True), nullable=True)

    action = db.Column(db.String(100), nullable=False, index=True)
    metadata_json = db.Column("metadata", JSONB, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": str(self.id),
            "actor_type": self.actor_type,
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "merchant_id": str(self.merchant_id) if self.merchant_id else None,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "action": self.action,
            "metadata": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
