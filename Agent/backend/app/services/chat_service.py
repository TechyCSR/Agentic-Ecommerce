from app.extensions import db
from app.models import ChatSession
from app.services import agent_service, audit_service
from app.utils.exceptions import ForbiddenError, NotFoundError


def create_session(buyer_id: str) -> ChatSession:
    session = ChatSession(buyer_clerk_user_id=buyer_id)
    db.session.add(session)
    db.session.commit()
    return session


def list_sessions(buyer_id: str) -> list[ChatSession]:
    return (
        ChatSession.query.filter_by(buyer_clerk_user_id=buyer_id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )


def get_session_for_buyer(buyer_id: str, session_id) -> ChatSession:
    session = ChatSession.query.get(session_id)
    if not session:
        raise NotFoundError("Chat session not found", code="SESSION_NOT_FOUND")
    if session.buyer_clerk_user_id != buyer_id:
        raise ForbiddenError(
            "You do not have access to this chat session", code="SESSION_FORBIDDEN"
        )
    return session


def stream_message(buyer_id: str, session_id: str, text: str):
    session = get_session_for_buyer(buyer_id, session_id)
    return agent_service.stream_agent_turn(session, text)


def rename_session(buyer_id: str, session_id: str, title: str) -> ChatSession:
    session = get_session_for_buyer(buyer_id, session_id)
    session.title = title.strip()[:80] or session.title
    db.session.commit()
    return session


def delete_session(buyer_id: str, session_id: str) -> None:
    session = get_session_for_buyer(buyer_id, session_id)
    # A Telegram link may point at this session; the FK would otherwise
    # block the delete with a 500. Clearing it just starts that user a
    # fresh conversation next message.
    from app.models import TelegramLink

    TelegramLink.query.filter_by(session_id=session.id).update({"session_id": None})
    db.session.delete(session)
    db.session.commit()


def upsert_buyer_profile(buyer_id: str, email: str, display_name=None):
    """Keeps one email per buyer, and one buyer per email."""
    from app.models import BuyerProfile
    from app.utils.exceptions import ValidationError

    email = email.strip().lower()

    taken = BuyerProfile.query.filter(
        db.func.lower(BuyerProfile.email) == email,
        BuyerProfile.clerk_user_id != buyer_id,
    ).first()
    if taken is not None:
        raise ValidationError(
            "That email is already linked to a different account.",
            code="EMAIL_ALREADY_LINKED",
        )

    profile = BuyerProfile.query.filter_by(clerk_user_id=buyer_id).first()
    if profile is None:
        profile = BuyerProfile(clerk_user_id=buyer_id, email=email, display_name=display_name)
        db.session.add(profile)
    else:
        profile.email = email
        if display_name:
            profile.display_name = display_name
    db.session.commit()
    return profile


def truncate_from_message(buyer_id: str, session_id, message_id) -> int:
    """Removes a message and everything after it in the conversation.

    Used by "edit" and "regenerate", which rewrite the conversation from a
    point rather than appending a fresh exchange — otherwise the old and new
    answers both stay on screen and the agent keeps the stale turn in
    context.

    Orders and cart lines are untouched: they are records of what happened,
    and deleting a chat message must not erase them.
    """
    from app.models import ChatMessage

    session = get_session_for_buyer(buyer_id, session_id)
    target = ChatMessage.query.get(message_id)
    if target is None or target.session_id != session.id:
        raise NotFoundError("Message not found in this chat.", code="MESSAGE_NOT_FOUND")

    doomed = (
        ChatMessage.query.filter(
            ChatMessage.session_id == session.id,
            ChatMessage.created_at >= target.created_at,
        )
        .order_by(ChatMessage.created_at)
        .all()
    )
    removed = len(doomed)
    for message in doomed:
        db.session.delete(message)
    db.session.commit()

    audit_service.log_event(
        action="CHAT_TRUNCATED",
        session_id=session.id,
        buyer_clerk_user_id=buyer_id,
        metadata={"from_message_id": str(message_id), "removed": removed},
    )
    return removed
