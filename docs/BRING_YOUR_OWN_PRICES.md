# Bring your own prices

Join the prices you already hold to point-in-time SEC EDGAR filings data. Every multiple shows which part came from a filing and which from your price.

Take the closes from your market-data provider, broker export or internal price database. Valuein joins them to the filing that was public on the price's date and returns market cap, P/E, P/B, P/S, EV/EBITDA, EV/revenue and dividend yield. Each figure carries the `fact_id`s of the filed numbers behind it, plus the price and date you supplied, so the filed part can be traced to its filing and the price part stays visibly yours.

It works on every plan, the free sample included, from the SDK and from the MCP server.

- **SDK** (`valuein-sdk>=1.1.0`): prices you pass to the SDK stay on your machine; they are not sent to Valuein.
- **MCP** (`compute_price_multiples`, `compute_dcf` with `share_price`): prices are used for that call only and are not stored.

Runnable script: [`examples/python/bring_your_own_prices.py`](../examples/python/bring_your_own_prices.py).

## SDK

```bash
pip install "valuein-sdk>=1.1.0"
```

```python
import pandas as pd
from valuein_sdk import ValueinClient

closes = pd.read_parquet("my_closes.parquet")  # your prices

with ValueinClient() as client:  # reads VALUEIN_API_KEY; no key = the free sample
    out = client.price_multiples(closes, metrics=["pe", "market_cap", "ev_ebitda"])
    print(out[["cik", "price_date", "close", "pe", "market_cap", "fundamentals_accepted_at", "warnings"]])
```

`client.price_multiples(prices, metrics=..., lag=None, on_error="flag")`

- `prices`: a pandas, polars or pyarrow object, or a list of `valuein_sdk.models.UserPrice`.
- `metrics`: any of `market_cap`, `pe`, `pb`, `ps`, `ev_ebitda`, `ev_revenue`, `dividend_yield` (all by default).
- `lag`: calendar days to move the look-ahead cut-off earlier (T+n).
- `on_error`: `"flag"` keeps a rejected row with its `error`; `"raise"` raises; `"drop"` omits it.
- Optional keywords for rows that do not carry the value themselves: `currency` (default USD), `adjustment`, `adjusted_through`, `source_label`, `fx_rate`, `reference_date`, `stale_after_days`.

`client.attach_prices(prices)` registers the validated rows as the DuckDB view `user_price`, so you can join your prices to `fact`, `ratio` and the other tables in your own SQL through `client.run_query`. It returns the rejected rows; calling it again replaces the view.

### Input columns

Long rows, one close per company and date:

| Column | Required | Notes |
|---|---|---|
| `cik` or `ticker` | one of them | Prefer the CIK. |
| `price_date` | yes | ISO date. |
| `close` | yes | Above 0, at most 10,000,000, at most 8 decimal places. |
| `currency` | no | ISO 4217. The SDK assumes USD when absent and warns. |
| `adjustment` | no | `raw` (default), `split_adjusted` (needs `adjusted_through`) or `total_return` (refused). |
| `adjusted_through` | with `split_adjusted` | Date the adjustment runs to. |
| `source_label` | no | Your note on where the price came from, at most 64 characters. |
| `as_of` | no | When the price was observed, ISO 8601 with offset. Default: 16:00 New York on `price_date`. |
| `fx_rate` | no | See Currency below. |

A wide frame also works: dates as the index (or a `date` column), one column per ticker or CIK. Wide and long give identical output.

### Output columns

One row per input price: `cik`, `ticker`, `price_date`, `close`, `close_used`, `currency`, `price_basis` (always `"user_supplied"`), `source_label`, `as_of`, `fundamentals_period_end`, `fundamentals_accepted_at`, `fundamentals_accession_id`, `input_fact_ids` (input name to `fact_id`), `split_factor_applied`, `fx_rate`, then the metrics you asked for, `reasons` (why a metric is null), `warnings`, `uncertain_split_values`, `error` and `error_detail`.

## MCP

`compute_price_multiples` is read-only and available on every plan; a guest reads the sample tier's companies.

- `prices`: 1 to 25 rows per call, one per company and date. Each row has `price_date`, `close` and `currency` (all required), `cik` or `ticker`, and optionally `adjustment`, `adjusted_through`, `source_label`, `as_of` and `fx_rate`.
- `as_of_date` (optional, `YYYY-MM-DD`): only filings accepted before the end of that day are used, even when a price is later.

Each price returns `metrics`, `metrics_display`, `metrics_provenance` (every figure's `derived_id`, the filed `fact_id`s behind it and `rests_on: ["user_supplied_price"]`), `metrics_unavailable` (why a figure is null), `warnings` and `price_inputs_echo` (your price exactly as sent, `basis: "user_supplied"`). A bad row is rejected with a named error and never costs the rest of the batch. Cite the `derived_id` the way you cite a `fact_id`; `verify_facts` re-runs it.

`compute_dcf` accepts an optional `share_price` (the same row shape). The result then includes `upside_pct`, the DCF value per share against your price, marked as resting on a user-supplied price.

When an AI agent writes a figure that rests on your price, it states the price and its date beside the figure and calls it user-supplied. A share price is never a Valuein figure.

## The rules

- **Look-ahead is closed.** A price joins only filings accepted before 16:00 America/New_York on its `price_date`, unless you pass `as_of`. `lag` (SDK) or `as_of_date` (MCP) moves the cut-off earlier.
- **Annual basis.** Filed inputs come from the latest annual report (10-K, 20-F or 40-F) known at the cut-off.
- **Splits** come from the `corporate_action` table. Every recorded split effective after the filing's acceptance date and on or before the price date is applied: shares are scaled, per-share figures divided by the factor, and the factor is returned as `split_factor_applied`. An uncertain split is not applied; both values are returned with the warning `split_uncertain`. Check that your price and the filing use the same share basis; a split missing from the corporate-action table is not detected.
- **Tickers resolve on the price's own date.** A recycled ticker cannot attach to the wrong company. A symbol held by two companies on one day is rejected as `ambiguous_ticker`; a symbol nobody held on that date as `unknown_ticker_on_date`. Pass a `cik` where you can: ticker coverage for delisted names is best effort.
- **Multi-class issuers.** A company with more than one listed share class gets no multiple from one class's price: every metric is null with the reason `multi_class_price_needed`. A filer's per-share figures can be stated for a different class than the one you priced.
- **Currency.** `fx_rate` is the units of the filing's reporting currency per 1 unit of the price currency. A price in a different currency than the filing's returns `currency_mismatch` unless you pass your own `fx_rate`; the rate is yours and is labelled as such.
- **Stale prices.** A price more than 5 weekdays (Monday to Friday) before the reference date (today, or your `as_of_date` / `reference_date`) warns `stale_price`. Holidays are ignored.
- **`total_return` closes are refused.** A total-return series is not a price the share traded at, so a multiple on it would be wrong. Send raw or split-adjusted closes.
- **No forward-fill.** A missing price is never filled from an earlier day. In wide form, gaps are listed in `result.attrs["omitted"]` with the reason `missing_price`.
- **Row errors** are named: `invalid_close`, `invalid_price_date`, `future_price_date`, `duplicate_price_row`, `adjusted_through_required`, `total_return_not_allowed`, `ambiguous_ticker`, `unknown_ticker_on_date`.
- A price is always reported with its `price_date`, as the price you supplied.

## Related

- [`SDK_USE_CASES.md`](SDK_USE_CASES.md): the other SDK recipes
- [`METHODOLOGY.md`](METHODOLOGY.md): point-in-time data and restatements
- [`MCP_TOOLS.md`](MCP_TOOLS.md): the MCP tool reference
