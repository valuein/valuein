"""Valuein US Core Fundamentals — Point-in-Time (PIT) Backtesting

THE critical example for quant practitioners.

The problem: companies restate earnings. If Apple filed Q3 2023 earnings
in October 2023, then restated them in February 2024, most data providers
silently overwrite the original number. Your backtest now uses data you
didn't have at the time — that's look-ahead bias.

Valuein preserves every version of every fact with an accepted_at timestamp.
You can ask: "What did the market know on date X?"

What you'll learn:
- How the same period can have multiple versions over time (restatements)
- How to write a PIT-correct query using filing_date
- Why filtering by report_date instead of filing_date leaks future data
- The institutional standard for survivorship-bias-free backtesting

Run:
    export VALUEIN_API_KEY="your_token_here"
    python examples/python/pit_backtest.py
"""

from valuein_sdk import ValueinClient

client = ValueinClient(tables=["security", "filing", "fact"])

TICKER = "NVDA"
TRADE_DATE = "2024-01-15"

# ── 1. The restatement problem ────────────────────────────────────────────────
print("=" * 60)
print("1. Restatements — same period, multiple knowledge dates")
print("=" * 60)
print(
    f"  Each row below is a version of {TICKER}'s annual revenue.\n"
    "  A new row appears each time the company files an amendment.\n"
    "  Most providers keep only the latest — destroying history.\n"
)
df = client.query(f"""
    SELECT
        fa.period_end,
        fa.fiscal_year,
        f.form_type,
        f.filing_date,
        fa.accepted_at,
        round(fa.numeric_value / 1e9, 2) AS revenue_bn
    FROM   fact    fa
    JOIN   filing  f  ON fa.accession_id = f.accession_id
    JOIN   security s ON f.entity_id     = s.entity_id
    WHERE  s.symbol            = '{TICKER}'
      AND  s.is_active         = TRUE
      AND  fa.standard_concept = 'TotalRevenue'
      AND  f.form_type         IN ('10-K', '10-K/A')
    ORDER  BY fa.period_end DESC, fa.accepted_at ASC
    LIMIT  15
""")
print(df.to_string(index=False))
print()

# ── 2. PIT-correct query ──────────────────────────────────────────────────────
print("=" * 60)
print(f"2. PIT-correct: What did the market know about {TICKER} on {TRADE_DATE}?")
print("   CORRECT: filter by filing_date <= trade_date")
print("=" * 60)
df_pit = client.query(f"""
    SELECT
        fa.standard_concept,
        fa.fiscal_year,
        f.filing_date,
        round(fa.numeric_value / 1e9, 2) AS value_bn
    FROM   fact    fa
    JOIN   filing  f  ON fa.accession_id = f.accession_id
    JOIN   security s ON f.entity_id     = s.entity_id
    WHERE  s.symbol            = '{TICKER}'
      AND  s.is_active         = TRUE
      AND  fa.standard_concept IN ('TotalRevenue', 'NetIncome')
      AND  f.form_type          = '10-K'
      AND  f.filing_date       <= '{TRADE_DATE}'     -- ← PIT filter
    ORDER  BY f.filing_date DESC, fa.standard_concept
    LIMIT  10
""")
print(df_pit.to_string(index=False))
print()

# ── 3. The anti-pattern ───────────────────────────────────────────────────────
print("=" * 60)
print("3. WRONG: filtering by report_date introduces look-ahead bias")
print("   report_date is the fiscal period end, NOT when you learned it")
print("=" * 60)
df_wrong = client.query(f"""
    SELECT
        fa.standard_concept,
        fa.fiscal_year,
        fa.period_end   AS report_date,   -- ← fiscal period end
        f.filing_date,                    -- ← when market actually learned it
        round(fa.numeric_value / 1e9, 2) AS value_bn
    FROM   fact    fa
    JOIN   filing  f  ON fa.accession_id = f.accession_id
    JOIN   security s ON f.entity_id     = s.entity_id
    WHERE  s.symbol            = '{TICKER}'
      AND  s.is_active         = TRUE
      AND  fa.standard_concept IN ('TotalRevenue', 'NetIncome')
      AND  f.form_type          = '10-K'
      AND  fa.period_end       <= '{TRADE_DATE}'     -- ← WRONG: not when you knew it
    ORDER  BY fa.period_end DESC, fa.standard_concept
    LIMIT  10
""")
print(df_wrong.to_string(index=False))

pit_rows = len(df_pit)
wrong_rows = len(df_wrong)
if wrong_rows > pit_rows:
    print(
        f"\n  PIT-correct returned {pit_rows} rows. "
        f"The wrong query returned {wrong_rows} rows.\n"
        f"  Those extra {wrong_rows - pit_rows} rows contain data "
        "you couldn't have had at the trade date."
    )
print()

print("=" * 60)
print("This is why institutional quants pay for PIT data.")
print(
    "\nRule: ALWAYS filter by filing_date <= trade_date.\n"
    "      NEVER filter by report_date alone.\n"
    "      Use accepted_at for millisecond-precision PIT filtering."
)
print("=" * 60)
