from app.extensions import db
from app.models import AuditEvent


def log_event(
    actor_type,
    actor_id=None,
    merchant_id=None,
    resource_type=None,
    resource_id=None,
    action=None,
    metadata=None,
):
    event = AuditEvent(
        actor_type=actor_type,
        actor_id=actor_id,
        merchant_id=merchant_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        metadata_json=metadata or {},
    )
    db.session.add(event)
    db.session.commit()
    return event
