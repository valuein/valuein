"""Point-in-time factor backtest: universe, signal, forward returns, quantile backtest.

What it does: rebuilds the S&P 500 at each quarterly signal date (companies that later left are
included), attaches return on equity as it was known on each date, measures the return realized
after the signal, and runs a long/short quintile backtest with trading costs.
- Pro and Institutional (daily bars): client.forward_returns(panel, execution_lag=1) fills at the
  close one trading day after each signal date.
- Free tiers (month-end closes): fills at the first month-end close after the signal date, a
  few trading days later. Same columns, same backtest.
Who it is for: quants evaluating a fundamental signal without look-ahead or survivorship bias.
Plan: none (the free sample runs the month-end version; Pro and above run the daily version).
SDK methods: ValueinClient.universe, ValueinClient.signal_panel, ValueinClient.forward_returns,
valuein_sdk.backtest.
Tables: index_membership, references, ratio, stock_price (or stock_price_daily).
Notebook: examples/notebooks/04_pit_factor_backtest.ipynb

Run:
    pip install "valuein-sdk>=7.0.0"
    python examples/python/factor_backtest.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from valuein_sdk import ValueinClient, backtest

SIGNAL = "return_on_equity"
# Quarterly signal dates. The free sample's fundamentals begin with fiscal 2021, so start in 2022.
SIGNAL_DATES = [f"{y}-{m:02d}-24" for y in range(2022, 2027) for m in (3, 6, 9, 12)]
SIGNAL_DATES = [d for d in SIGNAL_DATES if d <= "2026-06-24"]


def monthly_forward_returns(client: ValueinClient, panel: pd.DataFrame) -> pd.DataFrame:
    """Append forward returns from month-end closes: enter and exit at the first close after
    each signal date; hold a company that stopped trading to its last close (truncated)."""
    bars = client.run_query("""
        SELECT entity_id AS cik, price_date, total_return_index AS tri
        FROM stock_price
        WHERE observation = 'monthly' AND total_return_index IS NOT NULL
        QUALIFY ROW_NUMBER() OVER (PARTITION BY entity_id, price_date ORDER BY security_id) = 1
    """)
    bars["price_date"] = pd.to_datetime(bars["price_date"])
    bars = bars.sort_values("price_date")
    dates = sorted(panel["rebalance_date"].unique())
    schedule = pd.DataFrame({"rebalance_date": dates[:-1], "next_date": dates[1:]})
    out = panel.merge(schedule, on="rebalance_date")
    for key, prefix in [("rebalance_date", "entry"), ("next_date", "exit")]:
        side = bars.rename(columns={"price_date": f"{prefix}_price_date", "tri": f"{prefix}_price"})
        out = pd.merge_asof(
            out.sort_values(key),
            side,
            by="cik",
            left_on=key,
            right_on=f"{prefix}_price_date",
            direction="forward",
            allow_exact_matches=False,
        )
    last = bars.groupby("cik").tail(1).rename(columns={"price_date": "last_date", "tri": "last"})
    out = out.merge(last, on="cik", how="left")
    out["truncated"] = out["exit_price"].isna() & (out["last_date"] > out["entry_price_date"])
    out.loc[out["truncated"], "exit_price"] = out.loc[out["truncated"], "last"]
    out["entry_stale"] = out["entry_price_date"].isna() | (
        (out["entry_price_date"] - out["rebalance_date"]).dt.days > 35
    )
    out["tradable"] = ~out["entry_stale"] & out["exit_price"].notna() & (out["entry_price"] > 0)
    out["forward_return"] = np.where(
        out["tradable"], out["exit_price"] / out["entry_price"] - 1, np.nan
    )
    return out.drop(columns=["next_date", "last_date", "last"]).reset_index(drop=True)


def main() -> None:
    """Run the three steps and the backtest, then print the summary."""
    with ValueinClient() as client:
        # 1. Survivorship-free membership, resolved independently at every signal date.
        universe = client.universe(dates=SIGNAL_DATES)
        # 2. The latest ratio vintage with accepted_at <= each date: no look-ahead.
        panel = client.signal_panel(universe, ratios=[SIGNAL], include_price=False)
        # 3. Returns realized only after the signal.
        if "stock_price_daily" in client.tables():
            with_returns = client.forward_returns(panel, execution_lag=1)
            fills = "next trading day's close (daily bars)"
        else:
            with_returns = monthly_forward_returns(client, panel)
            fills = "first month-end close after the signal (free tier)"
            # Record the fill delay (median weekdays) so the summary prints it with the results.
            filled = with_returns.dropna(subset=["entry_price_date"])
            weekdays = np.busday_count(
                filled["rebalance_date"].values.astype("datetime64[D]"),
                filled["entry_price_date"].values.astype("datetime64[D]"),
            )
            with_returns.attrs["execution_lag"] = int(np.median(weekdays))

    # 4. Quintiles, long the top and short the bottom, 10 bps per unit of notional traded.
    result = backtest(with_returns, signal=SIGNAL, quantiles=5, long_short=True, cost_bps=10.0)
    print(f"plan '{client.plan}', fills at the {fills}\n")
    print(result.summary())


if __name__ == "__main__":
    main()
