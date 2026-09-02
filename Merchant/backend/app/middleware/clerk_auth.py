from functools import wraps

from flask import g, request

from app.services.user_service import sync_user_from_clerk
from app.utils.clerk_client import verify_session_token
from app.utils.exceptions import UnauthorizedError


def _extract_bearer_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header.split(" ", 1)[1].strip()


def require_auth(fn):
    """Verify the Clerk JWT and attach the synchronized internal user to g.current_user."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            raise UnauthorizedError("Missing Authorization bearer token")

        claims = verify_session_token(token)
        clerk_user_id = claims["sub"]
        g.current_user = sync_user_from_clerk(clerk_user_id)
        return fn(*args, **kwargs)

    return wrapper
