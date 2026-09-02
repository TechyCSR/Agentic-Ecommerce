import jwt
from flask import current_app
from jwt import PyJWKClient

from app.utils.exceptions import UnauthorizedError

_jwk_client_cache = {}


def _get_jwk_client():
    jwks_url = current_app.config["CLERK_JWKS_URL"]
    if jwks_url not in _jwk_client_cache:
        _jwk_client_cache[jwks_url] = PyJWKClient(jwks_url)
    return _jwk_client_cache[jwks_url]


def verify_session_token(token: str) -> dict:
    """Verify a Clerk-issued JWT session token and return its claims.

    Only verifies the signature/issuer — this service has no need to call
    the Clerk backend API, it only needs a stable buyer identifier (the
    `sub` claim) to scope chat sessions and selections.
    """
    if not token:
        raise UnauthorizedError("Missing authentication token")

    issuer = current_app.config.get("CLERK_ISSUER")

    try:
        jwk_client = _get_jwk_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer if issuer else None,
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError(f"Invalid authentication token: {exc}") from exc

    if not claims.get("sub"):
        raise UnauthorizedError("Token missing subject claim")

    return claims
