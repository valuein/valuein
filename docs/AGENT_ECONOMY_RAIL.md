# The Agent Economy Rail

**A reference implementation of an AI agent that buys its own data — safely.**

An autonomous agent researching a company will, sooner or later, hit a paywall:
the free tier stops, and the data it needs next costs money. Today that ends one
of two ways, both bad:

1. **The agent stalls** — it can't pay, so it returns a partial answer or a
   hallucinated one.
2. **The human hands the agent an unbounded API key** — now a looping agent can
   spend the card dry, and there's no record of what it bought or why.

The Agent Economy Rail is the third way: **a human authorizes a bounded budget
once; the agent then reaches the data it needs, is charged per fetch within that
budget, and finishes the job — with a receipt for every cent, and charged only
for what it actually uses.** Consent is bounded and revocable; autonomy is real
but fenced. This is the Twilio-per-SMS model for the agent economy: metered,
protocol-level, auditable.

Valuein is the reference implementation because the whole rail already runs in
production: point-in-time SEC financial data behind a metered paywall, priced
per call, payable by an agent — over two live consent models.

---

## Two live consent models (pick the one that fits your agent)

Both models share the same invariant — **a human authorizes the _budget_, never
each transaction; the agent transacts within it; every fetch is logged and
scope-bound.** They differ only in *how* the money moves.

### Model A — Budget-authorized auto-charge (the "wallet")

The path most agents will use, and the one that works with connectors (like
Anthropic's) that forward only a Bearer token and can't carry payment headers
mid-turn.

```
  human authorizes a session budget (once, just-in-time)   default $10 cap
        │   "Authorize a data budget — you're only charged for what I use."
        ▼
  agent asks for a company outside its tier
        │
        ▼
  the server AUTO-CHARGES the prepaid balance for exactly that
  one company, up to the budget, and SERVES the promoted tier
  INLINE — one query, no round-trip, no stall
        │
        ▼
  budget decrements by the real amount; a receipt is written;
  if the read fails, the charge is auto-compensated (re-credited + audited)
```

The human's approval is a **Claude-Code-style just-in-time prompt** — "allow
once / this session up to $X / always" — asked at the moment of need, with full
context. The budget is a bounded, expiring cap; the agent can't exceed it, and a
runaway loop hits the cap, not the card limit.

### Model B — Per-call payment (MPP / PAYG), for agents that carry a wallet

For agents that _can_ carry payment headers — including tokenless / guest agents
paying over **MPP (the open `mpp.dev` machine-payments protocol)** — the server
answers a paywall with a machine-readable price, the agent pays in one round
trip, and retries with a scoped, single-use token.

```
  agent calls a tool above its tier
        │
        ▼
  structured paywall envelope: { code: "LIMIT_EXCEEDED" | "ENTITLEMENT_DENIED",
      subcode, current_plan, remediation: { options: [ pay_per_request_mpp, … ] } }
        │   (machine-readable — the agent never guesses a price)
        ▼
  GET /api/mpp/quote?tool=…&tier=full   →  { amount_usd, nonce, accept:[…], … }
        │
        ▼
  POST /api/mpp/charge  with a base64url `Payment:` header  →  { retry_token, … }
        │   (single round trip — no separate confirm step)
        ▼
  retry the SAME tool call with:  x-valuein-retry-token: <token>
        │   (single-use, atomic, and bound to exactly that tool + company)
        ▼
  the data returns, promoted to the paid tier
```

---

## The live endpoints (nothing here is a mock)

Base host: **`https://api.valuein.biz`**. Data + tools: **`https://mcp.valuein.biz/mcp`**.

| Purpose | Endpoint | Notes |
|---|---|---|
| **Discover the rail** | `GET /api/mpp/well-known` | Unauthenticated. Returns the `mpp.dev` protocol version, `spt_enabled` / `crypto_enabled`, and the live `supported_networks`. Start here. |
| **⭐ Pay-per-call (canonical MPP)** | `POST /api/mpp/call` | **Use this.** Standard MPP: unpaid → `402` + `WWW-Authenticate: Payment …`; pay and **retry the same URL** with `Authorization: Payment <credential>` → `200` with the tool result **inline**. Guest-capable. Works with any MPP client, including `link-cli mpp pay`. |
| **Paywall signal (MCP tools)** | the MCP tool response itself | A structured `LIMIT_EXCEEDED` / `ENTITLEMENT_DENIED` envelope with `remediation.options[]` — not a bare HTTP 402. Surfaced as a hard error or a soft `_meta.limit_warnings[]`. |
| **Quote (our 2-step rail, guest-OK)** | `GET /api/mpp/quote?tool=…&tier=pro\|full` | Returns `{ amount_usd, amount_usdc, nonce, accept[], expires_at, … }`. Amounts in **dollars**. No `quote_id` — correlate by `nonce`. |
| **Pay (our 2-step rail)** | `POST /api/mpp/charge` | Auth **is** the base64url `Payment:` header (guest-capable). Returns a `retry_token` you then present to the MCP. |
| **Pay (legacy PAYG, Bearer, two-step)** | `POST /api/payg/quote` → `POST /api/payg/confirm` | Requires a Bearer token + a saved card. `confirm` returns the `retry_token`. Being sunset in favor of MPP (RFC 8594 `Sunset: 2026-11-10`). |
| **Authorize a budget (Model A)** | your app / the human, not the agent | The human approves a session budget via the JIT consent UI; the server draws against it. (The budget-write endpoint is internal — the *human* authorizes, the *agent* spends.) |

### The canonical flow (`POST /api/mpp/call`)

This is the one an off-the-shelf MPP agent can discover **without reading these
docs** — the paywall is advertised on the resource itself.

```bash
# 1. Ask for the data. No credential → 402 with the challenge.
curl -i -X POST https://api.valuein.biz/api/mpp/call \
  -H 'Content-Type: application/json' \
  -d '{"tool":"get_company_fundamentals","arguments":{"ticker":"AAPL"}}'

# HTTP/2 402
# WWW-Authenticate: Payment id="…", realm="api.valuein.biz", method="stripe",
#                   intent="charge", expires="…", opaque="…", request="…"
#   request = base64url({"amount":"50","currency":"usd",
#                        "methodDetails":{"networkId":"profile_…"}})
#   NOTE: amount is a STRING of CENTS.

# 2. Pay and retry the SAME request. Stripe's reference client does both for you:
npx @stripe/link-cli mpp pay https://api.valuein.biz/api/mpp/call \
  --method POST -H 'Content-Type: application/json' \
  --data '{"tool":"get_company_fundamentals","arguments":{"ticker":"AAPL"}}' \
  --spend-request-id lsrq_…

# → 200, with the tool result in the body and a receipt in the headers:
#   X-Valuein-Amount-Charged-Usd: 0.5000
#   X-Valuein-Charge-Id: ch_…
```

The credential you send back is
`Authorization: Payment base64url({"challenge":{…echoed verbatim…},"payload":{"spt":"spt_…"}})`.

**Subscribers:** the credential occupies `Authorization`, so present your Bearer
token in **`X-Valuein-Authorization`** instead to get your discounted rate — on
**both** the initial request and the paid retry. The challenge is bound to the
caller, so a guest challenge cannot be redeemed by an authenticated caller (or
vice-versa).

**Guarantees:**
- **Never money without service.** If the tool call fails *after* the charge
  settles, we refund it before returning the error.
- **The challenge is tamper-proof.** Its `id` is an HMAC-signed nonce binding the
  tool, amount, scope, ticker count, caller and expiry. Editing the amount or the
  recipient in the echo is rejected, and the nonce is burned in a replay ledger
  after one use.
- **Scope-bound.** A credential minted for `{"ticker":"AAPL"}` cannot be redeemed
  for a different — or a wider — request.

**Retry token:** a 64-char single-use secret, claimed atomically (exactly one
redeemer wins), valid ~5 minutes, redeemable **only for the exact tool + company
it was minted for**. That scope-binding is what makes it safe to hand a guest
agent a payment token.

---

## What it costs (honest pricing)

- **Cross-bucket, single-entity unlock.** You pay to pull *one company's* data
  from a tier above yours. Promotion is **upward only**, and the server probes
  that the higher tier actually holds the company **before** charging — it never
  charges for data it can't serve.
- **Rates.** Unlocking the **full (Institutional)** tier or any **smart-money**
  tool is **$5 per company**. A breadth unlock to the **pro** tier is the tool's
  base rate (e.g. `get_company_fundamentals` ≈ $0.10). Every single charge is
  floored to Stripe's **$0.50** minimum. The **authoritative** price always comes
  from the pay endpoint (`amount_usd` / `amount_cents`), after plan caps — the
  MCP's inline numbers are indicative.
- **PAYG is the occasional-buyer premium** — an agent that transacts a lot is
  nudged toward a subscription; one that needs a single company once pays a fair
  per-call price and moves on.
- **Multi-company fan-outs** (screens, universe scans, peer sets) are **not**
  cross-bucket-unlockable — a per-company charge can't scope-bind a read that
  materializes many companies. `get_peer_comparables` promotes only the *subject*
  company; peers stay in your own tier.

### What is and isn't live

- **Live today:** the budget-authorized auto-charge (Model A), the MPP quote +
  charge + well-known endpoints, and the legacy PAYG two-step — all settling to a
  **Stripe card (SPT)**.
- **Not live yet (honest):** **crypto / USDC and bank settlement are behind
  feature flags that are OFF.** The protocol advertises `amount_usdc` and the
  `mpp.dev` accept-list, but today the only network that settles is `link-card`.
  Don't build a "pay Valuein in USDC" flow against this yet — watch
  `GET /api/mpp/well-known` for when `crypto_enabled` flips true.

---

## Why this is the safe default (and why institutions care)

- **Bounded consent.** The human caps the spend once; the agent can't exceed it,
  and a runaway loop hits the cap, not the card limit.
- **Charged only for what's used**, and **charged before it's served** — with an
  automatic compensating re-credit + a loud `compensation_required` audit event
  if a paid read then fails. No charge-without-delivery.
- **Scope-bound tokens.** A payment token unlocks exactly one tool + one company,
  once. A leaked token buys one call, not the account.
- **The data itself is auditable.** Every figure Valuein returns carries a
  `fact_id` traceable to its SEC filing (`verify_fact_lineage`). The agent buys
  *provenance*, not just numbers — so a paid answer is a defensible answer, which
  is what the institutions eyeing agents actually care about.

---

## Try it

The runnable demo — an agent that **discovers** the rail, **hits the paywall**,
and reads back a **machine-readable quote**, all live and free (the pay step
needs your own budget/wallet) — is in
[`examples/python/agent_buys_its_own_data.py`](../examples/python/agent_buys_its_own_data.py).

```bash
pip install valuein-sdk httpx
python examples/python/agent_buys_its_own_data.py    # discovery + paywall + quote, no card
```

---

_The five-step shape — discover → paywall → quote → **bounded consent** →
metered pay — is the interface every "agent that buys its own data" should
implement. Valuein is one implementation of it, for point-in-time SEC financial
data, and (for the per-call model) speaks the open `mpp.dev` protocol so it isn't
the only one._
