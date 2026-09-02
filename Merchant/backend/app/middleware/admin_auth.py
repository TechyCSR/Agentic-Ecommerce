from functools import wraps

from flask import g, request

from app.utils.admin_auth import verify_admin_token
from app.utils.exceptions import UnauthorizedError


def _extract_bearer_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header.split(" ", 1)[1].strip()


def require_admin(fn):
    """Verify the admin session JWT (separate from Clerk and API-key auth)."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            raise UnauthorizedError("Missing admin session token")

        g.admin_email = verify_admin_token(token)
        return fn(*args, **kwargs)

    return wrapper
