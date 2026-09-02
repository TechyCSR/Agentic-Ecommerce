from flask import Blueprint, g, request

from app.middleware.clerk_auth import require_auth
from app.schemas.store_schema import StoreCreateSchema, StoreUpdateSchema
from app.services import store_service
from app.utils.responses import success
from app.utils.validation import validate_payload

bp = Blueprint("stores", __name__, url_prefix="/api/v1/stores")


@bp.route("", methods=["POST"])
@require_auth
def create_store():
    payload = validate_payload(StoreCreateSchema(), request.get_json(silent=True))
    store = store_service.create_store(g.current_user, payload)
    return success(store.to_dict(), status=201)


@bp.route("", methods=["GET"])
@require_auth
def list_stores():
    stores = store_service.list_stores_for_user(g.current_user)
    return success([s.to_dict() for s in stores])


@bp.route("/<uuid:store_id>", methods=["GET"])
@require_auth
def get_store(store_id):
    store = store_service.get_store_for_user(g.current_user, store_id)
    return success(store.to_dict())


@bp.route("/<uuid:store_id>", methods=["PATCH"])
@require_auth
def update_store(store_id):
    payload = validate_payload(StoreUpdateSchema(), request.get_json(silent=True))
    store = store_service.update_store(g.current_user, store_id, payload)
    return success(store.to_dict())
