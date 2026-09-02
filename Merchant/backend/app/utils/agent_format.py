def variant_to_agent_dict(variant):
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
        "availability": variant.availability,
        "stock_quantity": variant.stock_quantity,
    }


def product_to_agent_dict(product):
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
        "variants": [variant_to_agent_dict(v) for v in product.variants],
        "agent_searchable": product.is_agent_searchable,
    }
