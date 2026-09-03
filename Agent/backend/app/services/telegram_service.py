"""Telegram as a second front-end onto the existing shopping agent.

Nothing here is a second implementation of anything. Messages go through
`chat_service.stream_message` — the same agent, tools, catalog, cart,
checkout and audit trail the web chat uses. This module only translates
between Telegram's API and that existing flow.

Account scoping is the one thing worth reading closely: every account-aware
operation keys off `TelegramLink.buyer_id()`. A linked user resolves to
their Clerk id; an unlinked one resolves to a namespaced `tg:<id>` that
simply owns no orders. So "don't leak another user's data" needs no special
case — an unlinked Telegram user queries their own empty world, and a linked
one can only ever reach the account their Telegram id is mapped to. Order
ids from the user are never trusted as a lookup key.
"""

import threading
from datetime import datetime, timezone

import requests
from flask import current_app

from app.extensions import db
from app.models import BuyerProfile, ChatSession, TelegramLink
from app.services import audit_service, checkout_service, selection_service

API_BASE = "https://api.telegram.org"
SEND_TIMEOUT = 15
# Telegram caps a message at 4096 chars; leave room for our own formatting.
MAX_MESSAGE = 3500
# How many products to push as rich cards before falling back to a summary.
MAX_PRODUCT_CARDS = 4

WELCOME = (
    "*Welcome to Agentic Commerce.*\n\n"
    "I can help you discover products, compare options, answer product "
    "questions, and help you complete a purchase.\n\n"
    "To connect your existing account, use:\n"
    "`/login your-email@example.com`\n\n"
    "If you don't have an existing account, you can still explore products.\n\n"
    "*Commands*\n"
    "/login <email> — Connect your account\n"
    "/logout — Disconnect your account\n"
    "/help — Show available commands"
)

HELP = (
    "*Commands*\n"
    "/login <email> — Connect your account\n"
    "/logout — Disconnect your account\n"
    "/help — Show available commands\n\n"
    "You can chat naturally with me to search, compare, and purchase products."
)

TOOL_NOTICES = {
    "search_catalog": "🔎 Searching products...",
    "get_product_details": "📦 Checking product details...",
    "get_order_status": "✓ Finding your latest order...",
}


# ---- Telegram API ----


def _token() -> str:
    return current_app.config.get("TELEGRAM_BOT_TOKEN") or ""


def _api(method: str, payload: dict):
    token = _token()
    if not token:
        return None
    try:
        resp = requests.post(
            f"{API_BASE}/bot{token}/{method}", json=payload, timeout=SEND_TIMEOUT
        )
        return resp.json()
    except requests.RequestException:
        # A failed send must never break the turn that triggered it.
        return None


def send_message(chat_id: int, text: str, buttons: list | None = None, preview: bool = False):
    payload = {
        "chat_id": chat_id,
        "text": text[:MAX_MESSAGE],
        "parse_mode": "Markdown",
        "link_preview_options": {"is_disabled": not preview},
    }
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    return _api("sendMessage", payload)


def send_photo(chat_id: int, photo_url: str, caption: str, buttons: list | None = None):
    payload = {"chat_id": chat_id, "photo": photo_url, "caption": caption[:1000], "parse_mode": "Markdown"}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    return _api("sendPhoto", payload)


def answer_callback(callback_id: str, text: str = ""):
    return _api("answerCallbackQuery", {"callback_query_id": callback_id, "text": text[:200]})


def send_typing(chat_id: int):
    return _api("sendChatAction", {"chat_id": chat_id, "action": "typing"})


# ---- Identity ----


def get_or_create_link(tg_user: dict, chat_id: int) -> TelegramLink:
    link = TelegramLink.query.filter_by(telegram_user_id=tg_user["id"]).first()
    if link is None:
        link = TelegramLink(
            telegram_user_id=tg_user["id"],
            telegram_chat_id=chat_id,
            telegram_username=tg_user.get("username"),
        )
        db.session.add(link)
        db.session.commit()
    elif link.telegram_chat_id != chat_id:
        link.telegram_chat_id = chat_id
        db.session.commit()
    return link


def get_session(link: TelegramLink) -> ChatSession:
    """One long-running conversation per Telegram user, so context carries
    across messages the way it does on the web."""
    session = ChatSession.query.get(link.session_id) if link.session_id else None
    # A session belongs to a buyer id; after login/logout the identity
    # changes, so a fresh session is started rather than leaking the
    # previous identity's conversation.
    if session is None or session.buyer_clerk_user_id != link.buyer_id():
        session = ChatSession(buyer_clerk_user_id=link.buyer_id(), title="Telegram chat")
        db.session.add(session)
        db.session.commit()
        link.session_id = session.id
        db.session.commit()
    return session


def login(link: TelegramLink, email: str) -> tuple[bool, str]:
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False, "Please provide a valid email, like `/login you@example.com`"

    profile = BuyerProfile.query.filter(
        db.func.lower(BuyerProfile.email) == email
    ).first()
    if profile is None:
        return False, (
            "We couldn't find an account with that email.\n\n"
            "Please use an existing account email — sign in on the web app first "
            "if you haven't already."
        )

    link.buyer_clerk_user_id = profile.clerk_user_id
    link.linked_email = profile.email
    link.linked_at = datetime.now(timezone.utc)
    link.session_id = None  # start a session under the newly linked identity
    db.session.commit()

    audit_service.log_event(
        action="TELEGRAM_ACCOUNT_LINKED",
        buyer_clerk_user_id=profile.clerk_user_id,
        metadata={"telegram_user_id": link.telegram_user_id, "email": profile.email},
    )
    return True, (
        "✓ Your Telegram account is now connected.\n\n"
        "You can continue your shopping conversations and access your orders here."
    )


def logout(link: TelegramLink) -> str:
    if not link.is_linked:
        return "You're not connected to an account right now."
    previous = link.buyer_clerk_user_id
    link.buyer_clerk_user_id = None
    link.linked_email = None
    link.linked_at = None
    link.session_id = None  # don't leave the linked conversation reachable
    db.session.commit()
    audit_service.log_event(
        action="TELEGRAM_ACCOUNT_UNLINKED",
        buyer_clerk_user_id=previous,
        metadata={"telegram_user_id": link.telegram_user_id},
    )
    return "You have been logged out successfully."


# ---- Agent bridge ----


def _product_buttons(card: dict, link: TelegramLink) -> list:
    variants = card.get("variants") or []
    in_stock = next((v for v in variants if v.get("availability") == "IN_STOCK"), None)
    buttons = []
    if in_stock:
        buttons.append(
            [{
                "text": "🛒 Select product",
                "callback_data": f"sel:{card['product_id']}:{in_stock['variant_id']}"[:64],
            }]
        )
    return buttons


def _send_products(chat_id: int, cards: list, link: TelegramLink):
    for card in cards[:MAX_PRODUCT_CARDS]:
        price = card.get("price") or {}
        amount = price.get("amount")
        price_text = f"₹{amount / 100:,.0f}" if amount else "Price unavailable"
        desc = (card.get("description") or "").strip()
        if len(desc) > 180:
            desc = desc[:180].rsplit(" ", 1)[0] + "…"

        caption = f"*{card.get('name')}*\n\n{price_text}"
        if card.get("brand"):
            caption += f"  ·  {card['brand']}"
        if desc:
            caption += f"\n\n{desc}"
        if card.get("availability") != "IN_STOCK":
            caption += "\n\n_Currently out of stock_"

        buttons = _product_buttons(card, link)
        image = card.get("image_url")
        if image:
            sent = send_photo(chat_id, image, caption, buttons)
            if sent and sent.get("ok"):
                continue
        # Photo can fail on an unreachable image host; text still works.
        send_message(chat_id, caption, buttons)

    if len(cards) > MAX_PRODUCT_CARDS:
        send_message(chat_id, f"_…and {len(cards) - MAX_PRODUCT_CARDS} more. Ask me to narrow it down._")


def handle_agent_message(link: TelegramLink, text: str):
    """Runs one turn through the existing agent and renders it for Telegram."""
    from app.services import chat_service

    chat_id = link.telegram_chat_id
    session = get_session(link)
    send_typing(chat_id)

    reply = ""
    cards: list = []
    notified: set = set()

    try:
        for event in chat_service.stream_message(link.buyer_id(), session.id, text):
            kind = event.get("type")
            if kind == "token":
                reply += event["delta"]
            elif kind == "retract":
                reply = ""
            elif kind == "tool_start":
                notice = TOOL_NOTICES.get(event.get("tool"))
                # One notice per tool per turn, so a multi-step turn doesn't spam.
                if notice and event.get("tool") not in notified:
                    notified.add(event.get("tool"))
                    send_message(chat_id, notice)
            elif kind == "product_cards":
                cards = event.get("cards") or []
            elif kind == "error":
                send_message(chat_id, "Something went wrong while processing your request. Please try again.")
                return
    except Exception:  # noqa: BLE001 — a bot reply must never surface a traceback
        send_message(chat_id, "Something went wrong while processing your request. Please try again.")
        return

    if reply.strip():
        send_message(chat_id, reply.strip())
    if cards:
        _send_products(chat_id, cards, link)

    # An unlinked user asking about their own orders gets a nudge rather than
    # a confusing "you have no orders".
    if not link.is_linked and _looks_account_scoped(text):
        send_message(
            chat_id,
            "To see your orders and payment status here, connect your account "
            "with `/login your-email@example.com`",
        )


def _looks_account_scoped(text: str) -> bool:
    lowered = (text or "").lower()
    return any(
        kw in lowered
        for kw in ("my order", "my payment", "did my payment", "order status", "receipt", "my purchase")
    )


# ---- Selection and checkout ----


def handle_selection(link: TelegramLink, product_id: str, variant_id: str) -> str:
    """Reuses the existing cart logic — same validation, same stock checks."""
    session = get_session(link)
    try:
        selection_service.add_to_cart(link.buyer_id(), session.id, product_id, variant_id, 1)
    except Exception as exc:  # noqa: BLE001 — surface the service's own message
        return getattr(exc, "message", None) or "That product couldn't be selected right now."

    if not link.is_linked:
        return (
            "✓ Added to your cart.\n\n"
            "To check out, connect your account first with "
            "`/login your-email@example.com`"
        )
    return "✓ Added to your cart. Say *checkout* when you're ready to pay."


def create_checkout_link(link: TelegramLink) -> tuple[str, list | None]:
    """Prepares an order with the existing checkout service and hands back a
    link to the deployed web checkout. Telegram never takes a payment."""
    if not link.is_linked:
        return (
            "To check out, connect your account first with `/login your-email@example.com`",
            None,
        )

    session = get_session(link)
    try:
        order = checkout_service.create_checkout(link.buyer_id(), session.id)
    except Exception as exc:  # noqa: BLE001 — service messages are already buyer-safe
        return (
            getattr(exc, "message", None) or "I couldn't prepare your checkout right now.",
            None,
        )

    web_url = (current_app.config.get("AGENT_WEB_URL") or "").rstrip("/")
    lines = "\n".join(
        f"• {i['quantity']} × {i['product_name']} — ₹{i['line_total']['amount'] / 100:,.0f}"
        for i in (order.items or [])
    )
    text = (
        "*Your order is ready.*\n\n"
        f"{lines}\n\n"
        f"*Total: ₹{order.amount_total / 100:,.0f}*\n\n"
        "Payment is completed securely on the web checkout — "
        "I can't take a payment here."
    )
    buttons = [[{"text": "🛒 Complete Payment", "url": f"{web_url}/?order={order.id}"}]] if web_url else None
    return text, buttons


def looks_like_checkout(text: str) -> bool:
    lowered = (text or "").lower().strip()
    return any(
        kw in lowered
        for kw in ("checkout", "check out", "i want to pay", "pay now", "complete payment", "buy now")
    )


# ---- Update dispatch ----


def process_update(app, update: dict):
    """Runs on a background thread so the webhook can answer Telegram
    immediately — otherwise Telegram times out and redelivers the update,
    and the buyer gets duplicate replies."""
    with app.app_context():
        try:
            _dispatch(update)
        except Exception as exc:  # noqa: BLE001 — never let a thread die silently
            audit_service.log_event(
                action="TELEGRAM_UPDATE_FAILED",
                metadata={"error": str(exc)[:400]},
            )


def _dispatch(update: dict):
    callback = update.get("callback_query")
    if callback:
        _handle_callback(callback)
        return

    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = (message.get("chat") or {}).get("id")
    tg_user = message.get("from") or {}
    text = (message.get("text") or "").strip()
    if not chat_id or not tg_user.get("id"):
        return

    link = get_or_create_link(tg_user, chat_id)

    if text.startswith("/start"):
        send_message(chat_id, WELCOME)
        return
    if text.startswith("/help"):
        send_message(chat_id, HELP)
        return
    if text.startswith("/login"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Please include your email: `/login you@example.com`")
            return
        _, msg = login(link, parts[1])
        send_message(chat_id, msg)
        return
    if text.startswith("/logout"):
        send_message(chat_id, logout(link))
        return
    if text.startswith("/"):
        send_message(chat_id, "I don't know that command. Try /help")
        return
    if not text:
        send_message(chat_id, "Send me a message describing what you're shopping for.")
        return

    if looks_like_checkout(text):
        msg, buttons = create_checkout_link(link)
        send_message(chat_id, msg, buttons, preview=True)
        return

    handle_agent_message(link, text)


def _handle_callback(callback: dict):
    data = callback.get("data") or ""
    tg_user = callback.get("from") or {}
    chat_id = ((callback.get("message") or {}).get("chat") or {}).get("id")
    if not chat_id or not tg_user.get("id"):
        return

    link = get_or_create_link(tg_user, chat_id)
    answer_callback(callback["id"])

    if data.startswith("sel:"):
        try:
            _, product_id, variant_id = data.split(":", 2)
        except ValueError:
            send_message(chat_id, "That selection is no longer valid.")
            return
        send_message(chat_id, handle_selection(link, product_id, variant_id))
