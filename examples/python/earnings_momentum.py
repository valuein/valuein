"""Valuein US Core Fundamentals — Earnings Momentum Screen

A classic quant factor: companies whose earnings growth is *accelerating*
tend to outperform companies whose earnings growth is decelerating.

This script builds the simplest possible earnings-momentum screen over the
S&P 500: rank by year-over-year growth of TotalRevenue and NetIncome from
the two most recent 10-Ks. Positive values = accelerating fundamentals.

What you'll learn:
- How to pull the two most recent 10-Ks per company in one query (LATERAL x2)
- How to compute YoY growth with NULLIF-safe division
- How to join two pivoted fact scans (latest vs prior) on accession_id
- How to surface the top and bottom of a factor ranking

Run:
    export VALUEIN_API_KEY="your_token_here"
    python examples/python/earnings_momentum.py
"""

from valuein_sdk import ValueinClient

client = ValueinClient(tables=["references", "filing", "fact"])

# ── 1. Assemble latest and prior 10-K fundamentals per S&P 500 company ───────
# Two LATERAL subqueries: the first picks the most recent 10-K, the second
# picks the 10-K filed strictly before it. Then we pivot revenue + net income
# on each filing and join the two pivots on the S&P 500 company.
print("=" * 60)
print("1. Computing YoY revenue & earnings growth (S&P 500)")
print("=" * 60)
df = client.query("""
    WITH latest AS (
        SELECT
            r.cik, r.symbol, r.name, r.sector,
            f.accession_id, f.filing_date
        FROM "references" r
        JOIN LATERAL (
            SELECT accession_id, filing_date
            FROM   filing
            WHERE  entity_id = r.cik AND form_type = '10-K'
            ORDER  BY filing_date DESC
            LIMIT  1
        ) f ON TRUE
        WHERE r.is_sp500 = TRUE AND r.is_active = TRUE
    ),
    prior AS (
        SELECT
            l.cik,
            f.accession_id AS prior_accession_id
        FROM latest l
        JOIN LATERAL (
            SELECT accession_id
            FROM   filing
            WHERE  entity_id = l.cik
              AND  form_type = '10-K'
              AND  filing_date < l.filing_date
            ORDER  BY filing_date DESC
            LIMIT  1
        ) f ON TRUE
    ),
    latest_pivot AS (
        SELECT
            fa.accession_id,
            MAX(CASE WHEN fa.standard_concept = 'TotalRevenue' THEN fa.numeric_value END) AS revenue,
            MAX(CASE WHEN fa.standard_concept = 'NetIncome'    THEN fa.numeric_value END) AS net_income
        FROM fact fa
        WHERE fa.standard_concept IN ('TotalRevenue', 'NetIncome')
          AND fa.fiscal_period = 'FY'
        GROUP BY fa.accession_id
    ),
    prior_pivot AS (
        SELECT
            fa.accession_id,
            MAX(CASE WHEN fa.standard_concept = 'TotalRevenue' THEN fa.numeric_value END) AS revenue,
            MAX(CASE WHEN fa.standard_concept = 'NetIncome'    THEN fa.numeric_value END) AS net_income
        FROM fact fa
        WHERE fa.standard_concept IN ('TotalRevenue', 'NetIncome')
          AND fa.fiscal_period = 'FY'
        GROUP BY fa.accession_id
    )
    SELECT
        l.symbol, l.name, l.sector,
        round(lp.revenue    / 1e9, 2) AS rev_bn,
        round(lp.net_income / 1e9, 2) AS ni_bn,
        round(100.0 * (lp.revenue    - pp.revenue)    / NULLIF(pp.revenue, 0), 1)    AS rev_yoy_pct,
        round(100.0 * (lp.net_income - pp.net_income) / NULLIF(ABS(pp.net_income), 0), 1) AS ni_yoy_pct
    FROM latest l
    JOIN latest_pivot lp ON lp.accession_id = l.accession_id
    JOIN prior        p  ON p.cik           = l.cik
    JOIN prior_pivot  pp ON pp.accession_id = p.prior_accession_id
    WHERE lp.revenue IS NOT NULL
      AND pp.revenue IS NOT NULL
      AND lp.net_income IS NOT NULL
      AND pp.net_income IS NOT NULL
""")
print(f"  Rows returned: {len(df)}")
print()

# ── 2. Top 20 by revenue momentum ────────────────────────────────────────────
print("=" * 60)
print("2. Top 20 by revenue YoY growth")
print("=" * 60)
cols = ["symbol", "name", "sector", "rev_bn", "rev_yoy_pct", "ni_yoy_pct"]
print(df.nlargest(20, "rev_yoy_pct")[cols].to_string(index=False))
print()

# ── 3. Top 20 by net income momentum ─────────────────────────────────────────
print("=" * 60)
print("3. Top 20 by net income YoY growth")
print("=" * 60)
print(df.nlargest(20, "ni_yoy_pct")[cols].to_string(index=False))
print()

# ── 4. Momentum "sweet spot" — both revenue and earnings accelerating ────────
print("=" * 60)
print("4. Double-accelerators: revenue AND net income growing > 15%")
print("=" * 60)
sweet = df[(df["rev_yoy_pct"] > 15) & (df["ni_yoy_pct"] > 15)]
sweet = sweet.sort_values("ni_yoy_pct", ascending=False)
print(f"  {len(sweet)} S&P 500 names qualify.")
print()
print(sweet[cols].head(20).to_string(index=False))
print()

print("  Classic momentum signal: double-digit revenue growth *and* earnings")
print("  growing faster than revenue (operating leverage). Combine with the")
print("  factor_screen.py Quality/Efficiency ranks for a real screen.")
