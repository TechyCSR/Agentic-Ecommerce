import time

import jwt
import requests
from flask import current_app
from jwt import PyJWKClient

from app.utils.exceptions import UnauthorizedError

_jwk_client_cache = {}
_user_cache = {}
_USER_CACHE_TTL_SECONDS = 60


def _get_jwk_client():
    jwks_url = current_app.config["CLERK_JWKS_URL"]
    if jwks_url not in _jwk_client_cache:
        _jwk_client_cache[jwks_url] = PyJWKClient(jwks_url)
    return _jwk_client_cache[jwks_url]


def verify_session_token(token: str) -> dict:
    """Verify a Clerk-issued JWT session token and return its claims."""
    if not token:
        raise UnauthorizedError("Missing authentication token")

    issuer = current_app.config.get("CLERK_ISSUER")

    try:
        jwk_client = _get_jwk_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        options = {"verify_aud": False}
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer if issuer else None,
            options=options,
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError(f"Invalid authentication token: {exc}") from exc

    if not claims.get("sub"):
        raise UnauthorizedError("Token missing subject claim")

    return claims


def get_clerk_user(clerk_user_id: str) -> dict:
    """Fetch profile info for a Clerk user from the Clerk Backend API."""
    now = time.time()
    cached = _user_cache.get(clerk_user_id)
    if cached and now - cached["fetched_at"] < _USER_CACHE_TTL_SECONDS:
        return cached["data"]

    secret_key = current_app.config.get("CLERK_SECRET_KEY")
    if not secret_key:
        return {}

    response = requests.get(
        f"https://api.clerk.com/v1/users/{clerk_user_id}",
        headers={"Authorization": f"Bearer {secret_key}"},
        timeout=10,
    )
    if response.status_code != 200:
        return {}

    data = response.json()
    _user_cache[clerk_user_id] = {"data": data, "fetched_at": now}
    return data


def extract_primary_email(clerk_user: dict) -> str | None:
    email_addresses = clerk_user.get("email_addresses") or []
    primary_id = clerk_user.get("primary_email_address_id")
    for entry in email_addresses:
        if entry.get("id") == primary_id:
            return entry.get("email_address")
    if email_addresses:
        return email_addresses[0].get("email_address")
    return None
