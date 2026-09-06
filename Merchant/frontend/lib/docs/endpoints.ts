/**
 * The agent API, described once.
 *
 * Both the reference and the playground read from this, so a documented
 * parameter and a sent request can't drift apart — the previous docs
 * described two endpoints while the API served ten.
 */

export type HttpMethod = "GET" | "POST" | "DELETE";

export interface Param {
  name: string;
  type: string;
  required?: boolean;
  description: string;
  /** Prefilled in the playground so Send works without reading first. */
  example?: string;
}

export interface Endpoint {
  id: string;
  method: HttpMethod;
  /** `:name` segments are editable in the playground. */
  path: string;
  scope: string;
  title: string;
  summary: string;
  /** Things that are true but not obvious from the signature. */
  notes?: string[];
  pathParams?: Param[];
  query?: Param[];
  body?: Record<string, unknown>;
  bodyFields?: Param[];
  response: string;
}

export const SCOPES = [
  {
    name: "catalog:read",
    description: "Search the catalog and read the shelves and brands it stocks.",
  },
  {
    name: "product:read",
    description: "Read one product in full — every variant, price, image and stock level.",
  },
  {
    name: "checkout:create",
    description:
      "Hold stock, register a paid order, and read or cancel one back. This is the only scope that changes anything.",
  },
];

export const ENDPOINTS: Endpoint[] = [
  {
    id: "catalog-search",
    method: "GET",
    path: "/api/v1/agent/catalog/search",
    scope: "catalog:read",
    title: "Search the catalog",
    summary:
      "The main read. Returns active, agent-searchable products with live prices and stock.",
    notes: [
      "`category` and `brand` are constraints, matched on whole words — `car` will not reach `Hair Care`. Use `/catalog/facets` to get the values that exist.",
      "`q` is for descriptive words a category can't express (`mechanical`, `cotton`). Every word must match, so keep it short.",
      "`stock_quantity` is what you can actually buy: units on hand minus what other checkouts are holding.",
    ],
    query: [
      { name: "q", type: "string", description: "Descriptive keywords. Each word must match somewhere.", example: "" },
      { name: "category", type: "string", description: "Exact shelf name. A parent searches everything beneath it.", example: "Smartphones" },
      { name: "brand", type: "string", description: "Exact brand name.", example: "" },
      { name: "min_price", type: "integer", description: "Lowest price, in paise.", example: "" },
      { name: "max_price", type: "integer", description: "Highest price, in paise. ₹30,000 is 3000000.", example: "" },
      { name: "currency", type: "string", description: "Three-letter code, e.g. INR.", example: "" },
      { name: "in_stock", type: "boolean", description: "`true` to exclude anything with no stock.", example: "true" },
      { name: "merchant_id", type: "uuid", description: "Restrict to one merchant.", example: "" },
      { name: "store_id", type: "uuid", description: "Restrict to one store.", example: "" },
      { name: "limit", type: "integer", description: "Page size. Default 20, max 100.", example: "2" },
      { name: "offset", type: "integer", description: "Pagination offset. Default 0.", example: "" },
    ],
    response: `{
  "success": true,
  "data": [
    {
      "product_id": "6b67982b-df3b-40a1-b2ab-c47d1bb9ceae",
      "name": "Vivo X21",
      "brand": "Vivo",
      "category": "Smartphones",
      "description": "The Vivo X21 is a premium smartphone…",
      "merchant": { "merchant_id": "3d28b16…", "name": "Chandan's Store" },
      "store":    { "store_id": "16d80f9…", "name": "VoltEdge", "currency": "INR" },
      "images": [{ "url": "https://…/1.webp", "is_primary": true }],
      "variants": [
        {
          "variant_id": "…", "name": "128GB", "sku": "VIVO-X21-128GB",
          "price": { "amount": 4099900, "currency": "INR" },
          "compare_at_price": { "amount": 4899900, "currency": "INR" },
          "availability": "IN_STOCK",
          "stock_quantity": 12,   // what you can buy
          "stock_on_hand": 12,    // physically in the warehouse
          "stock_held": 0         // held by other checkouts
        }
      ],
      "agent_searchable": true
    }
  ],
  "meta": { "total": 40, "limit": 2, "offset": 0, "has_more": true }
}`,
  },
  {
    id: "catalog-facets",
    method: "GET",
    path: "/api/v1/agent/catalog/facets",
    scope: "catalog:read",
    title: "List shelves and brands",
    summary:
      "Every category and brand that currently holds a live product, with counts.",
    notes: [
      "Call this before searching. A category you invent returns nothing, which reads to a buyer as 'we don't sell that' when in fact you asked for a shelf that doesn't exist.",
    ],
    response: `{
  "success": true,
  "data": {
    "categories": [
      { "name": "Bath & Body", "product_count": 45 },
      { "name": "Beverages",   "product_count": 45 }
    ],
    "brands": [
      { "name": "Apple", "product_count": 30 },
      { "name": "Amul",  "product_count": 22 }
    ]
  }
}`,
  },
  {
    id: "product-get",
    method: "GET",
    path: "/api/v1/agent/products/:product_id",
    scope: "product:read",
    title: "Get one product",
    summary: "The full record for a single product, in the same shape search returns.",
    notes: [
      "404s for anything inactive or not agent-searchable — a merchant can take a product off the agent API without deleting it.",
    ],
    pathParams: [
      {
        name: "product_id",
        type: "uuid",
        required: true,
        description: "From a search result's `product_id`.",
        example: "6b67982b-df3b-40a1-b2ab-c47d1bb9ceae",
      },
    ],
    response: `{ "success": true, "data": { "product_id": "…", "name": "Vivo X21", … } }`,
  },
  {
    id: "reservations-create",
    method: "POST",
    path: "/api/v1/agent/reservations",
    scope: "checkout:create",
    title: "Hold stock",
    summary:
      "Reserves units while a buyer pays, so two agents can't be quoted the same last one.",
    notes: [
      "Idempotent on `agent_order_id`: posting again re-prices the hold against the cart you send and restarts the clock.",
      "The hold is logical — `stock_on_hand` doesn't move. It comes off `stock_quantity` for everyone else.",
      "Expiry is enforced on read, so an abandoned checkout frees its stock on its own. `ttl_minutes` defaults to 15 and is capped at 60.",
      "Refused with `INSUFFICIENT_STOCK` if the units aren't there — that is the failure you want, because it happens before you charge anyone.",
    ],
    bodyFields: [
      { name: "agent_order_id", type: "string", required: true, description: "Your own order id. The idempotency key." },
      { name: "items[].variant_id", type: "uuid", required: true, description: "Which variant to hold." },
      { name: "items[].quantity", type: "integer", required: true, description: "How many. At least 1." },
      { name: "ttl_minutes", type: "integer", description: "How long to hold. Default 15, max 60." },
    ],
    body: {
      agent_order_id: "demo-order-1",
      items: [{ variant_id: "a3a03da3-f7e4-4e37-9d7e-46b219237a55", quantity: 1 }],
      ttl_minutes: 10,
    },
    response: `{
  "success": true,
  "data": {
    "agent_order_id": "demo-order-1",
    "expires_at": "2026-09-06T05:36:01.764136+00:00",
    "ttl_seconds": 599,
    "reservations": [
      { "id": "…", "variant_id": "…", "quantity": 1, "status": "HELD",
        "expires_at": "…", "settled_at": null }
    ]
  }
}`,
  },
  {
    id: "reservations-get",
    method: "GET",
    path: "/api/v1/agent/reservations/:agent_order_id",
    scope: "checkout:create",
    title: "Check a hold",
    summary: "What is still held for an order, and for how much longer.",
    notes: ["`held: false` means it lapsed or was never taken — not an error."],
    pathParams: [
      { name: "agent_order_id", type: "string", required: true, description: "The id you reserved under.", example: "demo-order-1" },
    ],
    response: `{
  "success": true,
  "data": {
    "agent_order_id": "demo-order-1",
    "held": true,
    "expires_at": "2026-09-06T05:36:01.764136+00:00",
    "ttl_seconds": 594,
    "reservations": [ … ]
  }
}`,
  },
  {
    id: "reservations-delete",
    method: "DELETE",
    path: "/api/v1/agent/reservations/:agent_order_id",
    scope: "checkout:create",
    title: "Release a hold",
    summary: "Give the stock back early, when a buyer walks away or changes the cart.",
    notes: [
      "Never an error when there is nothing held — a late release still reads as success.",
    ],
    pathParams: [
      { name: "agent_order_id", type: "string", required: true, description: "The id you reserved under.", example: "demo-order-1" },
    ],
    bodyFields: [
      { name: "reason", type: "string", description: "Recorded on the audit event." },
    ],
    body: { reason: "buyer_changed_cart" },
    response: `{ "success": true, "data": { "agent_order_id": "demo-order-1", "released": 1 } }`,
  },
  {
    id: "orders-create",
    method: "POST",
    path: "/api/v1/agent/orders",
    scope: "checkout:create",
    title: "Register a paid order",
    summary:
      "Records an order you have already collected payment for, and brings stock down.",
    notes: [
      "Nothing about price, merchant or store is taken from your request. Every line is re-read here and priced from this database.",
      "Idempotent on `agent_order_id`. A retry after a timeout returns the existing order rather than creating a second one or decrementing twice.",
      "One cart can span stores, so this returns a list — one order per store.",
      "Consumes any hold you took under the same `agent_order_id`, in the same transaction as the decrement.",
      "`INSUFFICIENT_STOCK` here means the goods went while the buyer was paying. It will never succeed on retry, so refund rather than retrying.",
    ],
    bodyFields: [
      { name: "agent_order_id", type: "string", required: true, description: "Your order id. The idempotency key." },
      { name: "buyer_ref", type: "string", description: "Your own identifier for the buyer." },
      { name: "currency", type: "string", description: "Defaults to INR." },
      { name: "items[].variant_id", type: "uuid", required: true, description: "Which variant was bought." },
      { name: "items[].quantity", type: "integer", required: true, description: "How many." },
      { name: "payment.provider_order_id", type: "string", description: "Razorpay order id, for reconciliation." },
      { name: "payment.provider_payment_id", type: "string", description: "Razorpay payment id." },
    ],
    body: {
      agent_order_id: "demo-order-1",
      buyer_ref: "buyer_123",
      currency: "INR",
      items: [{ variant_id: "a3a03da3-f7e4-4e37-9d7e-46b219237a55", quantity: 1 }],
      payment: { provider_order_id: "order_XXXX", provider_payment_id: "pay_XXXX" },
    },
    response: `{
  "success": true,
  "data": {
    "created": true,
    "orders": [
      { "id": "…", "status": "PAID", "total_amount": 10900, "currency": "INR",
        "agent_order_id": "demo-order-1", "items": [ … ], "payments": [ … ] }
    ]
  }
}`,
  },
  {
    id: "orders-get",
    method: "GET",
    path: "/api/v1/agent/orders/:agent_order_id",
    scope: "checkout:create",
    title: "Read an order back",
    summary: "Fulfillment status, so you can answer “where is my order?”.",
    notes: [
      "Status moves PAID → CONFIRMED → PACKED → SHIPPED → DELIVERED as the merchant works it.",
      "Returns every order the id produced, so report the least-advanced one for a cart that spanned stores.",
    ],
    pathParams: [
      { name: "agent_order_id", type: "string", required: true, description: "The id you registered under.", example: "demo-order-1" },
    ],
    response: `{ "success": true, "data": { "orders": [ { "id": "…", "status": "PAID", … } ] } }`,
  },
  {
    id: "orders-cancel",
    method: "POST",
    path: "/api/v1/agent/orders/:agent_order_id/cancel",
    scope: "checkout:create",
    title: "Cancel an order",
    summary: "Cancels a registered order and puts its stock back.",
    notes: [
      "Refused with `ORDER_ALREADY_SHIPPED` once it is on its way. An order that has shipped can't be unshipped, and restoring stock for it would corrupt the merchant's inventory.",
      "Refunding the buyer is your side of the job — this only reverses the merchant's record.",
    ],
    pathParams: [
      { name: "agent_order_id", type: "string", required: true, description: "The id you registered under.", example: "demo-order-1" },
    ],
    bodyFields: [{ name: "reason", type: "string", description: "Recorded on the audit event." }],
    body: { reason: "buyer_cancelled" },
    response: `{ "success": true, "data": { "cancelled": [ { "id": "…", "status": "CANCELLED" } ] } }`,
  },
];

export const ERRORS = [
  { status: "401", code: "UNAUTHORIZED", meaning: "No API key, or one this service doesn't recognise." },
  { status: "403", code: "INSUFFICIENT_SCOPE", meaning: "The key is valid but lacks the scope this endpoint needs." },
  { status: "403", code: "API_KEY_INACTIVE", meaning: "The key was revoked or suspended." },
  { status: "404", code: "PRODUCT_NOT_FOUND", meaning: "No active, agent-searchable product with that id." },
  { status: "404", code: "ORDER_NOT_FOUND", meaning: "No order registered under that agent_order_id." },
  { status: "404", code: "VARIANT_NOT_FOUND", meaning: "That variant id doesn't exist." },
  { status: "422", code: "INSUFFICIENT_STOCK", meaning: "Not enough units. Permanent — refund rather than retry." },
  { status: "422", code: "PRODUCT_NOT_AVAILABLE", meaning: "The product is no longer active." },
  { status: "422", code: "RESERVATION_ALREADY_CONSUMED", meaning: "That order was already placed; its hold is spent." },
  { status: "422", code: "ORDER_ALREADY_SHIPPED", meaning: "Too late to cancel." },
  { status: "422", code: "VALIDATION_ERROR", meaning: "A parameter or body field failed validation." },
];
