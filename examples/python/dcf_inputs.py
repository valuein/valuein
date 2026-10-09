"""DCF inputs and a two-stage DCF from reported SEC data.

What it does: assembles annual free cash flow (operating cash flow minus |capex|), cash, debt
and diluted shares for one company from its filings, then runs a two-stage DCF with explicit,
editable assumptions and prints the value per share next to the latest close, plus the growth
rate the price implies.
Valuein publishes the reported inputs, not an intrinsic value: the assumptions are yours.
Who it is for: valuation analysts and developers building valuation tools.
Plan: none. Runs on the free sample tier (last five fiscal years) with no API key.
SDK methods: ValueinClient.resolve, ValueinClient.run_query, ValueinClient.stock_price.
Tables: fact, references, stock_price.
Notebook: examples/notebooks/10_dcf_valuation.ipynb

Run:
    pip install valuein-sdk
    python examples/python/dcf_inputs.py
"""

from __future__ import annotations

import pandas as pd

from valuein_sdk import ValueinClient

TICKER = "MSFT"
DISCOUNT_RATE = 0.09  # your required return
TERMINAL_GROWTH = 0.025  # long-run growth after stage 1
YEARS = 5  # length of stage 1
MAX_GROWTH = 0.15  # cap on the stage-1 growth taken from history


def annual(client: ValueinClient, cik: str, concepts: list[str]) -> pd.DataFrame:
    """Latest-vintage annual values, one row per fiscal year end, one column per concept.

    Annual flows are `numeric_value` on FY rows (on an FY row derived_quarterly_value is the
    implied fourth quarter, not the year).
    """
    names = ", ".join(f"'{c}'" for c in concepts)
    long = client.run_query(f"""
        SELECT period_end, standard_concept, numeric_value
        FROM fact
        WHERE entity_id = '{cik}' AND standard_concept IN ({names}) AND fiscal_period = 'FY'
          AND (period_span_days BETWEEN 350 AND 380 OR period_start IS NULL)
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY standard_concept, period_end ORDER BY accepted_at DESC, priority DESC) = 1
    """)
    return long.pivot(index="period_end", columns="standard_concept", values="numeric_value")


def value_per_share(fcf: float, growth: float, net_cash: float, shares: float) -> float:
    """Two-stage DCF: stage-1 growth for YEARS, then TERMINAL_GROWTH forever."""
    flows = [fcf * (1 + growth) ** t for t in range(1, YEARS + 1)]
    present = sum(f / (1 + DISCOUNT_RATE) ** t for t, f in enumerate(flows, start=1))
    terminal = flows[-1] * (1 + TERMINAL_GROWTH) / (DISCOUNT_RATE - TERMINAL_GROWTH)
    return (present + terminal / (1 + DISCOUNT_RATE) ** YEARS + net_cash) / shares


def main() -> None:
    """Print the inputs, the DCF value and the growth the price implies."""
    with ValueinClient() as client:
        cik = client.resolve(TICKER)["cik"].iloc[0]
        flows = annual(client, cik, ["OperatingCashFlow", "CAPEX"]).sort_index()
        balance = annual(
            client,
            cik,
            [
                "CashAndEquivalents",
                "TotalDebt",
                "LongTermDebtTotal",
                "LongTermDebt",
                "WeightedAvgSharesDiluted",
            ],
        ).sort_index()
        price = float(client.stock_price(TICKER)["close"].iloc[0])

    flows["FCF"] = flows["OperatingCashFlow"] - flows["CAPEX"].abs()  # capex sign varies
    print(f"{TICKER} annual free cash flow, USD bn:")
    print((flows / 1e9).round(2).to_string())

    latest = balance.iloc[-1]
    debt = next(
        latest[c]
        for c in ["TotalDebt", "LongTermDebtTotal", "LongTermDebt"]
        if c in latest.index and pd.notna(latest[c])
    )
    net_cash = latest["CashAndEquivalents"] - debt
    shares = latest["WeightedAvgSharesDiluted"]
    years = (flows.index[-1] - flows.index[0]).days / 365.25
    history = (flows["FCF"].iloc[-1] / flows["FCF"].iloc[0]) ** (1 / years) - 1
    growth = min(max(history, 0.0), MAX_GROWTH)
    fcf = flows["FCF"].iloc[-1]

    value = value_per_share(fcf, growth, net_cash, shares)
    print(f"\nnet cash {net_cash / 1e9:,.1f} bn | diluted shares {shares / 1e9:,.3f} bn")
    print(
        f"assumptions: growth {growth:.1%} (history {history:.1%}), discount {DISCOUNT_RATE:.1%}, "
        f"terminal {TERMINAL_GROWTH:.1%}, {YEARS} years"
    )
    print(f"value per share {value:,.2f} vs latest close {price:,.2f}")

    low, high = -0.5, 1.0  # bisection for the growth that makes value == price
    for _ in range(100):
        mid = (low + high) / 2
        too_low = value_per_share(fcf, mid, net_cash, shares) < price
        low, high = (mid, high) if too_low else (low, mid)
    print(f"stage-1 growth implied by the price: {(low + high) / 2:.1%} per year")


if __name__ == "__main__":
    main()
