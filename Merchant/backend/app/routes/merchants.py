from flask import Blueprint, g, request

from app.middleware.clerk_auth import require_auth
from app.schemas.merchant_schema import MerchantCreateSchema, MerchantUpdateSchema
from app.services import merchant_service
from app.utils.responses import success
from app.utils.validation import validate_payload

bp = Blueprint("merchants", __name__, url_prefix="/api/v1/merchants")


@bp.route("", methods=["POST"])
@require_auth
def create_merchant():
    payload = validate_payload(MerchantCreateSchema(), request.get_json(silent=True))
    merchant = merchant_service.create_merchant(g.current_user, payload)
    return success(merchant.to_dict(), status=201)


@bp.route("/me", methods=["GET"])
@require_auth
def get_my_merchant():
    merchant = merchant_service.get_merchant_for_user(g.current_user)
    return success(merchant.to_dict())


@bp.route("/me", methods=["PATCH"])
@require_auth
def update_my_merchant():
    payload = validate_payload(MerchantUpdateSchema(), request.get_json(silent=True))
    merchant = merchant_service.update_merchant(g.current_user, payload)
    return success(merchant.to_dict())
