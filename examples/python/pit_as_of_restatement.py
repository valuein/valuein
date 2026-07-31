"""Valuein US Core Fundamentals — Point-in-Time `as_of`: the same query, two answers

The single most important property of this dataset, in 30 lines.

Monolithic Power Systems (MPWR) reported FY2024 net income of $1.7867bn in its
10-K accepted 2025-03-03. A later filing restated that same fiscal year to
$1.592058bn — a $194.6m reduction. The company filed an SEC Item 4.02
"non-reliance" notice, so this is a disclosed restatement, not a reclassification.

Most vendors overwrite the original number. Ask them what MPWR earned in FY2024
and you get $1.592bn — including for a backtest dated mid-2025, when nobody on
earth could have known that. That is look-ahead bias, and it silently flatters
every strategy that touches earnings.

Valuein keeps every vintage of every fact with an `accepted_at` timestamp. Set
`as_of` on the client and the whole DuckDB session is filtered to what was
public at that instant.

What you'll learn:
- How `as_of` rewrites the answer to an identical query
- How to read the specific filing each number came from
- Why a stale earnings number distorts every multiple computed off it

Run:
    # Install (either workflow):  pip install valuein-sdk   |   uv pip install valuein-sdk
    # Token is OPTIONAL — without it, the SDK runs in SAMPLE mode (S&P 500, last 5 years).
    # only when you want full universe / full history
    export VALUEIN_API_KEY="your_token_here"
    python examples/python/pit_as_of_restatement.py
"""

from datetime import datetime, timezone

from valuein_sdk import ValueinClient

# ── The question, held constant ───────────────────────────────────────────────
# Only `as_of` changes between the two runs below. The SQL never moves.
QUESTION = """
    SELECT f.numeric_value / 1e9 AS net_income_bn, f.accession_id, f.accepted_at
    FROM fact f
    JOIN "references" r ON r.cik = f.entity_id
    WHERE r.symbol = 'MPWR'
      AND f.standard_concept = 'NetIncome'
      AND f.period_end = DATE '2024-12-31'
    QUALIFY ROW_NUMBER() OVER (ORDER BY f.accepted_at DESC) = 1
"""

# ── Ask it twice, from two different moments in history ───────────────────────
for label, as_of in [
    ("What an analyst saw on 2025-06-30", datetime(2025, 6, 30, tzinfo=timezone.utc)),
    ("What the same query returns today ", datetime(2026, 7, 31, tzinfo=timezone.utc)),
]:
    # `as_of` must be timezone-aware. It defaults to "now" when omitted.
    client = ValueinClient(tables=["references", "fact"], as_of=as_of)
    row = client.run_query(QUESTION).iloc[0]
    print(
        f"{label}: ${row.net_income_bn:,.3f}bn   "
        f"(filing {row.accession_id}, accepted {row.accepted_at:%Y-%m-%d})"
    )

# ── Why a quant should care ───────────────────────────────────────────────────
orig, restated = 1.786700, 1.592058
print(
    f"\nThe FY2024 number fell by ${orig - restated:.3f}bn ({(restated / orig - 1) * 100:.2f}%)."
)
print(
    f"Every P/E computed off the original overstated earnings by "
    f"{(orig / restated - 1) * 100:.1f}% -- for ~12 months."
)
print("\nA multiple is price / denominator. The price on the day never changes when")
print(
    "the company later restates -- so the distortion is exact and needs no price data."
)
