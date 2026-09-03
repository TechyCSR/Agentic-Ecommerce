from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class BuyerProfile(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Maps a buyer's Clerk id to their email.

    This service verifies Clerk JWTs but never calls Clerk's backend API, so
    it has no other way to answer "which account owns this email?" — which
    Telegram's `/login <email>` needs. The row is written when the signed-in
    web app syncs its profile, so the Clerk id always comes from a verified
    token.
    """

    __tablename__ = "buyer_profiles"

    clerk_user_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    display_name = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "clerk_user_id": self.clerk_user_id,
            "email": self.email,
            "display_name": self.display_name,
        }
