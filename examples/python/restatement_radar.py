"""Restatement Radar: every number a later SEC filing changed, and how it was disclosed.

What it does: shows how revisions reach the public (the three disclosure classes), pulls one
revision with both filings and prints the sec.gov links to verify it, then lists recent material
revisions announced with an 8-K Item 4.02.
- non_reliance: the company filed an 8-K Item 4.02 (read from the 8-K, never inferred).
- amended: the new value arrived in a 10-K/A or 10-Q/A.
- undisclosed: the value changed inside a routine 10-K or 10-Q, with no 4.02 and no amendment.
The class describes disclosure mechanics only, not intent.
Who it is for: forensic analysts, auditors, quants studying revisions.
Plan: none. The feed is available on every plan, including the free sample with no API key.
SDK methods: ValueinClient.restatements, ValueinClient.run_query.
Tables: restatement_events.
Notebook: examples/notebooks/06_restatements.ipynb

Run:
    pip install "valuein-sdk>=7.0.0"
    python examples/python/restatement_radar.py
"""

from __future__ import annotations

import pandas as pd

from valuein_sdk import ValueinClient


def sec_folder(cik: str, accession: str) -> str:
    """URL of the EDGAR folder holding every document of one filing."""
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"


def main() -> None:
    """Print the class mix, one verified revision and recent material non-reliance events."""
    with ValueinClient() as client:
        mix = client.run_query("""
            SELECT disclosure_class, count(*) AS revisions, count(DISTINCT cik) AS companies
            FROM restatement_events GROUP BY disclosure_class ORDER BY revisions DESC
        """)
        print("How revisions reach the public:")
        print(mix.to_string(index=False))

        mpwr = client.restatements(ticker="MPWR", limit=500)
        event = mpwr[
            (mpwr["standard_concept"] == "NetIncome")
            & (mpwr["period_end"] == pd.Timestamp("2024-12-31"))
        ].iloc[0]
        print(f"\nMPWR net income, fiscal 2024 ({event['disclosure_class']}):")
        print(
            f"  as first filed: {event['first_value'] / 1e9:.4f} bn  "
            f"{sec_folder(event['cik'], event['first_accession'])}"
        )
        print(
            f"  as restated   : {event['current_value'] / 1e9:.4f} bn  "
            f"{sec_folder(event['cik'], event['current_accession'])}"
        )
        print(f"  change        : {event['delta_pct']:+.1%}  (delta_pct is a fraction)")

        events = client.restatements(disclosure_class="non_reliance", limit=20000)

    # Bound the size: a few rows are scale artifacts (thousands vs units) near -100%.
    material = events[
        events["standard_concept"].isin(["NetIncome", "TotalRevenue", "OperatingIncome"])
        & (events["unit"] == "USD")
        & events["delta_pct"].abs().between(0.10, 0.90)
        & (events["last_filed_at"] >= pd.Timestamp("2023-01-01", tz="UTC"))
    ]
    print(f"\nMaterial Item 4.02 revisions filed since 2023: {len(material)}")
    columns = [
        "ticker",
        "standard_concept",
        "period_end",
        "first_value",
        "current_value",
        "delta_pct",
        "last_filed_at",
    ]
    print(material[columns].head(10).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
