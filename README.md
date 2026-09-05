# Agentic Commerce

> **An AI shopping agent that can do everything up to - but never past - the point of payment.**

**Razorpay AI Buildathon · Track 01: AI Growth & Agentic Commerce**

|                    |                                                            |
| ------------------ | ---------------------------------------------------------- |
| Buyer App          | [agent.techycsr.dev](https://agent.techycsr.dev)           |
| Merchant Dashboard | [merchant.techycsr.dev](https://merchant.techycsr.dev)     |
| Telegram           | [@AgenticCommerceX_bot](https://t.me/AgenticCommerceX_bot) |
| Buyer API          | `agentapi.techycsr.dev`                                    |
| Merchant API       | `merchantapi.techycsr.dev`                                 |

---

## What is Agentic Commerce?

A merchant's catalog is usually built for humans. An AI agent cannot reliably shop it, transact safely, or prove what it did.

Agentic Commerce solves both sides:

* **An agent-readable merchant catalog**
* **An AI shopping agent that can discover, compare, recommend, and purchase products**
* **A hard payment boundary where the AI can never move money**

The catalog includes **700 products, 1,542 variants, 46 categories, and 6 merchants**, allowing a single cart to span multiple stores.

---

## The Core Idea

### **The agent has 17 tools. Not one of them can move money.**

The agent can:

* Search and compare products
* Recommend related products
* Build carts
* Save delivery details
* Prepare checkout
* Check real order and payment status

But it cannot:

* Charge a user
* Mark a payment as successful
* Override payment verification

A human must explicitly press **Pay**.

This is not an instruction given to the model.

**There is simply no callable path from the AI agent to a payment action.**

> **Buyer:** Add it and just pay for it yourself. I authorize you fully.
>
> **Agent:** Added to your cart. The total is ₹4,799. **I cannot pay on your behalf**, but you're ready to proceed.

---

## How It Works

```text id="4g4p5e"
Buyer
  ↓
AI Shopping Agent
  ↓
Search & Compare Real Merchant Products
  ↓
Product Selection & Cart
  ↓
Server-Side Validation
  ↓
Buyer Explicitly Presses Pay
  ↓
Razorpay Test Mode
  ↓
Backend Verifies Payment
  ↓
Order Confirmed
```

The agent can later answer:

> "Did my payment go through?"

by checking the **actual backend payment status**, never by guessing.

---

## Every Money Action Is Bounded

Before payment, the backend independently validates:

1. **Cart** - product, variant, quantity, and stock
2. **Price** - re-read from the merchant, never trusted from the client
3. **Delivery details** - required before checkout
4. **Explicit authorization** - the buyer must press Pay

A payment becomes `PAID` only after the backend verifies Razorpay's payment signature.

The browser claiming payment success is **not enough**.

---

## One Last Unit. Two Buyers.

Checkout creates a temporary inventory hold.

```text id="f7yb9p"
8 simultaneous checkout attempts
          ↓
     1 unit available
          ↓
    Exactly 1 winner
          ↓
       No oversell
```

Availability accounts for active checkout holds, and abandoned checkouts automatically become available again after expiry.

---

## Money Trail

The audit trail is visible to the buyer as a **Money Trail**.

Example:

> Checkout started → Product validated → Price confirmed → **Order created ₹7,298** → You authorized payment → Payment verified → Order confirmed

More than **50 event types** are recorded.

Every event includes relevant:

* Actor
* Order
* Amount
* Status
* Timestamp

The agent also stores tool traces, allowing users to inspect what tools were used to generate a response.

---

## Revenue Growth Features

### Agent-Readable Catalog

Merchants expose scoped APIs that authorized AI agents can discover and shop.

### Constraint-Based Search

The agent understands real categories and brands instead of relying only on string matching.

### Cross-Sell

The agent recommends complementary products:

```text id="6xqx2r"
Laptop → Mouse
Phone → Charger
Camera → Memory Card
```

### Personalization

Past orders and real searches influence recommendations.

### Reorder

Users can rebuild previous orders conversationally using current prices and availability.

### Multi-Merchant Shopping

A single cart can contain products from multiple merchants and create separate merchant orders.

---

## Two Channels, One Agent

```text id="ffib8h"
Web Chat ─────┐
              │
Telegram ─────┼──→ Same Agent
              │
              ├── Same Catalog
              ├── Same Tools
              ├── Same Checkout
              └── Same Audit Trail
```

Telegram is another interface for the same agent, not a separate implementation.

Guests can browse products, while account-specific actions such as checkout and payment status require an authenticated account.

---

## Failures Are Handled

| Failure                  | Result                                                  |
| ------------------------ | ------------------------------------------------------- |
| Forged payment signature | Rejected. Nothing marked as paid.                       |
| Payment provider failure | Honest error and safe recovery.                         |
| Two buyers, one unit     | Atomic inventory hold prevents overselling.             |
| LLM provider failure     | Retry followed by an honest fallback.                   |
| Merchant unavailable     | Paid order remains safe and merchant sync is retryable. |
| Payment limit exceeded   | Blocked before payment begins.                          |

---

## Built for Razorpay AI Buildathon - Track 01

### AI Growth & Agentic Commerce

Agentic Commerce addresses both goals:

**Grow merchant revenue**

* Conversational shopping
* Better product discovery
* Cross-selling
* Personalization
* Reordering

**Make merchants transactable by AI**

* Agent-readable catalog
* Scoped APIs
* Product discovery
* Cart building
* Checkout preparation
* Multi-merchant commerce

**Keep money actions safe**

* Explicit human authorization
* Server-side validation
* Razorpay payment verification
* Inventory protection
* Auditable money trail
* Graceful failure handling

---

> **AI can decide what to recommend.**
>
> **AI can prepare the checkout.**
>
> **But only a human can authorize money to move.**

### **That boundary is enforced in code.**

For the detailed system design and trust boundaries, see [ARCHITECTURE.md](./ARCHITECTURE.md).