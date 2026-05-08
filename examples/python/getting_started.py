"""Valuein US Core Fundamentals — Getting Started

The first script every new user should run. Confirms your token works,
loads two lightweight tables, and shows you how to look up a company
by ticker. Completes in under 30 seconds.

Run (no token required — falls back to the SAMPLE tier automatically):
    pip install valuein-sdk      # or: uv pip install valuein-sdk
    python examples/python/getting_started.py

Add a token only when you need full universe / full history:
    export VALUEIN_API_KEY="your_token_here"
"""

from valuein_sdk import ValueinClient

# ── Step 1: Connect and verify ────────────────────────────────────────────────
# tables=[] skips all data downloads — instant auth check.
print("Connecting to Valuein gateway...")
client = ValueinClient(tables=[])

me = client.me()
snap = client.manifest().get("snapshot", "unknown")
print(f"  Plan     : {me.get('plan', 'unknown')}")
print(f"  Status   : {me.get('status', 'unknown')}")
print()

# ── Step 2: Load entity + security (lightweight, no financials) ───────────────
print("Loading entity and security tables...")
client = ValueinClient(tables=["entity", "security"])

counts = client.run_query("""
    SELECT
        (SELECT count(*) FROM entity)   AS entities,
        (SELECT count(*) FROM security) AS securities
""")
print(f"  Entities  : {counts['entities'].iloc[0]:,}")
print(f"  Securities: {counts['securities'].iloc[0]:,}")
print()

# ── Step 3: Look up a company by ticker ───────────────────────────────────────
print("Looking up AAPL...")
df = client.run_query("""
    SELECT
        e.cik,
        e.name,
        e.sector,
        e.industry,
        e.status,
        s.symbol,
        s.exchange
    FROM security s
    JOIN entity   e ON s.entity_id = e.cik
    WHERE s.symbol    = 'AAPL'
      AND s.is_active = TRUE
    LIMIT 1
""")
print(df.to_string(index=False))
print()

print("Setup complete. You're ready to query US Core Fundamentals.")
print("Next step → python examples/usage.py")
