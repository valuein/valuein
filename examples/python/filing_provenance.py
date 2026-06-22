"""Valuein US Core Fundamentals — Filing Provenance Links

Every number Valuein serves traces back to an SEC filing. This script turns a
ticker into click-through SEC EDGAR links so you (or an auditor, or your agent's
human) can open the exact source filing in a browser and verify a figure.

`client.filing_links()` returns three links per filing, strongest provenance
first:

  • inline_viewer_url — the SEC Inline-XBRL viewer opened on the rendered
    primary document; every tagged number is highlighted in-page. `None` when
    the filing is not Inline-XBRL (older filings) — the /ix? overlay only
    renders for iXBRL.
  • viewer_url        — the cgi-bin Financial-Report viewer; any XBRL filing.
  • sec_url           — the EDGAR filing-index page; always exists.

Prefer inline_viewer_url → viewer_url → sec_url.

Run (no token required — falls back to the SAMPLE tier automatically):
    pip install valuein-sdk      # or: uv pip install valuein-sdk
    python examples/python/filing_provenance.py

Add a token only when you need full universe / full history:
    export VALUEIN_API_KEY="your_token_here"
"""

from valuein_sdk import ValueinClient

# ── Connect (no financial tables needed — filing_links streams the filing table)
client = ValueinClient(tables=["references", "filing"])

# ── Pull the last few annual filings for a company ────────────────────────────
df = client.filing_links("AAPL", form_types=["10-K"], limit=3)

print(f"{len(df)} filing(s) for AAPL:\n")
for _, row in df.iterrows():
    # The link your UI should use — strongest provenance with graceful fallback.
    best = row["inline_viewer_url"] or row["viewer_url"] or row["sec_url"]
    print(f"  {row['form_type']}  filed {row['filing_date']}  ({row['accession_id']})")
    print(f"    → {best}")
    print()

# ── Why inline_viewer_url is sometimes None ───────────────────────────────────
# Inline-XBRL (iXBRL) became standard for 10-K/10-Q around 2019. For older
# filings the column is None and the code above falls back to viewer_url /
# sec_url — both always resolve.
print("Columns:", ", ".join(df.columns))
