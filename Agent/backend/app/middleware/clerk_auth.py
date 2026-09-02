from functools import wraps

from flask import g, request

from app.utils.clerk_client import verify_session_token
from app.utils.exceptions import UnauthorizedError


def _extract_bearer_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header.split(" ", 1)[1].strip()


def require_auth(fn):
    """Verify the Clerk JWT and attach the buyer's clerk_user_id to g.buyer_id."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            raise UnauthorizedError("Missing Authorization bearer token")

        claims = verify_session_token(token)
        g.buyer_id = claims["sub"]
        return fn(*args, **kwargs)

    return wrapper
