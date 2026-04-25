"""Valuein US Core Fundamentals — SDK Reference

Comprehensive walkthrough of every SDK method. Run this after
getting_started.py to see the full API surface.

Run:
    export VALUEIN_API_KEY="your_token_here"
    python examples/usage.py
"""

from valuein_sdk import ValueinClient

# ── a) Authentication & health check ─────────────────────────────────────────
print("=" * 60)
print("a) Authentication")
print("=" * 60)
client = ValueinClient(tables=[])
me = client.me()
manifest = client.manifest()
print(f"  Email    : {me.get('email', 'N/A')}")
print(f"  Plan     : {me.get('plan')}")
print(f"  Status   : {me.get('status')}")
print(f"  Snapshot : {manifest.get('snapshot')}")
print(f"  Updated  : {manifest.get('last_updated', 'N/A')}")
print()

# ── b) Loading specific tables ────────────────────────────────────────────────
print("=" * 60)
print("b) Loading specific tables")
print("=" * 60)
client = ValueinClient(tables=["entity", "security", "filing"])
print(f"  Loaded: {client.tables()}")
print()

# ── c) client.me() / client.manifest() / client.tables() ─────────────────────
print("=" * 60)
print("c) Introspection methods")
print("=" * 60)
print(f"  client.me()       → {client.me()}")
print(f"  client.tables()   → {client.tables()}")
print(f"  client.manifest() → {client.manifest()}")
print()

# ── d) client.query() — three examples ───────────────────────────────────────
print("=" * 60)
print("d) client.query() — Simple: entity status counts")
print("=" * 60)
df = client.query("""
    SELECT status, count(*) AS companies
    FROM   entity
    GROUP  BY status
    ORDER  BY companies DESC
""")
print(df.to_string(index=False))
print()

print("=" * 60)
print("d) client.query() — Join: top 10 companies by filing count")
print("=" * 60)
df = client.query("""
    SELECT e.name, e.sector, count(f.accession_id) AS filings
    FROM   entity   e
    JOIN   security s ON s.entity_id = e.cik AND s.is_active = TRUE
    JOIN   filing   f ON f.entity_id = e.cik
    GROUP  BY e.name, e.sector
    ORDER  BY filings DESC
    LIMIT  10
""")
print(df.to_string(index=False))
print()

print("=" * 60)
print("d) client.query() — Filter: NVDA 10-K filings")
print("=" * 60)
df = client.query("""
    SELECT f.form_type, f.filing_date, f.report_date, f.accession_id
    FROM   filing   f
    JOIN   security s ON f.entity_id = s.entity_id
    WHERE  s.symbol    = 'NVDA'
      AND  s.is_active = TRUE
      AND  f.form_type = '10-K'
    ORDER  BY f.filing_date DESC
    LIMIT  5
""")
print(df.to_string(index=False))
print()

# ── e) client.get() — data dictionary ────────────────────────────────────────
print("=" * 60)
print("e) client.get('taxonomy_guide') — data dictionary sample")
print("=" * 60)
client_full = ValueinClient(tables=["taxonomy_guide"])
tg = client_full.get("taxonomy_guide")
print(
    tg[["standard_concept", "human_name", "unit_type"]].head(10).to_string(index=False)
)
print()

# ── f) client.run_template() ──────────────────────────────────────────────────
print("=" * 60)
print("f) client.run_template() — named SQL template")
print("=" * 60)
try:
    client_t = ValueinClient(tables=["entity", "security", "filing", "fact"])
    df = client_t.run_template(
        "fundamentals_by_ticker",
        ticker="AAPL",
        form_types=["10-K"],
        start_date="2020-01-01",
        end_date="2024-12-31",
        metrics=["Revenues", "NetIncomeLoss"],
    )
    print(df.head(10).to_string(index=False))
except FileNotFoundError as e:
    print(f"  (template not found — {e})")
print()

print("=" * 60)
print("You've used every SDK method.")
print("See examples/notebooks/ for advanced workflows.")
print("=" * 60)
