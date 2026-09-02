from flask import Blueprint, g, request

from app.middleware.clerk_auth import require_auth
from app.schemas.api_client_schema import ApiClientCreateSchema
from app.services import api_client_service
from app.utils.responses import success
from app.utils.validation import validate_payload

bp = Blueprint("api_clients", __name__, url_prefix="/api/v1/api-clients")


@bp.route("", methods=["POST"])
@require_auth
def create_api_client():
    payload = validate_payload(ApiClientCreateSchema(), request.get_json(silent=True))
    client, raw_key = api_client_service.create_api_client(g.current_user, payload)

    data = client.to_dict()
    # The raw API key is only ever returned once, at creation time.
    data["api_key"] = raw_key
    return success(data, status=201)


@bp.route("", methods=["GET"])
@require_auth
def list_api_clients():
    clients = api_client_service.list_api_clients_for_user(g.current_user)
    return success([c.to_dict() for c in clients])


@bp.route("/<uuid:client_id>", methods=["GET"])
@require_auth
def get_api_client(client_id):
    client = api_client_service.get_api_client_for_user(g.current_user, client_id)
    return success(client.to_dict())


@bp.route("/<uuid:client_id>/revoke", methods=["POST"])
@require_auth
def revoke_api_client(client_id):
    client = api_client_service.revoke_api_client(g.current_user, client_id)
    return success(client.to_dict())
