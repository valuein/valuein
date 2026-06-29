"""Smart-money screen — insider buys + 13F top holders + 13D activist flags.

Demonstrates the four smart-money templates shipped in valuein-sdk v3.x:

  * insider_buys                 — Form 4 "P" purchases joined to insider_party
  * top_institutional_holders    — 13F holders ranked by market value
  * manager_portfolio            — A specific 13F filer's positions + QoQ deltas
  * blockholders                 — SC 13D / 13G with `going_active` flag

Requires an Enterprise (`full`) plan API key — smart-money tables are tier-gated
to the FULL bucket at the gateway.  Sample / Free / Pro tokens receive 403.

Usage::

    VALUEIN_API_KEY=valuein_live_... uv run python smart_money_screen.py NVDA

If no ticker is provided, defaults to NVDA.
"""

from __future__ import annotations

import os
import sys

from valuein_sdk import ValueinClient


def main(ticker: str = "NVDA") -> None:
    token = os.environ.get("VALUEIN_API_KEY")
    if not token:
        print(
            "VALUEIN_API_KEY not set — these tables are Enterprise-tier only and "
            "the demo cannot run without a `full` token.  Get one at "
            "https://valuein.biz/pricing"
        )
        sys.exit(2)

    client = ValueinClient(api_key=token)
    me = client.me()
    if me.get("plan") != "full":
        print(
            f"This script requires a `full` plan token; current plan is "
            f"{me.get('plan')!r}.  Upgrade at https://valuein.biz/pricing"
        )
        sys.exit(2)

    print(f"\n=== {ticker} — Insider Buys (last 180 days) ===")
    df_buys = client.run_template(
        "insider_buys",
        ticker=ticker,
        lookback_days=180,
        min_shares=1_000,
    )
    if not df_buys.empty:
        print(df_buys[["transaction_date", "insider_name", "shares", "price_per_share", "notional_usd"]].head(10))
    else:
        print("(no insider buys in window)")

    print(f"\n=== {ticker} — Top 10 Institutional Holders (latest 13F) ===")
    df_holders = client.run_template("top_institutional_holders", ticker=ticker, top_n=10)
    if not df_holders.empty:
        print(df_holders[["filer_name", "shares", "market_value_usd", "period_end"]])
    else:
        print("(no 13F holders on record)")

    print(f"\n=== {ticker} — Blockholders (SC 13D / 13G) ===")
    df_blocks = client.run_template("blockholders", ticker=ticker, schedule_filter="both")
    if not df_blocks.empty:
        active = df_blocks[df_blocks["going_active"]]
        if not active.empty:
            print("⚠  Going-active filers (13G → 13D conversion) detected:")
            print(active[["filer_name", "schedule_type", "percent_owned", "filing_date"]])
        print("\nAll current blockholders:")
        print(df_blocks[["filer_name", "schedule_type", "percent_owned", "filing_date", "going_active"]])
    else:
        print("(no 13D / 13G filings on record)")

    print("\n=== Berkshire Hathaway 13F portfolio (latest quarter) ===")
    df_brk = client.run_template("manager_portfolio", filer_cik="0001067983", top_n=10)
    if not df_brk.empty:
        print(df_brk[
            ["ticker", "name_of_issuer", "shares", "market_value_usd", "position_type_qoq"]
        ])
    else:
        print("(no positions on record for that filer)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "NVDA")
