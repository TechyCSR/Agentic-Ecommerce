from flask import Blueprint, g, request

from app.middleware.admin_auth import require_admin
from app.schemas.api_client_schema import ApiClientCreateSchema
from app.services import api_client_service
from app.utils.admin_auth import create_admin_token, verify_admin_credentials
from app.utils.exceptions import UnauthorizedError
from app.utils.responses import success
from app.utils.validation import validate_payload

bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


@bp.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not verify_admin_credentials(email, password):
        raise UnauthorizedError("Invalid admin credentials")

    token, expires_at = create_admin_token(email)
    return success({"token": token, "expires_at": expires_at, "email": email})


@bp.route("/api-clients", methods=["GET"])
@require_admin
def list_api_clients():
    clients = api_client_service.list_all_api_clients()
    return success([c.to_dict() for c in clients])


@bp.route("/api-clients", methods=["POST"])
@require_admin
def create_api_client():
    payload = validate_payload(ApiClientCreateSchema(), request.get_json(silent=True))
    client, raw_key = api_client_service.create_central_api_client(g.admin_email, payload)

    data = client.to_dict()
    # The raw API key is only ever returned once, at creation time.
    data["api_key"] = raw_key
    return success(data, status=201)


@bp.route("/api-clients/<uuid:client_id>/revoke", methods=["POST"])
@require_admin
def revoke_api_client(client_id):
    client = api_client_service.revoke_api_client(g.admin_email, client_id)
    return success(client.to_dict())
