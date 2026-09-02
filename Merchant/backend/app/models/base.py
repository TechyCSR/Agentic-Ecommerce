import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


def gen_uuid():
    return uuid.uuid4()


def utcnow():
    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin:
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
