"""The LLM tool-calling loop that powers the shopping chat — streamed.

Talks to any OpenAI-compatible chat completions endpoint (configured via
LLM_BASE_URL/LLM_API_KEY/LLM_MODEL — currently api.bluesminds.com,
model gpt-4o). Manual loop, not a framework's agent runner, so
every tool call can be audit-logged and its raw JSON kept for
product-card extraction — cards are built only from tool results, never
parsed from the model's prose, so the agent cannot present a product it
didn't actually look up.

`stream_agent_turn` is a generator yielding small SSE-ready event dicts as
the turn progresses (tool_start/tool_end/token/product_cards/suggestions/
done) instead of blocking until the whole reply is ready — see
`app/routes/chat.py` for how these get framed onto the wire.

Confirmed live against a prior provider (NaraRouter, not assumed from
docs — the defenses below are kept because they're provider-agnostic,
not because this specific provider is known to need them): on a
tool-calling round a model can stream a few words of narration ("Here
are some mechanical keyboards...") *before* the tool_calls delta
arrives. That text isn't grounded in any tool result yet, so it is
deliberately buffered and discarded the moment a tool call starts —
never sent to the client — rather than trusting the "don't narrate"
system-prompt rule to hold on its own.
"""

import json
import queue
import threading

from flask import current_app
from openai import OpenAI

from app.extensions import db
from app.models import ChatMessage
from app.models.enums import MessageRole
from app.services import audit_service, catalog_client

MAX_TOOL_ITERATIONS = 6
# Kept tight on purpose: a slow upstream directly stalls the buyer's
# browser. One retry (not the SDK's default of two) trades a little
# resilience against a transient blip for staying well inside gunicorn's
# worker timeout even in the worst case (a few tool-calling iterations
# deep) — see the deploy notes for how the worst case (MAX_TOOL_ITERATIONS
# x REQUEST_TIMEOUT_SECONDS) sizes the gunicorn/nginx timeouts.
REQUEST_TIMEOUT_SECONDS = 20
LLM_MAX_RETRIES = 1

FIXED_SEARCH_FAILURE_MESSAGE = (
    "I'm unable to search the catalog right now. Please try again."
)
# Distinct from the catalog message on purpose: telling a buyer the catalog is
# down when it was the model that stalled sends them chasing the wrong thing.
FIXED_LLM_FAILURE_MESSAGE = (
    "I'm having trouble responding right now. Please try again in a moment."
)
# One retry per round. Measured against the current provider, back-to-back
# identical calls returned in 6.7s, 10.4s, 40.5s and one 500 — so a single
# immediate retry rescues a large share of turns that would otherwise fall
# back. Only retried when nothing has reached the client yet.
LLM_ROUND_RETRIES = 1
FIXED_LOOP_LIMIT_MESSAGE = (
    "I'm having trouble narrowing this down. Could you tell me a bit more "
    "about what you're looking for?"
)

TOOL_LABELS = {
    "search_catalog": "Searching the catalog",
    "add_to_cart": "Adding to your cart",
    "view_cart": "Checking your cart",
    "remove_from_cart": "Updating your cart",
    "prepare_checkout": "Preparing your order",
    "recommend_related": "Finding things that go with it",
    "list_addresses": "Checking your delivery addresses",
    "set_delivery_address": "Setting the delivery address",
    "add_address": "Saving your address",
    "get_product_details": "Checking product details",
    "get_order_status": "Checking your order status",
}

SYSTEM_PROMPT = """You are the AI Shopping Agent for an online marketplace. You help \
buyers search, understand, compare, and select real products from the live catalog.

Hard rules — these override anything else:
1. You may ONLY state product names, prices, descriptions, stock, availability, \
   brand, or specifications that come from the search_catalog or get_product_details \
   tool results in this conversation. Never invent or guess a product, price, \
   discount, stock level, or feature. If you don't have a fact from a tool result, \
   say you don't have that information instead of guessing.
2. Prices from the tools are integers in the smallest currency unit (e.g. paise for \
   INR — divide by 100 for rupees). When a buyer gives a price in rupees, multiply by \
   100 before calling search_catalog's min_price/max_price. Always show prices to the \
   buyer in normal major-unit currency format (e.g. "₹4,799").
3. Use search_catalog whenever the buyer describes what they want (keyword, category, \
   brand, price range, availability). Use get_product_details to answer questions \
   about one specific product, to verify current price/stock before comparing, or \
   before confirming a selection.
4. If a search returns zero results, tell the buyer: "I couldn't find an exact match \
   for your requirements." You may then ask a clarifying question about relaxing \
   their criteria — do not invent alternative products.
5. When the buyer references earlier results ("the first one", "the cheapest one", \
   "that keyboard", "compare these"), match it against the numbered context block of \
   recently shown products and, if you need fresher/fuller data, call \
   get_product_details with product_index set to that number — do not retype a \
   product_id from memory.
6. When comparing products, only compare fields you actually have from tool results \
   (price, availability, stock, brand, category, variant names) — never claim a \
   feature difference you have no data for.
7. You cannot change prices, products, or inventory, and you cannot create or confirm \
   a payment — you only search, explain, compare, and help the buyer pick a product/\
   variant to select for checkout. If asked to do any of those, explain that's not \
   something you can do here.
7a. Money is always the buyer's decision. You may explain checkout, show what an \
   order costs, and report order/payment status — but you must never start, \
   authorize, retry, or confirm a payment, and never say a payment succeeded, \
   failed, or is being processed unless a get_order_status result in this \
   conversation says so. If they want to pay or retry, tell them to use the \
   checkout button — only they can authorize a charge. If they ask about a \
   payment or order, call get_order_status and report exactly what it returns; \
   if it returns no orders, say so rather than guessing.
7b. You can act on the buyer's behalf up to — but never past — the point of \
   payment. add_to_cart, view_cart, remove_from_cart and prepare_checkout are \
   yours to use when the buyer asks ("add it", "what's in my cart", "checkout"). \
   prepare_checkout prices the order and shows them a Pay button; it does NOT \
   pay. After it, state the total and say they can press Pay to authorize it — \
   never say the payment is done, processing, or successful. Only \
   get_order_status can tell you a payment's real state.
7c. Grow the basket honestly. After the buyer adds something, you may call \
   recommend_related once to suggest genuinely complementary items from the \
   catalog, and mention them briefly. Never invent an accessory, never claim a \
   discount or bundle that no tool returned, and drop it if they say no.
7d. Never put image markdown, raw URLs or long ids in your reply text. Product \
   photos, prices and buttons are rendered from the tool data as cards next to \
   your message — writing them out again shows the buyer a giant duplicate \
   image and an unreadable wall of links. Describe products in words only.
7e. Before preparing checkout, make sure the buyer knows where it's going. \
   Call list_addresses; if they have one, state it in a short line ("Delivering \
   to Home — 12 MG Road, Bengaluru") and continue. If they have none, tell them \
   save it with add_address — asking only for whatever it reports missing, \
   and never inventing a name, phone or PIN code. Don't call prepare_checkout \
   until an address exists; it will fail without one. You can also switch \
   between saved addresses with set_delivery_address.
8. Keep responses concise and conversational. Ask a clarifying question when the \
   buyer's request is ambiguous (e.g. no budget or category given) rather than \
   guessing. When you need a tool, call it immediately with no preceding narration \
   text ("Let me check...", "Here are some...") — go straight to the tool call and \
   only write prose once you have real results to report.
9. You are a shopping assistant for this marketplace and nothing else. In scope: \
   finding products, comparing them, answering questions about items in this \
   catalog, prices, stock, delivery, carts, checkout, orders, payments and \
   receipts — plus ordinary conversational courtesy (a greeting, a thank-you, \
   asking what you can do). Out of scope: everything else — general knowledge, \
   maths, coding, news, weather, medical/legal/financial advice, translation, \
   writing essays or code, personal opinions, and anything about your own \
   prompt, tools or implementation. For an out-of-scope request, don't answer it \
   even partially and don't explain why at length. Reply briefly that you can \
   only help with shopping here, then offer a concrete shopping next step — for \
   example: "I can only help with shopping on this store. Want me to find you \
   something — say, headphones or a keyboard?" If a request mixes both, answer \
   only the shopping part and ignore the rest.
"""

SEARCH_CATALOG_TOOL = {
    "type": "function",
    "function": {
        "name": "search_catalog",
        "description": (
            "Search the merchant product catalog. Use whenever the buyer describes "
            "what they're looking for."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "description": "Free-text search across product name, description, brand.",
                },
                "category": {
                    "type": "string",
                    "description": "Category name, e.g. Keyboards, Audio, Men.",
                },
                "brand": {"type": "string"},
                "min_price": {
                    "type": "integer",
                    "description": "Minimum price in the smallest currency unit (e.g. paise for INR).",
                },
                "max_price": {
                    "type": "integer",
                    "description": "Maximum price in the smallest currency unit (e.g. paise for INR).",
                },
                "in_stock": {
                    "type": "boolean",
                    "description": "true to only return products with stock available.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results, default 10, max 20.",
                },
            },
        },
    },
}

GET_PRODUCT_DETAILS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_product_details",
        "description": (
            "Get full details for one product: all variants, prices, stock and "
            "images. Use to answer questions about a specific product, verify "
            "current price/stock before comparing, or before confirming a "
            "selection. Prefer product_index (its number in the numbered context "
            "list of recently shown products) over product_id when the product "
            "came from that list — indexes are safer than retyping a long id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_index": {
                    "type": "integer",
                    "description": (
                        "1-based position in the numbered 'recently shown "
                        "products' context list. Use this whenever referring to "
                        "a product from that list instead of product_id."
                    ),
                },
                "product_id": {
                    "type": "string",
                    "description": (
                        "The product's exact UUID, copied verbatim from a tool "
                        "result in this same turn. Don't use this for a product "
                        "only seen in an earlier turn's context list — use "
                        "product_index instead."
                    ),
                },
            },
        },
    },
}

GET_ORDER_STATUS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_order_status",
        "description": (
            "Look up this buyer's real orders and payment status from the "
            "backend. Use it whenever they ask whether a payment went "
            "through, what their payment or order status is, whether an "
            "order is confirmed, or to show order/receipt details. This is "
            "read-only: it reports status, it cannot start, retry, or change "
            "a payment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": (
                        "A specific order's UUID, if the buyer named one. "
                        "Omit to get their most recent orders in this chat."
                    ),
                },
            },
        },
    },
}


ADD_TO_CART_TOOL = {
    "type": "function",
    "function": {
        "name": "add_to_cart",
        "description": (
            "Put a product the buyer has chosen into their cart. Use when they "
            "say things like 'I'll take it', 'add the second one', 'buy that'. "
            "Adding to a cart costs nothing and charges nothing — it only "
            "reserves the buyer's intent. Never call it speculatively; only "
            "when the buyer has actually picked something."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_index": {
                    "type": "integer",
                    "description": "1-based position in the numbered list of recently shown products.",
                },
                "variant_index": {
                    "type": "integer",
                    "description": "1-based option number when the product has several (size/colour). Defaults to the first in-stock option.",
                },
                "quantity": {"type": "integer", "description": "How many. Defaults to 1."},
            },
            "required": ["product_index"],
        },
    },
}

VIEW_CART_TOOL = {
    "type": "function",
    "function": {
        "name": "view_cart",
        "description": (
            "Show what's currently in the buyer's cart, with quantities and the "
            "running total. Use before checkout, or whenever they ask what "
            "they've picked."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

REMOVE_FROM_CART_TOOL = {
    "type": "function",
    "function": {
        "name": "remove_from_cart",
        "description": "Take an item out of the cart, by its number in the cart listing.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_index": {
                    "type": "integer",
                    "description": "1-based position in the cart as last shown by view_cart.",
                }
            },
            "required": ["item_index"],
        },
    },
}

PREPARE_CHECKOUT_TOOL = {
    "type": "function",
    "function": {
        "name": "prepare_checkout",
        "description": (
            "Price the buyer's cart into a confirmed order summary they can pay "
            "for. Re-checks every item against the live catalog and computes the "
            "authoritative total.\n\n"
            "This does NOT take a payment and does NOT charge anyone — it only "
            "prepares the order and shows the buyer a Pay button they must press "
            "themselves. Use it when the buyer wants to check out or pay. After "
            "calling it, tell them the total and that they can press Pay to "
            "authorize the payment; never say the payment is done."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

RECOMMEND_RELATED_TOOL = {
    "type": "function",
    "function": {
        "name": "recommend_related",
        "description": (
            "Find real products that complement one the buyer is looking at or "
            "has in their cart — accessories, or items from a related category. "
            "Use it to suggest genuinely useful additions after they pick "
            "something, not to pad every reply. Results come from the live "
            "catalog, so only suggest what it returns."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_index": {
                    "type": "integer",
                    "description": "1-based position of the product to find complements for.",
                },
                "max_price": {
                    "type": "integer",
                    "description": "Optional cap in the smallest currency unit (paise).",
                },
            },
        },
    },
}

LIST_ADDRESSES_TOOL = {
    "type": "function",
    "function": {
        "name": "list_addresses",
        "description": (
            "Show the buyer's saved delivery addresses and which is the "
            "default. Use before preparing checkout so you can confirm where "
            "the order is going, or when they ask about delivery."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

SET_DEFAULT_ADDRESS_TOOL = {
    "type": "function",
    "function": {
        "name": "set_delivery_address",
        "description": (
            "Choose which saved address this order ships to, by its number in "
            "the list. Use when the buyer picks one ('send it to my office'). "
            "It cannot create an address — if they have none, tell them to add "
            "one from the Addresses panel."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "address_index": {
                    "type": "integer",
                    "description": "1-based position in the list from list_addresses.",
                }
            },
            "required": ["address_index"],
        },
    },
}

ADD_ADDRESS_TOOL = {
    "type": "function",
    "function": {
        "name": "add_address",
        "description": (
            "Save a delivery address the buyer types in chat. CALL THIS "
            "whenever they state or dictate an address — e.g. 'deliver to 12 MG "
            "Road Bengaluru', 'set delivery address to ...', 'ship it to my "
            "office at ...' — even if parts are missing.\n\n"
            "Map their words onto the fields yourself: the building/street/area "
            "becomes line1, the city becomes city, a 6-digit number is "
            "postal_code, a 10-digit number is phone. Carry over details they "
            "gave in earlier messages in this conversation.\n\n"
            "If something required is still missing the result lists exactly "
            "what — ask only for those, then call this again with the full set. "
            "Never invent a name, phone number or PIN code."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "Home, Office, etc."},
                "full_name": {"type": "string"},
                "phone": {"type": "string"},
                "line1": {"type": "string", "description": "Building, street, area."},
                "line2": {"type": "string"},
                "city": {"type": "string"},
                "state": {"type": "string"},
                "postal_code": {"type": "string", "description": "PIN / ZIP code."},
            },
        },
    },
}

TOOLS = [
    SEARCH_CATALOG_TOOL,
    GET_PRODUCT_DETAILS_TOOL,
    GET_ORDER_STATUS_TOOL,
    ADD_TO_CART_TOOL,
    VIEW_CART_TOOL,
    REMOVE_FROM_CART_TOOL,
    PREPARE_CHECKOUT_TOOL,
    RECOMMEND_RELATED_TOOL,
    LIST_ADDRESSES_TOOL,
    SET_DEFAULT_ADDRESS_TOOL,
    ADD_ADDRESS_TOOL,
]

# There is deliberately no tool that authorizes, captures, retries or
# confirms a payment. The furthest the agent can go is preparing a priced
# order; charging requires the buyer to press Pay, which goes through the
# authenticated checkout routes and Razorpay's own UI. That boundary is
# structural, not a matter of the model behaving well.


def _client() -> OpenAI:
    return OpenAI(
        base_url=current_app.config["LLM_BASE_URL"],
        api_key=current_app.config["LLM_API_KEY"],
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES,
    )


def _to_card(product: dict) -> dict:
    images = product.get("images") or []
    primary_image = next((i["url"] for i in images if i.get("is_primary")), None)
    if not primary_image and images:
        primary_image = images[0].get("url")

    variants = product.get("variants") or []
    in_stock_variants = [v for v in variants if v.get("availability") == "IN_STOCK"]
    cheapest = min(
        (in_stock_variants or variants),
        key=lambda v: v["price"]["amount"],
        default=None,
    )

    return {
        "product_id": product.get("product_id"),
        "name": product.get("name"),
        "brand": product.get("brand"),
        "category": product.get("category"),
        "description": product.get("description"),
        "image_url": primary_image,
        # Full list (primary first) so the UI can show a real image gallery
        # without a second round-trip for the same product.
        "images": ([primary_image] if primary_image else [])
        + [i["url"] for i in images if i.get("url") and i.get("url") != primary_image],
        "merchant_name": (product.get("merchant") or {}).get("name"),
        "store_name": (product.get("store") or {}).get("name"),
        "price": cheapest["price"] if cheapest else None,
        "availability": cheapest["availability"] if cheapest else None,
        "variants": [
            {
                "variant_id": v.get("variant_id"),
                "name": v.get("name"),
                "sku": v.get("sku"),
                "price": v.get("price"),
                "availability": v.get("availability"),
                "stock_quantity": v.get("stock_quantity"),
            }
            for v in variants
        ],
    }


def _get_last_shown_cards(session) -> list[dict]:
    last_with_cards = next(
        (
            m
            for m in reversed(session.messages)
            if m.role == MessageRole.ASSISTANT and m.product_cards
        ),
        None,
    )
    return last_with_cards.product_cards if last_with_cards else []


def _format_grounding_context(cards: list[dict]) -> str | None:
    if not cards:
        return None

    lines = []
    for i, card in enumerate(cards, start=1):
        price = card.get("price") or {}
        lines.append(
            f"{i}. {card.get('name')} (price: {price.get('amount')} "
            f"{price.get('currency')}, availability: {card.get('availability')})"
        )
    return (
        "[Context — products most recently shown to the buyer, in order, for "
        "resolving references like 'the first one' or 'the cheapest one':\n"
        + "\n".join(lines)
        + "\nWhen looking up one of these with get_product_details, pass "
        "product_index (its number above) — do not retype an id from memory.]"
    )


def _format_order_context(session) -> str | None:
    """Recent orders for this chat, so the agent knows a purchase happened
    without having to be asked. Status only — the tool is still the way to
    get details, and nothing here lets it move money."""
    from app.models import Order  # local import keeps model imports lazy here

    orders = (
        Order.query.filter_by(session_id=session.id)
        .order_by(Order.created_at.desc())
        .limit(3)
        .all()
    )
    if not orders:
        return None

    lines = []
    for o in orders:
        payment = o.latest_payment()
        amount = o.amount_total / 100
        symbol = "₹" if o.currency == "INR" else f"{o.currency} "
        lines.append(
            f"- Order {o.id}: {symbol}{amount:,.0f}, order status "
            f"{o.status.value if o.status else 'UNKNOWN'}, payment "
            f"{payment.status.value if payment and payment.status else 'NONE'}"
        )
    return (
        "[Context — this buyer's orders in this chat. Use get_order_status for "
        "details or delivery status; never state a payment outcome that isn't "
        "shown here or in a tool result:\n" + "\n".join(lines) + "]"
    )


def _build_messages(session, grounding: str | None) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    history = list(session.messages)
    last_user_index = max(
        (i for i, m in enumerate(history) if m.role == MessageRole.USER), default=-1
    )
    for i, msg in enumerate(history):
        role = "user" if msg.role == MessageRole.USER else "assistant"
        content = msg.content
        if grounding and i == last_user_index:
            content = f"{grounding}\n\n{content}"
        messages.append({"role": role, "content": content})

    return messages


def _detect_comparison_intent(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in ("compare", " vs ", " vs.", "versus", "difference between"))


def _build_suggestions(
    *, cards, had_search, had_zero_results, had_details, comparison_intent, is_first_turn
) -> list[str]:
    """Deterministic, template-derived follow-ups — never model-generated, so
    they carry the same no-hallucination guarantee as product cards, and
    cost no extra LLM round-trip (which would hurt the exact latency this
    streaming rework is meant to fix)."""
    if had_zero_results:
        return ["Try a different category", "Increase the budget", "Search a different brand"]
    if comparison_intent and len(cards) >= 2:
        return ["Which one has better value?", "Show only in-stock options", "Add the cheaper one to cart"]
    if len(cards) >= 2:
        return ["Compare these", "Show cheaper options", "Add the first one to cart"]
    if len(cards) == 1:
        return ["Add to cart", "Show similar products", "Any other variants?"]
    if had_details:
        return ["Compare with something else", "Show similar products"]
    if had_search:
        return ["Refine my search", "Show more options"]
    if is_first_turn:
        return ["Show trending products", "Search by category", "Search under a budget"]
    return ["Search something else"]


def _persist_assistant_reply(session, text: str, cards: list[dict], suggestions: list[str] | None, prepared_checkout=None):
    message = ChatMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=text,
        product_cards=cards or None,
        suggested_replies=suggestions or None,
        prepared_checkout=prepared_checkout,
    )
    db.session.add(message)
    if not session.title:
        session.title = text.strip()[:80] or "New chat"
    db.session.commit()
    return message


def _execute_tool_call(session, buyer_id: str, name: str, args: dict, last_shown_cards, collected_cards, checkout_ready=None):
    """Runs one tool call, audit-logs it, and returns a JSON-serializable result.

    `checkout_ready` collects orders prepared during the turn so the caller
    can surface a Pay button — the agent prepares, the buyer authorizes."""
    checkout_ready = checkout_ready if checkout_ready is not None else []
    if name == "search_catalog":
        limit = min(int(args.get("limit") or 10), 20)
        data, meta = catalog_client.search_catalog(
            q=args.get("q"),
            category=args.get("category"),
            brand=args.get("brand"),
            min_price=args.get("min_price"),
            max_price=args.get("max_price"),
            in_stock=args.get("in_stock"),
            limit=limit,
        )
        audit_service.log_event(
            action="PRODUCT_SEARCH",
            session_id=session.id,
            buyer_clerk_user_id=buyer_id,
            metadata={"params": args, "result_count": len(data)},
            commit=False,
        )
        if not data:
            audit_service.log_event(
                action="NO_PRODUCTS_FOUND",
                session_id=session.id,
                buyer_clerk_user_id=buyer_id,
                metadata={"params": args},
                commit=False,
            )
        for product in data:
            collected_cards[product["product_id"]] = _to_card(product)
        return {"results": data, "total": meta.get("total", len(data))}

    if name == "get_product_details":
        product_id = args.get("product_id")
        product_index = args.get("product_index")
        # Resolve product_index against the known, server-side list of
        # recently shown products instead of trusting an LLM-transcribed
        # UUID — models occasionally garble a long id when copying it from
        # context (observed: a character silently dropped mid-string).
        if product_index is not None:
            idx = int(product_index) - 1
            if 0 <= idx < len(last_shown_cards):
                product_id = last_shown_cards[idx].get("product_id")

        product = catalog_client.get_product(product_id) if product_id else None
        audit_service.log_event(
            action="PRODUCT_DETAILS_REQUESTED",
            session_id=session.id,
            buyer_clerk_user_id=buyer_id,
            metadata={
                "product_id": product_id,
                "product_index": product_index,
                "found": product is not None,
            },
            commit=False,
        )
        if product is None:
            return {"error": "Product not found or not available."}
        collected_cards[product["product_id"]] = _to_card(product)
        return product

    if name == "get_order_status":
        # Read-only by construction: this reads order/payment rows and
        # returns them. There is deliberately no tool that can create,
        # authorize, retry, or alter a payment — those require an explicit
        # user action against the checkout routes.
        from app.services import checkout_service  # local import avoids a cycle

        order_id = args.get("order_id")
        if order_id:
            try:
                orders = [checkout_service.get_order_for_buyer(buyer_id, order_id)]
            except Exception:  # noqa: BLE001 — unknown/forbidden id is answerable, not fatal
                return {"error": "No order found with that id for this buyer."}
        else:
            orders = checkout_service.list_orders(buyer_id)[:3]

        audit_service.log_event(
            action="ORDER_STATUS_REQUESTED",
            session_id=session.id,
            buyer_clerk_user_id=buyer_id,
            metadata={"order_id": order_id, "result_count": len(orders)},
            commit=False,
        )

        if not orders:
            return {"orders": [], "note": "This buyer has no orders yet."}

        return {
            "orders": [
                {
                    "order_id": str(o.id),
                    "order_status": o.status.value if o.status else None,
                    "payment_status": (
                        o.latest_payment().status.value
                        if o.latest_payment() and o.latest_payment().status
                        else None
                    ),
                    "amount": o.amount_total,
                    "currency": o.currency,
                    "items": [
                        {
                            "product_name": i.get("product_name"),
                            "variant_name": i.get("variant_name"),
                            "quantity": i.get("quantity"),
                        }
                        for i in (o.items or [])
                    ],
                    # Read back from the merchant, so "where is my order?" is
                    # answered from the seller's real fulfillment state. Each
                    # lookup is a ~6s cross-region HTTP call, so it is limited
                    # to the most recent order — asking about delivery almost
                    # always means the latest one, and fetching it for every
                    # order made a single turn tens of seconds slower.
                    "fulfillment_status": (
                        checkout_service.get_fulfillment_status(o)
                        if idx == 0
                        else None
                    ),
                    "payment_id": (
                        o.latest_payment().provider_payment_id if o.latest_payment() else None
                    ),
                    "payment_method": (
                        o.latest_payment().method if o.latest_payment() else None
                    ),
                    "payment_method_detail": (
                        o.latest_payment().method_detail if o.latest_payment() else None
                    ),
                    "paid_at": (
                        o.latest_payment().paid_at.isoformat()
                        if o.latest_payment() and o.latest_payment().paid_at
                        else None
                    ),
                    "failure_reason": (
                        o.latest_payment().failure_reason if o.latest_payment() else None
                    ),
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                    "confirmed_at": o.confirmed_at.isoformat() if o.confirmed_at else None,
                }
                for idx, o in enumerate(orders)
            ]
        }


    if name in ("add_to_cart", "view_cart", "remove_from_cart", "prepare_checkout"):
        from app.services import checkout_service, selection_service

        if name == "add_to_cart":
            idx = int(args.get("product_index") or 0) - 1
            if not (0 <= idx < len(last_shown_cards)):
                return {"error": "That product isn't in the list I showed. Search again first."}
            card = last_shown_cards[idx]
            variants = card.get("variants") or []
            in_stock = [v for v in variants if v.get("availability") == "IN_STOCK"]
            if not in_stock:
                return {"error": f"{card.get('name')} is out of stock."}

            if args.get("variant_index") is not None:
                vi = int(args["variant_index"]) - 1
                variant = variants[vi] if 0 <= vi < len(variants) else None
                if variant is None:
                    return {"error": "That option doesn't exist for this product."}
                if variant.get("availability") != "IN_STOCK":
                    return {"error": f"The {variant.get('name')} option is out of stock."}
            else:
                variant = in_stock[0]

            quantity = max(1, int(args.get("quantity") or 1))
            try:
                item = selection_service.add_to_cart(
                    buyer_id, session.id, card["product_id"], variant["variant_id"], quantity
                )
            except Exception as exc:  # noqa: BLE001 — service messages are buyer-safe
                return {"error": getattr(exc, "message", None) or "Couldn't add that to the cart."}
            return {
                "added": True,
                "product_name": item.product_name_snapshot,
                "variant_name": item.variant_name_snapshot,
                "quantity": item.quantity,
                "unit_price": {"amount": item.price_amount_snapshot, "currency": item.currency_snapshot},
            }

        if name == "view_cart":
            cart = selection_service.get_cart(buyer_id, session.id)
            return {
                "items": [
                    {
                        "index": i + 1,
                        "product_name": it["product_name"],
                        "variant_name": it["variant_name"],
                        "quantity": it["quantity"],
                        "line_total": it["line_total"],
                    }
                    for i, it in enumerate(cart["items"])
                ],
                "total": cart["total"],
                "is_empty": not cart["items"],
            }

        if name == "remove_from_cart":
            cart = selection_service.get_cart(buyer_id, session.id)
            idx = int(args.get("item_index") or 0) - 1
            if not (0 <= idx < len(cart["items"])):
                return {"error": "That item isn't in the cart."}
            item = cart["items"][idx]
            selection_service.remove_from_cart(buyer_id, session.id, item["id"])
            return {"removed": True, "product_name": item["product_name"]}

        # prepare_checkout — prices the cart into a payable order. It stops
        # exactly here: no Razorpay order, no authorization, no charge. The
        # buyer presses Pay themselves, which is a separate authenticated
        # request they alone can make.
        try:
            order = checkout_service.create_checkout(buyer_id, session.id)
        except Exception as exc:  # noqa: BLE001 — validation messages are buyer-safe
            return {"error": getattr(exc, "message", None) or "Couldn't prepare the checkout."}

        checkout_ready.append(
            {
                "order_id": str(order.id),
                "amount": order.amount_total,
                "currency": order.currency,
                "items": order.items or [],
            }
        )
        return {
            "order_prepared": True,
            "order_id": str(order.id),
            "total": {"amount": order.amount_total, "currency": order.currency},
            "items": [
                {"product_name": i["product_name"], "quantity": i["quantity"], "line_total": i["line_total"]}
                for i in (order.items or [])
            ],
            "payment_status": "NOT_PAID",
            "next_step": (
                "Tell the buyer the total and that a Pay button is now shown. "
                "They must press it themselves to authorize the payment. "
                "Do not claim the payment has happened."
            ),
        }

    if name in ("list_addresses", "set_delivery_address", "add_address"):
        from app.services import address_service

        if name == "list_addresses":
            addresses = address_service.list_addresses(buyer_id)
            return {
                "addresses": [
                    {
                        "index": i + 1,
                        "label": a.label,
                        "full_name": a.full_name,
                        "address": a.one_line(),
                        "is_default": a.is_default,
                    }
                    for i, a in enumerate(addresses)
                ],
                "has_any": bool(addresses),
                "note": (
                    None if addresses else
                    "No saved addresses. The buyer must add one from the Addresses "
                    "panel — you cannot create one for them."
                ),
            }

        if name == "add_address":
            # Report precisely what's missing so the agent asks once, for the
            # right things, instead of guessing a phone number or PIN.
            required = {
                "full_name": "the recipient's full name",
                "phone": "a contact phone number",
                "line1": "the street address",
                "city": "the city",
                "postal_code": "the PIN code",
            }
            missing = [label for field, label in required.items()
                       if not (args.get(field) or "").strip()]
            if missing:
                return {
                    "saved": False,
                    "missing": missing,
                    "note": "Ask the buyer for exactly these, then call add_address again.",
                }
            try:
                address = address_service.create_address(buyer_id, args)
            except Exception as exc:  # noqa: BLE001 — validation messages are buyer-safe
                return {"error": getattr(exc, "message", None) or "Couldn't save that address."}
            return {
                "saved": True,
                "delivery_address": address.one_line(),
                "label": address.label,
                "is_default": address.is_default,
            }

        addresses = address_service.list_addresses(buyer_id)
        idx = int(args.get("address_index") or 0) - 1
        if not (0 <= idx < len(addresses)):
            return {"error": "That address isn't in the list."}
        chosen = address_service.set_default(buyer_id, addresses[idx].id)
        return {"delivery_address": chosen.one_line(), "label": chosen.label}

    if name == "recommend_related":
        idx = int(args.get("product_index") or 1) - 1
        anchor = last_shown_cards[idx] if 0 <= idx < len(last_shown_cards) else None
        if anchor is None:
            return {"error": "I don't have that product in view to base suggestions on."}

        # Grounded in the real catalog: same category, excluding the anchor.
        data, _meta = catalog_client.search_catalog(
            category=anchor.get("category"),
            max_price=args.get("max_price"),
            in_stock=True,
            limit=6,
        )
        related = [p for p in data if p.get("product_id") != anchor.get("product_id")][:3]
        audit_service.log_event(
            action="CROSS_SELL_SUGGESTED",
            session_id=session.id,
            buyer_clerk_user_id=buyer_id,
            metadata={
                "anchor_product": anchor.get("name"),
                "category": anchor.get("category"),
                "suggested_count": len(related),
            },
            commit=False,
        )
        for product in related:
            collected_cards[product["product_id"]] = _to_card(product)
        if not related:
            return {"related": [], "note": "Nothing else in that category right now."}
        return {"related": [{"name": p["name"], "category": p.get("category")} for p in related]}

    return {"error": f"Unknown tool '{name}'."}


def _produce_stream(client, model, messages, q: "queue.Queue"):
    """Runs on a background daemon thread — does the actual blocking network
    call and pushes each chunk onto `q` as it arrives. Exists solely so the
    consumer's `q.get(timeout=...)` can enforce a real, preemptable
    deadline (see `_consume_stream_round`)."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.4,
            max_tokens=1024,
            stream=True,
        )
        for chunk in response:
            q.put(("chunk", chunk))
        q.put(("done", None))
    except Exception as exc:  # noqa: BLE001 — handed to the consumer thread via the queue, never raised here
        q.put(("error", exc))


def _consume_stream_round(client, model, messages, state: dict):
    """Consumes one streamed completion, yielding a `tool_start` SSE event
    the moment each tool call's name becomes known; buffers everything else
    into `state` (finish_reason/content/tool_calls) for the caller to act
    on once the round is fully drained — content is never yielded here, so
    pre-tool-call narration is structurally impossible to leak to the
    client (see module docstring).

    Runs the actual SDK call on a background thread and reads its output
    through a queue with `q.get(timeout=REQUEST_TIMEOUT_SECONDS)`, rather
    than relying on the client's own configured timeout. Confirmed live
    against NaraRouter: a streaming response can trickle keepalive frames
    that keep httpx's own read-timeout clock reset indefinitely, and
    because that block happens *inside* the SDK's iterator, a wall-clock
    check in the consuming `for` loop can never run until a chunk is
    already yielded — it can't preempt a stall that never yields one. A
    queue with a timeout can: `q.get()` returns control to this generator
    even if the background thread stays stuck, giving a real, bounded
    "no progress for REQUEST_TIMEOUT_SECONDS" cutoff regardless of what the
    SDK/transport is doing under the hood. Observed directly: a turn that
    hung past 60s with the client's own 20s timeout never firing."""
    content_parts: list[str] = []
    tool_calls: dict[int, dict] = {}
    finish_reason = None
    started: set[int] = set()
    emitted_text = False
    # Kept current as we go (not just at the end) so the caller can still tell
    # what reached the client if this round raises part-way through.
    state["streamed_text"] = False
    state["emitted_any"] = False

    q: queue.Queue = queue.Queue()
    threading.Thread(target=_produce_stream, args=(client, model, messages, q), daemon=True).start()

    while True:
        try:
            kind, payload = q.get(timeout=REQUEST_TIMEOUT_SECONDS)
        except queue.Empty as exc:
            raise TimeoutError("LLM stream produced no data within the time budget") from exc

        if kind == "error":
            raise payload
        if kind == "done":
            break

        chunk = payload
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        delta = choice.delta
        if choice.finish_reason:
            finish_reason = choice.finish_reason
        if delta and delta.content:
            content_parts.append(delta.content)
            # Sent the instant it arrives — this is what makes the reply feel
            # immediate. If it turns out to have been pre-tool narration, the
            # retract below takes it back before it can stand as an answer.
            yield {"type": "token", "delta": delta.content}
            emitted_text = True
            state["streamed_text"] = True
            state["emitted_any"] = True
        if delta and delta.tool_calls:
            if emitted_text:
                # This round is calling a tool after all, so everything streamed
                # so far was narration written before any grounded result
                # existed. Tell the client to drop it.
                yield {"type": "retract"}
                emitted_text = False
                state["streamed_text"] = False
            for tc in delta.tool_calls:
                entry = tool_calls.setdefault(tc.index, {"id": None, "name": None, "arguments": ""})
                if tc.id:
                    entry["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        entry["name"] = tc.function.name
                    if tc.function.arguments:
                        entry["arguments"] += tc.function.arguments
                if tc.index not in started and entry["name"]:
                    started.add(tc.index)
                    state["emitted_any"] = True
                    yield {"type": "tool_start", "tool": entry["name"], "label": TOOL_LABELS.get(entry["name"], "Working")}

    state["finish_reason"] = finish_reason
    state["content"] = "".join(content_parts)
    state["tool_calls"] = tool_calls
    # True when this round's text reached the client and was not retracted, so
    # the caller knows not to send it a second time.
    state["streamed_text"] = emitted_text


def _stream_text(text: str, chunk_size: int = 14):
    for i in range(0, len(text or ""), chunk_size):
        yield {"type": "token", "delta": text[i : i + chunk_size]}


def _emit_final(
    session,
    text: str,
    collected_cards: dict,
    suggestions: list[str],
    already_streamed: bool = False,
    checkout_ready: list | None = None,
):
    checkout_ready = checkout_ready or []
    message = _persist_assistant_reply(
        session, text, list(collected_cards.values()), suggestions,
        prepared_checkout=checkout_ready[-1] if checkout_ready else None,
    )
    if not already_streamed:
        # Only the fallback paths land here — their text was never streamed
        # live, so it still needs sending.
        yield from _stream_text(text)
    yield {"type": "product_cards", "cards": message.product_cards or []}
    if checkout_ready:
        # The agent prepared a priced order; the client renders a Pay button.
        # Authorization stays with the buyer.
        yield {"type": "checkout_ready", "order": checkout_ready[-1]}
    yield {"type": "suggestions", "items": suggestions}
    yield {"type": "done", "message_id": str(message.id)}


def stream_agent_turn(session, user_message_text: str):
    buyer_id = session.buyer_clerk_user_id
    is_first_turn = len(session.messages) == 0

    audit_service.log_event(
        action="USER_MESSAGE_RECEIVED",
        session_id=session.id,
        buyer_clerk_user_id=buyer_id,
        metadata={"message": user_message_text},
        commit=False,
    )
    comparison_intent = _detect_comparison_intent(user_message_text)
    if comparison_intent:
        audit_service.log_event(
            action="PRODUCT_COMPARISON",
            session_id=session.id,
            buyer_clerk_user_id=buyer_id,
            metadata={"message": user_message_text},
            commit=False,
        )

    db.session.add(
        ChatMessage(session_id=session.id, role=MessageRole.USER, content=user_message_text)
    )
    db.session.commit()

    last_shown_cards = _get_last_shown_cards(session)
    grounding = _format_grounding_context(last_shown_cards)
    order_context = _format_order_context(session)
    if order_context:
        grounding = f"{order_context}\n\n{grounding}" if grounding else order_context
    messages = _build_messages(session, grounding)

    client = _client()
    model = current_app.config["LLM_MODEL"]
    collected_cards: dict[str, dict] = {}
    checkout_ready: list = []
    had_search = had_zero_results = had_details = False

    # A real state, not a decorative one: the turn genuinely is waiting on
    # the model to decide what to do before any tool call exists to report.
    yield {"type": "thinking"}

    for _ in range(MAX_TOOL_ITERATIONS):
        round_state: dict = {}
        round_failed = None
        for attempt in range(LLM_ROUND_RETRIES + 1):
            round_state = {}
            try:
                yield from _consume_stream_round(client, model, messages, round_state)
                round_failed = None
                break
            except Exception as exc:  # noqa: BLE001 — any LLM/network/response-parsing failure (including our own stall timeout) must degrade to a fixed message, never invent a reply or crash
                round_failed = exc
                # Retry only while nothing has reached the client; replaying a
                # round after events were sent would duplicate them.
                if attempt < LLM_ROUND_RETRIES and not round_state.get("emitted_any"):
                    audit_service.log_event(
                        action="LLM_ROUND_RETRIED",
                        session_id=session.id,
                        buyer_clerk_user_id=buyer_id,
                        metadata={"error": str(exc)[:300], "attempt": attempt + 1},
                        commit=False,
                    )
                    continue
                break

        if round_failed is not None:
            audit_service.log_event(
                action="TOOL_FAILURE",
                session_id=session.id,
                buyer_clerk_user_id=buyer_id,
                metadata={"error": str(round_failed)},
            )
            if round_state.get("streamed_text"):
                # Clear the half-written reply so the fixed message replaces it
                # rather than appending to a truncated sentence.
                yield {"type": "retract"}
            yield from _emit_final(session, FIXED_LLM_FAILURE_MESSAGE, collected_cards, [])
            return

        tool_calls = round_state.get("tool_calls") or {}

        if not tool_calls:
            text = round_state.get("content", "")
            suggestions = _build_suggestions(
                cards=list(collected_cards.values()),
                had_search=had_search,
                had_zero_results=had_zero_results,
                had_details=had_details,
                comparison_intent=comparison_intent,
                is_first_turn=is_first_turn,
            )
            yield from _emit_final(
                session,
                text,
                collected_cards,
                suggestions,
                already_streamed=round_state.get("streamed_text", False),
                checkout_ready=checkout_ready,
            )
            return

        ordered_calls = [tool_calls[i] for i in sorted(tool_calls)]
        messages.append(
            {
                "role": "assistant",
                "content": round_state.get("content") or None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in ordered_calls
                ],
            }
        )

        tool_failed = False
        for tc in ordered_calls:
            try:
                args = json.loads(tc["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}

            try:
                result_payload = _execute_tool_call(
                    session, buyer_id, tc["name"], args, last_shown_cards,
                    collected_cards, checkout_ready,
                )
                if tc["name"] == "search_catalog":
                    had_search = True
                    results = result_payload.get("results") or []
                    if not results:
                        had_zero_results = True
                    yield {
                        "type": "tool_end",
                        "tool": tc["name"],
                        "result_count": len(results),
                        "args": args,
                    }
                elif tc["name"] == "get_product_details":
                    had_details = True
                    yield {
                        "type": "tool_end",
                        "tool": tc["name"],
                        "result_count": 0 if result_payload.get("error") else 1,
                        "args": args,
                        "product_name": result_payload.get("name"),
                    }
                elif tc["name"] in ("add_to_cart", "view_cart", "remove_from_cart",
                                    "prepare_checkout", "recommend_related",
                                    "list_addresses", "set_delivery_address", "add_address"):
                    yield {
                        "type": "tool_end",
                        "tool": tc["name"],
                        "error": bool(result_payload.get("error")),
                        "args": args,
                    }
                elif tc["name"] == "get_order_status":
                    yield {
                        "type": "tool_end",
                        "tool": tc["name"],
                        "result_count": len(result_payload.get("orders") or []),
                        "args": args,
                    }
                else:
                    yield {"type": "tool_end", "tool": tc["name"], "args": args}
            except catalog_client.CatalogError as exc:
                tool_failed = True
                audit_service.log_event(
                    action="TOOL_FAILURE",
                    session_id=session.id,
                    buyer_clerk_user_id=buyer_id,
                    metadata={"tool": tc["name"], "error": str(exc)},
                )
                result_payload = {"error": "Catalog temporarily unavailable."}
                yield {"type": "tool_end", "tool": tc["name"], "error": True}

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result_payload),
                }
            )

        if tool_failed:
            yield from _emit_final(session, FIXED_SEARCH_FAILURE_MESSAGE, collected_cards, [])
            return

    yield from _emit_final(session, FIXED_LOOP_LIMIT_MESSAGE, collected_cards, [])
