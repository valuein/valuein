"""Survivorship bias, measured: today's index members vs the index as it really was.

What it does: takes every S&P 500 member on a start date, computes each company's total return
to the latest month-end (holding companies that stopped trading to their last close), and
compares the equal-weight return of the honest universe with that of today's survivors only.
The gap is the survivorship bias of the window.
Who it is for: anyone backtesting on an index; risk and research leads reviewing backtests.
Plan: none. Runs on the free sample tier with no API key (month-end prices).
SDK methods: ValueinClient.pit_universe, ValueinClient.run_query.
Tables: index_membership, references, stock_price.
Notebook: examples/notebooks/03_survivorship_free_screening.ipynb

Run:
    pip install "valuein-sdk>=7.0.0"
    python examples/python/survivorship_bias.py
"""

from __future__ import annotations

import pandas as pd

from valuein_sdk import ValueinClient

START = "2022-06-30"


def member_returns(client: ValueinClient, start: str) -> pd.DataFrame:
    """Return one row per member on `start` with its total return to its last month-end close."""
    members = client.pit_universe(start)[["cik", "company_name", "removal_date"]]
    members = members.drop_duplicates("cik")
    prices = client.run_query(f"""
        WITH bars AS (
            SELECT entity_id, price_date, total_return_index AS tri
            FROM stock_price
            WHERE observation = 'monthly'
            -- two share classes are two series under one CIK: keep one per month
            QUALIFY ROW_NUMBER() OVER (PARTITION BY entity_id, price_date ORDER BY security_id) = 1
        )
        SELECT entity_id AS cik,
               arg_max(tri, price_date) FILTER (WHERE price_date <= DATE '{start}') AS tri_start,
               arg_max(tri, price_date) AS tri_end,
               max(price_date) AS last_bar
        FROM bars GROUP BY entity_id
    """)
    out = members.merge(prices, on="cik", how="left")
    out["total_return"] = out["tri_end"] / out["tri_start"] - 1
    out["still_member"] = out["removal_date"].isna()
    return out


def main() -> None:
    """Print the honest, survivor-only and departed-only equal-weight returns."""
    with ValueinClient() as client:
        returns = member_returns(client, START)

    priced = returns.dropna(subset=["total_return"])
    honest = priced["total_return"].mean()
    survivors = priced.loc[priced["still_member"], "total_return"].mean()
    departed = priced.loc[~priced["still_member"], "total_return"].mean()

    print(f"S&P 500 members on {START}: {len(returns)}; with prices at both ends: {len(priced)}")
    print(f"left the index since: {int((~returns['still_member']).sum())}")
    print(f"\nEqual-weight total return from {START} to each company's last month-end close:")
    print(f"  all members on {START} (honest) : {honest:+.1%}")
    print(f"  today's survivors only            : {survivors:+.1%}")
    print(f"  companies that left               : {departed:+.1%}")
    print(f"\nSurvivor-only minus honest: {(survivors - honest) * 100:+.1f} percentage points")

    worst = priced.loc[~priced["still_member"]].nsmallest(5, "total_return")
    print("\nWeakest departed members (what a survivor-only universe never sees):")
    print(
        worst[["company_name", "removal_date", "last_bar", "total_return"]]
        .round(3)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
