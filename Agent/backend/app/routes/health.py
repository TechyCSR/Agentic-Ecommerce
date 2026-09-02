from flask import Blueprint

from app.utils.responses import success

bp = Blueprint("health", __name__, url_prefix="/api/v1")


@bp.route("/health", methods=["GET"])
def health():
    return success({"status": "ok"})
