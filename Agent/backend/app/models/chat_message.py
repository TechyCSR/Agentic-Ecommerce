from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.extensions import db
from app.models.base import UUIDPrimaryKeyMixin, utcnow
from app.models.enums import MessageRole


class ChatMessage(UUIDPrimaryKeyMixin, db.Model):
    __tablename__ = "chat_messages"

    session_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("chat_sessions.id"), nullable=False, index=True
    )

    role = db.Column(SAEnum(MessageRole, name="message_role"), nullable=False)
    content = db.Column(db.Text, nullable=False)

    # Structured product data surfaced by this turn's tool calls — kept
    # separate from the prose reply, and always sourced from raw tool
    # results, never parsed out of the model's text.
    product_cards = db.Column(JSONB, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    session = db.relationship("ChatSession", back_populates="messages")

    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "role": self.role.value if self.role else None,
            "content": self.content,
            "product_cards": self.product_cards,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
