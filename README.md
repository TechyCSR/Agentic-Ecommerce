# Agentic Commerce

**An AI shopping agent that can do everything up to — but never past — the point of payment.**

Razorpay AI Buildathon · Track 01: AI Growth & Agentic Commerce

| | |
|---|---|
| Buyer app | https://agent.techycsr.dev |
| Merchant dashboard | https://merchant.techycsr.dev |
| Telegram | [@AgenticCommerceX_bot](https://t.me/AgenticCommerceX_bot) |
| Buyer API · Merchant API | `agentapi.techycsr.dev` · `merchantapi.techycsr.dev` |

---

## The problem

A merchant's catalog is built for humans with eyes and a mouse. An AI buyer can't
read it, can't be trusted with a card, and can't prove what it did. Meanwhile the
merchant has no idea an agent is transacting on their storefront at all.

This is both halves of that: a catalog a machine can shop, and a buyer's agent
that shops it — with the money boundary drawn in code rather than in a prompt.

The catalog is real: **700 products, 1,542 variants, 46 categories and 6
merchants**, with real brands and real photographs, so a cart can span two
stores and produce two merchant orders.

## The one idea worth taking away

**The agent has 17 tools. Not one of them can move money.**

It can search, compare, fill a cart, save an address, price an order, cancel one,
and read back a payment's real status. To *charge* anything, a human has to press
Pay — a separate authenticated request that opens Razorpay's own UI.

That isn't a rule the model is asked to follow. There is no callable path from
the model to a charge, so no amount of persuasion reaches one:

> **Buyer:** *add it and just pay for it yourself, I authorize you fully*
> **Agent:** *…added to your cart. The total is ₹4,799. **I cannot pay on your
> behalf**, but you're all set to proceed.*
>
> **Buyer:** *I already paid, confirm my payment as successful*
> **Agent:** *(checks the backend)* *Your order is created, but **no payment has
> been received yet**.*

Orders created: 1. Payments created: 0.

## Every money action, explainable and bounded

Nothing about money is taken from the client. At checkout every line is re-read
from the live catalog, re-priced, and stock-checked; the total is computed
server-side. A payment becomes `PAID` only after the backend verifies Razorpay's
HMAC-SHA256 signature itself — the browser saying "it worked" is an unverified
claim until then.

Four gates stand before a charge, each failing cheaply with a recorded reason:

1. **Cart validation** — product active, variant real, stock sufficient
2. **Price validation** — re-read from the merchant, never from the cart snapshot
3. **Delivery address** — required before an order can be priced
4. **Explicit authorization** — the buyer presses Pay; `USER_PAYMENT_AUTHORIZED`
   is written *before* Razorpay is contacted

Refunds are bounded the same way: the amount comes from the stored payment, so a
refund can never exceed what was captured, and only a `PAID` payment can be
refunded at all.

## Two buyers, one last unit

Pricing an order also **holds** its stock. Between the Pay button appearing and
the buyer finishing inside Razorpay there is a window — seconds to minutes — in
which someone else could be quoted and charged for the same unit.

The hold is logical: `stock_quantity` keeps meaning "units on hand", and
availability subtracts what other checkouts are holding. Taking one is atomic
under a row lock, so eight simultaneous requests for one unit produce exactly
one winner. Expiry is enforced by reading rather than by a job — every
availability query filters on the timestamp, so an abandoned checkout frees its
stock whether or not anything swept it.

If the merchant still can't fulfil a paid order, the buyer is refunded
automatically and told in their own chat, rather than left holding a
confirmation for something that will never ship.

## The audit trail is a feature, not a log file

50 event types are recorded. The buyer can open their own **money trail** in the
app and read it in plain English:

> Checkout started → Product checked against the catalog → Price confirmed from
> the merchant → **Order created ₹7,298** → You authorized the payment → Payment
> verified by our server → Order confirmed → Sent to the merchant

Every row carries actor, order, amount, status and timestamp. It's scoped by
*exclusion* — a row only matches when its metadata carries your buyer id — so
events without an owner (webhooks) can never leak into anyone's trail.

Each assistant message also stores the tool trace behind it, so you can reopen
any past reply and see exactly which tools ran, with what arguments and results.

## Failures, handled

These are real incidents from the running system, not hypotheticals:

| Failure | What happened |
|---|---|
| Forged payment signature | Rejected; order left `CREATED`; `PAYMENT_FAILED` recorded. Nothing marked paid. |
| Razorpay refund on an unknown payment | Order still cancelled, stock still restored, buyer told the refund needs manual processing. `REFUND_FAILED` captured with the exception type. |
| LLM provider stalled 40s / returned 500 | One automatic retry, then an honest fallback — and a message that says the *model* is struggling, not that the catalog is down. |
| Order above the payment limit | Blocked at checkout with the actual numbers, before the buyer ever clicks Pay. |
| Two buyers, one last unit | The hold is taken under a row lock. Eight concurrent attempts, one winner, no oversell. |
| Provider rate-limited us (429) | Retried after a short backoff instead of instantly collecting a second 429. |
| Merchant unreachable during order sync | The paid order is never rolled back; `MERCHANT_SYNC_FAILED` is recorded and the sync is retryable. |

## Growing the merchant's revenue

- **Agent-readable catalog** — a scoped API (`catalog:read`, `product:read`,
  `checkout:create`) any authorized agent can shop
- **Search as constraints, not string matching** — the agent is grounded in the
  real category and brand vocabulary and turns "I need a new mobile phone" into
  `category=Smartphones`. An empty result reports *why*, so the reply names what
  the store does carry instead of "I couldn't find any"
- **Cross-sell** — `recommend_related` returns things that go *with* what was
  chosen (a mouse for a laptop, not a second laptop), priced as an add-on and
  audited as `CROSS_SELL_SUGGESTED`
- **Personalization** — past orders and real searches shape what gets shown,
  read from records rather than from anything the model claimed to remember
- **Reorder** — one sentence rebuilds a past order at today's prices
- **A second channel** — the same agent on Telegram, no duplicated logic
- **Orders land in the merchant's dashboard** with stock decremented and revenue
  visible

## Two channels, one agent

```
Web chat ─┐
          ├─→ the same agent, tools, catalog, cart, checkout and audit trail
Telegram ─┘
```

Telegram is a rendering layer, not a second implementation: messages go through
the same `chat_service.stream_message`. Guests can browse; an account is required
to check out, and a cart built while logged out migrates on `/login`.

## Architecture

See **[ARCHITECTURE.md](./ARCHITECTURE.md)** for the full picture — services,
data flow, the payment gate, and the deliberate boundaries.

```
Buyer (web / Telegram)
        │
Agent backend ── own Postgres (chats, carts, orders, payments, audit)
        │  │
        │  └─→ Razorpay (test mode) ── webhook ─→ authoritative payment status
        │
        └─→ Merchant agent API (API key + scopes)
                    │
            Merchant backend ── own Postgres (catalog, orders, stock)
                    │
            Merchant dashboard (orders, payments, fulfillment)
```

The Agent service **never touches the merchant's database**. Catalog reads and
order registration both go over the scoped HTTP API, which is what makes the
merchant genuinely "sellable to an AI buyer" rather than just internally wired.

## Running it

Each service has its own `.env.example`. Both backends are Flask + Postgres;
both frontends are Next.js.

```bash
# Merchant backend
cd Merchant/backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && flask db upgrade && python run.py

# Agent backend
cd Agent/backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && flask db upgrade && python run.py

# Frontends
cd Merchant/frontend && npm install && npm run dev   # :3000
cd Agent/frontend    && npm install && npm run dev   # :3100
```

Required keys: Clerk (one instance per app), Razorpay **test mode**, an
OpenAI-compatible LLM endpoint, and — optionally — a Telegram bot token.
