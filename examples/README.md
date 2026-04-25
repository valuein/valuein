# Examples — Getting Started with Valuein SDK

Practical, copy-paste scripts that go from zero to real financial data in minutes.

## Prerequisites

```bash
pip install valuein-sdk
export VALUEIN_API_KEY=your_key_here
```

Get your API key at [valuein.biz](https://valuein.biz).

## Start Here

**→ [`getting_started.py`](python/getting_started.py)** — Verify your connection, check your plan, and run your first query. Under 60 lines.

## Scripts

| File | Description | Tables Used | Level |
|---|---|---|---|
| [`getting_started.py`](python/getting_started.py) | Auth check, plan info, first query | `entity`, `security` | Beginner |
| [`usage.py`](python/usage.py) | Every public SDK method demonstrated | `entity`, `security`, `filing`, `fact` | Reference |
| [`entity_screening.py`](python/entity_screening.py) | Screen the universe: sectors, SIC codes, active vs inactive | `entity`, `security` | Beginner |
| [`financial_analysis.py`](python/financial_analysis.py) | Revenue trends, balance sheets, gross margin, concept normalization | `entity`, `security`, `filing`, `fact` | Intermediate |
| [`pit_backtest.py`](python/pit_backtest.py) | Point-in-Time discipline: `accepted_at`, `filing_date` vs `report_date` | `entity`, `security`, `filing`, `fact` | Intermediate |
| [`survivorship_bias.py`](python/survivorship_bias.py) | Bankrupt and delisted companies — "We have the data others deleted" | `entity`, `security`, `filing`, `fact` | Intermediate |

## Run any script

```bash
VALUEIN_API_KEY=your_key python examples/getting_started.py
```

## Notebooks

Interactive versions in [`notebooks/`](notebooks/):

| Notebook | Colab |
|---|---|
| [`quickstart.ipynb`](notebooks/quickstart.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/quants/blob/main/examples/notebooks/quickstart.ipynb) |
| [`fundamental_analysis.ipynb`](notebooks/fundamental_analysis.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/quants/blob/main/examples/notebooks/fundamental_analysis.ipynb) |
| [`pit_backtest.ipynb`](notebooks/pit_backtest.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/quants/blob/main/examples/notebooks/pit_backtest.ipynb) |
| [`survivorship_bias.ipynb`](notebooks/survivorship_bias.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/quants/blob/main/examples/notebooks/survivorship_bias.ipynb) |

## Going deeper?

See [`research/`](../research/) for full investment strategy implementations, backtests, and data quality proofs.
