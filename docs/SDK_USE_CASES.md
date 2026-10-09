# Valuein SDK: use cases

The common jobs people do with [`valuein-sdk`](https://pypi.org/project/valuein-sdk/), easiest
first. Each one has a minimal snippet and a link to a runnable script and a notebook. The
notebooks are committed with their output, executed on the free sample tier, so the real
results are one click away; the snippets here are taken from them.

Every use case below runs with **no API key** except smart money (Institutional) and daily price
bars (Pro and Institutional), which say so. Without a key the SDK reads the public sample: S&P 500
companies, including the ones that later left the index, for the last five years, with month-end
prices. With `VALUEIN_API_KEY` set, the same code reads your plan's data. Plans:
[valuein.biz/pricing](https://valuein.biz/pricing) (live limits: `GET https://data.valuein.biz/v1/plans`).

| # | Use case | Plan | Script | Notebook |
|---|---|---|---|---|
| 1 | [First data, no API key](#1-first-data-no-api-key) | none | [`getting_started.py`](../examples/python/getting_started.py) | [01](../examples/notebooks/01_quickstart.ipynb) |
| 2 | [Discover tables and columns](#2-discover-tables-and-columns) | none | [`getting_started.py`](../examples/python/getting_started.py) | [01](../examples/notebooks/01_quickstart.ipynb) |
| 3 | [One company's statements](#3-one-companys-statements) | none | [`financial_analysis.py`](../examples/python/financial_analysis.py) | [02](../examples/notebooks/02_fundamentals_as_of_a_date.ipynb) |
| 4 | [What was known on a date](#4-what-was-known-on-a-date) | none | [`pit_backtest.py`](../examples/python/pit_backtest.py) | [02](../examples/notebooks/02_fundamentals_as_of_a_date.ipynb) |
| 5 | [Screen the index as it was](#5-screen-the-index-as-it-was) | none | [`entity_screening.py`](../examples/python/entity_screening.py), [`survivorship_bias.py`](../examples/python/survivorship_bias.py) | [03](../examples/notebooks/03_survivorship_free_screening.ipynb) |
| 6 | [Backtest a factor](#6-backtest-a-factor) | none (daily bars: Pro) | [`factor_backtest.py`](../examples/python/factor_backtest.py), [`pit_factor_dataset.py`](../examples/python/pit_factor_dataset.py) | [04](../examples/notebooks/04_pit_factor_backtest.ipynb) |
| 7 | [Prices and total return](#7-prices-and-total-return) | none (daily bars: Pro) | [`price_total_return.py`](../examples/python/price_total_return.py) | [05](../examples/notebooks/05_prices_and_total_return.ipynb) |
| 8 | [Restatements](#8-restatements) | none | [`restatement_radar.py`](../examples/python/restatement_radar.py) | [06](../examples/notebooks/06_restatements.ipynb) |
| 9 | [Smart money](#9-smart-money) | Institutional | [`smart_money_screen.py`](../examples/python/smart_money_screen.py) | [07](../examples/notebooks/07_smart_money.ipynb) |
| 10 | [Verify a number](#10-verify-a-number) | none | [`filing_provenance.py`](../examples/python/filing_provenance.py) | [08](../examples/notebooks/08_verify_a_number.ipynb) |
| 11 | [From an AI assistant](#11-from-an-ai-assistant) | none | [`agent_buys_its_own_data.py`](../examples/python/agent_buys_its_own_data.py) | [09](../examples/notebooks/09_ai_assistant.ipynb) |
| 12 | [Production extracts](#12-production-extracts) | none | [`production_service.py`](../examples/python/production_service.py) | |

Research workflows (DCF, Piotroski, earnings quality, DuPont by sector, restatement event study,
capital allocation, filing delay) are notebooks 10 to 16; see
[`examples/README.md`](../examples/README.md).

---

## 1. First data, no API key

```python
from valuein_sdk import ValueinClient

with ValueinClient() as client:          # no key: the public sample
    print(client.plan)                   # 'sample'
    print(client.resolve("AAPL"))        # ticker -> CIK, the stable company key
```

Nothing downloads at construction: each table is fetched the first time a query uses it, then
cached on disk.

## 2. Discover tables and columns

```python
client.get_schema("fact")        # {column: type}, from the manifest, no download
client.list_templates()          # ready-made SQL templates
client.capabilities()            # plan, cutoff, tables, methods, research workflow, conventions
```

The tables you will use most: `references` (one row per security: `cik`, `symbol`, `name`,
`sector`, `is_active`), `index_membership`, `filing`, `fact`, `ratio`, `stock_price`,
`restatement_events`. Concept names: [`data_catalog.md`](data_catalog.md).

## 3. One company's statements

```python
cik = client.resolve("MSFT")["cik"].iloc[0]
annual = client.run_query(f"""
    SELECT period_end, standard_concept, numeric_value
    FROM fact
    WHERE entity_id = '{cik}'
      AND standard_concept IN ('TotalRevenue', 'NetIncome')
      AND fiscal_period = 'FY' AND period_span_days BETWEEN 350 AND 380
    QUALIFY ROW_NUMBER() OVER (PARTITION BY standard_concept, period_end ORDER BY accepted_at DESC, priority DESC) = 1
""")
```

A 10-K repeats prior years and later filings revise them, so keep one vintage per `period_end`.
For quarterly cash flows use `COALESCE(derived_quarterly_value, numeric_value)`: 10-Q cash flows
are year to date.

## 4. What was known on a date

```python
from datetime import datetime, timezone

with ValueinClient(as_of=datetime(2025, 6, 30, tzinfo=timezone.utc)) as past:
    past.run_query(...)          # every point-in-time table filtered to accepted_at <= as_of
```

The same query returns the restated value today and the original value as of the past date
(the notebook shows a real Item 4.02 restatement). Gate on `accepted_at`, never `period_end`.

## 5. Screen the index as it was

```python
members = client.universe(dates=["2022-06-30"])          # includes later-removed members
panel = client.signal_panel(members, ratios=["return_on_equity", "debt_to_equity"],
                            include_price=False)          # values known on that date
```

`client.pit_universe("2022-06-30")` returns the same membership with the ticker each company
used on that date. Notebook 03 measures the survivorship bias of a survivor-only universe.

## 6. Backtest a factor

```python
from valuein_sdk import backtest

panel = client.signal_panel(client.universe(dates=dates), ratios=["return_on_equity"],
                            include_price=False)
panel = client.forward_returns(panel, execution_lag=1)   # daily bars: Pro and Institutional
result = backtest(panel, signal="return_on_equity", quantiles=5, cost_bps=10.0)
print(result.summary())
```

On Pro and Institutional, `client.factor_backtest("return_on_equity", start=..., end=...,
freq="QE")` runs all steps in one call. On the free tiers the script and notebook build forward
returns from month-end closes instead; the backtest is the same.

## 7. Prices and total return

```python
client.stock_price("AAPL")                    # latest close known at as_of
client.run_query("""SELECT symbol, price_date, close, total_return_index
                    FROM stock_price WHERE observation = 'monthly' AND symbol = 'NVDA'""")
client.total_return("NVDA", "2024-01-01", "2024-12-31")   # daily bars: Pro and Institutional
```

Compute returns from `total_return_index` (splits and dividends included), never from `close`,
and never add `div_cash` on top. A company with two share classes has two price series.

## 8. Restatements

```python
client.restatements(ticker="MPWR")
client.restatements(disclosure_class="non_reliance", limit=1000)
```

One row per number a later filing changed, with both values and both accessions.
`disclosure_class` is `non_reliance` (8-K Item 4.02), `amended` (10-K/A, 10-Q/A) or
`undisclosed` (changed inside a routine filing); it describes disclosure mechanics, not intent.
`delta_pct` is a fraction (`-0.10` = -10%).

## 9. Smart money

```python
from valuein_sdk import ValueinPlanError

try:
    client.insider_transactions("NVDA", transaction_codes=["P", "S"])
    client.institutional_holdings(issuer="NVDA")
    client.advisers(name_contains="bridgewater")
except ValueinPlanError as exc:
    print(exc)        # raised before any request on plans other than Institutional
```

Insider and 13F rows are filtered by `accepted_at`. Form ADV advisers are keyed by CRD, not CIK,
and `raum_total` must not be summed across firms.

## 10. Verify a number

```python
from valuein_sdk import compute_fact_id

compute_fact_id(entity_id, accession_id, concept, period_end, unit) == fact_id   # True
client.filing_links("AAPL", form_types=["10-K"])   # Inline XBRL viewer and document links
```

`fact_id` identifies the number (company, filing, concept, period, unit); open the filing to
check the value. `client.report_issue(...)` reports a number you believe is wrong.

## 11. From an AI assistant

Register `https://mcp.valuein.biz/mcp` as an MCP server with your key as a Bearer token
([`MCP_TOOLS.md`](MCP_TOOLS.md)), or let a coding agent use the SDK: `client.capabilities()`
describes the surface, and every error is a `ValueinError` whose message says how to fix the
call. Notebook 09 shows a tool function that returns each value with its `fact_id` and filing.

## 12. Production extracts

`production_service.py` shows a scheduled job: resource limits with `ValueinConfig`, a fixed
`as_of` so re-runs reproduce the same data, typed errors mapped to exit codes, Parquet output
with a manifest of the plan and snapshot read.

---

## See also

- [`QUERY_COOKBOOK.md`](QUERY_COOKBOOK.md): DuckDB recipes and anti-patterns
- [`METHODOLOGY.md`](METHODOLOGY.md): how point-in-time data, restatements and XBRL
  normalization work
- [`accuracy/`](accuracy/): the measured accuracy baseline
