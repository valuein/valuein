"""Getting started: connect, resolve a ticker, run a first query.

What it does: connects to Valuein, prints the plan and data snapshot you are reading,
resolves a ticker to its SEC CIK, and prints the company's annual revenue and net income.
Who it is for: anyone trying the SDK for the first time.
Plan: none. Runs on the free sample tier (S&P 500 companies, last five years) with no API
key. Set VALUEIN_API_KEY to read your own plan's data with the same code.
SDK methods: ValueinClient, ValueinClient.resolve, ValueinClient.run_query.
Tables: references, fact (each is fetched the first time a query needs it).
Notebook: examples/notebooks/01_quickstart.ipynb

Run:
    pip install valuein-sdk
    python examples/python/getting_started.py
"""

from __future__ import annotations

import pandas as pd

from valuein_sdk import ValueinClient

TICKER = "AAPL"


def annual_series(client: ValueinClient, cik: str, concepts: list[str]) -> pd.DataFrame:
    """Return one row per fiscal year end and one column per concept, in USD billions.

    A 10-K repeats prior years as comparatives and a later filing can revise a value, so
    the same fiscal year appears in several rows. Keep the latest vintage per period.
    """
    concept_list = ", ".join(f"'{c}'" for c in concepts)
    long = client.run_query(f"""
        SELECT period_end, standard_concept, numeric_value / 1e9 AS usd_bn
        FROM fact
        WHERE entity_id = '{cik}'
          AND standard_concept IN ({concept_list})
          AND fiscal_period = 'FY'
          AND period_span_days BETWEEN 350 AND 380
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY standard_concept, period_end ORDER BY accepted_at DESC, priority DESC
        ) = 1
    """)
    return long.pivot(index="period_end", columns="standard_concept", values="usd_bn").sort_index()


def main() -> None:
    """Connect, resolve the ticker and print its annual fundamentals."""
    with ValueinClient() as client:
        print(f"plan     : {client.plan}")
        print(f"as_of    : {client.as_of:%Y-%m-%d %H:%M} UTC")
        print(f"snapshot : {client.manifest().get('snapshot')}")

        # A ticker can be retired and reused; the CIK is the stable key every table joins on.
        match = client.resolve(TICKER).iloc[0]
        print(f"\n{TICKER} -> CIK {match['cik']} ({match['name']})")

        table = annual_series(client, match["cik"], ["TotalRevenue", "NetIncome"])
        print(f"\n{match['name']}: annual revenue and net income, USD billions")
        print(table.round(1).to_string())

        print("\nNext: python examples/python/financial_analysis.py")


if __name__ == "__main__":
    main()
