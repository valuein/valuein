"""Valuein US Core Fundamentals — DCF Inputs

Build the raw inputs for a two-stage Discounted Cash Flow model from the
`fact` table, then cross-check against Valuein's pre-computed `valuation`
table. This is the example a fundamental analyst runs when they want to
roll their own DCF — we hand you the ingredients, you choose the WACC.

What you'll learn:
- How to assemble a 5-year FCF history (OperatingCashFlow − |CAPEX|)
- How to compute the Stage-1 growth CAGR from that history
- How to pull balance-sheet context (cash, debt, equity) in a single scan
- How to read back the valuation row Valuein pre-computed for the same entity

Run:
    export VALUEIN_API_KEY="your_token_here"
    python examples/python/dcf_inputs.py
"""

from valuein_sdk import ValueinClient

TICKER = "MSFT"

client = ValueinClient(tables=["references", "filing", "fact", "valuation"])

# ── 1. Five-year annual FCF history ───────────────────────────────────────────
# CAPEX sign varies by filer — always wrap in ABS() before subtracting.
print("=" * 60)
print(f"1. {TICKER} — 5-year annual FCF history")
print("   FCF = OperatingCashFlow − |CAPEX|")
print("=" * 60)
fcf = client.query(f"""
    WITH fy_10k AS (
        SELECT
            fa.accession_id, fa.fiscal_year, fa.period_end,
            MAX(CASE WHEN fa.standard_concept = 'OperatingCashFlow' THEN fa.numeric_value END) AS ocf,
            MAX(CASE WHEN fa.standard_concept = 'CAPEX'             THEN fa.numeric_value END) AS capex
        FROM fact fa
        JOIN filing  f  ON fa.accession_id = f.accession_id
        JOIN "references" r ON f.entity_id    = r.cik
        WHERE r.symbol        = '{TICKER}'
          AND r.is_active     = TRUE
          AND f.form_type     = '10-K'
          AND fa.fiscal_period = 'FY'
          AND fa.standard_concept IN ('OperatingCashFlow', 'CAPEX')
        GROUP BY fa.accession_id, fa.fiscal_year, fa.period_end
        QUALIFY ROW_NUMBER() OVER (PARTITION BY fa.fiscal_year ORDER BY fa.period_end DESC) = 1
    )
    SELECT
        fiscal_year,
        period_end,
        round(ocf / 1e9, 3)                 AS ocf_bn,
        round(ABS(capex) / 1e9, 3)          AS capex_bn,
        round((ocf - ABS(capex)) / 1e9, 3)  AS fcf_bn
    FROM fy_10k
    WHERE ocf IS NOT NULL AND capex IS NOT NULL
    ORDER BY fiscal_year DESC
    LIMIT 5
""")
print(fcf.to_string(index=False))
print()

# ── 2. Stage-1 growth CAGR from the FCF series ───────────────────────────────
if len(fcf) >= 2:
    oldest = fcf["fcf_bn"].iloc[-1]
    newest = fcf["fcf_bn"].iloc[0]
    years = len(fcf) - 1
    if oldest and oldest > 0 and newest > 0:
        cagr = (newest / oldest) ** (1 / years) - 1
        print(
            f"  {years}-year FCF CAGR: {cagr:.2%}  (Stage-1 growth assumption starting point)"
        )
    else:
        print("  CAGR not computable (negative or zero FCF in window)")
else:
    print("  Not enough FCF history in the Sample tier for a CAGR")
print()

# ── 3. Latest balance sheet context ──────────────────────────────────────────
# A DCF needs the capital structure to convert enterprise value → equity value,
# and EPS_Diluted (or share count) to convert equity value → per-share value.
print("=" * 60)
print(f"2. {TICKER} — latest balance sheet context")
print("=" * 60)
bs = client.query(f"""
    WITH latest AS (
        SELECT f.accession_id
        FROM   filing    f
        JOIN   "references" r ON f.entity_id = r.cik
        WHERE  r.symbol    = '{TICKER}'
          AND  r.is_active = TRUE
          AND  f.form_type = '10-K'
        ORDER  BY f.filing_date DESC
        LIMIT  1
    )
    SELECT
        fa.standard_concept,
        round(fa.numeric_value / 1e9, 3) AS value_bn,
        fa.period_end
    FROM fact fa
    JOIN latest l ON fa.accession_id = l.accession_id
    WHERE fa.standard_concept IN (
        'CashAndEquivalents',
        'TotalAssets',
        'TotalLiabilities',
        'StockholdersEquity',
        'EPS_Diluted'
    )
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY fa.standard_concept ORDER BY fa.period_end DESC
    ) = 1
    ORDER BY fa.standard_concept
""")
print(bs.to_string(index=False))
print()

# ── 4. Valuein pre-computed DCF (cross-check) ────────────────────────────────
# The `valuation` table already contains two-stage DCF + DDM intrinsic values
# keyed by entity + period_end. Useful as a sanity check on your own model.
print("=" * 60)
print(f"3. Valuein pre-computed valuation for {TICKER}")
print("=" * 60)
val = client.query(f"""
    SELECT
        v.period_end,
        round(v.dcf_value_per_share, 2)      AS dcf_per_share,
        round(v.ddm_value_per_share, 2)      AS ddm_per_share,
        round(v.wacc, 4)                     AS wacc,
        round(v.terminal_growth_rate, 4)     AS terminal_g,
        round(v.stage1_growth_rate, 4)       AS stage1_g,
        v.stage1_years                       AS stage1_yrs,
        round(v.fcf_base / 1e9, 3)           AS fcf_base_bn,
        round(v.shares_outstanding / 1e9, 3) AS shares_bn
    FROM   valuation v
    JOIN   "references" r ON v.entity_id = r.cik
    WHERE  r.symbol    = '{TICKER}'
      AND  r.is_active = TRUE
    ORDER  BY v.period_end DESC
    LIMIT  3
""")
if val.empty:
    print(f"  (No pre-computed valuation for {TICKER} in this plan tier)")
else:
    print(val.to_string(index=False))
print()

print("  You now have: FCF history, balance sheet, WACC + terminal growth.")
print("  Drop these into your own two-stage DCF sheet (or `valuein_sdk.dcf.*`")
print("  helpers when you upgrade) to produce a per-share intrinsic value.")
