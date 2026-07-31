"""Valuein US Core Fundamentals — Restatement Radar

Every fact a later SEC filing materially changed, as a before/after diff with
both filings attached.

The headline is not "companies restate" — everyone knows that. It is *how* the
change reaches the public:

  - `non_reliance` — the company filed an 8-K Item 4.02 formally telling the SEC
                     not to rely on previously issued financials. Announced.
  - `amended`      — the number changed in a 10-K/A or 10-Q/A. Flagged.
  - `undisclosed`  — the number changed inside a *routine* 10-Q or 10-K. No 4.02,
                     no amendment. Nothing announced it.

That third bucket is the product. Databases built by parsing 8-Ks can only ever
see what companies announced; finding the rest requires having kept every vintage
of every fact. `undisclosed` is a claim about DISCLOSURE, never about wrongdoing —
ASC 606/842 adoptions restate comparatives with nobody at fault.

What you'll learn:
- The real disclosure mix across the sample universe
- How to pull a before/after diff with both accession numbers
- How to turn an accession into an SEC.gov URL and check us in 30 seconds

Run:
    # Install (either workflow):  pip install valuein-sdk   |   uv pip install valuein-sdk
    # Token is OPTIONAL — without it, the SDK runs in SAMPLE mode (S&P 500, last 5 years).
    # only when you want full universe / full history
    export VALUEIN_API_KEY="your_token_here"
    python examples/python/restatement_radar.py
"""

from valuein_sdk import ValueinClient

client = ValueinClient(tables=["restatement_events"])

# ── 1. How do revisions actually reach the public? ────────────────────────────
print("How revisions actually reach the public:")
print(
    client.run_query("""
    SELECT disclosure_class, count(*) AS revisions,
           round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct
    FROM restatement_events
    GROUP BY disclosure_class ORDER BY revisions DESC
""").to_string(index=False)
)

# ── 2. A single revision, with both filings ───────────────────────────────────
# MPWR's FY2024 net income, restated under an Item 4.02 non-reliance notice.
print("\nThe MPWR revision, with both filings for one-click verification:")
print(
    client.run_query("""
    SELECT ticker, standard_concept, fiscal_period, period_end,
           first_value / 1e9  AS as_first_filed_bn,
           current_value / 1e9 AS current_bn,
           round(delta_pct * 100, 2) AS delta_pct,
           disclosure_class, first_accession, current_accession
    FROM restatement_events
    WHERE ticker = 'MPWR' AND standard_concept = 'NetIncome'
      AND period_end = DATE '2024-12-31'
""").to_string(index=False)
)

# ── 3. Verify us against the source, without asking us anything ───────────────
# Accession 0001437749-25-005903 -> strip the dashes for the EDGAR path.
CIK = "1280452"
for accession in ("0001437749-25-005903", "0001437749-26-014084"):
    plain = accession.replace("-", "")
    print(f"  {accession} -> https://www.sec.gov/Archives/edgar/data/{CIK}/{plain}/")

# ── 4. The company-level claim ────────────────────────────────────────────────
# Most numbers that change, change quietly. This is a statement about
# DISCLOSURE, not about wrongdoing.
print("\nHow many companies revise, and how many ever announce it:")
print(
    client.run_query("""
    SELECT count(DISTINCT cik) AS companies_with_a_revision,
           count(DISTINCT CASE WHEN disclosure_class = 'non_reliance' THEN cik END)
               AS companies_that_ever_filed_a_402,
           count(DISTINCT CASE WHEN disclosure_class = 'undisclosed' THEN cik END)
               AS companies_with_an_undisclosed_revision
    FROM restatement_events
""").to_string(index=False)
)

# ── 5. Largest undisclosed revisions to headline earnings ─────────────────────
# NOTE the magnitude guard. A small number of rows in this table are unit/scale
# artifacts rather than economic restatements — the same figure re-tagged at a
# different scale shows up as a ~99.9% "change". Bounding |delta_pct| below 0.6
# and pinning `unit` keeps those out of an analyst-facing list.
print("\nLargest undisclosed NetIncome revisions (changed inside a routine filing):")
print(
    client.run_query("""
    SELECT ticker, fiscal_period, period_end,
           first_value / 1e9 AS as_first_filed_bn,
           current_value / 1e9 AS current_bn,
           round(delta_pct * 100, 1) AS delta_pct
    FROM restatement_events
    WHERE disclosure_class = 'undisclosed'
      AND standard_concept = 'NetIncome'
      AND unit = 'USD'
      AND abs(delta_pct) BETWEEN 0.05 AND 0.60
    ORDER BY abs(delta_abs) DESC LIMIT 10
""").to_string(index=False)
)
