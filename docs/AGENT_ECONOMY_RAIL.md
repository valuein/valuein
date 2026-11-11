# The Agent Economy Rail

**A reference implementation of an AI agent that buys its own data — safely.**

An autonomous agent researching a company will, sooner or later, hit a paywall:
the free tier stops, and the data it needs next costs money. Today that ends one
of two ways, both bad:

1. **The agent stalls** — it can't pay, so it returns a partial answer or a
   hallucinated one.
2. **The human hands the agent an unbounded API key** — now a looping agent can
   spend the card dry, and there's no record of what it bought or why.

The Agent Economy Rail is the third way: **the agent asks, is quoted an exact
price before anything is authorized, pays for exactly that, and is charged only
if the data arrives — with a receipt for every cent.** The human's consent is
bounded by the payment itself: a Shared Payment Token approved for one price.
This is the Twilio-per-SMS model for the agent economy: metered, protocol-level,
auditable.

Valuein is the reference implementation because the whole rail already runs in
production: point-in-time SEC financial data behind a paywall, priced up front,
payable by an agent over the open `mpp.dev` protocol.

---

## The promise

> **Ask → get a price → pay → get data.**
> **You are only ever charged for data you actually received.**

That second line is a guarantee, and it is enforced in code rather than in a
support policy. On `POST /api/mpp/call`, paying does **not** move money:

```
1. AUTHORIZE   we place a HOLD on the funds. Nothing settles. Nothing
               appears on a statement.
2. VERIFY      we fetch your data and confirm it was actually delivered
               at the level you paid for — not an error, not the free tier.
3. CAPTURE     only now is the money taken. Once.
```

Anything less than a verified delivery **releases the hold**. Not refunded —
**never charged**. No charge is created, so there is nothing to reconcile,
nothing to dispute, and nothing for a human to ask about later.

| what happens | what you pay |
|---|---|
| you get the data you asked for | the quoted price, once |
| the tool returns an error | **nothing** |
| the ticker doesn't exist | **nothing** |
| we cannot confirm the paid data was delivered | **nothing** |
| the payment itself fails to complete | **nothing** |

If our own infrastructure dies mid-payment, a sweep releases the hold within
minutes — it never rots on your card waiting for Stripe's 7-day expiry.

The uncertain case resolves in **your** favour by construction: if we cannot
*prove* you received the data, we do not capture. The worst outcome is that we
serve data we failed to bill for — our loss, not yours. It is deliberately
cheaper for us to lose a sale than to take a cent we cannot justify.

---

## One rail: MPP, card, on the full MCP endpoint

Machine payment is **MPP only**: the open [`mpp.dev`](https://mpp.dev) protocol,
settled by **card** (a Stripe Shared Payment Token). There is one paid route,
`POST https://api.valuein.biz/api/mpp/call`, and the offer is made on one MCP
endpoint, **`https://mcp.valuein.biz/mcp`**. The read-only research endpoint
(`/research/mcp`) and the sign-in workspace endpoint (`/workspace/mcp`) never
offer a payment. There is no account to create, no balance to top up, and no
minimum purchase beyond the price of what you ask for.

```
  agent asks for data it can't reach yet
        │      POST /api/mpp/call  {"tool":…, "arguments":{…}}
        ▼
  402 + WWW-Authenticate: Payment …          ← a PRICE, not a bill.
        │                                       You have not been charged.
        ▼
  retry the SAME request with the credential
        │      Authorization: Payment <base64url({challenge, payload:{spt}})>
        ▼
  ┌─ we HOLD the funds ─────────────────────────────────────────┐
  │  fetch the data · verify it was delivered                   │
  │                                                             │
  │   verified  → CAPTURE.  200 + data inline + a receipt       │
  │   anything  → RELEASE.  no charge is ever created           │
  │   else                                                      │
  └─────────────────────────────────────────────────────────────┘
```

This is the flow any standards-compliant MPP client speaks natively — including
Stripe's own `link-cli mpp pay` — with no Valuein-specific code.

*(A structured `LIMIT_EXCEEDED` / `ENTITLEMENT_DENIED` error with
`extensions.remediation.options[]` is still what an MCP **tool call** returns when
it hits a limit — it tells the agent the price and points it here. How to read a
tool error: the agent contract in [`MCP_TOOLS.md`](MCP_TOOLS.md#reading-tool-results-errors-and-paging).)*

---

## What you buy: a company pass, plus a per-run fee for heavy work

- **Company pass.** One company (a CIK) at one data level for **24 hours**: every
  company-data tool for that company, as often as you like, until it expires.
  Level `pro` (Pro data, history from 2011) is **$1.00**; level `full`
  (Institutional data: history back to 1993, plus the smart-money tools and
  `verify_filing_figures`) is **$5.00**. One order covers up to 50 companies. The payment returns your passes in the
  `X-Valuein-Mpp-Pass` response header and in `_meta["valuein/mpp"].passes`.
- **Pass reuse.** Send a pass back in the `x-valuein-mpp-pass` header on later
  `/mcp` calls and its company is served at its level, free of further charge,
  until it expires.
- **Per-run fees** for work that is not one company's data: **compute**
  (`compute_dcf`, `compute_lbo`, `forensic_audit`, document generation, …)
  **$1.00**, **verification** (the figure-checking tools, up to 50 figures a
  run) **$1.00**, and **universe** scans (`screen_universe`, `get_pit_universe`,
  `run_backtest`) **$5.00**. A compute or verification run also buys a pass for
  each company it reads that you do not already cover (a pass you hold or your
  own plan): `compute_dcf` on AAPL as a guest is $1.00 + $1.00 = **$2.00**. A
  universe run buys no passes.
- **Token holders pay 50%.** Any valid Valuein token halves every price, the
  free Benchmark token included. The
  payment occupies the `Authorization` header, so present your Bearer token in
  **`X-Valuein-Authorization`** instead, on both the initial request and the
  paid retry.
- **Verification trial.** Every account verifies its first **100 figures** free,
  once, on the four verification tools (a whole-report check is all or nothing,
  and the first one is free in full). A paid verification run covers only the
  figures your own plan does not already include. A guest has no trial.
- **Subscribers too.** A subscriber pays the same prices for data outside
  their plan.
- **No minimum.** The price of the call is the whole charge.

Tools that are free (`search_companies`, `describe_schema`, `verify_fact_lineage`,
…) cost nothing and never reach the paywall. The Workspace tools (watchlists,
signals, agents, reports, …) and bulk streaming (`get_compute_ready_stream`)
are not sold per call: they come with a subscription.

The **authoritative** prices are machine-readable and free:
`GET https://api.valuein.biz/api/mpp/tools` (the payable menu) and
`GET https://api.valuein.biz/api/mpp/quote?tool=…&tickers=…&level=pro|full` (a
price lookup that returns nothing redeemable). The exact charge for a call is the
`402` challenge's `request.amount`, stated in cents **before** you pay. Don't
infer a price from anything else — including this page.

---

## The live endpoints (nothing here is a mock)

Base host: **`https://api.valuein.biz`**. Data + tools: **`https://mcp.valuein.biz/mcp`**.

| Purpose | Endpoint | Notes |
|---|---|---|
| **Discover the rail** | `GET /api/mpp/well-known` | Unauthenticated. Returns the `mpp.dev` protocol version, `spt_enabled` / `crypto_enabled`, the live `supported_networks`, and the pass header name. Start here. |
| **Discover what you can buy** | `GET /api/mpp/tools` | Unauthenticated. The payable menu and the price book (pass prices, per-run fees, token discount). Call it once and you know the whole rate card. |
| **Price lookup** | `GET /api/mpp/quote?tool=…&tickers=…&level=pro\|full` | Unauthenticated and free. Returns the amount and the passes the call would buy. Nothing in it is redeemable; the `402` is the binding quote. |
| **Pay (the only paid route)** | `POST /api/mpp/call` | Standard MPP: unpaid → `402` + `WWW-Authenticate: Payment …`; pay and **retry the same URL** with `Authorization: Payment <credential>` → `200` with the tool result **inline**. Guest-capable. Body is `{"tool":…,"arguments":{…},"level":"pro"\|"full"}`. Works with any MPP client, including `link-cli mpp pay`. |
| **Receipt — "did I pay?"** | `GET /api/mpp/receipt?nonce=…` | Unauthenticated (the nonce is your secret). Answers `charged` (with the charge id), `not_charged` (with the reason), `refunded`, or `unconfirmed`; a `404` means no record yet. Use it when a response is lost. |
| **Paywall signal (MCP tools)** | the MCP tool response itself | A structured `LIMIT_EXCEEDED` / `ENTITLEMENT_DENIED` error with `extensions.remediation.options[]`, on `/mcp` only. |

### The flow, step by step (`POST /api/mpp/call`)

The paywall is advertised on the resource itself, so an off-the-shelf MPP agent
can discover it without reading these docs.

```bash
# 1. Ask for the data. No credential → 402 with the challenge.
curl -i -X POST https://api.valuein.biz/api/mpp/call \
  -H 'Content-Type: application/json' \
  -d '{"tool":"get_company_fundamentals","arguments":{"ticker":"AAPL"}}'

# HTTP/2 402
# WWW-Authenticate: Payment id="…", realm="api.valuein.biz", method="stripe",
#                   intent="charge", expires="…", opaque="…", request="…"
#   request = base64url({"amount":"100","currency":"usd",
#                        "methodDetails":{"networkId":"profile_…",
#                                         "paymentMethodTypes":["card"]}})
#   NOTE: amount is a STRING of CENTS ("100" = $1.00, one pro-level company pass).

# 2. Pay and retry the SAME request. Stripe's reference client does both for you
#    (npm install -g @stripe/link-cli):
link-cli mpp pay https://api.valuein.biz/api/mpp/call -X POST \
  -H 'Content-Type: application/json' \
  -d '{"tool":"get_company_fundamentals","arguments":{"ticker":"AAPL"}}' \
  --context "Buying one pro-level company pass for AAPL so my research agent can read its point-in-time fundamentals with filing lineage."
```

`mpp pay` probes the `402`, creates a Link spend request, waits for the user to
approve it in the Link app, then pays and retries. `--context` must be at least
100 characters and say what is being bought and why. Pass
`--spend-request-id lsrq_…` to reuse a spend request that is already approved.

```
# → 200, the tool result in the body and a receipt in the headers:
#   X-Valuein-Amount-Charged-Usd: 1.00
#   X-Valuein-Charge-Id: ch_…
#   X-Valuein-Mpp-Pass: …
#   _meta["valuein/mpp"] = {
#     "charged_usd": 1, "unlock_level": "pro",
#     "passes": [{ "cik": "0000320193", "level": "pro", "expires_at": … }]
#   }
```

If you build the credential yourself, it is
`Authorization: Payment base64url({"challenge":{…echoed verbatim…},"payload":{"spt":"spt_…"}})`.

Reuse the pass for the next 24 hours, with no further payment, by sending it on
the MCP endpoint:

```
POST https://mcp.valuein.biz/mcp
x-valuein-mpp-pass: <the X-Valuein-Mpp-Pass value>
```

**Guarantees:**
- **Never money without service.** We authorize a hold, verify the data actually
  came back, and only then capture. Anything else releases the hold — no charge
  is ever created, so there is nothing to refund. See *The promise* above.
- **The challenge is tamper-proof.** Its `id` is an HMAC-signed nonce binding the
  tool, amount, scope, caller and expiry. Editing the amount or the recipient in
  the echo is rejected, and the nonce is burned in a replay ledger after one use.
- **Scope-bound.** A credential minted for one company cannot be redeemed for a
  different — or a wider — request, and a pass covers its own company only.

**How to tell what happened:**
- `200` — you got the data; `X-Valuein-Charge-Id` is your receipt.
- `402` with `WWW-Authenticate: Payment` — a price (or a fresh challenge), not a
  bill. A credential that fails verification is answered the same way.
- `402` without that header — the payment itself failed. You were not charged.
- `502 PAYMENT_STATE_UNKNOWN` — nothing was served and the payment could not be
  confirmed either way. **Do not pay again**; ask for the receipt.

---

## What is and isn't live

- **Live today:** MPP on `POST /api/mpp/call`, settled by **Stripe card (SPT)**,
  with company passes and per-run fees, on `/mcp`.
- **Not live yet (honest):** **crypto / USDC and bank settlement are behind
  feature flags that are OFF.** Today the only network that settles is
  `link-card`. Don't build a "pay Valuein in USDC" flow against this yet — watch
  `GET /api/mpp/well-known` for when `crypto_enabled` flips true.

---

## Why this is the safe default (and why institutions care)

- **Bounded by construction.** Each payment is an approved Shared Payment Token
  for one stated price; a looping agent cannot spend more than the human
  approves, request by request.
- **Charged only for what is delivered**, with a hold that is released if the
  data does not arrive. No charge-without-delivery.
- **Scope-bound.** A payment unlocks one company at one level for 24 hours, or
  one run. A leaked credential buys one call, not the account.
- **The data itself is auditable.** Every figure Valuein returns carries a
  `fact_id` traceable to its SEC filing (`verify_fact_lineage`). The agent buys
  *provenance*, not just numbers — so a paid answer is a defensible answer, which
  is what the institutions eyeing agents actually care about.

If the human operator repeatedly pays per call, a subscription is cheaper:
[valuein.biz/pricing](https://valuein.biz/pricing).

---

## Try it

The runnable demo — an agent that **discovers** the rail, **hits the paywall**,
and reads back a **machine-readable quote**, all live and free (the pay step
needs your own wallet) — is in
[`examples/python/agent_buys_its_own_data.py`](../examples/python/agent_buys_its_own_data.py).

```bash
pip install "valuein-sdk>=1.0.0" httpx
python examples/python/agent_buys_its_own_data.py    # discovery + paywall + quote, no card
```

---

_The shape — discover → paywall → quote → **pay with a bounded token** → data
plus receipt — is the interface every "agent that buys its own data" should
implement. Valuein is one implementation of it, for point-in-time SEC financial
data, and speaks the open `mpp.dev` protocol so it isn't the only one._
