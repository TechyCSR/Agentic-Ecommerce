# Agentic Commerce

> An autonomous AI shopping agent that can do everything up to — but never past — the point of payment.

| Application | Live URL | Purpose |
| :--- | :--- | :--- |
| **Buyer App** | [agent.techycsr.dev](https://agent.techycsr.dev) | Conversational AI shopping interface, cart building, and checkout |
| **Merchant Console** | [merchant.techycsr.dev](https://merchant.techycsr.dev) | Store management, product catalog, inventory holds, and order telemetry |

---

## The Problem with Conversational Commerce Today

Most existing "AI shopping assistants" fall into one of two traps:

1. **They are affiliate link generators:** They recommend products from static knowledge, hallucinate discontinued items, or dump web links onto the user without knowing whether the product is actually in stock.
2. **They are dangerous:** Prototypes that give autonomous agents direct access to credit cards or wallet balances create unacceptable financial risk. A single prompt injection, semantic confusion, or model hallucination can trigger unauthorized transactions.

Real e-commerce systems require strict guarantees: inventory must not be oversold, prices must be validated against a database rather than trusted from an LLM prompt, and money must never move without explicit, cryptographic human authorization.

Agentic Commerce is an end-to-end implementation of an e-commerce ecosystem designed from the ground up for autonomous AI agents, built with deterministic backend guards and hard trust boundaries.

---

## Core System Architecture

The architecture separates the agent's exploratory reasoning from financial execution. The agent operates within a restricted tool runtime, while financial mutations occur exclusively inside an isolated transaction pipeline.

```text
       Buyer (Human User)
               │
               ▼
      AI Shopping Agent
   (17 Sandboxed Agent Tools)
               │
   ┌───────────┴───────────┐
   │ • Search Catalog      │
   │ • Filter by Facets    │
   │ • Compare Specs       │
   │ • Hold Stock          │
   │ • Build Multi-Store   │
   │   Unified Cart        │
   │ • Validate Address    │
   └───────────┬───────────┘
               ▼
      Checkout Prepared
   (Immutable Draft Created)
               │
   ════════════╪════════════  ◄── HARD TRUST BOUNDARY (Enforced at Code Level)
               │
        Human Reviews &
       Explicitly Pays
               │
               ▼
       Razorpay Gateway
    (Client Modal / 3DS)
               │
               ▼
   Backend Cryptographic Check
   (HMAC-SHA256 Signature)
               │
               ▼
     Order State: SETTLED
  (Inventory Permanently Deducted)
```

### The Trust Boundary

The agent has **17 tools**, but not one of them can initiate a payment, mark an order as paid, or modify product prices:

* **No Financial Write Paths:** The agent has zero API routes, database models, or tools capable of initiating a charge or overriding payment verification.
* **Server-Authoritative Pricing:** Prices are re-fetched directly from the merchant database during order preparation. The LLM's conversational output is never trusted as the source of truth for amounts.
* **Cryptographic Verification:** Orders transition to `PAID` exclusively when the backend verifies Razorpay's HMAC-SHA256 signature against the shared secret.

---

## State Machine: Lifecycle of an Agentic Purchase

Every transaction follows a deterministic, seven-stage state machine:

```text
[DISCOVERY] ──► [SELECTION] ──► [RESERVATION] ──► [CHECKOUT_DRAFT]
                                                        │
                                                        ▼
[FULFILLED] ◄── [SETTLED] ◄── [VERIFICATION] ◄── [HUMAN_AUTHORIZATION]
```

1. **Discovery:** The agent queries merchant endpoints using structured facets (category slugs, brand constraints, price ranges, and in-stock booleans).
2. **Selection:** The buyer selects variants. The agent tracks items, quantities, and store origins in a unified cart session.
3. **Reservation:** When checkout approaches, the backend requests a temporary 15-minute hold on the selected SKU variants using database row-level locking.
4. **Checkout Draft:** The backend compiles items across stores, applies currency rules, verifies delivery details, and generates a immutable draft order.
5. **Human Authorization:** The UI renders the final order summary. The buyer explicitly clicks "Pay".
6. **Verification:** The Razorpay modal processes the charge. The payment payload is posted to the backend, which cryptographically verifies the signature before updating the state.
7. **Settlement:** Stock is permanently deducted, inventory holds are cleared, and separate fulfillment tickets are routed to each respective merchant.

---

## Deep Technical Capabilities

### Multi-Merchant Unified Cart
A buyer can ask for items from completely different stores in the same chat (e.g., milk from a grocery store and wireless earbuds from an electronics merchant). The agent constructs a single composite checkout. Upon settlement, the backend automatically partitions the order into separate merchant fulfillments with independent fulfillment IDs.

### Atomic Inventory Reservations
To prevent race conditions when multiple buyers or agents target the same limited stock, the system uses an atomic reservation model:
* A database transaction executes `SELECT stock_on_hand, stock_held FROM product_variants WHERE id = :id FOR UPDATE`.
* Available inventory is computed dynamically as:
  $$\text{Available Stock} = \text{stock\_on\_hand} - \text{stock\_held}$$
* If stock is available, `stock_held` is incremented and an expiration timestamp (TTL = 15 minutes) is assigned.
* If a buyer abandons checkout, a periodic background worker releases expired holds automatically, making the stock immediately available again without human intervention.

### Full Telemetry & The Money Trail
Every action leaves an immutable record in the audit log (`AuditEvent`). Buyers and merchants can inspect the exact reasoning trail behind every purchase:
```text
Session Initiated ──► Catalog Searched [query="cow milk", facets={category: "Dairy"}]
                  ──► Variant Identified [SKU="COW-MILK-500ML", price=24900]
                  ──► Stock Held [qty=1, expires_in=900s]
                  ──► Order Created [order_id="ord_98f1...", total=24900 INR]
                  ──► Buyer Authorized [method="card", gateway="razorpay"]
                  ──► Signature Verified [signature_match=true]
                  ──► Order Settled
```

### Defensive Error Handling

| Edge Case | System Response |
| :--- | :--- |
| **Forged Signature** | Webhook and client verification calculate expected HMAC-SHA256 signature. Mismatch raises `PaymentVerificationError` and logs a security incident. |
| **Concurrent Last-Unit Race** | Row locks ensure only one transaction acquires the inventory hold. The second transaction immediately receives an out-of-stock response. |
| **Model Hallucination** | If the LLM generates a non-existent variant ID, the tool validation layer rejects the call before hitting the database. |
| **Network Timeout During Hold** | Holds have an explicit TTL. If connectivity drops, unfinalized reservations lapse safely without strand inventory. |
| **Merchant Service Partition** | If a merchant service is temporarily unreachable during sync, the verified paid order remains secure in the local database and retries sync idempotently. |

---

## System Components & Stack

The codebase is structured as a monorepo containing two decoupled microservices and two frontends:

```text
Agentic-Ecommerce/
├── Agent/
│   ├── frontend/         # Next.js 14 App Router (Buyer Chat Interface)
│   └── backend/          # Python 3.12 / Flask (Agent Logic, Tool Runtime, Checkout)
├── Merchant/
│   ├── frontend/         # Next.js 14 App Router (Merchant Operations & Analytics)
│   └── backend/          # Python 3.12 / Flask (Catalog Engine, Inventory Holds, APIs)
└── catalyst.json         # Infrastructure & container runtime configuration
```

* **AI Agent Engine:** LLM orchestration with streaming Server-Sent Events (SSE) and deterministic tool dispatch.
* **Backend Services:** Python 3.12, Flask, Gunicorn WSGI with multi-worker concurrency, and SQLAlchemy 2.0.
* **Database:** Serverless PostgreSQL via Neon with connection pooling and pre-ping health checks.
* **Authentication:** Clerk for session tokens, JWT validation, and role-based access.
* **Media & Assets:** Cloudinary CDN for product image storage and transformations.
* **Payment Integration:** Razorpay Test Mode with server-side signature verification.

---

## Local Development Setup

### Prerequisites
* Python 3.12+
* Node.js 18+ and npm
* PostgreSQL instance (local or Neon connection URL)

### 1. Clone Repository
```bash
git clone https://github.com/techycsr/Agentic-Ecommerce.git
cd Agentic-Ecommerce
```

### 2. Configure Environment Variables
Copy the template `.env.example` files to `.env` in both backend directories:
```bash
cp Agent/backend/.env.example Agent/backend/.env
cp Merchant/backend/.env.example Merchant/backend/.env
```
Fill in your database URL, Clerk keys, and payment credentials.

### 3. Run Backend Microservices
```bash
# Terminal 1: Merchant Backend
cd Merchant/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 run.py

# Terminal 2: Agent Backend
cd Agent/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 run.py
```

### 4. Run Frontend Applications
```bash
# Terminal 3: Buyer Experience App
cd Agent/frontend
npm install
npm run dev

# Terminal 4: Merchant Dashboard
cd Merchant/frontend
npm install
npm run dev
```

The Buyer App will be live at `http://localhost:3000` and the Merchant Dashboard at `http://localhost:3001`.

---

## Project Principles

1. **Deterministic Over Generative:** Use the LLM for language comprehension and discovery; use deterministic code and ACID database transactions for prices, stock, and checkouts.
2. **Explicit Human Consent:** No money moves without human authorization. The boundary between recommendation and purchase is inviolable.
3. **Graceful Degradation:** When APIs disconnect, models timeout, or stock sells out, the system fails cleanly with structured explanations instead of infinite loops.
