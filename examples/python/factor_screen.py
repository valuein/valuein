"""Valuein US Core Fundamentals — Multi-Factor Fundamental Screen

Screen the S&P 500 by a composite fundamental score across three factors:

  - Quality  : Return on Equity (NetIncome / StockholdersEquity)
  - Growth   : Year-over-year revenue growth
  - Efficiency: Asset turnover (TotalRevenue / TotalAssets)

Each factor is z-scored within the universe, then averaged to produce a
composite rank. This is the skeleton every quant factor strategy starts from —
swap in your own factors, add more, re-weight, layer on a sector neutraliser.

What you'll learn:
- How to start a cross-company screen from `references` (zero 3-table joins)
- How to pull the latest 10-K + prior 10-K in one query using LATERAL
- How to pivot multiple `standard_concept` values in one `fact` scan
- How to safely z-score with outliers via pandas

Run:
    export VALUEIN_API_KEY="your_token_here"
    python examples/python/factor_screen.py
"""

import pandas as pd

from valuein_sdk import ValueinClient

client = ValueinClient(tables=["references", "filing", "fact"])

# ── 1. Pull latest + prior annual fundamentals for the S&P 500 ───────────────
# For each S&P 500 company we take:
#   - `latest` : most recent 10-K
#   - `prior`  : 10-K filed one fiscal year before `latest`
# Then we pivot five standard_concept values in a single `fact` scan per filing.
print("=" * 60)
print("1. Pulling latest + prior-year 10-K fundamentals (S&P 500)")
print("=" * 60)
df = client.query("""
    WITH latest AS (
        SELECT
            r.cik, r.symbol, r.name, r.sector,
            f.accession_id, f.filing_date, f.report_date
        FROM "references" r
        JOIN LATERAL (
            SELECT accession_id, filing_date, report_date
            FROM   filing
            WHERE  entity_id = r.cik AND form_type = '10-K'
            ORDER  BY filing_date DESC
            LIMIT  1
        ) f ON TRUE
        WHERE r.is_sp500 = TRUE AND r.is_active = TRUE
    ),
    prior AS (
        SELECT
            l.cik, f.accession_id AS prior_accession_id
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
    latest_facts AS (
        SELECT
            fa.accession_id,
            MAX(CASE WHEN fa.standard_concept = 'TotalRevenue'       THEN fa.numeric_value END) AS revenue,
            MAX(CASE WHEN fa.standard_concept = 'NetIncome'          THEN fa.numeric_value END) AS net_income,
            MAX(CASE WHEN fa.standard_concept = 'StockholdersEquity' THEN fa.numeric_value END) AS equity,
            MAX(CASE WHEN fa.standard_concept = 'TotalAssets'        THEN fa.numeric_value END) AS total_assets
        FROM fact fa
        WHERE fa.standard_concept IN
              ('TotalRevenue','NetIncome','StockholdersEquity','TotalAssets')
          AND fa.fiscal_period = 'FY'
        GROUP BY fa.accession_id
    ),
    prior_facts AS (
        SELECT
            fa.accession_id,
            MAX(CASE WHEN fa.standard_concept = 'TotalRevenue' THEN fa.numeric_value END) AS revenue
        FROM fact fa
        WHERE fa.standard_concept = 'TotalRevenue'
          AND fa.fiscal_period = 'FY'
        GROUP BY fa.accession_id
    )
    SELECT
        l.symbol, l.name, l.sector,
        lf.revenue       AS revenue,
        lf.net_income    AS net_income,
        lf.equity        AS equity,
        lf.total_assets  AS total_assets,
        pf.revenue       AS revenue_prior
    FROM latest l
    JOIN latest_facts lf ON lf.accession_id = l.accession_id
    LEFT JOIN prior p    ON p.cik           = l.cik
    LEFT JOIN prior_facts pf ON pf.accession_id = p.prior_accession_id
""")
print(f"  Rows returned: {len(df)}")
print()

# ── 2. Compute factors (with NULLIF-style safety via pandas) ─────────────────
# Every ratio is computed on a pandas Series where the denominator has been
# replaced with NaN on zero / negative values. Dividing by NaN propagates NaN
# instead of raising — companies missing a denominator simply drop out of the
# ranking for that factor.
df["roe"] = df["net_income"] / df["equity"].where(df["equity"] > 0)
df["asset_turnover"] = df["revenue"] / df["total_assets"].where(df["total_assets"] > 0)
df["rev_growth"] = (df["revenue"] - df["revenue_prior"]) / df["revenue_prior"].where(
    df["revenue_prior"] > 0
)

# Drop companies missing any factor
factors = ["roe", "asset_turnover", "rev_growth"]
ranked = df.dropna(subset=factors).copy()


def zscore(s: pd.Series) -> pd.Series:
    # Winsorise at 1st/99th percentile to blunt outliers before z-scoring.
    lo, hi = s.quantile([0.01, 0.99])
    s = s.clip(lower=lo, upper=hi)
    return (s - s.mean()) / s.std(ddof=0)


for f in factors:
    ranked[f"z_{f}"] = zscore(ranked[f])

ranked["composite"] = ranked[[f"z_{f}" for f in factors]].mean(axis=1)

# ── 3. Top and bottom of the screen ──────────────────────────────────────────
print("=" * 60)
print("2. Top 15 S&P 500 names by composite factor score")
print("   (Quality + Growth + Efficiency, equal-weighted z-scores)")
print("=" * 60)
cols = ["symbol", "name", "sector", "roe", "rev_growth", "asset_turnover", "composite"]
top = ranked.nlargest(15, "composite")[cols].round(3)
print(top.to_string(index=False))
print()

print("=" * 60)
print("3. Bottom 15 S&P 500 names by composite factor score")
print("=" * 60)
bot = ranked.nsmallest(15, "composite")[cols].round(3)
print(bot.to_string(index=False))
print()

# ── 4. Sector averages ────────────────────────────────────────────────────────
print("=" * 60)
print("4. Composite score by sector (median)")
print("=" * 60)
by_sector = (
    ranked.groupby("sector")["composite"]
    .median()
    .sort_values(ascending=False)
    .round(3)
    .to_frame("median_composite")
)
print(by_sector.to_string())
print()

print("  Tip: this is a factor *template*. Rebalance quarterly, neutralise by")
print("  sector, add a quality filter (e.g. operating margin > 0), and you have")
print("  the skeleton of a long/short portfolio.")
