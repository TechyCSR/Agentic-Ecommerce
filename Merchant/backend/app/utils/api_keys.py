import hashlib
import hmac
import secrets

from flask import current_app


def generate_api_key() -> str:
    prefix = current_app.config.get("API_KEY_PREFIX", "ac_test_")
    token = secrets.token_hex(24)
    return f"{prefix}{token}"


def hash_api_key(raw_key: str) -> str:
    secret = current_app.config.get("API_KEY_SECRET", "dev-api-key-secret").encode()
    return hmac.new(secret, raw_key.encode(), hashlib.sha256).hexdigest()


def split_key_parts(raw_key: str, prefix: str):
    last4 = raw_key[-4:] if len(raw_key) >= 4 else raw_key
    return prefix, last4
