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
FIXED_LOOP_LIMIT_MESSAGE = (
    "I'm having trouble narrowing this down. Could you tell me a bit more "
    "about what you're looking for?"
)

TOOL_LABELS = {
    "search_catalog": "Searching the catalog",
    "get_product_details": "Checking product details",
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
8. Keep responses concise and conversational. Ask a clarifying question when the \
   buyer's request is ambiguous (e.g. no budget or category given) rather than \
   guessing. When you need a tool, call it immediately with no preceding narration \
   text ("Let me check...", "Here are some...") — go straight to the tool call and \
   only write prose once you have real results to report.
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

TOOLS = [SEARCH_CATALOG_TOOL, GET_PRODUCT_DETAILS_TOOL]


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


def _persist_assistant_reply(session, text: str, cards: list[dict], suggestions: list[str] | None):
    message = ChatMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=text,
        product_cards=cards or None,
        suggested_replies=suggestions or None,
    )
    db.session.add(message)
    if not session.title:
        session.title = text.strip()[:80] or "New chat"
    db.session.commit()
    return message


def _execute_tool_call(session, buyer_id: str, name: str, args: dict, last_shown_cards, collected_cards):
    """Runs one tool call, audit-logs it, and returns a JSON-serializable result."""
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
        )
        if not data:
            audit_service.log_event(
                action="NO_PRODUCTS_FOUND",
                session_id=session.id,
                buyer_clerk_user_id=buyer_id,
                metadata={"params": args},
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
        )
        if product is None:
            return {"error": "Product not found or not available."}
        collected_cards[product["product_id"]] = _to_card(product)
        return product

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
        if delta and delta.tool_calls:
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
                    yield {"type": "tool_start", "tool": entry["name"], "label": TOOL_LABELS.get(entry["name"], "Working")}

    state["finish_reason"] = finish_reason
    state["content"] = "".join(content_parts)
    state["tool_calls"] = tool_calls


def _stream_text(text: str, chunk_size: int = 14):
    for i in range(0, len(text or ""), chunk_size):
        yield {"type": "token", "delta": text[i : i + chunk_size]}


def _emit_final(session, text: str, collected_cards: dict, suggestions: list[str]):
    message = _persist_assistant_reply(session, text, list(collected_cards.values()), suggestions)
    yield from _stream_text(text)
    yield {"type": "product_cards", "cards": message.product_cards or []}
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
    )
    comparison_intent = _detect_comparison_intent(user_message_text)
    if comparison_intent:
        audit_service.log_event(
            action="PRODUCT_COMPARISON",
            session_id=session.id,
            buyer_clerk_user_id=buyer_id,
            metadata={"message": user_message_text},
        )

    db.session.add(
        ChatMessage(session_id=session.id, role=MessageRole.USER, content=user_message_text)
    )
    db.session.commit()

    last_shown_cards = _get_last_shown_cards(session)
    grounding = _format_grounding_context(last_shown_cards)
    messages = _build_messages(session, grounding)

    client = _client()
    model = current_app.config["LLM_MODEL"]
    collected_cards: dict[str, dict] = {}
    had_search = had_zero_results = had_details = False

    for _ in range(MAX_TOOL_ITERATIONS):
        round_state: dict = {}
        try:
            yield from _consume_stream_round(client, model, messages, round_state)
        except Exception as exc:  # noqa: BLE001 — any LLM/network/response-parsing failure (including our own stall timeout) must degrade to the fixed message, never invent a reply or crash
            audit_service.log_event(
                action="TOOL_FAILURE",
                session_id=session.id,
                buyer_clerk_user_id=buyer_id,
                metadata={"error": str(exc)},
            )
            yield from _emit_final(session, FIXED_SEARCH_FAILURE_MESSAGE, collected_cards, [])
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
            yield from _emit_final(session, text, collected_cards, suggestions)
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
                    session, buyer_id, tc["name"], args, last_shown_cards, collected_cards
                )
                if tc["name"] == "search_catalog":
                    had_search = True
                    results = result_payload.get("results") or []
                    if not results:
                        had_zero_results = True
                    yield {"type": "tool_end", "tool": tc["name"], "result_count": len(results)}
                elif tc["name"] == "get_product_details":
                    had_details = True
                    yield {
                        "type": "tool_end",
                        "tool": tc["name"],
                        "result_count": 0 if result_payload.get("error") else 1,
                    }
                else:
                    yield {"type": "tool_end", "tool": tc["name"]}
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
