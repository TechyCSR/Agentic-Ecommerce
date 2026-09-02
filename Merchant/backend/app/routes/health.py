from flask import Blueprint

from app.utils.responses import success

bp = Blueprint("health", __name__)


@bp.route("/health", methods=["GET"])
@bp.route("/api/v1/health", methods=["GET"])
def health():
    return success({"status": "ok"})
