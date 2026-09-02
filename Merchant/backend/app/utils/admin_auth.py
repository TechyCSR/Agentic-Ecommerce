from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app

from app.utils.exceptions import UnauthorizedError

ADMIN_TOKEN_TTL = timedelta(hours=12)


def verify_admin_credentials(email: str, password: str) -> bool:
    configured_email = current_app.config.get("ADMIN_EMAIL", "")
    configured_password = current_app.config.get("ADMIN_PASSWORD", "")
    if not configured_email or not configured_password:
        return False
    return email == configured_email and password == configured_password


def create_admin_token(email: str) -> tuple[str, str]:
    secret = current_app.config["ADMIN_JWT_SECRET"]
    now = datetime.now(timezone.utc)
    expires_at = now + ADMIN_TOKEN_TTL
    token = jwt.encode(
        {"sub": email, "role": "admin", "iat": now, "exp": expires_at},
        secret,
        algorithm="HS256",
    )
    return token, expires_at.isoformat()


def verify_admin_token(token: str) -> str:
    secret = current_app.config["ADMIN_JWT_SECRET"]
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired admin session") from exc

    if claims.get("role") != "admin" or not claims.get("sub"):
        raise UnauthorizedError("Invalid admin session")

    return claims["sub"]
