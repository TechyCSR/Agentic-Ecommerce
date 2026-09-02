from flask import Blueprint, g, request

from app.middleware.clerk_auth import require_auth
from app.services import chat_service, selection_service
from app.utils.exceptions import ValidationError
from app.utils.responses import success

bp = Blueprint("chat", __name__, url_prefix="/api/v1/chat")


@bp.route("/sessions", methods=["POST"])
@require_auth
def create_session():
    session = chat_service.create_session(g.buyer_id)
    return success(session.to_dict(), status=201)


@bp.route("/sessions", methods=["GET"])
@require_auth
def list_sessions():
    sessions = chat_service.list_sessions(g.buyer_id)
    return success([s.to_dict() for s in sessions])


@bp.route("/sessions/<uuid:session_id>", methods=["GET"])
@require_auth
def get_session(session_id):
    session = chat_service.get_session_for_buyer(g.buyer_id, session_id)
    data = session.to_dict()
    data["messages"] = [m.to_dict() for m in session.messages]
    return success(data)


@bp.route("/sessions/<uuid:session_id>/messages", methods=["POST"])
@require_auth
def send_message(session_id):
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        raise ValidationError("Message text is required")

    reply = chat_service.send_message(g.buyer_id, session_id, text)
    return success(reply.to_dict(), status=201)


@bp.route("/sessions/<uuid:session_id>/select", methods=["POST"])
@require_auth
def select_product(session_id):
    body = request.get_json(silent=True) or {}
    product_id = body.get("product_id")
    variant_id = body.get("variant_id")
    if not product_id or not variant_id:
        raise ValidationError("product_id and variant_id are required")

    selection = selection_service.select_product(g.buyer_id, session_id, product_id, variant_id)
    return success(selection.to_dict(), status=201)


@bp.route("/sessions/<uuid:session_id>/selection", methods=["GET"])
@require_auth
def get_selection(session_id):
    selection = selection_service.get_active_selection(g.buyer_id, session_id)
    return success(selection.to_dict() if selection else None)
