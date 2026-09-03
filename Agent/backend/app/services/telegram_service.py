"""Telegram as a second front-end onto the existing shopping agent.

Nothing here is a second implementation of anything. Messages go through
`chat_service.stream_message` — the same agent, tools, catalog, cart,
checkout and audit trail the web chat uses. This module only translates
between Telegram's API and that existing flow.

Two Telegram-specific constraints shape the code:

* **callback_data is capped at 64 bytes.** Two UUIDs need 77, so buttons
  carry a small index into `TelegramLink.last_cards` and the real ids are
  resolved server-side. (Truncating instead silently corrupted every
  selection into "This variant is no longer available.")
* **Markdown mode rejects the whole message** when `*`/`_`/`[` are
  unbalanced, which LLM prose does constantly. Everything is rendered as a
  safe HTML subset, with a plain-text retry so a reply can never vanish.

Account scoping: every account-aware operation keys off
`TelegramLink.buyer_id()`. A linked user resolves to their Clerk id; an
unlinked one to a namespaced `tg:<id>` that owns nothing. Order ids from the
user are never trusted as a lookup key.
"""

import threading
from datetime import datetime, timezone

import requests
from flask import current_app

from app.extensions import db
from app.models import BuyerProfile, ChatSession, TelegramLink
from app.services import audit_service, checkout_service, selection_service
from app.utils.telegram_format import markdown_to_telegram_html, plain_text

API_BASE = "https://api.telegram.org"
SEND_TIMEOUT = 15
MAX_MESSAGE = 3500
MAX_PRODUCT_CARDS = 4
MAX_GALLERY_IMAGES = 4

WELCOME = (
    "<b>Welcome to Agentic Commerce.</b>\n\n"
    "I can help you discover products, compare options, answer product "
    "questions, and help you complete a purchase.\n\n"
    "To connect your existing account:\n"
    "<code>/login your-email@example.com</code>\n\n"
    "You can browse and ask about products without logging in — you'll only "
    "need an account to check out or see your orders."
)

HELP = (
    "<b>Commands</b>\n"
    "/login &lt;email&gt; — Connect your account\n"
    "/logout — Disconnect your account\n"
    "/cart — See what's in your cart\n"
    "/orders — Your recent orders and payment status\n"
    "/help — Show this message\n\n"
    "You can chat naturally with me to search, compare, and purchase products."
)

TOOL_NOTICES = {
    "search_catalog": "🔎 Searching products…",
    "get_product_details": "📦 Checking product details…",
    "get_order_status": "🧾 Finding your latest order…",
}

# Filler the deterministic builder falls back to when it has nothing useful
# to add. On the web these sit quietly under a message; in Telegram each one
# becomes a "What next?" block with a button, so a lone filler is pure noise —
# and tapping it just produces the same filler again.
GENERIC_SUGGESTIONS = {
    "search something else",
    "show more options",
    "refine my search",
}

LOGIN_PROMPT = (
    "You'll need to connect your account for that.\n\n"
    "<code>/login your-email@example.com</code>\n\n"
    "Use the same email you sign in with on the web app."
)


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
        return None


def send_message(chat_id: int, html_text: str, buttons: list | None = None, preview: bool = False):
    """Sends HTML, falling back to plain text if Telegram still objects, so a
    reply is never silently dropped."""
    payload = {
        "chat_id": chat_id,
        "text": html_text[:MAX_MESSAGE],
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": not preview},
    }
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}

    result = _api("sendMessage", payload)
    if result and result.get("ok"):
        return result

    payload.pop("parse_mode", None)
    payload["text"] = plain_text(html_text)[:MAX_MESSAGE]
    return _api("sendMessage", payload)


def send_markdown(chat_id: int, markdown_text: str, buttons: list | None = None, preview: bool = False):
    return send_message(chat_id, markdown_to_telegram_html(markdown_text), buttons, preview)


def send_photo(chat_id: int, photo_url: str, caption_html: str, buttons: list | None = None):
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption_html[:1000],
        "parse_mode": "HTML",
    }
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    return _api("sendPhoto", payload)


def send_gallery(chat_id: int, image_urls: list, caption_html: str):
    """Multiple product photos as one swipeable album."""
    media = []
    for i, url in enumerate(image_urls[:MAX_GALLERY_IMAGES]):
        item = {"type": "photo", "media": url}
        if i == 0:
            item["caption"] = caption_html[:1000]
            item["parse_mode"] = "HTML"
        media.append(item)
    return _api("sendMediaGroup", {"chat_id": chat_id, "media": media})


def edit_message(chat_id: int, message_id: int, html_text: str, buttons: list | None = None) -> bool:
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": html_text[:MAX_MESSAGE],
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True},
    }
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    result = _api("editMessageText", payload)
    return bool(result and result.get("ok"))


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
    session = ChatSession.query.get(link.session_id) if link.session_id else None
    # A session belongs to a buyer id; after login/logout the identity
    # changes, so a fresh one starts rather than carrying the old identity's
    # conversation across.
    if session is None or session.buyer_clerk_user_id != link.buyer_id():
        session = ChatSession(buyer_clerk_user_id=link.buyer_id(), title="Telegram chat")
        db.session.add(session)
        db.session.commit()
        link.session_id = session.id
        db.session.commit()
    return session


def login(link: TelegramLink, email: str) -> tuple[bool, str]:
    email = (email or "").strip().lower().strip("<>")
    if not email or "@" not in email or " " in email:
        return False, "Please provide a valid email, like <code>/login you@example.com</code>"

    profile = BuyerProfile.query.filter(db.func.lower(BuyerProfile.email) == email).first()
    if profile is None:
        return False, (
            "We couldn't find an account with that email.\n\n"
            "Sign in at <a href=\"https://agent.techycsr.dev\">agent.techycsr.dev</a> "
            "with this email first, send one message there, then try "
            "<code>/login</code> again."
        )

    previous_buyer = link.buyer_id()
    previous_session_id = link.session_id
    switching_account = link.is_linked and link.buyer_clerk_user_id != profile.clerk_user_id

    link.buyer_clerk_user_id = profile.clerk_user_id
    link.linked_email = profile.email
    link.linked_at = datetime.now(timezone.utc)
    link.session_id = None
    db.session.commit()

    # Carry a cart built while logged out into the account they just
    # connected — otherwise "add to cart, then log in to pay" silently loses
    # everything and checkout reports an empty cart. Not done when switching
    # between two real accounts, where the items belong to the first one.
    moved = 0
    if previous_session_id and not switching_account and previous_buyer.startswith("tg:"):
        moved = _migrate_guest_cart(previous_buyer, previous_session_id, link)

    audit_service.log_event(
        action="TELEGRAM_ACCOUNT_LINKED",
        buyer_clerk_user_id=profile.clerk_user_id,
        metadata={"telegram_user_id": link.telegram_user_id, "email": profile.email},
    )
    message = (
        "✅ <b>Your Telegram account is now connected.</b>\n\n"
        "You can continue your shopping conversations and access your orders here."
    )
    if moved:
        message += (
            f"\n\nI also moved {moved} item{'s' if moved != 1 else ''} from your "
            "cart into this account — say <b>checkout</b> when you're ready."
        )
    else:
        message += "\n\nTry “find me a mechanical keyboard under ₹5,000”, or /orders."
    return True, message


def _migrate_guest_cart(previous_buyer: str, previous_session_id, link: TelegramLink) -> int:
    """Moves a logged-out cart onto the account that just connected."""
    from app.models import SelectedProduct
    from app.models.enums import SelectionStatus

    items = SelectedProduct.query.filter_by(
        session_id=previous_session_id,
        buyer_clerk_user_id=previous_buyer,
        status=SelectionStatus.SELECTED,
    ).all()
    if not items:
        return 0

    session = get_session(link)  # session for the newly linked identity
    for item in items:
        item.session_id = session.id
        item.buyer_clerk_user_id = link.buyer_clerk_user_id
    db.session.commit()

    audit_service.log_event(
        action="TELEGRAM_GUEST_CART_MIGRATED",
        buyer_clerk_user_id=link.buyer_clerk_user_id,
        metadata={"items": len(items), "from_buyer": previous_buyer},
    )
    return len(items)


def logout(link: TelegramLink) -> str:
    if not link.is_linked:
        return "You're not connected to an account right now."
    previous = link.buyer_clerk_user_id
    link.buyer_clerk_user_id = None
    link.linked_email = None
    link.linked_at = None
    link.session_id = None
    link.last_cards = None
    link.last_suggestions = None
    db.session.commit()
    audit_service.log_event(
        action="TELEGRAM_ACCOUNT_UNLINKED",
        buyer_clerk_user_id=previous,
        metadata={"telegram_user_id": link.telegram_user_id},
    )
    return (
        "You have been logged out successfully.\n\n"
        "You can still browse products — log in again any time with "
        "<code>/login your-email@example.com</code>"
    )


# ---- Rendering ----


def _money(amount, currency="INR") -> str:
    if amount is None:
        return "—"
    symbol = "₹" if currency == "INR" else f"{currency} "
    return f"{symbol}{amount / 100:,.0f}"


def _card_title(card: dict) -> str:
    return f"<b>{markdown_to_telegram_html(card.get('name') or 'Product')}</b>"


def _card_caption(card: dict) -> str:
    price = card.get("price") or {}
    parts = [f"<b>{markdown_to_telegram_html(card.get('name') or 'Product')}</b>"]
    line = _money(price.get("amount"), price.get("currency", "INR"))
    if card.get("brand"):
        line += f"  ·  {markdown_to_telegram_html(card['brand'])}"
    parts.append(line)

    desc = (card.get("description") or "").strip()
    if desc:
        if len(desc) > 200:
            desc = desc[:200].rsplit(" ", 1)[0] + "…"
        parts.append(markdown_to_telegram_html(desc))

    variants = card.get("variants") or []
    in_stock = [v for v in variants if v.get("availability") == "IN_STOCK"]
    if not in_stock:
        parts.append("<i>Currently out of stock</i>")
    elif len(in_stock) > 1:
        parts.append(f"<i>{len(in_stock)} options available</i>")
    return "\n\n".join(parts)


def _card_buttons(card_index: int, card: dict) -> list:
    """All callback_data stays far under Telegram's 64-byte cap by carrying
    indexes instead of UUIDs."""
    variants = card.get("variants") or []
    buttons = []
    in_stock = [(i, v) for i, v in enumerate(variants) if v.get("availability") == "IN_STOCK"]

    if len(in_stock) == 1:
        buttons.append([{"text": "🛒 Add to cart", "callback_data": f"sel:{card_index}:{in_stock[0][0]}"}])
    elif len(in_stock) > 1:
        # One button per option, so the buyer picks the variant explicitly.
        for vi, v in in_stock[:3]:
            label = (v.get("name") or "Option")[:20]
            buttons.append(
                [{"text": f"🛒 {label} · {_money((v.get('price') or {}).get('amount'))}",
                  "callback_data": f"sel:{card_index}:{vi}"}]
            )
    return buttons


def _remember(link: TelegramLink, cards=None, suggestions=None):
    if cards is not None:
        link.last_cards = cards
    if suggestions is not None:
        link.last_suggestions = suggestions
    db.session.commit()


def _card_images(card: dict) -> list:
    images = [u for u in (card.get("images") or []) if u]
    if not images and card.get("image_url"):
        images = [card["image_url"]]
    return images


def _send_products(chat_id: int, cards: list, link: TelegramLink):
    for idx, card in enumerate(cards[:MAX_PRODUCT_CARDS]):
        caption = _card_caption(card)
        buttons = _card_buttons(idx, card)
        images = _card_images(card)

        if len(images) > 1:
            # Album first — Telegram doesn't allow an inline keyboard on a
            # media group, so the actions follow in their own message.
            sent = send_gallery(chat_id, images, _card_title(card))
            if sent and sent.get("ok"):
                send_message(chat_id, caption, buttons)
                continue

        if images:
            sent = send_photo(chat_id, images[0], caption, buttons)
            if sent and sent.get("ok"):
                continue

        # An unreachable image host must not cost the buyer the product.
        send_message(chat_id, caption, buttons)

    if len(cards) > MAX_PRODUCT_CARDS:
        send_message(
            chat_id,
            f"<i>…and {len(cards) - MAX_PRODUCT_CARDS} more. Tell me your budget or "
            "brand and I'll narrow it down.</i>",
        )


def _useful_suggestions(suggestions: list, just_asked: str | None = None) -> list:
    """Keeps only follow-ups worth a button.

    Drops the generic filler, and drops whatever the buyer just tapped so a
    suggestion can't loop back on itself. Returns [] when nothing meaningful
    is left, in which case no prompt block is sent at all.
    """
    asked = (just_asked or "").strip().lower()
    kept = [
        s for s in (suggestions or [])
        if s.strip().lower() not in GENERIC_SUGGESTIONS and s.strip().lower() != asked
    ]
    # A single leftover option isn't a menu; it's clutter.
    return kept[:3] if len(kept) >= 2 else []


def _suggestion_buttons(suggestions: list) -> list:
    """Two per row where they're short, so the keyboard stays compact."""
    rows, row = [], []
    for i, text in enumerate(suggestions):
        row.append({"text": text[:32], "callback_data": f"sug:{i}"})
        if len(row) == 2 or len(text) > 22:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return rows


# ---- Agent bridge ----


def handle_agent_message(link: TelegramLink, text: str, just_asked: str | None = None):
    from app.services import chat_service

    chat_id = link.telegram_chat_id
    session = get_session(link)
    send_typing(chat_id)

    reply = ""
    cards: list = []
    suggestions: list = []
    notified: set = set()

    try:
        for event in chat_service.stream_message(link.buyer_id(), session.id, text):
            kind = event.get("type")
            if kind == "token":
                reply += event["delta"]
            elif kind == "retract":
                reply = ""
            elif kind == "tool_start":
                tool = event.get("tool")
                notice = TOOL_NOTICES.get(tool)
                if notice and tool not in notified:
                    notified.add(tool)
                    send_message(chat_id, notice)
                    send_typing(chat_id)
            elif kind == "product_cards":
                cards = event.get("cards") or []
            elif kind == "suggestions":
                suggestions = event.get("items") or []
            elif kind == "error":
                send_message(chat_id, "Something went wrong while processing your request. Please try again.")
                return
    except Exception:  # noqa: BLE001 — a bot reply must never surface a traceback
        send_message(chat_id, "Something went wrong while processing your request. Please try again.")
        return

    _remember(link, cards=cards, suggestions=suggestions)

    if reply.strip():
        send_markdown(chat_id, reply.strip())
    if cards:
        _send_products(chat_id, cards, link)

    if not link.is_linked and _looks_account_scoped(text):
        send_message(chat_id, LOGIN_PROMPT)
        return

    follow_ups = _useful_suggestions(suggestions, just_asked or text)
    if not follow_ups:
        return

    # Attach the buttons to a line that earns its place, rather than a bare
    # "What next?" after every single reply.
    if cards:
        actions = _suggestion_buttons(follow_ups)
        if link.is_linked:
            actions.append([{"text": "🧾 View cart", "callback_data": "cart"}])
        send_message(chat_id, "<i>Anything else?</i>", actions)
    else:
        send_message(chat_id, "<i>Anything else?</i>", _suggestion_buttons(follow_ups))


def _looks_account_scoped(text: str) -> bool:
    lowered = (text or "").lower()
    return any(
        kw in lowered
        for kw in ("my order", "my payment", "did my payment", "order status",
                   "receipt", "my purchase", "my cart")
    )


# ---- Cart, checkout, orders ----


def handle_selection(link: TelegramLink, card_index: int, variant_index: int) -> tuple[str, list | None]:
    cards = link.last_cards or []
    if card_index >= len(cards):
        return ("That product is no longer in view — search again and I'll show it.", None)

    card = cards[card_index]
    variants = card.get("variants") or []
    if variant_index >= len(variants):
        return ("That option is no longer available.", None)

    variant = variants[variant_index]
    session = get_session(link)
    try:
        selection_service.add_to_cart(
            link.buyer_id(), session.id, card["product_id"], variant["variant_id"], 1
        )
    except Exception as exc:  # noqa: BLE001 — service messages are buyer-safe
        return (getattr(exc, "message", None) or "That product couldn't be added right now.", None)

    name = markdown_to_telegram_html(card.get("name") or "Item")
    price = _money((variant.get("price") or {}).get("amount"))
    body = f"✅ <b>Added to cart</b>\n\n{name} · {variant.get('name')} — {price}"

    if not link.is_linked:
        return (
            body + "\n\nTo check out you'll need an account:\n"
            "<code>/login your-email@example.com</code>",
            None,
        )
    return (
        body + "\n\nSay <b>checkout</b> when you're ready, or keep browsing.",
        [[{"text": "🧾 View cart", "callback_data": "cart"}],
         [{"text": "💳 Checkout", "callback_data": "co"}]],
    )


def cart_summary(link: TelegramLink) -> tuple[str, list | None]:
    if not link.is_linked:
        # An unlinked user still has a cart under their tg: identity.
        session = get_session(link)
        cart = selection_service.get_cart(link.buyer_id(), session.id)
        if not cart["items"]:
            return ("Your cart is empty. Tell me what you're looking for.", None)
        lines = "\n".join(
            f"• {i['quantity']} × {markdown_to_telegram_html(i['product_name'])} — "
            f"{_money(i['line_total']['amount'], i['line_total']['currency'])}"
            for i in cart["items"]
        )
        return (
            f"<b>Your cart</b>\n\n{lines}\n\n"
            f"<b>Total: {_money(cart['total']['amount'], cart['total']['currency'])}</b>\n\n"
            + LOGIN_PROMPT,
            None,
        )

    session = get_session(link)
    cart = selection_service.get_cart(link.buyer_id(), session.id)
    if not cart["items"]:
        return ("Your cart is empty. Tell me what you're looking for.", None)

    lines = "\n".join(
        f"• {i['quantity']} × {markdown_to_telegram_html(i['product_name'])} — "
        f"{_money(i['line_total']['amount'], i['line_total']['currency'])}"
        for i in cart["items"]
    )
    return (
        f"<b>Your cart</b>\n\n{lines}\n\n"
        f"<b>Total: {_money(cart['total']['amount'], cart['total']['currency'])}</b>",
        [[{"text": "💳 Checkout", "callback_data": "co"}]],
    )


def create_checkout_link(link: TelegramLink) -> tuple[str, list | None]:
    if not link.is_linked:
        return (
            "Checkout needs a connected account, so your order is tied to you.\n\n" + LOGIN_PROMPT,
            None,
        )

    session = get_session(link)
    try:
        order = checkout_service.create_checkout(link.buyer_id(), session.id)
    except Exception as exc:  # noqa: BLE001 — service messages are buyer-safe
        return (
            markdown_to_telegram_html(
                getattr(exc, "message", None) or "I couldn't prepare your checkout right now."
            ),
            None,
        )

    web_url = (current_app.config.get("AGENT_WEB_URL") or "").rstrip("/")
    lines = "\n".join(
        f"• {i['quantity']} × {markdown_to_telegram_html(i['product_name'])} — "
        f"{_money(i['line_total']['amount'], i['line_total']['currency'])}"
        for i in (order.items or [])
    )
    text = (
        "<b>Your order is ready.</b>\n\n"
        f"{lines}\n\n"
        f"<b>Total: {_money(order.amount_total, order.currency)}</b>\n\n"
        "Payment happens securely on the web checkout — I can't take a payment here. "
        "Come back afterwards and ask “did my payment go through?”"
    )
    buttons = (
        [[{"text": f"🛒 Complete Payment · {_money(order.amount_total, order.currency)}",
           "url": f"{web_url}/?order={order.id}"}]]
        if web_url else None
    )
    return text, buttons


ORDERS_PER_PAGE = 3


def orders_summary(link: TelegramLink, page: int = 0) -> tuple[str, list | None]:
    if not link.is_linked:
        return ("Your orders live with your account.\n\n" + LOGIN_PROMPT, None)

    all_orders = checkout_service.list_orders(link.buyer_id())
    if not all_orders:
        return ("You don't have any orders yet.", None)

    pages = max(1, (len(all_orders) + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE)
    page = max(0, min(page, pages - 1))
    orders = all_orders[page * ORDERS_PER_PAGE : (page + 1) * ORDERS_PER_PAGE]

    blocks = []
    for o in orders:
        payment = o.latest_payment()
        status = payment.status.value if payment and payment.status else "PENDING"
        icon = {"PAID": "✅", "FAILED": "❌", "CANCELLED": "⚠️"}.get(status, "⏳")
        items = ", ".join(
            f"{i.get('quantity')} × {i.get('product_name')}" for i in (o.items or [])
        )
        blocks.append(
            f"{icon} <b>{_money(o.amount_total, o.currency)}</b> — {markdown_to_telegram_html(items)}\n"
            f"    Payment: {status} · Order: {o.status.value if o.status else '—'}\n"
            f"    <code>{str(o.id)[:8]}</code>"
        )

    header = "<b>Your orders</b>"
    if pages > 1:
        header += f"  <i>(page {page + 1} of {pages})</i>"

    nav = []
    if page > 0:
        nav.append({"text": "◀ Previous", "callback_data": f"ord:{page - 1}"})
    if page < pages - 1:
        nav.append({"text": "Next ▶", "callback_data": f"ord:{page + 1}"})

    buttons = [nav] if nav else None
    return (header + "\n\n" + "\n\n".join(blocks), buttons)


def looks_like_checkout(text: str) -> bool:
    lowered = (text or "").lower().strip()
    return any(
        kw in lowered
        for kw in ("checkout", "check out", "i want to pay", "pay now", "complete payment",
                   "place order", "buy it", "purchase it")
    )


# ---- Update dispatch ----


def process_update(app, update: dict):
    """Runs on a background thread so the webhook can answer Telegram
    immediately — a slow 200 makes Telegram retry and duplicate replies."""
    with app.app_context():
        try:
            _dispatch(update)
        except Exception as exc:  # noqa: BLE001 — never let the thread die silently
            audit_service.log_event(
                action="TELEGRAM_UPDATE_FAILED", metadata={"error": str(exc)[:400]}
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
            send_message(chat_id, "Please include your email: <code>/login you@example.com</code>")
            return
        _, msg = login(link, parts[1])
        send_message(chat_id, msg)
        return
    if text.startswith("/logout"):
        send_message(chat_id, logout(link))
        return
    if text.startswith("/cart"):
        msg, buttons = cart_summary(link)
        send_message(chat_id, msg, buttons)
        return
    if text.startswith("/orders"):
        msg, buttons = orders_summary(link)
        send_message(chat_id, msg, buttons)
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

    if data.startswith("sel:"):
        answer_callback(callback["id"], "Adding to cart…")
        try:
            _, ci, vi = data.split(":", 2)
            msg, buttons = handle_selection(link, int(ci), int(vi))
        except (ValueError, TypeError):
            msg, buttons = "That selection is no longer valid.", None
        send_message(chat_id, msg, buttons)
        return

    if data.startswith("pic:"):
        answer_callback(callback["id"])
        try:
            idx = int(data.split(":", 1)[1])
            card = (link.last_cards or [])[idx]
        except (ValueError, IndexError):
            send_message(chat_id, "Those photos are no longer available.")
            return
        images = card.get("images") or ([card["image_url"]] if card.get("image_url") else [])
        if len(images) > 1:
            send_gallery(chat_id, images, f"<b>{markdown_to_telegram_html(card.get('name') or '')}</b>")
        elif images:
            send_photo(chat_id, images[0], f"<b>{markdown_to_telegram_html(card.get('name') or '')}</b>")
        else:
            send_message(chat_id, "No photos available for that product.")
        return

    if data.startswith("sug:"):
        answer_callback(callback["id"])
        try:
            idx = int(data.split(":", 1)[1])
            suggestion = (link.last_suggestions or [])[idx]
        except (ValueError, IndexError):
            send_message(chat_id, "That suggestion expired — just tell me what you need.")
            return
        # Echo it so the conversation reads naturally, then answer it.
        send_message(chat_id, f"<i>{markdown_to_telegram_html(suggestion)}</i>")
        if looks_like_checkout(suggestion):
            msg, buttons = create_checkout_link(link)
            send_message(chat_id, msg, buttons, preview=True)
        else:
            handle_agent_message(link, suggestion, just_asked=suggestion)
        return

    if data.startswith("ord:"):
        answer_callback(callback["id"])
        try:
            page = int(data.split(":", 1)[1])
        except ValueError:
            page = 0
        msg, buttons = orders_summary(link, page)
        message_id = (callback.get("message") or {}).get("message_id")
        # Editing keeps the order list in one place rather than posting a new
        # message on every page turn.
        if message_id and not edit_message(chat_id, message_id, msg, buttons):
            send_message(chat_id, msg, buttons)
        return

    if data == "cart":
        answer_callback(callback["id"])
        msg, buttons = cart_summary(link)
        send_message(chat_id, msg, buttons)
        return

    if data == "co":
        answer_callback(callback["id"], "Preparing checkout…")
        msg, buttons = create_checkout_link(link)
        send_message(chat_id, msg, buttons, preview=True)
        return

    answer_callback(callback["id"])
