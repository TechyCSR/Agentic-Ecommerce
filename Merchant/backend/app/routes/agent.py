from flask import Blueprint, g, request

from app.middleware.api_key_auth import require_scopes
from app.models.enums import ApiScope
from app.services import audit_service, product_service, search_service
from app.utils.agent_format import product_to_agent_dict
from app.utils.pagination import build_meta, paginate_params
from app.utils.responses import success
from app.utils.search_filters import parse_search_filters

bp = Blueprint("agent", __name__, url_prefix="/api/v1/agent")


@bp.route("/catalog/search", methods=["GET"])
@require_scopes(ApiScope.CATALOG_READ.value)
def agent_search():
    limit, offset = paginate_params(request.args)
    filters = parse_search_filters(request.args)

    products, total = search_service.search_products(
        filters, limit, offset, require_agent_searchable=True
    )

    audit_service.log_event(
        actor_type="AGENT",
        actor_id=g.api_client.id,
        merchant_id=g.api_client.merchant_id,
        resource_type="CATALOG",
        action="CATALOG_SEARCHED",
        metadata={"filters": filters, "client": g.api_client.name},
    )

    return success(
        [product_to_agent_dict(p) for p in products],
        meta=build_meta(total, limit, offset),
    )


@bp.route("/products/<uuid:product_id>", methods=["GET"])
@require_scopes(ApiScope.PRODUCT_READ.value)
def agent_get_product(product_id):
    product = product_service.get_product_or_404(product_id)

    audit_service.log_event(
        actor_type="AGENT",
        actor_id=g.api_client.id,
        merchant_id=g.api_client.merchant_id,
        resource_type="PRODUCT",
        resource_id=product.id,
        action="PRODUCT_VIEWED",
        metadata={"client": g.api_client.name},
    )

    if product.status.value != "ACTIVE" or not product.is_agent_searchable:
        from app.utils.exceptions import NotFoundError

        raise NotFoundError("Product not found", code="PRODUCT_NOT_FOUND")

    return success(product_to_agent_dict(product))
