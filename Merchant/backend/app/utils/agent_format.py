def variant_to_agent_dict(variant, held: int = 0):
    """The agent's view of a variant.

    `stock_quantity` reports what this caller could actually buy right now —
    units on hand minus what other buyers are holding mid-checkout — because
    that is the number the agent reasons and promises against. The raw counts
    are kept alongside it so the split stays inspectable rather than implied.
    """
    on_hand = variant.stock_quantity or 0
    available = max(0, on_hand - (held or 0))

    if variant.status.value == "DISCONTINUED":
        availability = "DISCONTINUED"
    elif available > 0:
        availability = "IN_STOCK"
    else:
        availability = "OUT_OF_STOCK"

    return {
        "variant_id": str(variant.id),
        "name": variant.name,
        "sku": variant.sku,
        "price": {
            "amount": variant.price,
            "currency": variant.currency,
        },
        "compare_at_price": (
            {"amount": variant.compare_at_price, "currency": variant.currency}
            if variant.compare_at_price is not None
            else None
        ),
        "availability": availability,
        "stock_quantity": available,
        "stock_on_hand": on_hand,
        "stock_held": held or 0,
    }


def product_to_agent_dict(product, held_map=None):
    """`held_map` maps variant id -> units held by in-flight checkouts. It is
    passed in rather than looked up here so a page of search results costs one
    query instead of one per variant."""
    held_map = held_map or {}
    store = product.store
    merchant = store.merchant if store else None
    primary_category = product.primary_category

    return {
        "product_id": str(product.id),
        "merchant": (
            {"merchant_id": str(merchant.id), "name": merchant.business_name}
            if merchant
            else None
        ),
        "store": (
            {
                "store_id": str(store.id),
                "name": store.name,
                "currency": store.currency,
            }
            if store
            else None
        ),
        "name": product.name,
        "description": product.description or product.short_description,
        "brand": product.brand,
        "category": primary_category.name if primary_category else None,
        "images": [
            {"url": image.image_url, "is_primary": image.is_primary}
            for image in product.images
        ],
        "variants": [
            variant_to_agent_dict(v, held_map.get(v.id, 0)) for v in product.variants
        ],
        "agent_searchable": product.is_agent_searchable,
    }
