"""Prices and total return: why returns come from total_return_index, never raw close.

What it does: shows NVIDIA's 10-for-1 split in June 2024 breaking a return computed from raw
`close` while `total_return_index` stays correct, then shows how much of five dividend payers'
return was the dividend. On Pro and Institutional it also calls the daily-bar helpers.
Who it is for: anyone computing returns, from a single chart to a backtest.
Plan: none for the month-end examples (free sample tier, table `stock_price`). The daily
helpers (`client.prices`, `client.total_return`) need `stock_price_daily`, included with Pro
and Institutional; on other plans the script says so instead of calling them.
SDK methods: ValueinClient.run_query, ValueinClient.prices, ValueinClient.total_return.
Tables: stock_price (all plans), stock_price_daily (Pro, Institutional).
Notebook: examples/notebooks/05_prices_and_total_return.ipynb

Run:
    pip install valuein-sdk
    python examples/python/price_total_return.py
"""

from __future__ import annotations

import pandas as pd

from valuein_sdk import ValueinClient

DIVIDEND_PAYERS = ["KO", "PG", "PEP", "JNJ", "VZ"]


def month_end_bars(client: ValueinClient, symbols: list[str]) -> pd.DataFrame:
    """Month-end close and total-return index for the given symbols."""
    names = ", ".join(f"'{s}'" for s in symbols)
    return client.run_query(f"""
        SELECT symbol, price_date, close, total_return_index
        FROM stock_price
        WHERE observation = 'monthly' AND symbol IN ({names})
        ORDER BY symbol, price_date
    """)


def main() -> None:
    """Print the split example, the dividend table and, if available, the daily helpers."""
    with ValueinClient() as client:
        bars = month_end_bars(client, ["NVDA", *DIVIDEND_PAYERS])
        bars["price_date"] = pd.to_datetime(bars["price_date"])

        nvda = bars[
            (bars["symbol"] == "NVDA") & bars["price_date"].between("2024-04-01", "2024-07-31")
        ].copy()
        nvda["return_from_close"] = nvda["close"].pct_change()
        nvda["return_from_tri"] = nvda["total_return_index"].pct_change()
        print("NVIDIA around its June 2024 10-for-1 split (month-end bars):")
        print(nvda.drop(columns="symbol").round(3).to_string(index=False))

        payers = bars[bars["symbol"].isin(DIVIDEND_PAYERS)]
        first, last = payers.groupby("symbol").first(), payers.groupby("symbol").last()
        table = pd.DataFrame(
            {
                "from": first["price_date"].dt.date,
                "to": last["price_date"].dt.date,
                "price_return": last["close"] / first["close"] - 1,
                "total_return": last["total_return_index"] / first["total_return_index"] - 1,
            }
        )
        table["from_dividends"] = table["total_return"] - table["price_return"]
        print("\nPrice return vs total return (never add div_cash on top of the index):")
        print(table.round(3).to_string())

        if "stock_price_daily" in client.tables():
            daily = client.prices("NVDA").between("2024-06-01", "2024-06-30").to_pandas()
            print("\nDaily bars:\n", daily.head().to_string(index=False))
            year = client.total_return("NVDA", "2024-01-01", "2024-12-31")
            print(f"NVDA 2024 total return: {year:+.1%}")
        else:
            print(
                f"\nPlan '{client.plan}' has no daily bars; with Pro or Institutional run "
                "client.prices('NVDA').between(...).to_pandas() and client.total_return(...)."
            )


if __name__ == "__main__":
    main()
