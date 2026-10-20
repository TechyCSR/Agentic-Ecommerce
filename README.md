# Agentic Commerce

> **An autonomous AI shopping agent that can do everything up to — but never past — the point of payment.**

| Component | Web App | Backend API |
| :--- | :--- | :--- |
| **Buyer Experience** | [agent.techycsr.dev](https://agent.techycsr.dev) | [agentapi.techycsr.dev](https://agentapi.techycsr.dev) |
| **Merchant Dashboard** | [merchant.techycsr.dev](https://merchant.techycsr.dev) | [merchantapi.techycsr.dev](https://merchantapi.techycsr.dev) |

---

## Why Agentic Commerce?

Traditional e-commerce websites are built for human eyeballs: visual banners, dropdown menus, filters, and pagination. LLMs struggle to browse them reliably, scrape them accurately, or handle real stock constraints.

On the other hand, giving an AI autonomous access to your credit card is a security nightmare. A single hallucination or prompt injection could drain a bank account in seconds.

**Agentic Commerce solves both problems:**

1. **An Agent-Native Catalog:** Merchants expose machine-readable, scoped endpoints with real-time stock, variants, and price facets.
2. **An Autonomous Shopping Agent:** Discovers, compares, recommends, and holds stock across multiple merchants in a single conversational cart.
3. **A Code-Enforced Payment Boundary:** The AI prepares everything, but **only the human clicks Pay**.

The live demo catalog includes **700+ products, 1,500+ variants, 46 categories, and 6 distinct stores** — all searchable and purchasable in one flow.

---

## The Golden Rule: 17 Tools, Zero Money Privileges

```text
       Buyer (Human)
             │
             ▼
      AI Shopping Agent
   (17 Agent Tools & Logic)
             │
  ┌──────────┴──────────┐
  │  • Search Catalog   │
  │  • Compare Specs    │
  │  • Recommend Items  │
  │  • Hold Stock       │
  │  • Build Cart       │
  │  • Save Address     │
  └──────────┬──────────┘
             ▼
    Checkout Prepared
             │
   ══════════╪══════════  ◄── HARD TRUST BOUNDARY (Enforced in Code)
             │
      Buyer Presses "Pay"
             │
             ▼
     Razorpay Checkout
             │
             ▼
  Backend Verifies Signature
             │
             ▼
       Order Settled
```

The agent can look up items, check inventory, build carts, and verify if an order succeeded.

**What the agent can NEVER do:**
* It cannot charge a card.
* It cannot mark an order as paid.
* It cannot bypass price verification.

This isn't just a system prompt asking the model to *"please be careful with money"*. **There is literally no API route, tool, or database permission that allows the AI to initiate a financial transaction.**

---

## Key Features

### 🛒 Multi-Merchant Unified Cart
A single conversation can find headphones from Store A and a laptop sleeve from Store B. The agent compiles them into one checkout and splits them into distinct merchant orders under the hood.

### ⏱️ Atomic Inventory Reservations (No Overselling)
When you proceed toward checkout, the backend places a **temporary 15-minute inventory hold**.
If multiple buyers try to purchase the very last unit of a product at once:
* Exactly **1 buyer** secures the hold.
* The others are gracefully informed that stock is currently reserved.
* If a cart is abandoned, the reservation expires automatically and stock returns to the pool.

### 🔍 Constraint-Based Search & Discovery
Instead of simple keyword matching, the agent understands categories, price bounds, brands, and availability filters via structured merchant APIs.

### 💡 Context-Aware Recommendations
Bought a DSLR camera? The agent proactively highlights compatible lenses, memory cards, and cleaning kits that fit your cart.

### 🧾 Transparent "Money Trail"
Every money-adjacent action emits an immutable audit event visible in the UI:
> *Cart created → Price validated from database → Stock held → Order drafted → Buyer authorized → Payment signature verified → Settled.*

---

## Defensive Engineering & Failure Handling

We designed the system assuming that networks fail, models hallucinate, and users test edge cases:

| Failure Scenario | Defensive System Behavior |
| :--- | :--- |
| **Forged Payment Signature** | Rejected cryptographically. The status remains unpaid. |
| **Two Buyers, One Unit** | Atomic DB locks guarantee zero double-selling. |
| **Price Tampering in Client** | The backend ignores client prices and re-reads directly from the merchant DB. |
| **LLM Provider Outage** | Exponential backoff followed by a structured fallback response. |
| **Merchant Service Downtime** | If already paid, the order remains safe in queue and retries merchant sync. |
| **Order Over Limit** | Blocked server-side before checkout can initialize. |

---

## Architecture Overview

The system consists of two independent backend services communicating with Next.js frontends:

```text
┌────────────────────────┐      ┌────────────────────────┐
│      Buyer Frontend    │      │   Merchant Dashboard   │
│   (Next.js / Tailwind) │      │  (Next.js / Analytics) │
└───────────┬────────────┘      └───────────┬────────────┘
            │                               │
            ▼                               ▼
┌────────────────────────┐      ┌────────────────────────┐
│     agent-backend      │◄────►│    merchant-backend    │
│  • Agent Orchestrator  │ API  │  • Scoped Agent APIs   │
│  • SSE Chat Streaming  │ Key  │  • Inventory Holds     │
│  • Payment Verification│      │  • Multi-Store Catalog │
└───────────┬────────────┘      └───────────┬────────────┘
            │                               │
            └───────────────┬───────────────┘
                            ▼
              ┌───────────────────────────┐
              │  Serverless PostgreSQL    │
              │  (Neon DB with Pooling)   │
              └───────────────────────────┘
```

* **Backend Services:** Built with Flask & Gunicorn on Python 3.12.
* **Database:** Serverless Neon PostgreSQL with connection pooling.
* **Authentication:** Clerk for both buyer and merchant identity.
* **Media Assets:** Cloudinary CDN for product imagery.

---

## Getting Started Locally

### 1. Clone the repository
```bash
git clone https://github.com/techycsr/Agentic-Ecommerce.git
cd Agentic-Ecommerce
```

### 2. Configure Environment
Set up `.env` files in `Agent/backend/` and `Merchant/backend/` using the provided `.env.example` templates.

### 3. Start Backend Services
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

### 4. Start Frontends
```bash
# Terminal 3: Agent Frontend
cd Agent/frontend && npm install && npm run dev

# Terminal 4: Merchant Frontend
cd Merchant/frontend && npm install && npm run dev
```

---

> **AI can search, compare, and assemble the cart.**  
> **Only a human can authorize money to move.**  
> *That boundary is absolute.*
