from app.extensions import db
from app.models import ChatSession
from app.services import agent_service
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


def send_message(buyer_id: str, session_id: str, text: str):
    session = get_session_for_buyer(buyer_id, session_id)
    return agent_service.run_agent_turn(session, text)
