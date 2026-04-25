# Examples — Valuein SDK & MCP

Practical, copy-paste scripts and notebooks that go from zero to real financial data in minutes. All examples work against the SDK published on [PyPI](https://pypi.org/project/valuein-sdk/). The Sample tier runs every example without a token.

## Prerequisites

```bash
pip install valuein-sdk
# add a token only when you need full universe / full history
export VALUEIN_API_KEY=your_key_here
```

Get an API key at [valuein.biz/pricing](https://valuein.biz/pricing).

## Start here

**→ [`python/getting_started.py`](python/getting_started.py)** — verify your connection, check your plan, run your first query. Under 60 lines.

## Python scripts ([`python/`](python/))

| Script | Level | Tables loaded | What it shows |
|---|---|---|---|
| [`getting_started.py`](python/getting_started.py) | Beginner | `entity`, `security` | Auth check, plan info, first query |
| [`usage.py`](python/usage.py) | Reference | `entity`, `security`, `filing`, `fact` | Every public SDK method demonstrated |
| [`entity_screening.py`](python/entity_screening.py) | Beginner | `entity`, `security` | Screen by sector, SIC code, active vs inactive |
| [`financial_analysis.py`](python/financial_analysis.py) | Intermediate | `entity`, `security`, `filing`, `fact` | Revenue trends, margins, concept normalization, peer comparison |
| [`pit_backtest.py`](python/pit_backtest.py) | Intermediate | `entity`, `security`, `filing`, `fact` | PIT discipline — `filing_date` vs `report_date`, restatement impact |
| [`survivorship_bias.py`](python/survivorship_bias.py) | Intermediate | `entity`, `security`, `filing`, `fact` | Delisted/bankrupt companies, index membership, bias quantification |
| [`factor_screen.py`](python/factor_screen.py) | Intermediate | `references`, `filing`, `fact` | Composite Quality + Growth + Efficiency z-score ranking |
| [`earnings_momentum.py`](python/earnings_momentum.py) | Intermediate | `references`, `filing`, `fact` | YoY revenue & earnings acceleration across the S&P 500 |
| [`dcf_inputs.py`](python/dcf_inputs.py) | Intermediate | `references`, `filing`, `fact`, `valuation` | FCF assembly, balance sheet, Valuein's pre-computed DCF |
| [`production-ready.py`](python/production-ready.py) | Advanced | configurable | Service pattern for FastAPI / Celery / Airflow integrations |

## Run any script

```bash
# Sample tier — no token needed
python examples/python/getting_started.py

# Paid tier
VALUEIN_API_KEY=your_key python examples/python/factor_screen.py
```

## Notebooks ([`notebooks/`](notebooks/))

Interactive versions of the matching scripts.

| Notebook | Open in Colab |
|---|---|
| [`quickstart.ipynb`](notebooks/quickstart.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/quickstart.ipynb) |
| [`fundamental_analysis.ipynb`](notebooks/fundamental_analysis.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/fundamental_analysis.ipynb) |
| [`pit_backtest.ipynb`](notebooks/pit_backtest.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/pit_backtest.ipynb) |
| [`survivorship_bias.ipynb`](notebooks/survivorship_bias.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/survivorship_bias.ipynb) |
| [`factor_screen.ipynb`](notebooks/factor_screen.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/factor_screen.ipynb) |
| [`earnings_momentum.ipynb`](notebooks/earnings_momentum.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/earnings_momentum.ipynb) |
| [`dcf_inputs.ipynb`](notebooks/dcf_inputs.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/dcf_inputs.ipynb) |

## What's not here (yet)

- **MCP examples** — see [`docs/MCP_TOOLS.md`](../docs/MCP_TOOLS.md) for tool reference and connection instructions for Claude Desktop, Cursor, and other MCP-capable clients.
- **Excel** — see [`docs/excel-guide.md`](../docs/excel-guide.md) for the Power Query walkthrough.

## Contributing

Contributions are welcome — see [`CONTRIBUTING.md`](../CONTRIBUTING.md) for example-style rules and the PR process.
