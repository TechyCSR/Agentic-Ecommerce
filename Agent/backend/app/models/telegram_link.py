from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class TelegramLink(TimestampMixin, UUIDPrimaryKeyMixin, db.Model):
    """One Telegram account and the chat state that belongs to it.

    The row exists for every Telegram user who talks to the bot, linked or
    not: an unlinked user can still browse products, they just have no
    `buyer_clerk_user_id` and therefore no access to anyone's orders.

    `/logout` clears the link rather than deleting the row, so the chat
    session survives and the same person can log back in — and so an
    audit trail of the connection remains.
    """

    __tablename__ = "telegram_links"

    telegram_user_id = db.Column(db.BigInteger, nullable=False, unique=True, index=True)
    telegram_chat_id = db.Column(db.BigInteger, nullable=False)
    telegram_username = db.Column(db.String(255), nullable=True)

    # NULL until the user runs /login. Everything account-scoped keys off
    # this, so an unlinked Telegram user can never reach another account.
    buyer_clerk_user_id = db.Column(db.String(255), nullable=True, index=True)
    linked_email = db.Column(db.String(255), nullable=True)
    linked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # The buyer's ongoing conversation, so Telegram has the same memory the
    # web chat does rather than starting fresh each message.
    session_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("chat_sessions.id"), nullable=True
    )

    @property
    def is_linked(self) -> bool:
        return bool(self.buyer_clerk_user_id)

    def buyer_id(self) -> str:
        """The identity used to scope chat, cart and orders.

        Unlinked users get a namespaced pseudo-id so they can still browse
        and keep conversation context, while owning no orders — the account
        scoping that protects real buyers needs no special case.
        """
        return self.buyer_clerk_user_id or f"tg:{self.telegram_user_id}"

    def to_dict(self):
        return {
            "telegram_user_id": self.telegram_user_id,
            "telegram_username": self.telegram_username,
            "is_linked": self.is_linked,
            "linked_email": self.linked_email,
            "linked_at": self.linked_at.isoformat() if self.linked_at else None,
        }
