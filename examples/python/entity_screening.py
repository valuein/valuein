"""Valuein US Core Fundamentals — Entity Screening

Learn how to screen the full universe of 10,000+ public companies.
This script demonstrates survivorship-bias-free universe construction —
a critical first step for any quant strategy.

What you'll learn:
- How many active vs inactive companies are in the dataset
- Which sectors dominate the universe
- How to filter by sector, SIC code, or status
- Why including delisted companies matters for backtesting

Run:
    export VALUEIN_API_KEY="your_token_here"
    python examples/python/entity_screening.py
"""

from valuein_sdk import ValueinClient

# Load only the tables we need — fast init
client = ValueinClient(tables=["entity", "security"])

# ── 1. Active vs inactive count ───────────────────────────────────────────────
print("=" * 60)
print("1. Universe composition (active vs inactive)")
print("=" * 60)
df = client.query("""
    SELECT
        status,
        count(*) AS companies,
        round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct
    FROM entity
    GROUP BY status
    ORDER BY companies DESC
""")
print(df.to_string(index=False))
print()

# ── 2. Top 10 sectors by company count ───────────────────────────────────────
print("=" * 60)
print("2. Top 10 sectors by company count")
print("=" * 60)
df = client.query("""
    SELECT
        coalesce(sector::VARCHAR, '(unclassified)') AS sector,
        count(*) AS companies
    FROM entity
    GROUP BY sector::VARCHAR
    ORDER BY companies DESC
    LIMIT 10
""")
print(df.to_string(index=False))
print()

# ── 3. Companies in the Technology sector ────────────────────────────────────
print("=" * 60)
print("3. Active Technology companies (sample)")
print("=" * 60)
df = client.query("""
    SELECT e.cik, e.name, e.industry, s.symbol, s.exchange
    FROM   entity   e
    JOIN   security s ON s.entity_id = e.cik AND s.is_active = TRUE
    WHERE  e.sector::VARCHAR = 'Technology'
      AND  e.status = 'ACTIVE'
    ORDER  BY e.name
    LIMIT  15
""")
print(df.to_string(index=False))
print()

# ── 4. Specific SIC codes ─────────────────────────────────────────────────────
print("=" * 60)
print("4. Semiconductor companies (SIC 3674)")
print("=" * 60)
df = client.query("""
    SELECT e.name, e.status, s.symbol, s.exchange
    FROM   entity   e
    LEFT   JOIN security s ON s.entity_id = e.cik AND s.is_active = TRUE
    WHERE  e.sic_code = '3674'
    ORDER  BY e.status, e.name
    LIMIT  20
""")
print(df.to_string(index=False))
print()

# ── 5. Delisted / inactive companies (survivorship-bias-free showcase) ────────
print("=" * 60)
print("5. Inactive/delisted companies (what most datasets omit)")
print("=" * 60)
df = client.query("""
    SELECT e.name, e.sector::VARCHAR AS sector, e.status, e.fiscal_year_end
    FROM   entity e
    WHERE  e.status IN ('INACTIVE', 'DELISTED')
    ORDER  BY e.name
    LIMIT  20
""")
print(df.to_string(index=False))
print()

inactive_count = client.query(
    "SELECT count(*) AS n FROM entity WHERE status IN ('INACTIVE', 'DELISTED')"
)["n"].iloc[0]
print(
    f"  {inactive_count:,} inactive/delisted companies are in this dataset.\n"
    "  Most data providers delete these. We keep them — because your\n"
    "  strategy didn't know they'd fail when you back-tested it."
)
