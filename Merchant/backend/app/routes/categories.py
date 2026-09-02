from flask import Blueprint, request

from app.middleware.clerk_auth import require_auth
from app.services import category_service
from app.utils.responses import success

bp = Blueprint("categories", __name__, url_prefix="/api/v1/categories")


@bp.route("", methods=["GET"])
def list_categories():
    categories = category_service.list_categories()
    return success([c.to_dict() for c in categories])


@bp.route("", methods=["POST"])
@require_auth
def create_category():
    category = category_service.create_category(request.get_json(silent=True) or {})
    return success(category.to_dict(), status=201)
