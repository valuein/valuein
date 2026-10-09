"""Point-in-time discipline: the same query, asked at two dates, gives two answers.

What it does: asks for Monolithic Power Systems' fiscal 2024 net income twice, once with the
client's cutoff set to 2025-06-30 and once as of today. The company restated that figure in a
later 10-K (after an 8-K Item 4.02 non-reliance notice), so the two answers differ. A backtest
dated mid-2025 must use the first one. The script also shows how far `accepted_at` (when a
number became public) trails `period_end` (the period it describes).
Who it is for: quants building backtests; anyone who needs "what was known on date D".
Plan: none. Runs on the free sample tier with no API key.
SDK methods: ValueinClient(as_of=...), ValueinClient.resolve, ValueinClient.run_query.
Tables: references, fact.
Notebook: examples/notebooks/02_fundamentals_as_of_a_date.ipynb

Run:
    pip install "valuein-sdk>=7.0.0"
    python examples/python/pit_backtest.py
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from valuein_sdk import ValueinClient

TICKER = "MPWR"
PERIOD_END = "2024-12-31"
PAST = datetime(2025, 6, 30, tzinfo=timezone.utc)  # as_of must be timezone-aware

QUESTION = """
    SELECT numeric_value / 1e9 AS net_income_bn, accession_id, accepted_at
    FROM fact
    WHERE entity_id = '{cik}'
      AND standard_concept = 'NetIncome'
      AND fiscal_period = 'FY'
      AND period_end = DATE '{period_end}'
    QUALIFY ROW_NUMBER() OVER (ORDER BY accepted_at DESC, priority DESC) = 1
"""


def ask(as_of: datetime | None, cik: str) -> pd.Series:
    """Run QUESTION with the client's point-in-time cutoff at `as_of` (None = now)."""
    with ValueinClient(as_of=as_of) as client:
        return client.run_query(QUESTION.format(cik=cik, period_end=PERIOD_END)).iloc[0]


def publication_lag(cik: str) -> pd.DataFrame:
    """Days from period end to SEC acceptance for the company's annual net income."""
    with ValueinClient() as client:
        rows = client.run_query(f"""
            SELECT period_end, min(accepted_at) AS first_public
            FROM fact
            WHERE entity_id = '{cik}' AND standard_concept = 'NetIncome' AND fiscal_period = 'FY'
            GROUP BY period_end ORDER BY period_end
        """)
    rows["days_until_public"] = (
        pd.to_datetime(rows["first_public"], utc=True).dt.tz_localize(None)
        - pd.to_datetime(rows["period_end"])
    ).dt.days
    return rows


def main() -> None:
    """Ask the question at both dates and print the difference."""
    with ValueinClient() as client:
        cik = client.resolve(TICKER)["cik"].iloc[0]

    then = ask(PAST, cik)
    now = ask(None, cik)
    print(f"{TICKER} net income for the fiscal year ended {PERIOD_END}:")
    for label, row in [(f"known on {PAST:%Y-%m-%d}", then), ("known today      ", now)]:
        print(
            f"  {label}: {row['net_income_bn']:.4f} bn  "
            f"(filing {row['accession_id']}, accepted {row['accepted_at']:%Y-%m-%d})"
        )
    print(f"  change: {now['net_income_bn'] / then['net_income_bn'] - 1:+.1%}")

    print("\nA number exists at period end but becomes public only at SEC acceptance:")
    print(publication_lag(cik).tail(4).to_string(index=False))
    print("\nRule: gate on accepted_at (ValueinClient(as_of=...)), never on period_end.")


if __name__ == "__main__":
    main()
