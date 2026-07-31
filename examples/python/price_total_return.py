"""Valuein US Core Fundamentals — Prices and Total Return

Two traps live in this table, and both are silent.

TRAP 1 — the grain of `stock_price_daily` is (security, day), NOT (company, day).
A CIK is an *issuer*. DTE Energy files one set of financials but has five listed
securities (common plus four baby bonds). Partition price data on `entity_id`
alone and you are alternating between unrelated price series for roughly 6% of
issuers. The discriminator is `security_id` — never `symbol`, never `entity_id`.
Use `is_primary_listing` when you want the common stock.

TRAP 2 — do not recompound total return by hand. `total_return_index` is
prepopulated and dividend/split adjusted. Rebuilding it from `close`, `div_cash`
and `split_factor` is how people quietly drop a dividend.

What you'll learn:
- How to detect multi-security issuers before they corrupt a backtest
- How to compute price return vs total return correctly
- How much of long-run equity return is dividends (spoiler: for KO, a lot)

Run:
    # Install (either workflow):  pip install valuein-sdk   |   uv pip install valuein-sdk
    # Token is OPTIONAL — without it, the SDK runs in SAMPLE mode (S&P 500, last 5 years).
    # only when you want full universe / full history
    export VALUEIN_API_KEY="your_token_here"
    python examples/python/price_total_return.py
"""

from valuein_sdk import ValueinClient

client = ValueinClient(tables=["references", "stock_price_daily"])

# ── 1. Find the issuers that will break a naive entity_id partition ───────────
print("Issuers in this snapshot with three or more listed securities:")
print(
    client.run_query("""
    SELECT entity_id, count(DISTINCT security_id) AS securities,
           string_agg(DISTINCT symbol, ', ' ORDER BY symbol) AS symbols
    FROM stock_price_daily
    GROUP BY entity_id HAVING count(DISTINCT security_id) > 2
    ORDER BY securities DESC, entity_id
""").to_string(index=False)
)

# ── 2. Price return vs total return, partitioned on security_id ───────────────
print(
    "\nTotal return by SECURITY (dividends + splits already inside total_return_index):"
)
print(
    client.run_query("""
    WITH bounds AS (
        SELECT security_id, symbol,
               first_value(total_return_index) OVER w AS tri_start,
               last_value(total_return_index)  OVER w AS tri_end,
               first_value(close) OVER w              AS px_start,
               last_value(close)  OVER w              AS px_end
        FROM stock_price_daily
        WHERE symbol IN ('AAPL','MSFT','KO') AND price_date >= DATE '2023-01-01'
        WINDOW w AS (PARTITION BY security_id ORDER BY price_date
                     ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
    )
    SELECT DISTINCT symbol, security_id,
           round((px_end / px_start - 1) * 100, 1)   AS price_return_pct,
           round((tri_end / tri_start - 1) * 100, 1) AS total_return_pct
    FROM bounds ORDER BY total_return_pct DESC
""").to_string(index=False)
)

print("\nThe gap between the two columns is the dividend. Drop it and you have")
print("understated the return on every income-paying stock you hold.")
