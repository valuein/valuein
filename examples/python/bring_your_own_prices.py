"""Multiples on prices you hold, joined to point-in-time SEC EDGAR filings data.

What it does: takes a small table of closing prices (your own), calls `client.price_multiples()`,
and prints each multiple beside the acceptance time of the filing it rests on and the warnings.
Every multiple shows which part came from a filing (`input_fact_ids`) and which from your price.
Prices you pass to the SDK stay on your machine.
Who it is for: quants and analysts who already hold prices from a market-data provider, broker
export or internal price database.
Plan: none. Runs on the free sample tier (S&P 500 companies, last five years) with no API key.
SDK methods: ValueinClient.price_multiples, ValueinClient.attach_prices.
Tables: fact, filing, security, corporate_action.
Docs: docs/BRING_YOUR_OWN_PRICES.md

Run:
    pip install "valuein-sdk>=1.1.0"
    python examples/python/bring_your_own_prices.py
"""

from __future__ import annotations

import pandas as pd
from valuein_sdk import ValueinClient

# EXAMPLE VALUES ONLY: illustrative closes so the script runs. Replace this frame with your own
# prices (for example pd.read_parquet("my_closes.parquet")) before drawing any conclusion.
MY_CLOSES = pd.DataFrame(
    {
        "ticker": ["MSFT", "AAPL"],
        "price_date": ["2024-06-28", "2024-06-28"],
        "close": [400.00, 200.00],
        "currency": ["USD", "USD"],
        "source_label": ["example value", "example value"],
    }
)


def main() -> None:
    """Compute multiples on the example prices and print them with their provenance."""
    with ValueinClient() as client:
        out = client.price_multiples(MY_CLOSES, metrics=["market_cap", "pe", "pb", "ev_ebitda"])
        columns = [
            "cik",
            "price_date",
            "close",
            "market_cap",
            "pe",
            "pb",
            "ev_ebitda",
            "fundamentals_accepted_at",
            "warnings",
        ]
        print(out[columns].to_string(index=False))
        print("\nFiled inputs behind the first row (name -> fact_id):")
        print(out.iloc[0]["input_fact_ids"])

        # Join the same prices to the filings in your own SQL.
        rejected = client.attach_prices(MY_CLOSES)
        print(f"\nRejected rows: {len(rejected)}; the view `user_price` is ready for run_query().")


if __name__ == "__main__":
    main()
