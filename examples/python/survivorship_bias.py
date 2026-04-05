"""Valuein US Core Fundamentals — Survivorship-Bias-Free Data

Most financial databases quietly delete companies that went bankrupt,
were acquired, or were delisted. What's left is a graveyard of winners.
Backtest a momentum strategy on that universe and your Sharpe looks
great — because you never tested it on the companies that blew up.

We kept them. Every last one.

What you'll learn:
- How many inactive/delisted companies are in the dataset
- How to find former index members that departed (via index_membership)
- How to query their financials in the years before failure
- Why omitting these companies overstates backtested returns

Run:
    export VALUEIN_API_KEY="your_token_here"
    python examples/python/survivorship_bias.py
"""

from valuein_sdk import ValueinClient

client = ValueinClient(tables=["entity", "security", "fact", "filing", "index_membership"])

# ── 1. Scale of inactive entities ────────────────────────────────────────────
print("=" * 60)
print("1. The companies most providers deleted")
print("=" * 60)
df = client.query("""
    SELECT
        status,
        count(*)                                              AS companies,
        round(100.0 * count(*) / sum(count(*)) OVER (), 1)   AS pct_of_universe
    FROM entity
    GROUP BY status
    ORDER BY companies DESC
""")
print(df.to_string(index=False))
print()

# ── 2. Former S&P 500 members that departed (survivorship in action) ──────────
# index_membership tracks every company that ever joined an index.
# end_date IS NOT NULL means they left — acquired, delisted, or went bankrupt.
print("=" * 60)
print("2. Former S&P 500 members that left the index")
print("   (acquired, delisted, or bankrupt — data others deleted)")
print("=" * 60)
df = client.query("""
    SELECT
        e.name,
        e.status,
        s.symbol,
        im.start_date   AS joined_index,
        im.end_date     AS left_index
    FROM   index_membership im
    JOIN   security s ON s.id        = im.security_id
    JOIN   entity   e ON e.cik       = s.entity_id
    WHERE  im.index_name = 'S&P 500'
      AND  im.end_date IS NOT NULL
    QUALIFY row_number() OVER (PARTITION BY e.cik ORDER BY im.end_date DESC) = 1
    ORDER BY im.end_date DESC
    LIMIT 20
""")
print(df.to_string(index=False))
print()

# ── 3. Financials for a departed company in the years before exit ─────────────
# Pick the most recent departure with fact data, then show its income trend.
print("=" * 60)
print("3. Revenue and net income for a former index member (pre-exit)")
print("=" * 60)
df = client.query("""
    WITH departed AS (
        SELECT
            e.cik,
            e.name,
            im.end_date
        FROM   index_membership im
        JOIN   security s ON s.id    = im.security_id
        JOIN   entity   e ON e.cik   = s.entity_id
        WHERE  im.index_name = 'S&P 500'
          AND  im.end_date IS NOT NULL
        ORDER  BY im.end_date DESC
        LIMIT  1
    )
    SELECT
        d.name,
        fa.fiscal_year,
        fa.standard_concept,
        round(fa.numeric_value / 1e9, 3) AS value_bn
    FROM   fact   fa
    JOIN   filing f ON fa.accession_id = f.accession_id
    JOIN   departed d ON fa.entity_id  = d.cik
    WHERE  fa.standard_concept IN ('Revenues', 'NetIncomeLoss')
      AND  f.form_type = '10-K'
      AND  fa.fiscal_period = 'FY'
    QUALIFY row_number() OVER (
        PARTITION BY fa.fiscal_year, fa.standard_concept
        ORDER BY fa.period_end DESC
    ) = 1
    ORDER  BY fa.fiscal_year DESC, fa.standard_concept
    LIMIT  20
""")
if not df.empty:
    company = df["name"].iloc[0]
    print(f"  Company: {company}")
    print(df[["fiscal_year", "standard_concept", "value_bn"]].to_string(index=False))
else:
    # Fallback: any inactive entity with facts
    df = client.query("""
        WITH target AS (
            SELECT e.cik, e.name
            FROM   entity e
            WHERE  e.status != 'ACTIVE'
              AND  e.sector IS NOT NULL
            LIMIT  1
        )
        SELECT
            t.name,
            fa.fiscal_year,
            fa.standard_concept,
            round(fa.numeric_value / 1e9, 3) AS value_bn
        FROM   fact   fa
        JOIN   filing f ON fa.accession_id = f.accession_id
        JOIN   target t ON fa.entity_id    = t.cik
        WHERE  fa.standard_concept IN ('Revenues', 'NetIncomeLoss')
          AND  f.form_type = '10-K'
          AND  fa.fiscal_period = 'FY'
        QUALIFY row_number() OVER (
            PARTITION BY fa.fiscal_year, fa.standard_concept
            ORDER BY fa.period_end DESC
        ) = 1
        ORDER  BY fa.fiscal_year DESC, fa.standard_concept
        LIMIT  20
    """)
    if not df.empty:
        company = df["name"].iloc[0]
        print(f"  Company: {company}")
        print(df[["fiscal_year", "standard_concept", "value_bn"]].to_string(index=False))
    else:
        print("  (No inactive companies with fact data in this plan tier)")
print()

# ── 4. Why it matters (Refined Logic) ─────────────────────────────────────────
print("=" * 60)
# 1. Total Universe Stats
total_stats = client.query("""
    SELECT 
        count(*) as total,
        count(*) FILTER (WHERE status != 'ACTIVE') as inactive
    FROM entity
""").iloc[0]

# 2. Index Exit Stats - Distinguished by Status
exit_stats = client.query("""
    SELECT 
        e.status,
        count(DISTINCT s.entity_id) AS n
    FROM index_membership im
    JOIN security s ON s.id = im.security_id
    JOIN entity e ON e.cik = s.entity_id
    WHERE im.index_name = 'S&P 500' 
      AND im.end_date IS NOT NULL
    GROUP BY e.status
""")

# Parse numbers for the summary
total_count = total_stats["total"]
dead_count = total_stats["inactive"]
pct_dead = round(100.0 * dead_count / total_count, 1)

departed_active = exit_stats[exit_stats["status"] == "ACTIVE"]["n"].sum()
departed_inactive = exit_stats[exit_stats["status"] != "ACTIVE"]["n"].sum()
total_departed = departed_active + departed_inactive

print("  DATASET OVERVIEW:")
print(f"  - Total Entities: {total_count:,}")
print(f"  - Truly Inactive/Dead: {dead_count:,} ({pct_dead}%)")
print("\n  S&P 500 SURVIVORSHIP:")
print(f"  - {total_departed:,} companies left the S&P 500 index.")
print(f"    └─ {departed_active:,} are still trading (likely demoted to MidCap/SmallCap).")
print(f"    └─ {departed_inactive:,} are the true 'Survivorship Bias' cases (delisted/bankrupt).")
print("\n  A backtest that ignores the 'Inactive' subset is fundamentally flawed,")
print("  as it ignores the 100% losses that occur when a company ceases to exist.")
print("=" * 60)
