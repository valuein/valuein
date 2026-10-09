"""A two-stage DCF from reported SEC data, every input traced to its filing.

What it does: runs `client.dcf()` for one company with explicit, editable assumptions (the
stage-1 growth rate defaults to the company's historical free-cash-flow growth, capped), prints
each input with the `fact_id` and accession number of the filing it came from, the value per
share next to the last close, and the stage-1 growth rate the price implies.
Valuein publishes the reported inputs, not an opinion of value: the assumptions are yours.
Who it is for: valuation analysts and developers building valuation tools.
Plan: none. Runs on the free sample tier (S&P 500 companies, last five years) with no API key.
SDK methods: ValueinClient.resolve, ValueinClient.run_query, ValueinClient.dcf.
Tables: fact, filing, references, stock_price.
Notebook: examples/notebooks/10_dcf_valuation.ipynb

Run:
    pip install "valuein-sdk>=7.0.0"
    python examples/python/dcf_inputs.py
"""

from __future__ import annotations

from valuein_sdk import DcfResult, ValueinClient

TICKER = "MSFT"
WACC = 0.09  # your required return
TERMINAL_GROWTH = 0.025  # long-run growth after stage 1
YEARS = 5  # length of stage 1
MAX_GROWTH = 0.15  # cap on the stage-1 growth taken from history


def historical_fcf_growth(client: ValueinClient, cik: str) -> float:
    """Annualised growth of free cash flow (operating cash flow minus |capex|) over the history.

    Annual flows are `numeric_value` on FY rows (on an FY row derived_quarterly_value is the
    implied fourth quarter, not the year); one row per period at its latest vintage.
    """
    flows = client.run_query(f"""
        SELECT period_end, standard_concept, numeric_value
        FROM fact
        WHERE entity_id = '{cik}' AND fiscal_period = 'FY'
          AND standard_concept IN ('OperatingCashFlow', 'CAPEX')
          AND (period_span_days BETWEEN 350 AND 380 OR period_start IS NULL)
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY standard_concept, period_end ORDER BY accepted_at DESC, priority DESC) = 1
    """).pivot(index="period_end", columns="standard_concept", values="numeric_value")
    flows = flows.sort_index()
    fcf = flows["OperatingCashFlow"] - flows["CAPEX"].abs()  # capex sign varies by filer
    years = (fcf.index[-1] - fcf.index[0]).days / 365.25
    return float((fcf.iloc[-1] / fcf.iloc[0]) ** (1 / years) - 1)


def implied_growth(result: DcfResult, price: float) -> float:
    """Stage-1 growth that makes the DCF equal `price`, other inputs held (bisection).

    `per_share` is the dcf() model written out from the result's own fields.
    """
    a = {x.name: x.value for x in result.assumptions}
    wacc, gt, n = a["wacc"], a["terminal_growth_rate"], int(a["stage1_years"])

    def per_share(g: float) -> float:
        stage1 = sum(result.fcf_base * (1 + g) ** t / (1 + wacc) ** t for t in range(1, n + 1))
        terminal = result.fcf_base * (1 + g) ** (n + 1) / (wacc - gt) / (1 + wacc) ** n
        return (stage1 + terminal - result.net_debt) / result.shares_outstanding

    low, high = -0.5, 1.0
    for _ in range(100):
        mid = (low + high) / 2
        low, high = (mid, high) if per_share(mid) < price else (low, mid)
    return (low + high) / 2


def main() -> None:
    """Print the traced inputs, the DCF value and the growth the price implies."""
    with ValueinClient() as client:
        cik = client.resolve(TICKER)["cik"].iloc[0]
        history = historical_fcf_growth(client, cik)
        growth = min(max(history, 0.0), MAX_GROWTH)
        result = client.dcf(
            TICKER,
            stage1_growth_rate=growth,
            stage1_years=YEARS,
            wacc=WACC,
            terminal_growth_rate=TERMINAL_GROWTH,
        )

    print(f"{TICKER} DCF inputs, fiscal year ending {result.period_end}:")
    columns = ["name", "value", "concept", "source", "fact_id", "accession_id", "note"]
    print(result.inputs_frame()[columns].to_string(index=False))
    print(
        f"\nassumptions: growth {growth:.1%} (history {history:.1%}), wacc {WACC:.1%}, "
        f"terminal {TERMINAL_GROWTH:.1%}, {YEARS} years"
    )
    if result.value_per_share is None:
        print(f"no valuation: {result.reason}")
        return
    if result.price is None:
        print(f"value per share {result.value_per_share:,.2f} (no price on this plan)")
        return
    print(
        f"value per share {result.value_per_share:,.2f} vs last close {result.price:,.2f} "
        f"on {result.price_date} ({result.upside:+.1%})"
    )
    print(f"stage-1 growth implied by the price: {implied_growth(result, result.price):.1%}")


if __name__ == "__main__":
    main()
