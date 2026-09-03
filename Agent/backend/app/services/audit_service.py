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
    commit=True,
):
    """Writes into this service's own audit_events table.

    actor_id stays NULL — a Clerk id ("user_...") isn't a UUID, so the
    buyer identifier goes in metadata instead, alongside the chat session.

    `commit=False` stages the row without its own round trip, to be flushed
    by the next commit in the same request. The database sits in a different
    region from the app (~0.6s per write), so committing every event
    separately added seconds to a chat turn. Money and failure paths keep
    committing immediately — those must survive even if the turn dies —
    while chat-flow events ride along with the message write that follows
    them, so an event and the message it describes are persisted together
    or not at all.
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
    if commit:
        db.session.commit()
    return event
