from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.extensions import db
from app.models.base import UUIDPrimaryKeyMixin, utcnow


class AuditEvent(UUIDPrimaryKeyMixin, db.Model):
    """This service's own audit_events table (own database, separate from
    Merchant's) — same shape as Merchant's table so both services' audit
    trails stay directly comparable, but each service owns its own rows.
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
