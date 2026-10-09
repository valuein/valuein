"""Smart-money screen: insider trades, 13F holders and blockholders for one company.

What it does: for a ticker (default NVDA), prints recent open-market insider purchases and sales
(Forms 4), the largest 13F holders in the latest quarter, and 13D/13G blockholders, then one
manager's portfolio (Berkshire Hathaway). Every row is filtered by `accepted_at`: a filing counts
from the moment the SEC accepted it, not from the trade or quarter-end date.
Who it is for: PMs and analysts following insider and institutional activity.
Plan: Institutional. On any other plan, including the free sample, the script prints the plan
error and exits with status 2; the SDK raises ValueinPlanError before sending any request.
SDK methods: ValueinClient.insider_transactions, ValueinClient.institutional_holdings,
ValueinClient.run_template ("top_institutional_holders", "blockholders").
Tables: insider_transaction, institutional_holding, insider_ownership, insider_party.
Notebook: examples/notebooks/07_smart_money.ipynb

Run:
    pip install "valuein-sdk>=7.0.0"
    VALUEIN_API_KEY=<institutional key> python examples/python/smart_money_screen.py NVDA
"""

from __future__ import annotations

import sys

from valuein_sdk import ValueinClient, ValueinPlanError

BERKSHIRE_CIK = "0001067983"


def main(ticker: str = "NVDA") -> int:
    """Print the smart-money views for `ticker`; return a process exit status."""
    with ValueinClient() as client:
        try:
            trades = client.insider_transactions(ticker, transaction_codes=["P", "S"], limit=20)
        except ValueinPlanError as exc:
            print(f"ValueinPlanError: {exc}")
            return 2

        print(f"=== {ticker}: open-market insider purchases (P) and sales (S) ===")
        print(
            trades[
                [
                    "transaction_date",
                    "insider_name",
                    "insider_role",
                    "transaction_code",
                    "shares",
                    "price_per_share",
                    "accepted_at",
                ]
            ].to_string(index=False)
        )

        print(f"\n=== {ticker}: largest 13F holders, latest quarter ===")
        print(
            client.run_template("top_institutional_holders", ticker=ticker, top_n=10).to_string(
                index=False
            )
        )

        print(f"\n=== {ticker}: 13D / 13G blockholders, last 365 days ===")
        print(
            client.run_template("blockholders", ticker=ticker, lookback_days=365).to_string(
                index=False
            )
        )

        holdings = client.institutional_holdings(filer_cik=BERKSHIRE_CIK, limit=200)
        latest = holdings[holdings["period_end"] == holdings["period_end"].max()]
        print("\n=== Berkshire Hathaway 13F, latest quarter (FIGI-identified) ===")
        print(
            latest[["name_of_issuer", "share_class_figi", "shares", "market_value_usd"]]
            .head(10)
            .to_string(index=False)
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "NVDA"))
