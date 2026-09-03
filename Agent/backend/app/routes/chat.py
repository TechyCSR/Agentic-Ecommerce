import json

from flask import Blueprint, Response, g, request, stream_with_context

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


@bp.route("/sessions/<uuid:session_id>", methods=["PATCH"])
@require_auth
def rename_session(session_id):
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title:
        raise ValidationError("title is required")
    session = chat_service.rename_session(g.buyer_id, session_id, title)
    return success(session.to_dict())


@bp.route("/sessions/<uuid:session_id>", methods=["DELETE"])
@require_auth
def delete_session(session_id):
    chat_service.delete_session(g.buyer_id, session_id)
    return success(None, status=200)


@bp.route("/sessions/<uuid:session_id>/messages", methods=["POST"])
@require_auth
def send_message(session_id):
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        raise ValidationError("Message text is required")

    # get_session_for_buyer runs eagerly here (stream_message calls it
    # before constructing the agent_service generator), so an unknown/
    # forbidden session still raises a normal JSON error instead of a
    # broken stream — only genuine mid-turn failures (network, catalog,
    # LLM) get surfaced as an `error` SSE event below.
    events = chat_service.stream_message(g.buyer_id, session_id, text)

    def generate():
        try:
            for event in events:
                yield f"data: {json.dumps(event)}\n\n"
        except Exception:  # noqa: BLE001 — headers are already committed to text/event-stream; a raised exception here must become an SSE event, never a broken connection
            yield (
                "data: "
                + json.dumps({"type": "error", "message": "Something went wrong. Please try again."})
                + "\n\n"
            )

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@bp.route("/sessions/<uuid:session_id>/select", methods=["POST"])
@require_auth
def add_to_cart(session_id):
    body = request.get_json(silent=True) or {}
    product_id = body.get("product_id")
    variant_id = body.get("variant_id")
    quantity = int(body.get("quantity") or 1)
    if not product_id or not variant_id:
        raise ValidationError("product_id and variant_id are required")

    item = selection_service.add_to_cart(g.buyer_id, session_id, product_id, variant_id, quantity)
    return success(item.to_dict(), status=201)


@bp.route("/sessions/<uuid:session_id>/select/<uuid:selection_id>", methods=["PATCH"])
@require_auth
def update_cart_item(session_id, selection_id):
    body = request.get_json(silent=True) or {}
    quantity = body.get("quantity")
    if quantity is None:
        raise ValidationError("quantity is required")

    item = selection_service.update_quantity(g.buyer_id, session_id, selection_id, int(quantity))
    return success(item.to_dict())


@bp.route("/sessions/<uuid:session_id>/select/<uuid:selection_id>", methods=["DELETE"])
@require_auth
def remove_cart_item(session_id, selection_id):
    selection_service.remove_from_cart(g.buyer_id, session_id, selection_id)
    return success(None, status=200)


@bp.route("/sessions/<uuid:session_id>/selection", methods=["GET"])
@require_auth
def get_cart(session_id):
    cart = selection_service.get_cart(g.buyer_id, session_id)
    return success(cart)


@bp.route("/me", methods=["POST"])
@require_auth
def sync_profile():
    """Records the signed-in buyer's email so other channels can find them.

    The Clerk id comes from the verified JWT; the email is taken from the
    token's claims when Clerk includes them, and otherwise from the signed-in
    web app. An email already registered to a different Clerk id is refused,
    so one account cannot claim another's address and intercept its
    Telegram `/login`.
    """
    body = request.get_json(silent=True) or {}
    claims = getattr(g, "claims", {}) or {}
    email = (claims.get("email") or body.get("email") or "").strip().lower()
    if not email or "@" not in email:
        raise ValidationError("A valid email is required")

    profile = chat_service.upsert_buyer_profile(
        g.buyer_id, email, body.get("display_name")
    )
    return success(profile.to_dict())


@bp.route("/sessions/<uuid:session_id>/truncate", methods=["POST"])
@require_auth
def truncate_session(session_id):
    """Drops a message and everything after it, so an edited or regenerated
    turn replaces the old one instead of stacking on top of it."""
    body = request.get_json(silent=True) or {}
    message_id = body.get("message_id")
    if not message_id:
        raise ValidationError("message_id is required")
    removed = chat_service.truncate_from_message(g.buyer_id, session_id, message_id)
    return success({"removed": removed})
