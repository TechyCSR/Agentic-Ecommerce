def parse_search_filters(args):
    def to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    return {
        "q": args.get("q"),
        "category": args.get("category"),
        "merchant_id": args.get("merchant_id"),
        "store_id": args.get("store_id"),
        "min_price": to_int(args.get("min_price")),
        "max_price": to_int(args.get("max_price")),
        "currency": args.get("currency"),
        "in_stock": args.get("in_stock", "").lower() == "true",
        "brand": args.get("brand"),
    }
