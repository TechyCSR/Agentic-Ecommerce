from app.extensions import db
from app.models import AuditEvent


def log_event(
    *,
    action,
    resource_type="CHAT",
    resource_id=None,
    session_id=None,
    buyer_clerk_user_id=None,
    metadata=None,
):
    """Writes into the same audit_events table Phase 1 (Merchant) uses.

    actor_id stays NULL — a Clerk id ("user_...") isn't a UUID, so the
    buyer identifier goes in metadata instead, alongside the chat session.
    """
    meta = dict(metadata or {})
    if session_id is not None:
        meta.setdefault("session_id", str(session_id))
    if buyer_clerk_user_id is not None:
        meta.setdefault("buyer_clerk_user_id", buyer_clerk_user_id)

    event = AuditEvent(
        actor_type="BUYER_AGENT",
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        metadata_json=meta,
    )
    db.session.add(event)
    db.session.commit()
    return event
