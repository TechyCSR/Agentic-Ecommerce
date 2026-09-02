from app.extensions import db
from app.models import User
from app.utils.clerk_client import extract_primary_email, get_clerk_user
from app.utils.exceptions import UnauthorizedError


def sync_user_from_clerk(clerk_user_id: str) -> User:
    """Find the internal user for a Clerk user id, creating it on first sight."""
    user = User.query.filter_by(clerk_user_id=clerk_user_id).first()
    if user:
        return user

    clerk_user = get_clerk_user(clerk_user_id)
    if not clerk_user:
        raise UnauthorizedError("Unable to resolve authenticated user")

    email = extract_primary_email(clerk_user)
    if not email:
        raise UnauthorizedError("Authenticated user has no email address")

    user = User(
        clerk_user_id=clerk_user_id,
        email=email,
        first_name=clerk_user.get("first_name"),
        last_name=clerk_user.get("last_name"),
        profile_image_url=clerk_user.get("image_url"),
    )
    db.session.add(user)
    db.session.commit()
    return user
