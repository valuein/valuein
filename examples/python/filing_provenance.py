"""Filing provenance: trace a reported number to the SEC filing and document behind it.

What it does: takes a company's latest annual net income, recomputes its `fact_id` (the SHA-256
of entity_id|accession_id|concept|period_end|unit), and prints the links that open the exact
filing on sec.gov, strongest first:
- inline_viewer_url: the SEC Inline XBRL viewer, every tagged number highlighted (iXBRL filings
  only, phased in from 2019; empty for older filings)
- document_url: the primary document itself
- viewer_url: the SEC financial-report viewer (any XBRL filing)
- sec_url: the filing index page (always present)
The fact_id identifies the number (company, filing, concept, period, unit); to check the value,
open the filing.
Who it is for: auditors, compliance reviewers, and anyone citing a number in a report.
Plan: none. Runs on the free sample tier with no API key.
SDK methods: ValueinClient.read_table, ValueinClient.filing_links, compute_fact_id.
Tables: fact, filing, references.
Notebook: examples/notebooks/08_verify_a_number.ipynb

Run:
    pip install "valuein-sdk>=7.0.0"
    python examples/python/filing_provenance.py
"""

from __future__ import annotations

from valuein_sdk import ValueinClient, compute_fact_id

TICKER = "AAPL"
CONCEPT = "NetIncome"


def main() -> None:
    """Print the number, its verified fact_id and the links to its source filing."""
    with ValueinClient() as client:
        facts = client.read_table("fact", tickers=TICKER)  # this company's own partition file
        annual = facts[(facts["standard_concept"] == CONCEPT) & (facts["fiscal_period"] == "FY")]
        row = annual.sort_values(["period_end", "accepted_at", "priority"]).iloc[-1]

        recomputed = compute_fact_id(
            row["entity_id"],
            row["accession_id"],
            row["concept"],
            row["period_end"].date(),
            row["unit"],
        )
        print(
            f"{TICKER} {CONCEPT}, period ended {row['period_end']:%Y-%m-%d}: "
            f"{row['numeric_value']:,.0f} {row['unit']}"
        )
        print(f"  XBRL concept : {row['concept']}")
        accepted = f"{row['accepted_at']:%Y-%m-%d %H:%M %Z}"
        print(f"  filing       : {row['accession_id']} (accepted {accepted})")
        print(f"  fact_id      : {row['fact_id']}")
        print(f"  recomputed   : {'match' if recomputed == row['fact_id'] else 'MISMATCH'}")

        links = client.filing_links(TICKER, form_types=["10-K", "10-Q"], limit=20)
        match = links[links["accession_id"] == row["accession_id"]]
        if match.empty:
            print("  (the filing is outside the 20 most recent 10-K/10-Q filings)")
            return
        link = match.iloc[0]
        best = (
            link["inline_viewer_url"]
            or link["document_url"]
            or link["viewer_url"]
            or link["sec_url"]
        )
        print(f"\nOpen and search for {row['concept']}:\n  {best}")
        print(f"Every document of the filing:\n  {link['sec_url']}")


if __name__ == "__main__":
    main()
