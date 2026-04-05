[![Valuein Logo](https://www.valuein.biz/valuein/twitter-rounded.png)](https://valuein.biz)

[![PyPI version](https://img.shields.io/pypi/v/valuein-sdk?cacheSeconds=300)](https://pypi.org/project/valuein-sdk/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/valuein-sdk/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![CI](https://github.com/valuein/quants/actions/workflows/publish.yml/badge.svg)](https://github.com/valuein/quants/actions/workflows/publish.yml)

# 💎 Valuein Python SDK: Frictionless Financial Data
A high-performance toolkit for querying point-in-time US fundamentals from SEC EDGAR, built for quants, analysts, and data engineers.

The Valuein SDK, is a complete infrastructure solution for consuming point-in-time accurate US Core financial fundamentals (facts) on your daily workflow. Whether you are building complex asynchronous Python pipelines, performing forensic financial research in Excel, or executing templated SQL, this library provides frictionless, zero-setup access to institutional-grade data.

## The Data Engine
Powered by survivorship-bias-free data containing 12M+ filings and 108M+ facts from 10-Ks, 10-Qs, 8-Ks, 20-Fs, and amendments across 10,000+ active and delisted US companies since 1990.

## Why use this toolkit?

⚡ Lightning-Fast Python SDK: Execute blazing-fast queries against remote Parquet files hosted on R2, powered entirely by DuckDB under the hood. No database setup, no massive local downloads.

📊 Excel & Power Query Ready: Not a Python developer? Fetch, transform, and analyze the data directly within Excel spreadsheets using our provided integrations.

🛠️ Plug-and-Play SQL Templates: Skip the boilerplate. Use our pre-built SQL templates to immediately extract insights, calculate intrinsic values, or model standardized financial statements.

📚 Comprehensive Context: Deep-dive documentation mapping out table schemas, primary keys, and field definitions to support your specific financial research use cases.

## 🚀 Why Valuein Data and SDK Library
> Easy of use and intelligence.

| Feature                               | Benefit                                                    |
|---------------------------------------|-----------------------------------------------------------|
| 🕒 **<span title="Provides historical snapshots for accurate backtesting">Point‑in‑Time Data</span>** | Eliminate look‑ahead bias in backtests |
| ⚖️ **<span title="Includes companies that went bankrupt, delisted, or were acquired">Survivorship‑Bias Free</span>** | Includes bankrupt, delisted, and acquired firms |
| 📊 **<span title="Maps 15k+ raw XBRL tags to ~150 standard financial concepts">Standardized Concepts</span>** | 15k+ XBRL tags mapped to ~150 canonical financial concepts |
| 🚀 **<span title="High-speed in-memory SQL engine using DuckDB">DuckDB SQL Engine</span>** | Millisecond analytics directly in Python |
| ☁️ **<span title="Stream Parquet data from cloud storage without downloading locally">Cloud Parquet Streaming</span>** | No local data downloads required |
| 🧩 **<span title="Ready-to-use financial templates for backtesting and signals">Financial Templates</span>** | Production‑ready investment signals |


## 🧠 What You Can Do With This Repository

| Use Case | Who | Where to Start |
|---|---|---|
| **Query financial data via Python** | Quants, data engineers | [Quickstart](#quickstart) |
| **Run 39 pre-built financial signals** | Analysts, quants | [SQL Templates](#sql-templates) |
| **Learn with interactive notebooks** | Students, new users | [Examples & Notebooks](#examples--notebooks) |
| **Pull data into Excel** | Financial analysts | [Excel Integration](#excel-integration) |
| **Prove data quality to stakeholders** | Institutional buyers, compliance | [Research & Quality Proofs](#research--quality-proofs) |
| **Read methodology and compliance docs** | Due diligence, enterprise | [Documentation](#documentation) |
| **Contribute templates, examples, research** | Open-source contributors | [Contributing](#contributing) |

---

## ⚡ Quickstart

**1. Install Package**

``` bash
pip install valuein-sdk
```

### Run the script — no token required

Install and query real data immediately, no registration needed for the SAMPLE dataset:

```python
from valuein_sdk import ValueinClient

client = ValueinClient()                            # load all tables by default
print("Me: ", client.me())                          # dict: plan, status, email, createdAt
print("Manifest: ", client.manifest())              # dict: snapshot, last_updated, tables (cached 5 min)
print("Tables: ", client.tables())                  # list of loaded table names
print("Fact Schema: ", client.get_schema("fact"))  # dict: column → DuckDB type for any loaded table

sql_query = "SELECT COUNT(cik) FROM entity"
result_df = client.query(sql_query)             # SQL → pandas DataFrame
print(f"Query Results: {result_df}")
```

Add a token at any time to unlock the full dataset — no code changes needed.

## 🔑 2. Get Your API Token

| Data Plan        | Coverage                                                        | Price | Get Access                                                  |
|------------------|-----------------------------------------------------------------|------|-------------------------------------------------------------|
| **Sample**       | S&P 500 coverage<br>5-years only<br>Active & inactive companies | **Free** | No registration                                             |
| **S&P500**       | S&P 500 coverage<br>Full history<br>Active & inactive companies | **Free** | [Register](https://buy.stripe.com/3cI28qgx81Og66weXgco004)  |
| **Pro**          | Full universe of US stocks<br>US core fundamentals              | **$200 / month** | [Subscribe](https://buy.stripe.com/5kQ3cudkW0Kc3Yo02mco005) |
| **Pro (Annual)** | Same as Pro plan (20% Discount)                                 | **$1920 / year** | [Subscribe](https://buy.stripe.com/eVq00i94GakM52s6qKco003) |


## 🔐 3. Set Your API Token

```bash
echo 'VALUEIN_API_KEY="your_token"' >> .env
```

## ▶️ 4. Production-ready code

The ValueinClient handles authentication, table discovery, and local caching in a high-performance DuckDB instance.

The Recommended Way For Production is the Context Manager block/pattern because it ensures that temporary files and database connections are closed automatically, even if your script crashes.

```python
from valuein_sdk import ValueinClient, ValueinError

try:
    # load specific tables OR omit to load all tables
    with ValueinClient() as client:
                
        f_df = client.get(table="filing")               # download full table → pandas DataFrame
        print(f"Filings: {f_df.head()}")
                
        try:
            result_df = client.run_template(            # named SQL template → pandas DataFrame
                "fundamentals_by_ticker",
                ticker="AAPL",
                start_date="2020-01-01",
                end_date="2024-01-01",
                form_types=["10-K", "10-Q"],
                metrics=["TotalRevenue", "NetIncome", "OperatingCashFlow"],  # required — standard_concept filter
            )
            print(f"Template Results: {result_df}")
        except ValueinError as e:
            print(f"Catch all error types: {e}")       
except Exception as e:
    print(f"Initialization error: {e}")
```

---

# 🗂️ Data Schema
> Find more information regarding all tables, and it fields in [docs/schema.json](docs/schema.json).

| Table              | Description                   | Records |
|-------------------|-------------------------------|---------|
| **references**     | **Start here.** Flat join of entity + security + index_membership. One row per security. Boolean flags (`is_sp500`) replace three joins. | ~7K |
| **entity**         | Company metadata              | 19K+    |
| **security**       | Ticker history (SCD Type 2)   | 7K+     |
| **filing**         | Filing metadata               | 12M+    |
| **fact**           | Financial statement facts     | 108M+   |
| **valuation**      | Two-stage DCF + DDM intrinsic value per entity per period | 19K+    |
| **taxonomy_guide** | 2026 US GAAP Taxonomy Guide | 11,966  |
| **index_membership** | Historical index membership with start/end dates | 8K+     |


### 🔗 Key Joins

```
references.cik                  →  entity.cik  (references is the fast entry point)
security.entity_id              →  entity.cik
filing.entity_id                →  entity.cik
fact.entity_id                  →  entity.cik
fact.accession_id               →  filing.accession_id
index_membership.security_id    →  security.id
```

### ⚡ DuckDB Query Patterns

Three patterns that eliminate redundant joins and scans on every cross-company query:

**1. `references` replaces entity + security + index_membership**
```sql
-- Filter S&P 500 tech companies — zero joins
SELECT symbol, name, sector
FROM   references
WHERE  is_sp500 = TRUE AND sector ILIKE '%technology%' AND is_active = TRUE
```

**2. `LATERAL` for the latest filing per company**
```sql
JOIN LATERAL (
  SELECT accession_id, filing_date
  FROM   filing
  WHERE  entity_id = r.cik AND form_type = '10-K'
  ORDER  BY filing_date DESC
  LIMIT  1
) f ON true
```

**3. Pivot multiple concepts in one `fact` scan**
```sql
-- Debt + equity in one pass — no self-join
SELECT
  MAX(CASE WHEN standard_concept = 'LongTermDebt'       THEN numeric_value END) AS debt,
  MAX(CASE WHEN standard_concept = 'StockholdersEquity' THEN numeric_value END) AS equity
FROM fact WHERE standard_concept IN ('LongTermDebt', 'StockholdersEquity')
GROUP BY accession_id
```

> For quarterly cash flow metrics, use `COALESCE(derived_quarterly_value, numeric_value)` — Q2/Q3 10-Qs report YTD; this column isolates the single quarter.

See [`valuein_sdk/queries/SQL_CHEATSHEET.md`](valuein_sdk/queries/SQL_CHEATSHEET.md) for 8 complete patterns including FCF screens, PIT backtesting, and restatement auditing.

---

### 🏷️ Standard Concept Names

> [!Note]
> Raw XBRL tags (11,966 unique) are normalized to canonical `standard_concept` values. We standardized the most used
3,200 concepts from the US GAAP Taxonomy Code which allows to categorize 95% of all facts, the rest has the 'Other' category.

> Both the raw `concept` tag (xbrl_tag) and the normalized `standard_concept` are on the `fact` table — no join to a separate mapping table needed.


### 📅 Date Columns Reference

| Column | Table | Use for |
|---|---|---|
| `report_date` / `period_end` | `filing` / `fact` | Aligning to fiscal calendar |
| `filing_date` | `filing` | **PIT backtest filter** — when the SEC received the filing |
| `knowledge_at` | `fact` | Millisecond-precision PIT for intraday signal research |


### 🧩 Template Categories

| Range | Category | Examples |
|---|---|---|
| 01–04 | Data Access | Fundamentals by ticker, FIGI lookup, peer comparison, survivorship-bias-free screen |
| 05–09 | Income Statement | YoY revenue growth, TTM, margin analysis, FCF, R&D intensity |
| 10–15 | Balance Sheet | Liquidity, solvency, interest coverage, cash conversion, capex ratios |
| 16–20 | Investment Scores | DuPont, Piotroski F-Score, Altman Z-Score, accruals anomaly |
| 21–26 | Valuation & Screening | Sector aggregates, peer ranking, dilution, arbitrage signals |
| 27–33 | Short Signals | Late filers, restatements, 8-K events, ghost companies |
| 34–39 | Advanced Analytics | PIT backtest engine, Z-score outliers, seasonality, XBRL audit |

See [`valuein_sdk/queries/SQL_CHEATSHEET.md`](https://github.com/valuein/quants/blob/main/valuein_sdk/queries/SQL_CHEATSHEET.md) for the full template reference.


## 📚 Documentation

| Document | Description | Format |
|----------|------------|--------|
| [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) | Data sourcing, PIT architecture, restatement handling, XBRL normalization logic | Markdown |
| [`docs/COMPLIANCE_AND_DDQ.md`](docs/COMPLIANCE_AND_DDQ.md) | Data provenance, MNPI policy, PIT integrity, security, SLA summary | Markdown |
| [`docs/SLA.md`](docs/SLA.md) | Uptime targets, data freshness SLAs, support response times, SLA credits | Markdown |
| [`docs/excel-guide.md`](docs/excel-guide.md) | Full Excel / Power Query setup walkthrough | Markdown |
| [`docs/DATA_CATALOG.xlsx`](docs/DATA_CATALOG.xlsx) | All columns, types, definitions, sample values | Excel |
| [`docs/schema.json`](docs/schema.json) | Machine-readable JSON schema | JSON |

---

## 🐍 Python Examples
Standalone Python scripts and four Jupyter notebooks, designed to go from install to insight in under 3 minutes.*

### Ticker lookup example
Run any SQL against the data lake. No downloads. No local database. DuckDB executes your queries in-process.

```python
from valuein_sdk import ValueinClient

client = ValueinClient(tables=["entity", "security"])
# This client only fetch these 2 tables, making it faster!

df = client.query("""
    SELECT e.cik, e.name, e.sector, e.status,
           s.symbol, s.exchange
    FROM   security s
    JOIN   entity   e ON s.entity_id = e.cik
    WHERE  s.symbol = 'AAPL' AND s.is_active = TRUE
""")
print(df)
```

You are now querying **SEC financial statements directly from the
cloud**.


### Python scripts (`examples/python/`)

| Script | Level | What it demonstrates |
|---|---|---|
| [`getting_started.py`](examples/python/getting_started.py) | Beginner | Auth check, first query, entity counts by sector |
| [`usage.py`](examples/python/usage.py) | Reference | Every public SDK method demonstrated |
| [`entity_screening.py`](examples/python/entity_screening.py) | Beginner | Screen by sector, SIC code, active vs inactive status |
| [`financial_analysis.py`](examples/python/financial_analysis.py) | Intermediate | Revenue trends, margins, concept normalization, peer comparison |
| [`pit_backtest.py`](examples/python/pit_backtest.py) | Intermediate | Correct PIT discipline, restatement impact, `filing_date` vs `report_date` |
| [`survivorship_bias.py`](examples/python/survivorship_bias.py) | Intermediate | Delisted/bankrupt companies, index_membership, bias quantification |

### Jupyter notebooks (`examples/notebooks/`)

| Notebook | Open in Colab |
|---|---|
| [Quickstart](examples/notebooks/quickstart.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/quants/blob/main/examples/notebooks/quickstart.ipynb) |
| [Fundamental Analysis](examples/notebooks/fundamental_analysis.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/quants/blob/main/examples/notebooks/fundamental_analysis.ipynb) |
| [PIT Backtest](examples/notebooks/pit_backtest.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/quants/blob/main/examples/notebooks/pit_backtest.ipynb) |
| [Survivorship Bias](examples/notebooks/survivorship_bias.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/quants/blob/main/examples/notebooks/survivorship_bias.ipynb) |

---

### 🛡️ Error Handling

```python
from valuein_sdk import (
    ValueinAuthError,      # HTTP 401/403 — invalid or expired token
    ValueinPlanError,      # HTTP 403 — endpoint requires a higher plan
    ValueinNotFoundError,  # HTTP 404 — no table found 
    ValueinRateLimitError, # HTTP 429 — includes .retry_after (seconds)
    ValueinAPIError,       # HTTP 5xx — includes .status_code
    ValueinClient
)

client = None
try:
    client = ValueinClient()
    df = client.query("SELECT * FROM fact LIMIT 1000000")
except ValueinAuthError:
    print("Check your VALUEIN_API_KEY. It might be expired or invalid.")
except ValueinPlanError:
    print("This requires a higher-tier plan. Upgrade at valuein.biz.")
except ValueinRateLimitError as e:
    print(f"Slow down! Retry allowed in {e.retry_after}s.")
except ValueinNotFoundError as e:
    print(f"That table or endpoint doesn't exist: {e}")
except ConnectionError as e:
    print(f"Physical network issue: {e}")
except ValueinAPIError as e:
    print(f"The Gateway is having a bad day (Status {e.status_code}).")
except Exception as e:
    print(f"Non-SDK error (Python/Logic): {e}")
finally:
    # Always close manually if not using a context manager and if a client was created.
    if client is not None:
        client.close()
```

---

## 🔬 Research & Quality Proofs

16 runnable research modules that prove every data quality claim with code. Designed for institutional due diligence and quantitative research.

```bash
# Install research dependencies
uv sync --group research

# Run a proof
python research/quantitative/pit_correctness_proof.py
python research/quality_proof/balance_sheet_check.py
```

---
# 📊 Excel Integration

**Stream live SEC fundamental data directly into your spreadsheets. No Python, or complex scripts, just pure data power.**

### ⚡ Quick Start
Get up and running in less than 60 seconds.

1.  **Download Template:** Get the [`valuein-fundamentals.xlsx`](excel/valuein-fundamentals.xlsx) workbook.
2.  **Authorize:** Open the workbook and enter your API token in the **Connectivity Guide** sheet.
3.  **Sync Data:** Click **`Data > Refresh All`**.

> [!TIP]
> Data streams directly from Parquet files on Cloudflare R2, ensuring high-speed transfers and minimal local overhead.

### 🛠 Requirements
* **Microsoft 365** (Build 16.0.17531 or later)
* Active API Token

### 📂 Pre-Configured Sheets
The workbook includes **8 high-performance sheets** ready for analysis:

* **Financials:** Income Statement, Balance Sheet, Cash Flow
* **Metadata:** Entities, Securities, Filings
* **Reference:** Index Membership, Data Dictionary

### 🧑‍💻 Developer Customization
For those who prefer a "Do It Yourself" approach, the raw **M-language** source files for Power Query are available in the [`excel/power-query/`](excel/power-query/) directory. You can use these to build custom connections in your existing workbooks.

📖 **Need more help?** View the [Full Setup Walkthrough](docs/excel-guide.md).


### 📊 Research Modules

**`research/fundamental/`** — Financial statement analysis workflows
- Income statement, balance sheet, cash flow, DuPont decomposition, Altman Z-Score

**`research/quantitative/`** — Factor model and strategy research
- PIT correctness proof, survivorship bias quantification, restatement tracking as short signal, sector rotation

**`research/data_engineering/`** — XBRL normalization and pipeline analysis
- Concept mapping explorer, taxonomy coverage, filing timeline, data freshness by sector

**`research/quality_proof/`** — Automated data quality validation
- Zero PIT violations, balance sheet equation check (Assets = Liabilities + Equity within 1%), coverage report, SEC cross-reference spot-check

See [`research/README.md`](research/README.md) for a full breakdown of what each module proves and the key metric it validates.

---

## 🤝 Contributing

We welcome contributions including SQL templates, notebooks, scripts, research modules, and documentation improvements.

See [CONTRIBUTING.md](CONTRIBUTING.md) for code standards, naming conventions, and the PR process.

## 📄 License

Apache-2.0 License — see [LICENSE](LICENSE).

**Disclosure:** This repository is for research and educational purposes
only and does not constitute financial advice.
