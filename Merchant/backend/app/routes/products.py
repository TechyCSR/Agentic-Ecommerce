from flask import Blueprint, g, request

from app.middleware.clerk_auth import require_auth
from app.schemas.product_schema import (
    ProductCreateSchema,
    ProductImageSchema,
    ProductUpdateSchema,
    ProductVariantSchema,
    VariantUpdateSchema,
)
from app.services import product_service
from app.utils.exceptions import ValidationError
from app.utils.pagination import build_meta, paginate_params
from app.utils.responses import success
from app.utils.validation import validate_payload

bp = Blueprint("products", __name__, url_prefix="/api/v1/products")


@bp.route("", methods=["POST"])
@require_auth
def create_product():
    body = request.get_json(silent=True) or {}
    store_id = body.get("store_id")
    if not store_id:
        raise ValidationError("store_id is required")

    payload = validate_payload(ProductCreateSchema(), body)
    product = product_service.create_product(g.current_user, store_id, payload)
    return success(product.to_dict(), status=201)


@bp.route("", methods=["GET"])
@require_auth
def list_products():
    limit, offset = paginate_params(request.args)
    filters = {
        "store_id": request.args.get("store_id"),
        "status": request.args.get("status"),
        "q": request.args.get("q"),
    }
    products, total = product_service.list_products_for_user(
        g.current_user, filters, limit, offset
    )
    return success(
        [p.to_dict() for p in products], meta=build_meta(total, limit, offset)
    )


@bp.route("/stats", methods=["GET"])
@require_auth
def product_stats():
    stats = product_service.get_product_stats_for_user(g.current_user)
    return success(stats)


@bp.route("/<uuid:product_id>", methods=["GET"])
@require_auth
def get_product(product_id):
    product = product_service.get_product_for_user(g.current_user, product_id)
    return success(product.to_dict())


@bp.route("/<uuid:product_id>", methods=["PATCH"])
@require_auth
def update_product(product_id):
    payload = validate_payload(ProductUpdateSchema(), request.get_json(silent=True))
    product = product_service.update_product(g.current_user, product_id, payload)
    return success(product.to_dict())


@bp.route("/<uuid:product_id>", methods=["DELETE"])
@require_auth
def delete_product(product_id):
    product_service.delete_product(g.current_user, product_id)
    return success({"deleted": True})


@bp.route("/<uuid:product_id>/activate", methods=["POST"])
@require_auth
def activate_product(product_id):
    product = product_service.activate_product(g.current_user, product_id)
    return success(product.to_dict())


@bp.route("/<uuid:product_id>/deactivate", methods=["POST"])
@require_auth
def deactivate_product(product_id):
    product = product_service.deactivate_product(g.current_user, product_id)
    return success(product.to_dict())


@bp.route("/<uuid:product_id>/archive", methods=["POST"])
@require_auth
def archive_product(product_id):
    product = product_service.archive_product(g.current_user, product_id)
    return success(product.to_dict())


# ---- Variants ----


@bp.route("/<uuid:product_id>/variants", methods=["POST"])
@require_auth
def add_variant(product_id):
    payload = validate_payload(ProductVariantSchema(), request.get_json(silent=True))
    variant = product_service.add_variant(g.current_user, product_id, payload)
    return success(variant.to_dict(), status=201)


@bp.route("/variants/<uuid:variant_id>", methods=["PATCH"])
@require_auth
def update_variant(variant_id):
    payload = validate_payload(VariantUpdateSchema(), request.get_json(silent=True))
    variant = product_service.update_variant(g.current_user, variant_id, payload)
    return success(variant.to_dict())


@bp.route("/variants/<uuid:variant_id>", methods=["DELETE"])
@require_auth
def delete_variant(variant_id):
    product_service.delete_variant(g.current_user, variant_id)
    return success({"deleted": True})


# ---- Images ----


@bp.route("/<uuid:product_id>/images", methods=["POST"])
@require_auth
def add_image(product_id):
    payload = validate_payload(ProductImageSchema(), request.get_json(silent=True))
    image = product_service.add_image(g.current_user, product_id, payload)
    return success(image.to_dict(), status=201)


@bp.route("/<uuid:product_id>/images/<uuid:image_id>", methods=["DELETE"])
@require_auth
def delete_image(product_id, image_id):
    product_service.delete_image(g.current_user, product_id, image_id)
    return success({"deleted": True})


@bp.route("/<uuid:product_id>/images/reorder", methods=["PATCH"])
@require_auth
def reorder_images(product_id):
    body = request.get_json(silent=True) or {}
    image_ids = body.get("image_ids", [])
    images = product_service.reorder_images(g.current_user, product_id, image_ids)
    return success([i.to_dict() for i in images])


@bp.route("/<uuid:product_id>/images/<uuid:image_id>/primary", methods=["PATCH"])
@require_auth
def set_primary_image(product_id, image_id):
    images = product_service.set_primary_image(g.current_user, product_id, image_id)
    return success([i.to_dict() for i in images])
