"""The Agent Economy Rail — an agent that buys its own data, safely.

A runnable demo of the pattern in ``docs/AGENT_ECONOMY_RAIL.md``. An autonomous
agent:

    1. discovers Valuein on the free SAMPLE tier (no token, no card),
    2. discovers the payment rail via its ``mpp.dev`` well-known endpoint,
    3. reaches for a company above its tier and gets a machine-readable QUOTE
       (the exact price, live), then
    4. pays — either by a human authorizing a bounded budget (the "wallet"
       model) or per-call over MPP (the "wallet-holding agent" model) — and
       finishes the job.

Steps 1–3 run right now, for free, against the LIVE production endpoints (no
card, no token). Step 4 needs your own budget or wallet, so this demo PRINTS the
exact next call rather than spending your money.

    pip install valuein-sdk httpx
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
        print("① Discover the data — connecting on the free sample tier "
              "(no token, real data in <15s)…")
        client = ValueinClient(tables=[])
        plan = client.me().get("plan", "sample")
        print(f"   Connected as plan='{plan}'.\n")

        # ── Step 2: DISCOVER THE RAIL — the mpp.dev well-known endpoint ────────
        print("② Discover the rail — GET /api/mpp/well-known (unauthenticated)…")
        wk = http.get(f"{API}/api/mpp/well-known").json()
        print(f"   protocol={wk.get('protocol')} v{wk.get('protocol_version')} · "
              f"card={wk.get('spt_enabled')} · crypto={wk.get('crypto_enabled')} · "
              f"networks={wk.get('supported_networks')}")
        print("   (Card settlement is live; crypto/USDC is behind an OFF flag — "
              "watch crypto_enabled for when it flips.)\n")

        # ── Step 3: PAYWALL + QUOTE — ask the exact price of one company's data ─
        # Above-tier data returns a machine-readable price. The agent NEVER
        # guesses a cost; it reads it and relays it to its human.
        print(f"③ Paywall + quote — {TICKER}'s Institutional-tier fundamentals "
              f"cost how much?")
        quote = http.get(
            f"{API}/api/mpp/quote",
            params={"tool": TOOL, "tickers": TICKER, "tier": "full"},
        ).json()
        amount = quote.get("amount_usd")
        print(f"   Quote: ${amount} {quote.get('currency', 'usd').upper()} "
              f"for {TICKER} ({quote.get('pricing_mode')}, "
              f"{quote.get('billable_units')} unit). Pay to: {quote.get('pay_to_url')}")
        print(f"   Accepted now: {quote.get('accept')}. "
              f"nonce={str(quote.get('nonce'))[:16]}…  "
              f"(expires {quote.get('expires_at')})\n")

        # ── Step 4: PAY + FINISH — two consent models. We PRINT the next call. ─
        print("④ Pay + finish — two ways, both bounded-consent + audited:\n")

        print("   MODEL A — budget-authorized auto-charge (the 'wallet'):")
        print("     • Your human authorizes a session budget once (default $10, "
              "'charged only for what I use') in the Valuein workspace.")
        print("     • The agent then just asks for the company; the server "
              "auto-charges the balance for that ONE company and serves the")
        print("       promoted tier INLINE — one query, no round-trip. Works with "
              "connectors that only forward a Bearer (e.g. Anthropic's).\n")

        print("   MODEL B — canonical MPP, pay-per-call (a wallet-holding / guest agent):")
        print("     The paywall is advertised ON the resource, so a standard MPP")
        print("     client discovers it without reading any of our docs:\n")
        print(f"     POST {API}/api/mpp/call")
        print(f'       {{"tool": "{TOOL}", "arguments": {{"ticker": "{TICKER}"}}}}')
        print("       → 402  WWW-Authenticate: Payment id=… realm=… method=\"stripe\" …")
        print("            request = base64url({\"amount\":\"50\",\"currency\":\"usd\",")
        print("                                 \"methodDetails\":{\"networkId\":\"profile_…\"}})")
        print("            (amount is a STRING of CENTS)\n")
        print("     Retry the SAME request, now carrying the credential:")
        print("       Authorization: Payment <base64url({")
        print("         \"challenge\": { …the challenge params, echoed verbatim… },")
        print("         \"payload\":   { \"spt\": \"spt_<Shared Payment Token>\" } })>")
        print("       → 200, the data INLINE   (X-Valuein-Charge-Id: ch_…)\n")
        print("     Any MPP client does both steps for you:")
        print(f"       npx @stripe/link-cli mpp pay {API}/api/mpp/call \\")
        print("         --method POST -H 'Content-Type: application/json' \\")
        print(f'         --data \'{{"tool":"{TOOL}","arguments":{{"ticker":"{TICKER}"}}}}\' \\')
        print("         --spend-request-id lsrq_…\n")
        print("     THE PROMISE: paying does not move money. We HOLD the funds,")
        print("     fetch the data, verify it is genuinely the paid tier — and only")
        print("     then capture. A tool error, a bad ticker, or anything we cannot")
        print("     verify RELEASES the hold: no charge is ever created. Not")
        print("     refunded — never charged.\n")

        # If the caller has set up PAYG (a token + a saved card), point them at it.
        if os.environ.get("VALUEIN_API_KEY"):
            print("   You have VALUEIN_API_KEY set — you can run the legacy "
                  "Bearer PAYG two-step live:")
            print(f"     POST {API}/api/payg/quote   {{'tool': '{TOOL}', "
                  f"'tickers': ['{TICKER}']}}")
            print(f"     POST {API}/api/payg/confirm {{'quote_id': '<from quote>'}}"
                  "   # charges your saved card, returns a retry_token\n")

        print("Once paid (either model), the previously-paywalled data returns, "
              "promoted to the paid tier — and every fetch is logged, scope-bound "
              "to this one tool + company, and traceable to its SEC filing via "
              "verify_fact_lineage. That auditability is the whole point.")


if __name__ == "__main__":
    main()
