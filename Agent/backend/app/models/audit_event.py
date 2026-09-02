from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.extensions import db
from app.models.base import UUIDPrimaryKeyMixin, utcnow


class AuditEvent(UUIDPrimaryKeyMixin, db.Model):
    """Maps onto the audit_events table Phase 1 (Merchant) already owns and
    migrated — this service writes into the same shared table rather than
    creating a parallel one, so no migration creates this table here.
    """

    __tablename__ = "audit_events"

    actor_type = db.Column(db.String(50), nullable=False)
    actor_id = db.Column(UUID(as_uuid=True), nullable=True)

    merchant_id = db.Column(UUID(as_uuid=True), nullable=True)

    resource_type = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(UUID(as_uuid=True), nullable=True)

    action = db.Column(db.String(100), nullable=False)
    metadata_json = db.Column("metadata", JSONB, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
