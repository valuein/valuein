"""The Agent Economy Rail — an agent that buys its own data, safely.

A runnable demo of the pattern in ``docs/AGENT_ECONOMY_RAIL.md``. An autonomous
agent:

    1. discovers Valuein on the free SAMPLE tier (no token, no card),
    2. discovers the payment rail via its ``mpp.dev`` well-known endpoint,
    3. reaches for a company above its tier and gets a machine-readable QUOTE
       (the exact price, live), then
    4. pays over MPP (a standard 402 on ``POST /api/mpp/call``, settled by card)
       and finishes the job with a 24 h company pass.

Steps 1–3 run right now, for free, against the LIVE production endpoints (no
card, no token). Step 4 needs your own wallet, so this demo PRINTS the
exact next call rather than spending your money.

    pip install "valuein-sdk>=1.0.0" httpx
    python examples/python/agent_buys_its_own_data.py

Design note: deliberately a plain httpx script, not a framework demo, so the
RAIL is legible. Drop the same calls into any agent loop (Claude tool-use, an
OpenAI function, an MCP client).
"""

from __future__ import annotations

import os

import httpx

from valuein_sdk import ValueinClient

API = "https://api.valuein.biz"
TICKER = "AAPL"
# A single-entity, cross-bucket-unlockable tool. Institutional data (smart-money,
# full history) sits above the free/pro tiers — the perfect paywall to demo.
TOOL = "get_company_fundamentals"


def main() -> None:
    with httpx.Client(timeout=30) as http:
        # ── Step 1: DISCOVER THE DATA — the sample tier needs zero credentials ─
        print(
            "① Discover the data — connecting on the free sample tier "
            "(no token, real data in <15s)…"
        )
        client = ValueinClient(tables=[])
        plan = client.me().get("plan", "sample")
        print(f"   Connected as plan='{plan}'.\n")

        # ── Step 2: DISCOVER THE RAIL — the mpp.dev well-known endpoint ────────
        print("② Discover the rail — GET /api/mpp/well-known (unauthenticated)…")
        wk = http.get(f"{API}/api/mpp/well-known").json()
        print(
            f"   protocol={wk.get('protocol')} v{wk.get('protocol_version')} · "
            f"card={wk.get('spt_enabled')} · crypto={wk.get('crypto_enabled')} · "
            f"networks={wk.get('supported_networks')}"
        )
        print(
            "   (Card settlement is live; crypto/USDC is behind an OFF flag — "
            "watch crypto_enabled for when it flips.)\n"
        )

        # ── Step 3: PAYWALL + QUOTE — ask the exact price of one company's data ─
        # Above-tier data returns a machine-readable price. The agent NEVER
        # guesses a cost; it reads it and relays it to its human.
        print(f"③ Paywall + quote — {TICKER}'s fundamentals for 24 hours cost how much?")
        quote = http.get(
            f"{API}/api/mpp/quote",
            params={"tool": TOOL, "tickers": TICKER, "level": "pro"},
        ).json()
        print(
            f"   Quote: ${quote.get('amount_usd')} {str(quote.get('currency', 'usd')).upper()} "
            f"for {quote.get('company_count')} company "
            f"(unlock level: {quote.get('unlock_level')})."
        )
        print(f"   Passes this would buy: {quote.get('passes')}")
        print("   (A free price lookup — nothing in it is redeemable; the 402 is the binding quote.)\n")

        # ── Step 4: PAY + FINISH — canonical MPP. We PRINT the next call. ─
        print("④ Pay + finish — canonical MPP, a standard 402 any MPP client speaks:\n")
        print(f"     POST {API}/api/mpp/call")
        print(f'       {{"tool": "{TOOL}", "arguments": {{"ticker": "{TICKER}"}}}}')
        print('       → 402  WWW-Authenticate: Payment id=… realm=… method="stripe" …')
        print('            request = base64url({"amount":"100","currency":"usd",')
        print('                                 "methodDetails":{"networkId":"profile_…",')
        print('                                                  "paymentMethodTypes":["card"]}})')
        print("            (amount is a STRING of CENTS)\n")
        print("     Retry the SAME request, now carrying the credential:")
        print("       Authorization: Payment <base64url({")
        print('         "challenge": { …the challenge params, echoed verbatim… },')
        print('         "payload":   { "spt": "spt_<Shared Payment Token>" } })>')
        print("       → 200, the data INLINE (X-Valuein-Charge-Id: ch_…,")
        print("         X-Valuein-Mpp-Pass: … — a 24 h pass for this one company)\n")
        print("     Any MPP client does both steps for you (npm install -g @stripe/link-cli):")
        print(f"       link-cli mpp pay {API}/api/mpp/call -X POST \\")
        print("         -H 'Content-Type: application/json' \\")
        print(f'         -d \'{{"tool":"{TOOL}","arguments":{{"ticker":"{TICKER}"}}}}\' \\')
        print('         --context "<at least 100 characters: what is being bought and why>"\n')
        print("     Reuse the pass on https://mcp.valuein.biz/mcp for 24 hours with")
        print("     the header  x-valuein-mpp-pass: <the X-Valuein-Mpp-Pass value>\n")
        print("     THE PROMISE: paying does not move money. We HOLD the funds,")
        print("     fetch the data, verify it was delivered — and only then")
        print("     capture. A tool error, a bad ticker, or anything we cannot")
        print("     verify RELEASES the hold: no charge is ever created. Not")
        print("     refunded — never charged.\n")

        print(
            "Once paid, the previously-paywalled data returns, "
            "at the level you bought — and every fetch is logged, scope-bound "
            "to this one tool + company, and traceable to its SEC filing via "
            "verify_fact_lineage. That auditability is the whole point."
        )


if __name__ == "__main__":
    main()
