"""The Gemini tool-calling loop that powers the shopping chat.

Manual loop (not the SDK's automatic-function-calling mode) so every tool
call can be audit-logged and its raw JSON kept for product-card extraction
— cards are built only from tool results, never parsed from the model's
prose, so the agent cannot present a product it didn't actually look up.
"""

from flask import current_app
from google import genai
from google.genai import types

from app.extensions import db
from app.models import ChatMessage
from app.models.enums import MessageRole
from app.services import audit_service, catalog_client

MAX_TOOL_ITERATIONS = 6

FIXED_SEARCH_FAILURE_MESSAGE = (
    "I'm unable to search the catalog right now. Please try again."
)
FIXED_LOOP_LIMIT_MESSAGE = (
    "I'm having trouble narrowing this down. Could you tell me a bit more "
    "about what you're looking for?"
)

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
   "that keyboard", "compare these"), resolve the reference using the context block \
   that lists recently shown products with their product_id — call get_product_details \
   with that id if you need fresher/fuller data before answering.
6. When comparing products, only compare fields you actually have from tool results \
   (price, availability, stock, brand, category, variant names) — never claim a \
   feature difference you have no data for.
7. You cannot change prices, products, or inventory, and you cannot create or confirm \
   a payment — you only search, explain, compare, and help the buyer pick a product/\
   variant to select for checkout. If asked to do any of those, explain that's not \
   something you can do here.
8. Keep responses concise and conversational. Ask a clarifying question when the \
   buyer's request is ambiguous (e.g. no budget or category given) rather than \
   guessing.
"""

SEARCH_CATALOG_TOOL = types.FunctionDeclaration(
    name="search_catalog",
    description=(
        "Search the merchant product catalog. Use whenever the buyer describes "
        "what they're looking for."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "q": {
                "type": "string",
                "description": "Free-text search across product name, description, brand.",
            },
            "category": {"type": "string", "description": "Category name, e.g. Keyboards, Audio, Men."},
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
            "limit": {"type": "integer", "description": "Max results, default 10, max 20."},
        },
    },
)

GET_PRODUCT_DETAILS_TOOL = types.FunctionDeclaration(
    name="get_product_details",
    description=(
        "Get full details for one product by its product_id: all variants, prices, "
        "stock and images. Use to answer questions about a specific product, or to "
        "verify current price/stock before comparing or confirming a selection."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {"product_id": {"type": "string", "description": "The product's UUID."}},
        "required": ["product_id"],
    },
)


def _client():
    return genai.Client(api_key=current_app.config["GEMINI_API_KEY"])


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


def _build_grounding_context(session) -> str | None:
    last_with_cards = next(
        (
            m
            for m in reversed(session.messages)
            if m.role == MessageRole.ASSISTANT and m.product_cards
        ),
        None,
    )
    if not last_with_cards:
        return None

    lines = []
    for i, card in enumerate(last_with_cards.product_cards, start=1):
        price = card.get("price") or {}
        lines.append(
            f"{i}. {card.get('name')} (product_id: {card.get('product_id')}, "
            f"price: {price.get('amount')} {price.get('currency')}, "
            f"availability: {card.get('availability')})"
        )
    return (
        "[Context — products most recently shown to the buyer, in order, for "
        "resolving references like 'the first one' or 'the cheapest one':\n"
        + "\n".join(lines)
        + "\nUse the exact product_id above when calling get_product_details.]"
    )


def _build_contents(session, grounding: str | None) -> list:
    contents = []
    messages = list(session.messages)
    last_user_index = max(
        (i for i, m in enumerate(messages) if m.role == MessageRole.USER), default=-1
    )
    for i, msg in enumerate(messages):
        role = "user" if msg.role == MessageRole.USER else "model"
        text = msg.content
        if grounding and i == last_user_index:
            text = f"{grounding}\n\n{text}"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
    return contents


def _detect_comparison_intent(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in ("compare", " vs ", " vs.", "versus", "difference between"))


def _persist_assistant_reply(session, text: str, cards: list[dict]):
    message = ChatMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=text,
        product_cards=cards or None,
    )
    db.session.add(message)
    if not session.title:
        session.title = text.strip()[:80] or "New chat"
    db.session.commit()
    return message


def run_agent_turn(session, user_message_text: str) -> ChatMessage:
    buyer_id = session.buyer_clerk_user_id

    audit_service.log_event(
        action="USER_MESSAGE_RECEIVED",
        session_id=session.id,
        buyer_clerk_user_id=buyer_id,
        metadata={"message": user_message_text},
    )
    if _detect_comparison_intent(user_message_text):
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

    grounding = _build_grounding_context(session)
    contents = _build_contents(session, grounding)

    tool = types.Tool(function_declarations=[SEARCH_CATALOG_TOOL, GET_PRODUCT_DETAILS_TOOL])
    config = types.GenerateContentConfig(
        tools=[tool],
        system_instruction=SYSTEM_PROMPT,
        temperature=0.4,
        max_output_tokens=2048,
    )

    client = _client()
    collected_cards: dict[str, dict] = {}

    for _ in range(MAX_TOOL_ITERATIONS):
        try:
            response = client.models.generate_content(
                model=current_app.config["GEMINI_MODEL"],
                contents=contents,
                config=config,
            )
        except Exception as exc:  # noqa: BLE001 — any Gemini/network failure must degrade to the fixed message, never invent a reply
            audit_service.log_event(
                action="TOOL_FAILURE",
                session_id=session.id,
                buyer_clerk_user_id=buyer_id,
                metadata={"error": str(exc)},
            )
            return _persist_assistant_reply(session, FIXED_SEARCH_FAILURE_MESSAGE, [])

        function_calls = response.function_calls or []
        if not function_calls:
            return _persist_assistant_reply(
                session, response.text or "", list(collected_cards.values())
            )

        contents.append(response.candidates[0].content)

        function_response_parts = []
        tool_failed = False

        for fc in function_calls:
            args = fc.args or {}
            try:
                if fc.name == "search_catalog":
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
                    result_payload = {"results": data, "total": meta.get("total", len(data))}

                elif fc.name == "get_product_details":
                    product_id = args.get("product_id")
                    product = catalog_client.get_product(product_id)
                    audit_service.log_event(
                        action="PRODUCT_DETAILS_REQUESTED",
                        session_id=session.id,
                        buyer_clerk_user_id=buyer_id,
                        metadata={"product_id": product_id, "found": product is not None},
                    )
                    if product is None:
                        result_payload = {"error": "Product not found or not available."}
                    else:
                        collected_cards[product["product_id"]] = _to_card(product)
                        result_payload = product
                else:
                    result_payload = {"error": f"Unknown tool '{fc.name}'."}

            except catalog_client.CatalogError as exc:
                tool_failed = True
                audit_service.log_event(
                    action="TOOL_FAILURE",
                    session_id=session.id,
                    buyer_clerk_user_id=buyer_id,
                    metadata={"tool": fc.name, "error": str(exc)},
                )
                result_payload = {"error": "Catalog temporarily unavailable."}

            function_response_parts.append(
                types.Part.from_function_response(name=fc.name, response=result_payload)
            )

        contents.append(types.Content(role="user", parts=function_response_parts))

        if tool_failed:
            return _persist_assistant_reply(
                session, FIXED_SEARCH_FAILURE_MESSAGE, list(collected_cards.values())
            )

    return _persist_assistant_reply(
        session, FIXED_LOOP_LIMIT_MESSAGE, list(collected_cards.values())
    )
