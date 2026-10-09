"""Point-in-time, survivorship-free factor dataset, exported to Parquet and CSV.

What it does: rebuilds the S&P 500 as it stood on AS_OF_DATE (members that were later acquired,
delisted or dropped are included), attaches five factor ratios exactly as they were known on that
date (latest vintage with accepted_at <= AS_OF_DATE), ranks them into a direction-aware
composite, and writes pit_factor_dataset.parquet and pit_factor_dataset.csv to the current
directory: the input a portfolio optimizer, a backtester or a model-training job expects.
Who it is for: quants and data engineers who need a research-grade, reproducible factor file.
Plan: none. Runs on the free sample tier with no API key (pick AS_OF_DATE from mid-2022 on,
where the sample's ratios begin). With a free Benchmark key the same code covers 1996 onward.
SDK methods: ValueinClient(as_of=...), ValueinClient.universe, ValueinClient.signal_panel.
Tables: index_membership, references, ratio.
Notebook: examples/notebooks/04_pit_factor_backtest.ipynb

Run:
    pip install "valuein-sdk>=7.0.0" pyarrow
    python examples/python/pit_factor_dataset.py
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from valuein_sdk import ValueinClient

AS_OF_DATE = "2023-06-30"
MIN_FACTORS = 3  # a composite from fewer known factors is not comparable
INDEX = "SP500"
OUT_PARQUET = "pit_factor_dataset.parquet"
OUT_CSV = "pit_factor_dataset.csv"
# ratio_name -> True when a higher value is better.
FACTORS = {
    "return_on_equity": True,  # quality
    "revenue_cagr_1y": True,  # growth
    "fcf_margin": True,  # cash generation
    "debt_to_equity": False,  # leverage: lower is better
    "piotroski_f_score": True,  # fundamental trend, 0 to 9
}


def build_dataset(client: ValueinClient) -> pd.DataFrame:
    """Return one row per index member on AS_OF_DATE with its factors and composite score."""
    members = client.universe(INDEX, dates=[AS_OF_DATE])
    panel = client.signal_panel(members, ratios=list(FACTORS), include_price=False)
    ranks = pd.DataFrame(
        {
            name: panel[name].rank(pct=True, ascending=higher_is_better)
            for name, higher_is_better in FACTORS.items()
        }
    )
    panel["factors_known"] = ranks.notna().sum(axis=1)
    # Mean percentile over the known factors (1.0 = best on each); NaN below MIN_FACTORS.
    panel["composite_score"] = ranks.mean(axis=1).where(panel["factors_known"] >= MIN_FACTORS)
    panel["left_index_later"] = panel["index_removal_date"].notna()
    return panel.sort_values("composite_score", ascending=False).reset_index(drop=True)


def main() -> None:
    """Build, check and export the dataset."""
    cutoff = datetime.strptime(AS_OF_DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    # The client's as_of filters every point-in-time view at the cutoff as well.
    with ValueinClient(as_of=cutoff) as client:
        print(f"plan: {client.plan!r} | point-in-time cutoff: {AS_OF_DATE}")
        dataset = build_dataset(client)
        latest_vintage = client.run_query("SELECT max(accepted_at) AS latest FROM ratio")

    print(
        f"{INDEX} members on {AS_OF_DATE}: {len(dataset)} "
        f"({int(dataset['left_index_later'].sum())} have left the index since)"
    )
    print(f"latest ratio vintage visible to this session: {latest_vintage['latest'].iloc[0]}")
    columns = ["ticker", "name", "sector", *FACTORS, "composite_score"]
    print("\nTop 10 by composite score:")
    print(dataset[columns].head(10).round(3).to_string(index=False))

    dataset.to_parquet(OUT_PARQUET, index=False)
    dataset.to_csv(OUT_CSV, index=False)
    shape = f"{len(dataset)} rows x {len(dataset.columns)} columns"
    print(f"\nwrote {OUT_PARQUET} and {OUT_CSV}: {shape}")


if __name__ == "__main__":
    main()
