from datetime import datetime, timezone

from flask import current_app

from app.extensions import db
from app.models import ApiClient, ApiClientScope
from app.models.enums import PHASE1_ENABLED_SCOPES, ApiClientStatus, ApiClientType
from app.services import audit_service
from app.services.merchant_service import get_merchant_for_user
from app.utils.api_keys import generate_api_key, hash_api_key
from app.utils.exceptions import (
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


def create_api_client(user, payload):
    merchant = get_merchant_for_user(user)

    name = payload.get("name")
    if not name:
        raise ValidationError("API client name is required")

    scopes = payload.get("scopes") or list(PHASE1_ENABLED_SCOPES)
    invalid_scopes = [s for s in scopes if s not in PHASE1_ENABLED_SCOPES]
    if invalid_scopes:
        raise ValidationError(f"Unsupported scope(s) for Phase 1: {invalid_scopes}")

    client_type = payload.get("client_type", ApiClientType.AUTHORIZED_AGENT.value)

    prefix = current_app.config.get("API_KEY_PREFIX", "ac_test_")
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    last4 = raw_key[-4:]

    client = ApiClient(
        merchant_id=merchant.id,
        name=name,
        client_type=ApiClientType(client_type),
        api_key_hash=key_hash,
        api_key_prefix=prefix,
        api_key_last4=last4,
        status=ApiClientStatus.ACTIVE,
    )
    db.session.add(client)
    db.session.flush()

    for scope in scopes:
        db.session.add(ApiClientScope(api_client_id=client.id, scope=scope))

    db.session.commit()

    audit_service.log_event(
        actor_type="USER",
        actor_id=user.id,
        merchant_id=merchant.id,
        resource_type="API_CLIENT",
        resource_id=client.id,
        action="API_KEY_CREATED",
        metadata={"name": client.name, "scopes": scopes},
    )

    return client, raw_key


def list_api_clients_for_user(user):
    merchant = get_merchant_for_user(user)
    return (
        ApiClient.query.filter_by(merchant_id=merchant.id)
        .order_by(ApiClient.created_at.desc())
        .all()
    )


def get_api_client_for_user(user, client_id):
    client = ApiClient.query.get(client_id)
    if not client:
        raise NotFoundError("API client not found", code="API_CLIENT_NOT_FOUND")
    merchant = get_merchant_for_user(user)
    if client.merchant_id != merchant.id:
        raise ForbiddenError(
            "You do not have access to this API client", code="API_CLIENT_FORBIDDEN"
        )
    return client


def revoke_api_client(user, client_id):
    client = get_api_client_for_user(user, client_id)
    client.status = ApiClientStatus.REVOKED
    db.session.commit()

    audit_service.log_event(
        actor_type="USER",
        actor_id=user.id,
        merchant_id=client.merchant_id,
        resource_type="API_CLIENT",
        resource_id=client.id,
        action="API_KEY_REVOKED",
    )
    return client


def authenticate_api_key(raw_key: str) -> ApiClient:
    key_hash = hash_api_key(raw_key)
    client = ApiClient.query.filter_by(api_key_hash=key_hash).first()

    if not client:
        raise UnauthorizedError("Invalid API key", code="INVALID_API_KEY")

    if client.status != ApiClientStatus.ACTIVE:
        raise ForbiddenError("API key is not active", code="API_KEY_INACTIVE")

    client.last_used_at = datetime.now(timezone.utc)
    db.session.commit()

    return client
