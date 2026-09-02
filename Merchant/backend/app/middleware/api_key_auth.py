from functools import wraps

from flask import g, request

from app.services.api_client_service import authenticate_api_key
from app.utils.exceptions import ForbiddenError, UnauthorizedError


def _extract_bearer_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header.split(" ", 1)[1].strip()


def require_scopes(*required_scopes):
    """Validate the API key in the Authorization header and enforce required scopes."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            api_key = _extract_bearer_token()
            if not api_key:
                raise UnauthorizedError("Missing API key")

            client = authenticate_api_key(api_key)
            client_scopes = {s.scope for s in client.scopes}

            if required_scopes and not set(required_scopes).issubset(client_scopes):
                missing = set(required_scopes) - client_scopes
                raise ForbiddenError(
                    f"Missing required scope(s): {', '.join(sorted(missing))}",
                    code="INSUFFICIENT_SCOPE",
                )

            g.api_client = client
            return fn(*args, **kwargs)

        return wrapper

    return decorator
