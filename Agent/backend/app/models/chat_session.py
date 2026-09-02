from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ChatSession(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "chat_sessions"

    buyer_clerk_user_id = db.Column(db.String(255), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=True)

    messages = db.relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
    selections = db.relationship(
        "SelectedProduct",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SelectedProduct.created_at",
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
