"""Valuein — Point-in-Time, Survivorship-Free Factor Dataset

Build a research-grade, point-in-time (PIT), survivorship-bias-free factor
dataset and write it to **both Parquet and CSV** — the exact input a portfolio
optimizer, a backtester, or a model-training pipeline expects.

This is the core Valuein wedge made tangible: every number in the output was
*knowable* on the chosen `as_of` date. No look-ahead bias. No survivorship
bias. The membership set is reconstructed from `index_membership` (delisted and
acquired names included), and every fact is filtered by `filing_date <= as_of`,
not `report_date` — a company's Q4 numbers don't exist in the dataset until the
day the 10-K was actually filed.

What you'll learn:
- How to resolve a survivorship-free index universe at a historical date with
  `client.pit_universe()` (the `pit_universe_announcement` SQL template)
- How to score that universe with the `AlphaEngine` + built-in factors
  (ROE, REVENUE_GROWTH_YOY, FCF_TO_ASSETS, DEBT_TO_EQUITY, PIOTROSKI_F_SCORE)
- What's *underneath* the engine — the raw survivorship-free join
  (`references.cik = index_membership.cik`) and the `filing_date <= as_of`
  PIT filter — shown as one explicit SQL block so the correctness is visible
- How to export to Parquet (PyArrow) and CSV (pandas) for a downstream optimizer

Run:
    # Install (either workflow):  pip install valuein-sdk  |  uv pip install valuein-sdk
    # The FREE S&P 500 tier (1993+, 500 names) needs only a free lead-capture
    # token. Without any token the SDK runs in SAMPLE mode (~50 tickers, 2020+).
    export VALUEIN_API_KEY="your_token_here"
    python examples/python/pit_factor_dataset.py
"""

import os
import sys
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

from valuein_sdk import ValueinClient
from valuein_sdk.alpha import AlphaEngine
from valuein_sdk.alpha.factors import (
    DEBT_TO_EQUITY,
    FCF_TO_ASSETS,
    PIOTROSKI_F_SCORE,
    REVENUE_GROWTH_YOY,
    ROE,
)
from valuein_sdk.exceptions import ValueinPlanError

# ── Configuration ────────────────────────────────────────────────────────────
# The PIT cutoff. Every fact used is filtered by `filing_date <= AS_OF_DATE`,
# and the index universe is reconstructed as it stood on this exact day.
AS_OF_DATE = "2023-06-30"
INDEX = "SP500"
OUT_PARQUET = "pit_factor_dataset.parquet"
OUT_CSV = "pit_factor_dataset.csv"

# ── 0. Guards — deterministic, actionable error messages ─────────────────────
# Agents and humans both need to know exactly how to fix a bad call. Each guard
# fails fast with a message that points at the next action.
token = os.getenv("VALUEIN_API_KEY", "").strip()
if not token:
    print(
        "No VALUEIN_API_KEY found. This example needs the FREE S&P 500 tier "
        "(1993+, 500 names). Get a free token in ~30s at "
        "https://valuein.biz/pricing, then:  export VALUEIN_API_KEY=<token>",
        file=sys.stderr,
    )
    sys.exit(1)

# index_membership history begins in 1996 — earlier as_of dates have no
# survivorship-free membership set to reconstruct.
if AS_OF_DATE < "1996-01-01":
    print(
        f"as_of_date {AS_OF_DATE!r} is before 1996. The index_membership "
        "history starts 1996 — pick an as_of date on or after 1996-01-01.",
        file=sys.stderr,
    )
    sys.exit(1)

# ── 1. Construct the client, pinned to the PIT cutoff ────────────────────────
# `as_of` pushes the cutoff into the DuckDB views themselves: PIT tables (fact,
# filing_text, …) are filtered to `accepted_at <= as_of` at view-creation time,
# so even a raw `SELECT *` can't leak a future fact. Timezone-aware required.
as_of_dt = datetime.strptime(AS_OF_DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
client = ValueinClient(
    as_of=as_of_dt,
    tables=["references", "index_membership", "entity", "security", "filing", "fact"],
)
print(f"Client plan: {client.plan!r}  |  PIT cutoff: {AS_OF_DATE}")

# ── 2. Survivorship-free universe at the as_of date ──────────────────────────
# `pit_universe()` wraps the `pit_universe_announcement` template. It returns
# one row per (cik, ticker-at-the-date), INCLUDING companies that were later
# delisted/acquired — that is what makes the backtest survivorship-free. A name
# that was in the S&P 500 on AS_OF_DATE but has since vanished is still here.
print("=" * 64)
print(f"1. Survivorship-free {INDEX} membership as of {AS_OF_DATE}")
print("=" * 64)
try:
    universe = client.pit_universe(as_of_date=AS_OF_DATE, index=INDEX)
except ValueinPlanError as exc:
    # Tier-insufficient — surface the message AND the canonical upgrade URL.
    # (ValueinPlanError carries the gate reason in str(exc); the pricing page is
    # the single contract shared with the MCP Worker's upgrade_url field.)
    print(f"  Plan gate: {exc}", file=sys.stderr)
    print("  Upgrade to unlock this universe: https://valuein.biz/pricing", file=sys.stderr)
    sys.exit(1)

members = universe.dropna(subset=["ticker_at_date"])
print(f"  Members on {AS_OF_DATE}: {len(universe)}  (with a live ticker: {len(members)})")
print()

# ── 3. The headline — AlphaEngine factor scoring (PIT-safe) ──────────────────
# The engine runs each factor's SQL with `filing_date <= as_of` injected, then
# merges by cik. Built-in factors already encode every gotcha you'd otherwise
# hit by hand:
#   - COALESCE(derived_quarterly_value, numeric_value) for cash flow (FCF) —
#     Q2/Q3 10-Qs report YTD, so the single-quarter value must be isolated.
#   - NULLIF(denominator, 0) on every ratio so a zero denominator -> NULL,
#     never a divide-by-zero or a garbage Inf.
#   - ABS(capex) because the sign of CAPEX varies by filer.
print("=" * 64)
print("2. AlphaEngine factor scores (Quality / Growth / Cash / Leverage / F-Score)")
print("=" * 64)
engine = (
    AlphaEngine(client)
    .add_factor(ROE)  # Quality   — NetIncome / StockholdersEquity
    .add_factor(REVENUE_GROWTH_YOY)  # Growth    — (rev_t - rev_{t-1}) / rev_{t-1}
    .add_factor(FCF_TO_ASSETS)  # Cash      — (OCF - |CAPEX|) / TotalAssets
    .add_factor(DEBT_TO_EQUITY)  # Leverage  — TotalLiabilities / Equity (↓ better)
    .add_factor(PIOTROSKI_F_SCORE)  # Quality   — 0–9 fundamental composite
)
# `as_of` here is belt-and-suspenders: the client view is already PIT-filtered,
# and the engine *also* injects `AND filing_date <= as_of` into each factor SQL.
# sp500_only=True restricts to current S&P 500 membership on the free tier.
result = engine.compute(as_of=AS_OF_DATE, sp500_only=True, min_factors=3)
print(f"  Scored {len(result)} companies across {len(result.factor_names)} factors")

# Composite alpha = equal-weighted percentile rank, best name first. `.rank()`
# respects factor direction (DEBT_TO_EQUITY ranks low-is-good automatically),
# so a composite of 1.0 always means "best in universe".
composite = result.rank().combine()
factor_df = result.df.set_index("symbol")
dataset = factor_df.join(composite.rename("composite_alpha"), how="left")
dataset = dataset.sort_values("composite_alpha", ascending=False)

print()
print("  Top 12 by composite alpha:")
cols = [*result.factor_names, "composite_alpha"]
print(dataset[["name", *cols]].head(12).round(3).to_string())
print()

# ── 4. What's underneath — the raw survivorship-free, PIT-correct SQL ────────
# The engine is convenience. Here is the load-bearing correctness, in one
# explicit query a quant can audit line by line:
#   * `references.cik = index_membership.cik` (same column name since migration
#     0015) is the survivorship-free join — membership intervals, not a snapshot.
#   * `$date >= effective_date AND ($date < removal_date OR removal_date IS NULL)`
#     selects members AS OF the date — a name removed before AS_OF_DATE is
#     correctly excluded; a name added after it is too.
#   * `filing_date <= AS_OF_DATE` (NOT report_date) is the PIT filter — the
#     numbers are only those a researcher could have read on AS_OF_DATE.
#   * QUALIFY ROW_NUMBER() keeps the single latest filing known by the cutoff.
print("=" * 64)
print("3. The proof underneath: raw survivorship-free + PIT SQL (latest 10-K per member)")
print("=" * 64)
pit_sql = f"""
    WITH members AS (
        -- Survivorship-free membership AS OF the date (interval, not snapshot)
        SELECT r.cik, r.symbol, r.name, r.sector
        FROM "references" r
        JOIN index_membership im ON im.cik = r.cik          -- same column both sides
        WHERE im.index_name = '{INDEX}'
          AND DATE '{AS_OF_DATE}' >= im.effective_date
          AND (DATE '{AS_OF_DATE}' < im.removal_date OR im.removal_date IS NULL)
    ),
    latest_known_10k AS (
        -- PIT: only filings the market could SEE by AS_OF_DATE (filing_date,
        -- never report_date). QUALIFY keeps the single most-recent one.
        SELECT m.cik, m.symbol, m.name, m.sector,
               f.accession_id, f.filing_date, f.report_date
        FROM members m
        JOIN filing f ON f.entity_id = m.cik AND f.form_type = '10-K'
        WHERE f.filing_date <= DATE '{AS_OF_DATE}'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY m.cik ORDER BY f.filing_date DESC) = 1
    )
    SELECT
        k.symbol, k.name, k.sector, k.filing_date, k.report_date,
        MAX(CASE WHEN fa.standard_concept = 'NetIncome'   THEN fa.numeric_value END)
            / NULLIF(MAX(CASE WHEN fa.standard_concept = 'StockholdersEquity'
                              THEN fa.numeric_value END), 0)              AS roe_raw,
        MAX(CASE WHEN fa.standard_concept = 'TotalRevenue' THEN fa.numeric_value END)
                                                                          AS revenue
    FROM latest_known_10k k
    JOIN fact fa ON fa.accession_id = k.accession_id
        AND fa.standard_concept IN ('NetIncome', 'StockholdersEquity', 'TotalRevenue')
        AND fa.fiscal_period = 'FY'
    GROUP BY k.symbol, k.name, k.sector, k.filing_date, k.report_date
    ORDER BY roe_raw DESC NULLS LAST
"""
proof = client.run_query(pit_sql)
print(f"  Latest-known-10-K rows as of {AS_OF_DATE}: {len(proof)}")
if not proof.empty:
    # Note filing_date <= as_of in every row, while report_date (the period end)
    # can pre-date it by months — exactly the gap PIT discipline closes.
    print(
        proof[["symbol", "filing_date", "report_date", "roe_raw"]]
        .head(8)
        .round(3)
        .to_string(index=False)
    )
print()

# ── 5. Export — BOTH Parquet (optimizer/training) and CSV (portability) ──────
# Parquet via PyArrow: typed, columnar, the native format an optimizer or a
# feature store ingests. CSV via pandas: universally portable for a quick look.
print("=" * 64)
print("4. Writing the dataset")
print("=" * 64)
export = dataset.reset_index()  # bring `symbol` back as a column

pq.write_table(pa.Table.from_pandas(export, preserve_index=False), OUT_PARQUET)
export.to_csv(OUT_CSV, index=False)
print(f"  Parquet -> {OUT_PARQUET}  ({len(export)} rows × {len(export.columns)} cols)")
print(f"  CSV     -> {OUT_CSV}")
print()
print("  This dataset is PIT-correct and survivorship-free: every value was")
print(f"  knowable on {AS_OF_DATE}, and delisted/acquired members are included.")
print("  Feed it straight into a portfolio optimizer or a model-training run.")

# ── Full-universe path (19,000+ names, all delisted history) ─────────────────
# Swap to the Institutional/`full` tier and drop sp500_only to score the entire
# CIK universe; use client.stream(sql) for fact-heavy queries so the `fact`
# table is never fully materialised in RAM:
#   result = engine.compute(as_of=AS_OF_DATE, sp500_only=False, min_factors=3)
#   for chunk in client.stream("SELECT * FROM fact WHERE fiscal_year >= 2010"): ...

client.close()
