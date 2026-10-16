# Valuein SDK: use cases

The common jobs people do with [`valuein-sdk`](https://pypi.org/project/valuein-sdk/), easiest
first. Each one has a minimal snippet and, where one exists, a link to a runnable script and a
notebook. The notebooks are committed with their output, executed on the free sample tier, so
the real results are one click away. Use cases 14 to 16, and the newer calls inside the others
(`financials`, `screen`, `restatement_impact`, `study`, `sync`), quote the SDK's own documented
recipes, which its test suite executes.

Every use case below runs with **no API key** except smart money (Institutional) and anything
that reads daily price bars (Pro and Institutional), which say so. Without a key the SDK reads the public sample: S&P 500
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
| 13 | [Value a company](#13-value-a-company) | none | [`dcf_inputs.py`](../examples/python/dcf_inputs.py) | [10](../examples/notebooks/10_dcf_valuation.ipynb) |
| 14 | [Count your trials](#14-count-your-trials) | Pro | | |
| 15 | [Snapshots you can pin and mirror](#15-snapshots-you-can-pin-and-mirror) | none | | |
| 16 | [Your own tools: DuckDB, Arrow, Polars, Alphalens](#16-your-own-tools-duckdb-arrow-polars-alphalens) | none (Alphalens: Pro) | | |

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
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY from the environment; no key = free sample

print(client.get_schema("fact"))  # {column: type}, from the manifest, no download
print(client.list_templates())    # ready-made SQL templates
print(client.capabilities())      # plan, cutoff, tables, methods, conventions
```

The tables you will use most: `references` (one row per security: `cik`, `symbol`, `name`,
`sector`, `is_active`), `index_membership`, `filing`, `fact`, `ratio`, `stock_price`,
`restatement_events`. Concept names: [`data_catalog.md`](data_catalog.md).

## 3. One company's statements

```python
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY from the environment; no key = free sample

fin = client.financials("MSFT")                # fiscal years, as known at the client's as_of
print(fin.income)                              # one row per concept, one column per period end
print(fin.balance)
print(fin.cash_flow)
print(fin.lineage.head())                      # per number: fact_id, accession, form, accepted_at
print(fin.as_filed().income)                   # the same periods as first reported
print(client.financials("MSFT", freq="Q").cash_flow)  # standalone quarters ("TTM" = trailing twelve months)
```

Fiscal years key on the period end, so a 10-K's prior-year comparatives are separate columns.
Quarters are standalone: 10-Q year-to-date cash flows are de-cumulated and the fourth quarter
comes out of the 10-K. `fin.lineage` also says when (if ever) a later filing changed each number;
`fin.explain("TotalRevenue", period_end)` lists the facts behind one cell with EDGAR links.

The same numbers from SQL:

```python
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY from the environment; no key = free sample

cik = client.resolve("MSFT")["cik"].iloc[0]  # ticker -> 10-digit CIK
annual = client.run_query(f"""
    SELECT period_end, standard_concept, numeric_value
    FROM fact
    WHERE entity_id = '{cik}'
      AND standard_concept IN ('TotalRevenue', 'NetIncome')
      AND fiscal_period = 'FY' AND period_span_days BETWEEN 350 AND 380
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY standard_concept, period_end ORDER BY accepted_at DESC, priority DESC
    ) = 1
    ORDER BY period_end DESC, standard_concept
""")
print(annual.head(10))
```

A 10-K repeats prior years and later filings revise them, so keep one vintage per `period_end`.
For quarterly cash flows use `COALESCE(derived_quarterly_value, numeric_value)`: 10-Q cash flows
are year to date.

## 4. What was known on a date

```python
from datetime import datetime, timezone

from valuein_sdk import ValueinClient

# as_of must be timezone-aware; every point-in-time table is filtered to accepted_at <= as_of
as_of = datetime(2025, 6, 30, tzinfo=timezone.utc)
with ValueinClient(as_of=as_of) as past:   # reads VALUEIN_API_KEY; no key = free sample
    print(past.run_query("SELECT max(accepted_at) AS latest_filing_seen FROM filing"))
```

The same query returns the restated value today and the original value as of the past date
(the notebook shows a real Item 4.02 restatement). Gate on `accepted_at`, never `period_end`.

## 5. Screen the index as it was

```python
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY from the environment; no key = free sample

members = client.universe(dates=["2022-06-30"])  # includes later-removed members
panel = client.signal_panel(
    members,
    ratios=["return_on_equity", "debt_to_equity"],
    include_price=False,                         # values known on that date
)
print(panel.head())
print(client.pit_universe("2022-06-30").head())  # same membership, ticker used on that date
```

`client.pit_universe("2022-06-30")` returns the same membership with the ticker each company
used on that date. Notebook 03 measures the survivorship bias of a survivor-only universe.

`client.screen` does the same as a point-in-time screen builder:

```python
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY from the environment; no key = free sample

screen = client.screen("2024-06-28", universe="SP500").where("return_on_equity > 0.15")
result = screen.rank("gpoa", within="sector").top(5).to_pandas()
print(result.summary())  # every field with the period it reads and when it was filed
print(result.to_frame().head())
```

The members are those of that date, companies since delisted included, and every field is read
as known at the end of that day. Predicates are parsed, never run as SQL, and a missing value
never passes. A ratio holds an annual and a trailing-twelve-month value; a bare name reads the
one covering the later period (`roic@FY` or `roic@TTM` pins one), and `max_age_days=` treats a
stale fundamental as missing. `.preset("magic_formula")` (also `quality_value`,
`piotroski_value`, `net_nets`, `dividend_growers`) applies a documented formula, and
`.describe()` returns the definition. A fundamentals-only screen runs on every plan; price fields
and liquidity filters need daily bars (Pro and Institutional).

## 6. Backtest a factor

```python
from valuein_sdk import ValueinClient
from valuein_sdk import backtest

client = ValueinClient()  # reads VALUEIN_API_KEY from the environment; no key = free sample

dates = ["2019-12-31", "2020-12-31", "2021-12-31", "2022-12-31"]  # rebalance dates
panel = client.signal_panel(
    client.universe(dates=dates), ratios=["return_on_equity"], include_price=False
)
panel = client.forward_returns(panel, execution_lag=1)  # daily bars: Pro and Institutional
result = backtest(panel, signal="return_on_equity", quantiles=5, cost_bps=10.0)
print(result.summary())
```

On Pro and Institutional, `client.factor_backtest("return_on_equity", start=..., end=...,
freq="QE")` runs all steps in one call. On the free tiers the script and notebook build forward
returns from month-end closes instead; the backtest is the same.

Beyond the pipeline ratios, `signal_panel(..., library=["ep", "gpoa", "mom_12_1", "vol_1y"])`
adds documented academic factors computed from the same point-in-time reads (value, quality,
momentum, risk, size; `valuein_sdk.quant.describe_library()` gives each formula, its inputs and
the paper it comes from). A missing input gives `NaN`, never zero. On Pro and Institutional:

```python
from valuein_sdk import ValueinClient
from valuein_sdk.quant import fama_macbeth

client = ValueinClient()  # reads VALUEIN_API_KEY; Pro or Institutional key needed for daily bars

# One call: universe -> signal -> forward returns -> quantile backtest
result = client.factor_backtest(
    "gpoa", start="2015-01-01", end="2024-12-31", freq="QE", lineage=True
)
print(result.tearsheet())       # IC at 1, 2 and 4 quarters, quantile curves, turnover, exclusions
print(result.explain("2024-03-28"))  # the book held from that date, with filings and fact_ids

# Average factor slopes across dates, classic and Newey-West t-stats
panel = client.signal_panel(
    client.universe(start="2015-01-01", end="2024-12-31", freq="QE"),
    library=["ep", "mom_12_1"],
)
panel = client.forward_returns(panel, execution_lag=1)
print(fama_macbeth(panel, x=["ep", "mom_12_1"]))
```

With `lineage=True` every panel cell names the filings and `fact_id`s behind it; a
trailing-twelve-month value lists its four quarters. A backtest inferred from month-end
rebalances annualizes with 12, not the calendar gap. Every result object (`BacktestResult`,
`FactorReport`, `ScreenResult`, `Financials`, ...) has `summary()`, `to_frame()`, `to_dict()`,
`plot()` (needs `pip install "valuein-sdk[research]"`) and a notebook view.

## 7. Prices and total return

```python
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY from the environment; no key = free sample

print(client.stock_price("AAPL"))  # latest close known at as_of
print(client.run_query("""
    SELECT symbol, price_date, close, total_return_index
    FROM stock_price
    WHERE observation = 'monthly' AND symbol = 'NVDA'
    ORDER BY price_date DESC LIMIT 5
"""))
```

Daily bars (Pro and Institutional):

```python
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY; Pro or Institutional key needed for daily bars

print(client.total_return("NVDA", "2024-01-01", "2024-12-31"))  # daily bars: Pro and Institutional
```

Compute returns from `total_return_index` (splits and dividends included), never from `close`,
and never add `div_cash` on top. A company with two share classes has two price series.

## 8. Restatements

```python
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY from the environment; no key = free sample

print(client.restatements(ticker="MPWR").head())
print(client.restatements(disclosure_class="non_reliance", limit=1000).head())
```

One row per number a later filing changed, with both values and both accessions.
`disclosure_class` is `non_reliance` (8-K Item 4.02), `amended` (10-K/A, 10-Q/A) or
`undisclosed` (changed inside a routine filing); it describes disclosure mechanics, not intent.
`delta_pct` is a fraction (`-0.10` = -10%).

Does a factor depend on numbers that were later restated? On Pro and Institutional:

```python
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY; Pro or Institutional key needed for daily bars

impact = client.restatement_impact("return_on_equity", start="2012-01-01", end="2024-12-31")
print(impact.summary())  # point-in-time vs as-filed vs latest: cells changed, IC, Sharpe
print(impact.events)     # the restatements behind the changes, disclosure_class verbatim
```

The same switch is `vintage=` on `signal_panel` and `factor_backtest`: `"pit"` (the default)
reads what was known on each date, `"as_filed"` reads every period as first reported, and
`"latest"` reads today's restated numbers. `"latest"` is look-ahead by design, and every summary
of such a result says so. No score is computed: you get the changed cells and the filings.

## 9. Smart money

```python
from valuein_sdk import ValueinClient
from valuein_sdk import ValueinPlanError

client = ValueinClient()  # reads VALUEIN_API_KEY; Pro or Institutional key needed for daily bars

try:
    print(client.insider_transactions("NVDA", transaction_codes=["P", "S"]))
    print(client.institutional_holdings(issuer="NVDA"))
    print(client.advisers(name_contains="bridgewater"))
except ValueinPlanError as exc:
    print(exc)  # raised before any request on plans other than Institutional
```

Insider and 13F rows are filtered by `accepted_at`. Form ADV advisers are keyed by CRD, not CIK,
and `raum_total` must not be summed across firms.

## 10. Verify a number

```python
from valuein_sdk import ValueinClient
from valuein_sdk import compute_fact_id

client = ValueinClient()  # reads VALUEIN_API_KEY from the environment; no key = free sample

# fact_id identifies one number (company, filing, concept, period, unit); recompute it to check
row = client.run_query("""
    SELECT fact_id, entity_id, accession_id, concept, period_end, unit
    FROM fact LIMIT 1
""").iloc[0]
recomputed = compute_fact_id(
    row["entity_id"], row["accession_id"], row["concept"], row["period_end"], row["unit"]
)
print(recomputed == row["fact_id"])
print(client.filing_links("AAPL", form_types=["10-K"]).head())  # Inline XBRL viewer links
```

`fact_id` identifies the number (company, filing, concept, period, unit); open the filing to
check the value. `client.report_issue(...)` reports a number you believe is wrong.

## 11. From an AI assistant

Register `https://mcp.valuein.biz/mcp` as an MCP server with your key as a Bearer token
([`MCP_TOOLS.md`](MCP_TOOLS.md)), or let a coding agent use the SDK: `client.capabilities()`
describes the surface, and every error is a `ValueinError` whose message says how to fix the
call. Notebook 09 shows a tool function that returns each value with its `fact_id` and filing.
Every result object's `to_dict()` is strict JSON (no `NaN`, ISO dates) and carries its
parameters and provenance, so an agent's tool can return it as is.

## 12. Production extracts

`production_service.py` shows a scheduled job: resource limits with `ValueinConfig`, a fixed
`as_of` so re-runs reproduce the same data, typed errors mapped to exit codes, Parquet output
with a manifest of the plan and snapshot read.

`ValueinConfig(progress="auto")` draws a progress bar for downloads on a terminal, or pass a
callable that receives a `ProgressEvent` (`table`, `bytes_done`, `bytes_total`, `done`,
`source`). Large table files download over parallel ranged requests
(`ValueinConfig(download_streams=4)`). `read_table(table, tickers=...)` fetches per-company
files only while their count fits your plan's rate limit, and otherwise reads the table once;
`client.diagnostics()["read_plan"]` says which route it took. To freeze the data itself, see 15.

## 13. Value a company

```python
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY from the environment; no key = free sample

result = client.dcf("MSFT", stage1_growth_rate=0.08)  # the growth rate is yours, never guessed
print(result.value_per_share, result.price, result.upside)
print(result.inputs_frame())       # every input with its fact_id and filing accession
print(result.sensitivity_frame())  # value per share over discount rate x terminal growth
print(client.peers("MSFT", n=5))   # peers by SIC code with their ratios as of the client's as_of
```

A two-stage DCF computed locally from the latest annual filing known at `as_of`; defaults for
`wacc`, `terminal_growth_rate` and `stage1_years` are flagged in `result.assumptions`. The same
model is the MCP `compute_dcf` tool. Excel and Word files come from the Workspace or the MCP
`generate_*` tools, not the SDK.

## 14. Count your trials

Try ten factors and keep the best, and its Sharpe ratio is no longer honest. Run the search
inside a study and every backtest is counted (Pro and Institutional, for the daily bars):

```python
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY; Pro or Institutional key needed for daily bars

# Run the search inside a study: every backtest is counted
with client.study("quality") as study:
    for signal in ("gpoa", "roa_ttm", "accruals"):
        client.factor_backtest(signal, start="2015-01-01", end="2024-12-31", freq="QE")
print(study.summary())  # trials, deflated Sharpe, haircut Sharpe, probability of overfitting
```

Each backtest's `summary()` inside the study prints the live trial count, the deflated Sharpe
ratio (Bailey and López de Prado), the Holm haircut Sharpe (Harvey and Liu) and the minimum
backtest length. `result.robustness()` works outside a study too, and
`valuein_sdk.quant` exposes `deflated_sharpe`, `haircut_sharpe` and
`probability_of_backtest_overfitting` on their own.

## 15. Snapshots you can pin and mirror

```python
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY from the environment; no key = free sample

report = client.sync("./valuein-mirror", tables=["references", "fact"])
print(report.snapshot, report.downloaded, report.bytes_downloaded)

offline = ValueinClient.from_bundle("./valuein-mirror")  # same point-in-time views, no network
pinned = ValueinClient(snapshot=report.snapshot)         # refuses to read any other snapshot
print(offline.run_query("SELECT COUNT(*) AS n FROM \"references\""))
```

`sync` copies your plan's published table files byte for byte, with a SHA-256 and the published
ETag for each; re-running it moves only the tables that were republished, and `verify=True`
re-hashes the unchanged ones. It writes nothing if the snapshot changes while it runs, so a
mirror never mixes two. The gateway serves only its current snapshot: once the next one is
published, a pinned client raises `ValueinSnapshotError`, and the mirror still replays the old
one offline.

## 16. Your own tools: DuckDB, Arrow, Polars, Alphalens

```python
from valuein_sdk import ValueinClient

client = ValueinClient()  # reads VALUEIN_API_KEY from the environment; no key = free sample

con = client.duckdb()  # read-only, on the point-in-time views
print(con.execute("SELECT max(accepted_at) AS latest FROM fact").df())  # or .arrow(), .pl()

sql = "SELECT cik, name FROM \"references\" LIMIT 100"
df = client.run_query(sql, dtype_backend="pyarrow")  # Arrow-backed columns, lighter on big results
print(df.dtypes)
reader = client.stream_arrow(sql, batch_size=50)      # a RecordBatchReader, larger than memory
print(sum(batch.num_rows for batch in reader))
```

The Alphalens pair needs forward returns, so daily bars (Pro and Institutional):

```python
from valuein_sdk import ValueinClient
from valuein_sdk import to_alphalens

client = ValueinClient()  # reads VALUEIN_API_KEY; Pro or Institutional key needed for daily bars

panel = client.signal_panel(
    client.universe(start="2018-01-01", end="2024-12-31", freq="QE"), library=["gpoa"]
)
panel = client.forward_returns(panel, execution_lag=1)
factor, prices = to_alphalens(panel, signal="gpoa")  # Alphalens inputs on the total-return basis
print(factor.head(), prices.head())
```

A fresh `duckdb.connect()` sees none of the SDK's views; `client.duckdb()` runs on the client's
own connection, so every table it names is mounted point in time, and every statement passes the
same read-only gate as `run_query`. `client.to_polars(sql)` goes straight from Arrow. The
Alphalens pair prices on the total-return basis at the lagged entry bars, so Alphalens' own
returns match the SDK's, delisted names included.

---

## See also

- [`QUERY_COOKBOOK.md`](QUERY_COOKBOOK.md): DuckDB recipes and anti-patterns
- [`METHODOLOGY.md`](METHODOLOGY.md): how point-in-time data, restatements and XBRL
  normalization work
- [`accuracy/`](accuracy/): the measured accuracy baseline
