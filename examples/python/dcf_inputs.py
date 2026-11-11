"""A two-stage DCF from reported SEC data, every input traced to its filing.

What it does: runs `client.dcf()` for one company with explicit, editable assumptions (the
stage-1 growth rate defaults to the company's historical free-cash-flow growth, capped), prints
each input with the `fact_id` and accession number of the filing it came from, and the value per
share.
Valuein publishes the reported inputs, not an opinion of value: the assumptions are yours.
Who it is for: valuation analysts and developers building valuation tools.
Plan: none. Runs on the free sample tier (S&P 500 companies, last five years) with no API key.
SDK methods: ValueinClient.resolve, ValueinClient.run_query, ValueinClient.dcf.
Tables: fact, filing, references.
Notebook: examples/notebooks/10_dcf_valuation.ipynb

Run:
    pip install "valuein-sdk>=1.0.0"
    python examples/python/dcf_inputs.py
"""

from __future__ import annotations

from valuein_sdk import ValueinClient

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


def main() -> None:
    """Print the traced inputs and the DCF value per share."""
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
    print(f"value per share {result.value_per_share:,.2f}")


if __name__ == "__main__":
    main()
