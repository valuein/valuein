"""Survivorship-free screening: screen the S&P 500 as it stood on a past date.

What it does: rebuilds S&P 500 membership on a past date (including companies that later left
the index), attaches the ratios that were public on that date, applies a quality screen, and
flags which passing companies are no longer in the index today.
Who it is for: quants and PMs who screen historically; anyone tempted to use today's index list.
Plan: none. Runs on the free sample tier (S&P 500 members, last five years) with no API key.
Benchmark extends the same universe to 1993; Pro and Institutional cover every SEC filer.
SDK methods: ValueinClient.universe, ValueinClient.signal_panel.
Tables: index_membership, references, ratio.
Notebook: examples/notebooks/03_survivorship_free_screening.ipynb

Run:
    pip install valuein-sdk
    python examples/python/entity_screening.py
"""

from __future__ import annotations

import pandas as pd

from valuein_sdk import ValueinClient

SCREEN_DATE = "2022-06-30"  # the sample's ratios start with fiscal 2021: use mid-2022 or later
RATIOS = ["return_on_equity", "net_margin", "debt_to_equity"]


def screen(panel: pd.DataFrame) -> pd.DataFrame:
    """Keep profitable, moderately levered companies, best return on equity first."""
    passed = panel[
        (panel["return_on_equity"] > 0.20)
        & (panel["net_margin"] > 0.15)
        & panel["debt_to_equity"].between(0, 1.5)
    ].copy()
    passed["left_index_later"] = passed["index_removal_date"].notna()
    return passed.sort_values("return_on_equity", ascending=False)


def main() -> None:
    """Build the universe on SCREEN_DATE, screen it and print the result."""
    with ValueinClient() as client:
        members = client.universe(dates=[SCREEN_DATE])
        # Each value is the latest ratio vintage with accepted_at <= SCREEN_DATE.
        panel = client.signal_panel(members, ratios=RATIOS, include_price=False)

    known = panel["return_on_equity"].notna().sum()
    print(f"S&P 500 members on {SCREEN_DATE}: {len(panel)} ({known} with a known ROE)")
    print(f"members that have left the index since: {panel['index_removal_date'].notna().sum()}")

    result = screen(panel)
    print(
        f"\n{len(result)} companies pass the screen; "
        f"{int(result['left_index_later'].sum())} of them have since left the index"
    )
    columns = ["ticker", "name", "sector", *RATIOS, "left_index_later"]
    print(result[columns].head(20).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
