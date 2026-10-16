# Valuein SDK examples

Runnable notebooks and scripts for [`valuein-sdk`](https://pypi.org/project/valuein-sdk/), the
Python client for point-in-time, survivorship-free SEC fundamentals. They are ordered as a
learning path: start at 01 and stop when you have what you need.

Every notebook is committed **with its output**, executed on the free sample tier, so GitHub
shows the real results. Open any of them in Colab with the badge at its top.

## Run them

```bash
pip install "valuein-sdk>=7.1.0" matplotlib        # or: uv pip install "valuein-sdk>=7.1.0" matplotlib
python examples/python/getting_started.py
```

**No API key is needed to start.** Without `VALUEIN_API_KEY` the SDK reads the public sample:
S&P 500 companies (including the ones that later left the index), last five years, month-end
prices. With a key in the environment (or a `.env` file) the same code reads your plan's data.
Plans: [valuein.biz/pricing](https://valuein.biz/pricing).

## The learning path

| # | Notebook | What you learn | For | Plan |
|---|---|---|---|---|
| 01 | [Quickstart](notebooks/01_quickstart.ipynb) | Connect, resolve tickers to CIKs, discover tables, first SQL and plot, templates | everyone | none |
| 02 | [Fundamentals as of a date](notebooks/02_fundamentals_as_of_a_date.ipynb) | `as_of`, `accepted_at` vs `period_end`, restated vintages, the YTD cash-flow trap, TTM | quants, analysts | none |
| 03 | [Survivorship-free screening](notebooks/03_survivorship_free_screening.ipynb) | The index as it was on a date, screening it, measuring survivorship bias | quants, PMs | none |
| 04 | [Point-in-time factor backtest](notebooks/04_pit_factor_backtest.ipynb) | Universe → signal → forward returns → quantile backtest with costs and IC | quants | none (daily-bar section: Pro) |
| 05 | [Prices and total return](notebooks/05_prices_and_total_return.ipynb) | `total_return_index` vs `close` on a real split, dividends, share classes | everyone | none (daily helpers: Pro) |
| 06 | [Restatements](notebooks/06_restatements.ipynb) | The restatement feed, the three disclosure classes, verifying a revision on sec.gov | forensic analysts, auditors | none |
| 07 | [Smart money](notebooks/07_smart_money.ipynb) | Insider trades, 13F holders, blockholders, Form ADV; plan errors before any request | PMs, analysts | **Institutional** (runs on any plan, prints the plan error) |
| 08 | [Verify a number](notebooks/08_verify_a_number.ipynb) | `fact_id`, `compute_fact_id`, links to the exact filing, reporting a bad number | compliance, everyone | none |
| 09 | [Use it from an AI assistant](notebooks/09_ai_assistant.ipynb) | MCP setup, `capabilities()`, actionable errors, a tool that returns values with provenance | AI and agent builders | none |

Research workflows built on the path:

| # | Notebook | What you learn | Plan |
|---|---|---|---|
| 10 | [DCF valuation](notebooks/10_dcf_valuation.ipynb) | `client.dcf()`: a two-stage DCF with every input traced to its filing; sensitivity, reverse DCF, the same DCF on a past date, peers | none |
| 11 | [Piotroski F-score screen](notebooks/11_piotroski_screen.ipynb) | Screen on the published F-score as of a date; rebuild its nine tests from facts | none |
| 12 | [Earnings quality](notebooks/12_earnings_quality.ipynb) | Sloan accruals across the S&P 500 and a point-in-time backtest of the anomaly | none |
| 13 | [Sector comparison](notebooks/13_sector_comparison.ipynb) | DuPont decomposition of ROE by sector; outliers within a sector | none |
| 14 | [Restatement alpha](notebooks/14_restatement_alpha.ipynb) | Event study of returns after downward restatements, by disclosure class | none |
| 15 | [Capital allocation](notebooks/15_capital_allocation.ipynb) | Capex, acquisitions, buybacks, dividends as a share of operating cash flow | none |
| 16 | [Filing delay](notebooks/16_filing_delay.ipynb) | Reporting lag, late-against-own-history filers, after-close acceptances | none |

## Scripts

Standalone, typed scripts with a `main()`; each docstring says what it does, the plan it needs
and how to run it. Most pair with a notebook.

| Script | What it does | Notebook | Plan |
|---|---|---|---|
| [`getting_started.py`](python/getting_started.py) | Plan, snapshot, ticker → CIK, annual revenue and net income | 01 | none |
| [`financial_analysis.py`](python/financial_analysis.py) | Income statement and margins, single-quarter cash flow, peer ratios | 02 | none |
| [`pit_backtest.py`](python/pit_backtest.py) | The same query at two `as_of` dates gives two answers (a real restatement) | 02 | none |
| [`entity_screening.py`](python/entity_screening.py) | Screen the S&P 500 as it stood on a past date | 03 | none |
| [`survivorship_bias.py`](python/survivorship_bias.py) | Honest vs survivor-only equal-weight return | 03 | none |
| [`factor_backtest.py`](python/factor_backtest.py) | Universe → signal → forward returns → backtest (daily bars on Pro) | 04 | none |
| [`pit_factor_dataset.py`](python/pit_factor_dataset.py) | Point-in-time, survivorship-free factor file to Parquet and CSV | 04 | none |
| [`price_total_return.py`](python/price_total_return.py) | Split and dividend effects on returns | 05 | none (daily helpers: Pro) |
| [`restatement_radar.py`](python/restatement_radar.py) | Disclosure mix, one verified revision, recent Item 4.02 revisions | 06 | none |
| [`smart_money_screen.py`](python/smart_money_screen.py) | Insider trades, 13F holders, blockholders, a manager's portfolio | 07 | **Institutional** |
| [`filing_provenance.py`](python/filing_provenance.py) | A number, its recomputed `fact_id`, and the links to its filing | 08 | none |
| [`agent_buys_its_own_data.py`](python/agent_buys_its_own_data.py) | An agent discovers the payment rail and reads a live price quote | 09 | none (paying needs a budget or wallet) |
| [`dcf_inputs.py`](python/dcf_inputs.py) | `client.dcf()` with traced inputs, value per share, implied growth | 10 | none |
| [`production_service.py`](python/production_service.py) | A scheduled point-in-time extract to Parquet with limits, logging and exit codes | | none |

## Conventions the examples follow (copy them, or tell your AI assistant to)

- Join companies on `cik`; resolve tickers once with `client.resolve()`. Tickers get reused.
- Point in time: `ValueinClient(as_of=...)` (timezone-aware) or `accepted_at <= date`. Never gate
  on `period_end` or `report_date`.
- One row per period: `QUALIFY ROW_NUMBER() OVER (PARTITION BY ..., period_end ORDER BY accepted_at DESC, priority DESC) = 1`
  (`priority = 1` is the elected tag when several XBRL tags in one filing map to the same concept).
- Annual flows: `numeric_value` on `fiscal_period = 'FY'` rows. Quarterly flows:
  `COALESCE(derived_quarterly_value, numeric_value)`. Capex: `ABS(...)`.
- Index membership: `index_membership` (`effective_date <= d < removal_date`) or
  `client.universe()`. There is no `is_sp500` column.
- Returns: `total_return_index`, never `close`, and never add `div_cash` on top.
- `ratio` holds FY and TTM rows (`is_ttm`); ratios are decimals (`0.25` = 25%).
- Canonical concept names (`TotalRevenue`, `NetIncome`, ...) are listed in
  [`docs/data_catalog.md`](../docs/data_catalog.md). More SQL recipes:
  [`docs/QUERY_COOKBOOK.md`](../docs/QUERY_COOKBOOK.md). Use cases at a glance:
  [`docs/SDK_USE_CASES.md`](../docs/SDK_USE_CASES.md).

## Contributing

See [`CONTRIBUTING.md`](../CONTRIBUTING.md).
