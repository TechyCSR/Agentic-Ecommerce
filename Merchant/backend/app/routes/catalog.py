from flask import Blueprint, g, request

from app.middleware.clerk_auth import require_auth
from app.services import audit_service, search_service
from app.utils.pagination import build_meta, paginate_params
from app.utils.responses import success
from app.utils.search_filters import parse_search_filters

bp = Blueprint("catalog", __name__, url_prefix="/api/v1/catalog")


@bp.route("/search", methods=["GET"])
@require_auth
def search():
    limit, offset = paginate_params(request.args)
    filters = parse_search_filters(request.args)

    products, total = search_service.search_products(filters, limit, offset)

    audit_service.log_event(
        actor_type="USER",
        actor_id=g.current_user.id,
        resource_type="CATALOG",
        action="CATALOG_SEARCHED",
        metadata={"filters": filters},
    )

    return success(
        [p.to_dict() for p in products], meta=build_meta(total, limit, offset)
    )
