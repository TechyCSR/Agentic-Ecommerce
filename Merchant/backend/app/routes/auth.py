from flask import Blueprint, g

from app.middleware.clerk_auth import require_auth
from app.models import Merchant
from app.utils.responses import success

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@bp.route("/me", methods=["GET"])
@require_auth
def me():
    user = g.current_user
    merchant = Merchant.query.filter_by(owner_user_id=user.id).first()
    data = user.to_dict()
    data["merchant"] = merchant.to_dict() if merchant else None
    return success(data)
