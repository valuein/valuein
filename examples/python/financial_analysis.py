"""Valuein US Core Fundamentals — Financial Analysis

Core fundamental analysis using standardized financial concepts.
Covers revenue trends, balance sheet analysis, and margin ratios.

Every fact in the dataset has two concept columns:
  - concept          — the raw XBRL tag as filed with the SEC (e.g. us-gaap:Revenues)
  - standard_concept — the canonical label our system assigns across all companies
                       (e.g. 'Revenues'), enabling cross-company queries without
                       knowing each filer's specific tag choices.

What you'll learn:
- How to retrieve income statement items for any ticker
- How to compare companies side by side
- How to compute financial ratios inline with DuckDB SQL
- How standard_concept normalization works using fact.concept directly

Run:
    export VALUEIN_API_KEY="your_token_here"
    python examples/python/financial_analysis.py
"""

from valuein_sdk import ValueinClient

client = ValueinClient(tables=["entity", "security", "filing", "fact"])

# ── 1. NVDA revenue — last 5 fiscal years (10-K only) ────────────────────────
# QUALIFY deduplicates: each 10-K contains comparative periods; we keep only
# the current fiscal year row (latest period_end per fiscal_year).
print("=" * 60)
print("1. NVIDIA revenue — last 5 annual filings (10-K)")
print("=" * 60)
df = client.query("""
    SELECT
        fa.fiscal_year,
        fa.period_end,
        round(fa.numeric_value / 1e9, 2) AS revenue_bn_usd
    FROM   fact    fa
    JOIN   filing  f  ON fa.accession_id = f.accession_id
    JOIN   security s ON f.entity_id     = s.entity_id
    WHERE  s.symbol            = 'NVDA'
      AND  s.is_active         = TRUE
      AND  f.form_type         = '10-K'
      AND  fa.standard_concept = 'TotalRevenue'
      AND  fa.fiscal_period    = 'FY'
    QUALIFY row_number() OVER (
        PARTITION BY fa.fiscal_year ORDER BY fa.period_end DESC
    ) = 1
    ORDER  BY fa.fiscal_year DESC
    LIMIT  5
""")
print(df.to_string(index=False))
print()

# ── 2. NVDA vs TSLA revenue side by side ─────────────────────────────────────
print("=" * 60)
print("2. NVIDIA vs Tesla annual revenue comparison")
print("=" * 60)
df = client.query("""
    SELECT
        s.symbol,
        fa.fiscal_year,
        round(fa.numeric_value / 1e9, 2) AS revenue_bn_usd
    FROM   fact    fa
    JOIN   filing  f  ON fa.accession_id = f.accession_id
    JOIN   security s ON f.entity_id     = s.entity_id
    WHERE  s.symbol            IN ('NVDA', 'TSLA')
      AND  s.is_active         = TRUE
      AND  f.form_type         = '10-K'
      AND  fa.standard_concept = 'TotalRevenue'
      AND  fa.fiscal_period    = 'FY'
    QUALIFY row_number() OVER (
        PARTITION BY s.symbol, fa.fiscal_year ORDER BY fa.period_end DESC
    ) = 1
    ORDER  BY fa.fiscal_year DESC, s.symbol
    LIMIT  10
""")
print(df.to_string(index=False))
print()

# ── 3. NVDA latest balance sheet ─────────────────────────────────────────────
print("=" * 60)
print("3. NVIDIA latest balance sheet snapshot")
print("=" * 60)
df = client.query("""
    WITH latest AS (
        SELECT f.accession_id
        FROM   filing  f
        JOIN   security s ON f.entity_id = s.entity_id
        WHERE  s.symbol    = 'NVDA'
          AND  s.is_active = TRUE
          AND  f.form_type = '10-K'
        ORDER  BY f.filing_date DESC
        LIMIT  1
    )
    SELECT
        fa.standard_concept,
        fa.period_end,
        round(fa.numeric_value / 1e9, 2) AS value_bn_usd
    FROM fact fa
    JOIN latest l ON fa.accession_id = l.accession_id
    WHERE fa.standard_concept IN (
        'TotalAssets',
        'TotalLiabilities',
        'StockholdersEquity'
    )
    QUALIFY row_number() OVER (
        PARTITION BY fa.standard_concept ORDER BY fa.period_end DESC
    ) = 1
    ORDER BY fa.standard_concept
""")
print(df.to_string(index=False))
print()

# ── 4. AAPL gross margin — last 5 annual filings ─────────────────────────────
print("=" * 60)
print("4. Apple gross margin — last 5 annual filings")
print("=" * 60)
df = client.query("""
    SELECT
        rev.fiscal_year,
        round(rev.numeric_value / 1e9, 2)                          AS revenue_bn,
        round(gp.numeric_value  / 1e9, 2)                          AS gross_profit_bn,
        round(100.0 * gp.numeric_value / rev.numeric_value, 1)     AS gross_margin_pct
    FROM filing f
    JOIN security s  ON f.entity_id    = s.entity_id
    JOIN fact    rev ON rev.accession_id = f.accession_id
                    AND rev.standard_concept = 'TotalRevenue'
                    AND rev.fiscal_period    = 'FY'
    JOIN fact    gp  ON gp.accession_id  = f.accession_id
                    AND gp.standard_concept  = 'GrossProfit'
                    AND gp.fiscal_period     = 'FY'
    WHERE s.symbol    = 'AAPL'
      AND s.is_active = TRUE
      AND f.form_type = '10-K'
    QUALIFY row_number() OVER (PARTITION BY rev.fiscal_year ORDER BY rev.period_end DESC) = 1
    ORDER BY rev.fiscal_year DESC
    LIMIT 5
""")
if df.empty:
    # AAPL uses an unmapped XBRL tag for revenue; fall back to GrossProfit alone
    df = client.query("""
        SELECT
            fa.fiscal_year,
            round(fa.numeric_value / 1e9, 2) AS gross_profit_bn
        FROM fact fa
        JOIN filing  f ON fa.accession_id = f.accession_id
        JOIN security s ON f.entity_id    = s.entity_id
        WHERE s.symbol           = 'AAPL'
          AND s.is_active        = TRUE
          AND f.form_type        = '10-K'
          AND fa.standard_concept = 'GrossProfit'
          AND fa.fiscal_period   = 'FY'
        QUALIFY row_number() OVER (PARTITION BY fa.fiscal_year ORDER BY fa.period_end DESC) = 1
        ORDER BY fa.fiscal_year DESC
        LIMIT 5
    """)
    print("  (TotalRevenue not mapped for AAPL; showing GrossProfit)")
print(df.to_string(index=False))
print()

# ── 5. Normalization in action: many raw XBRL tags → one standard_concept ────
# The fact table carries both the raw concept (SEC-filed XBRL tag) and the
# standard_concept our system assigns. Querying DISTINCT pairs shows exactly
# how normalization works without needing any private mapping table.
print("=" * 60)
print("5. Normalization: raw XBRL tags that resolve to 'Revenues'")
print("   (fact.concept vs fact.standard_concept)")
print("=" * 60)
df = client.query("""
    SELECT DISTINCT
        fa.concept          AS raw_xbrl_tag,
        fa.standard_concept AS normalized_concept
    FROM   fact fa
    WHERE  fa.standard_concept = 'Revenues'
    ORDER  BY fa.concept
    LIMIT  20
""")
print(df.to_string(index=False))
print()
print("One standard_concept. Many raw tags. Normalised across all filers.")
