"""Financial analysis: one company's statements, margins and quarterly cash flow.

What it does: prints a company's annual income statement and margins, its single-quarter
operating cash flow (de-cumulating the year-to-date figures 10-Qs report), and a peer
comparison of pre-computed ratios.
Who it is for: analysts and developers building company tear-downs or dashboards.
Plan: none. Runs on the free sample tier with no API key.
SDK methods: ValueinClient.resolve, ValueinClient.run_query, ValueinClient.signal_panel,
ValueinClient.universe.
Tables: references, fact, ratio, index_membership.
Notebook: examples/notebooks/02_fundamentals_as_of_a_date.ipynb

Run:
    pip install valuein-sdk
    python examples/python/financial_analysis.py
"""

from __future__ import annotations

import pandas as pd

from valuein_sdk import ValueinClient

TICKER = "MSFT"
PEERS = ["MSFT", "AAPL", "GOOGL", "ORCL", "ADBE"]
INCOME = ["TotalRevenue", "GrossProfit", "OperatingIncome", "NetIncome"]


def annual_income_statement(client: ValueinClient, cik: str) -> pd.DataFrame:
    """Return annual income-statement lines (USD billions) and margins, one row per year."""
    names = ", ".join(f"'{c}'" for c in INCOME)
    long = client.run_query(f"""
        SELECT period_end, standard_concept, numeric_value / 1e9 AS usd_bn
        FROM fact
        WHERE entity_id = '{cik}' AND standard_concept IN ({names})
          AND fiscal_period = 'FY' AND period_span_days BETWEEN 350 AND 380
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY standard_concept, period_end ORDER BY accepted_at DESC, priority DESC) = 1
    """)
    table = long.pivot(index="period_end", columns="standard_concept", values="usd_bn")
    table = table.reindex(columns=INCOME).sort_index()
    for line in ["GrossProfit", "OperatingIncome", "NetIncome"]:
        table[f"{line}_margin"] = table[line] / table["TotalRevenue"]
    return table


def quarterly_operating_cash_flow(client: ValueinClient, cik: str) -> pd.DataFrame:
    """Return single-quarter operating cash flow (USD billions) per quarter end.

    10-Q cash flows are year to date; derived_quarterly_value holds the single quarter, and on
    the 10-K's FY row it holds the implied fourth quarter.
    """
    return client.run_query(f"""
        SELECT period_end, fiscal_period,
               numeric_value / 1e9 AS as_reported_bn,
               COALESCE(derived_quarterly_value, numeric_value) / 1e9 AS single_quarter_bn
        FROM fact
        WHERE entity_id = '{cik}' AND standard_concept = 'OperatingCashFlow'
          AND fiscal_period IN ('Q1', 'Q2', 'Q3', 'FY')
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY period_end
            ORDER BY accepted_at DESC, period_span_days DESC, priority DESC) = 1
        ORDER BY period_end
    """)


def peer_ratios(client: ValueinClient, tickers: list[str]) -> pd.DataFrame:
    """Return the latest known value of a few ratios for each peer."""
    ciks = client.resolve(tickers)[["identifier", "cik"]]
    as_of = client.as_of.date().isoformat()
    frame = ciks.rename(columns={"identifier": "ticker"}).assign(rebalance_date=as_of)
    ratios = ["gross_profit_margin", "operating_margin", "return_on_equity", "debt_to_equity"]
    panel = client.signal_panel(frame, ratios=ratios, include_price=False)
    return panel.set_index("ticker")[ratios]


def main() -> None:
    """Print the statement, the cash-flow trap and the peer table."""
    with ValueinClient() as client:
        cik = client.resolve(TICKER)["cik"].iloc[0]
        pd.set_option("display.width", 120)

        print(f"{TICKER}: annual income statement (USD bn) and margins")
        print(annual_income_statement(client, cik).round(3).to_string())

        print(f"\n{TICKER}: operating cash flow, as reported vs single quarter (USD bn)")
        print(quarterly_operating_cash_flow(client, cik).tail(8).round(2).to_string(index=False))

        print("\nPeers: latest known ratios")
        print(peer_ratios(client, PEERS).round(3).to_string())


if __name__ == "__main__":
    main()
