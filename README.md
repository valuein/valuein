[![Valuein Logo](https://www.valuein.biz/valuein/twitter-rounded.png)](https://valuein.biz)

[![PyPI version](https://img.shields.io/pypi/v/valuein-sdk?cacheSeconds=300)](https://pypi.org/project/valuein-sdk/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/valuein-sdk/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![MCP Registry](https://img.shields.io/badge/MCP-registry.modelcontextprotocol.io-blue)](https://registry.modelcontextprotocol.io)

# 💎 Valuein — Community, Docs, and Discovery Hub

This repository is the **public home** for Valuein's SEC EDGAR fundamentals data product. It is the place to:

- Find **documentation** (methodology, data catalog, compliance, SLA, Excel guide)
- Run **examples and notebooks** that connect to our live data
- Open **support tickets, bug reports, and feature requests**
- **Discover** our distribution channels — the Python SDK, the MCP server, the Excel template, and the REST API

The source code for the SDK, MCP server, and data pipeline lives in dedicated repositories. This repo is the front door.

---

## 📦 The Data Product

Survivorship-bias-free, point-in-time US fundamentals sourced from SEC EDGAR:

- **12M+ filings** (10-K, 10-Q, 8-K, 20-F + amendments), 1990–present
- **108M+ facts** across **10,000+** active and delisted US entities
- **11,966 XBRL tags** normalized to **~150 canonical `standard_concept`** values
- **Cloud Parquet** on Cloudflare R2 — stream with DuckDB, no local downloads

### Why it's different

| Feature | Why it matters |
|---|---|
| 🕒 **Point-in-Time (PIT)** | Every fact carries `filing_date` and `knowledge_at` — no look-ahead bias in backtests |
| ⚖️ **Survivorship-bias free** | Delisted, bankrupt, acquired companies included |
| 📊 **Standardized concepts** | 11,966 raw XBRL tags mapped to canonical names (both are on the `fact` table) |
| 🚀 **DuckDB native** | Millisecond analytics via `httpfs` against remote Parquet |
| ☁️ **Zero-setup** | `pip install` and query — no database provisioning, no large downloads |

---

## 🚚 Distribution Channels

We deliver the same underlying data through five interfaces so it lands wherever you already work.

| Channel | For | How to get it |
|---|---|---|
| **Python SDK** | Quants, engineers, data scientists | `pip install valuein-sdk` · [PyPI](https://pypi.org/project/valuein-sdk/) |
| **MCP Server** | AI agents (Claude, Cursor, Codex, etc.) | `https://mcp.valuein.biz/mcp` · see [MCP Discovery](#-mcp-discovery--ai-agents) |
| **Excel / Power Query** | Financial analysts, CPAs, researchers | [Excel setup guide](docs/excel-guide.md) |
| **Web Dashboard** | Non-technical users, retail, executives | [valuein.biz](https://valuein.biz) |
| **REST API** | B2B partners, third-party integrations | `https://data.valuein.biz` — [contact us](mailto:support@valuein.biz) for the integration guide |

All channels authenticate with the **same Stripe-issued API token** and share the same tier model.

---

## 💳 Plans & Access

| Plan | Coverage | Data | Price | Get Access |
|---|---|---|---|---|
| **Sample** | S&P 500 · last 5 years · active + inactive | Public, read-only | **Free** | No registration — works out of the box |
| **S&P 500** | S&P 500 · full history · active + inactive | Full Parquet access | **Free** | [Register](https://buy.stripe.com/3cI28qgx81Og66weXgco004) |
| **Pro** | Full US universe · all core fundamentals | Full Parquet access | **$200 / month** | [Subscribe](https://buy.stripe.com/5kQ3cudkW0Kc3Yo02mco005) |
| **Pro (Annual)** | Same as Pro · 20% discount | Full Parquet access | **$1,920 / year** | [Subscribe](https://buy.stripe.com/eVq00i94GakM52s6qKco003) |

One token unlocks the **SDK, MCP, Excel, and REST API** — no per-channel billing.

---

## ⚡ Quickstart — Python SDK

**1. Install**

```bash
pip install valuein-sdk
```

**2. Query real data without a token** (Sample tier, no registration):

```python
from valuein_sdk import ValueinClient

with ValueinClient() as client:
    print(client.me())                               # {plan, status, email, createdAt}
    print(client.manifest())                         # snapshot metadata
    print(client.tables())                           # loaded table names
    print(client.get_schema("fact"))                 # column → DuckDB type

    df = client.query("SELECT COUNT(*) FROM entity")
    print(df)
```

**3. Unlock the full dataset** — add a token, no code changes needed:

```bash
echo 'VALUEIN_API_KEY="your_token_here"' >> .env
```

**4. Production pattern** — context manager, typed errors, pre-built SQL templates:

```python
from valuein_sdk import ValueinClient, ValueinError

with ValueinClient() as client:
    try:
        df = client.run_template(
            "fundamentals_by_ticker",
            ticker="AAPL",
            start_date="2020-01-01",
            end_date="2024-01-01",
            form_types=["10-K", "10-Q"],
            metrics=["TotalRevenue", "NetIncome", "OperatingCashFlow"],
        )
        print(df)
    except ValueinError as e:
        print(f"SDK error: {e}")
```

---

## 🗂️ Data Model Essentials

Full schema in [`docs/schema.json`](docs/schema.json) and [`docs/data_catalog.md`](docs/data_catalog.md).

| Table | Description | Records |
|---|---|---|
| **`references`** | **Start here.** Flat join of entity + security + index_membership. One row per security with `is_sp500`, `is_active`, sector, exchange. Replaces 3-table joins. | ~7K |
| `entity` | Company metadata | 19K+ |
| `security` | Ticker history (SCD Type 2) | 7K+ |
| `filing` | Filing metadata (10-K, 10-Q, 8-K, 20-F + amendments) | 12M+ |
| `fact` | Financial statement facts — raw `concept` + canonical `standard_concept` on every row | 108M+ |
| `valuation` | Two-stage DCF + DDM intrinsic values per entity per period | 19K+ |
| `taxonomy_guide` | 2026 US GAAP Taxonomy Guide | 11,966 |
| `index_membership` | Historical index entry/exit dates | 8K+ |

### Key joins

```
references.cik               → entity.cik
security.entity_id           → entity.cik
filing.entity_id             → entity.cik
fact.entity_id               → entity.cik
fact.accession_id            → filing.accession_id
index_membership.security_id → security.id
```

### Date columns — which to use when

| Column | Table | Use for |
|---|---|---|
| `report_date` / `period_end` | `filing` / `fact` | Fiscal calendar alignment |
| `filing_date` | `filing` | **PIT backtest filter** — when the SEC received the filing |
| `knowledge_at` | `fact` | Millisecond-precision PIT for intraday research |

> For cross-company backtests, **always** filter by `filing_date <= trade_date`. Using `report_date` introduces look-ahead bias.

### Canonical `standard_concept` names

Query `fact.standard_concept` with canonical names like `'TotalRevenue'`, `'NetIncome'`, `'OperatingCashFlow'`, `'CAPEX'`, `'StockholdersEquity'` — **not** raw XBRL tags (`'Revenues'`, `'NetIncomeLoss'`, `'Assets'`). The full canonical list lives in [`docs/data_catalog.md`](docs/data_catalog.md).

### DuckDB query patterns that pay off

**Start from `references`** — zero joins for cross-company filters:
```sql
SELECT symbol, name, sector
FROM   references
WHERE  is_sp500 = TRUE AND is_active = TRUE AND sector ILIKE '%technology%'
```

**`LATERAL` for the latest filing per company**:
```sql
JOIN LATERAL (
    SELECT accession_id FROM filing
    WHERE  entity_id = r.cik AND form_type = '10-K'
    ORDER  BY filing_date DESC LIMIT 1
) f ON TRUE
```

**Pivot multiple concepts in one `fact` scan**:
```sql
SELECT
  MAX(CASE WHEN standard_concept = 'TotalRevenue'       THEN numeric_value END) AS revenue,
  MAX(CASE WHEN standard_concept = 'StockholdersEquity' THEN numeric_value END) AS equity
FROM   fact
WHERE  standard_concept IN ('TotalRevenue', 'StockholdersEquity')
GROUP  BY accession_id
```

> Cash flow items: use `COALESCE(derived_quarterly_value, numeric_value)` — Q2/Q3 10-Qs report YTD, this column isolates the quarter. CAPEX sign varies by filer — always `ABS(capex)`.

---

## 🐍 Examples in this Repository

All examples work against the SDK published on PyPI. The Sample tier runs without a token.

### Python scripts ([`examples/python/`](examples/python/))

| Script | Level | What it shows |
|---|---|---|
| [`getting_started.py`](examples/python/getting_started.py) | Beginner | First query, token check, entity counts by sector |
| [`usage.py`](examples/python/usage.py) | Reference | Every public SDK method demonstrated |
| [`entity_screening.py`](examples/python/entity_screening.py) | Beginner | Screen by sector, SIC code, active vs inactive |
| [`financial_analysis.py`](examples/python/financial_analysis.py) | Intermediate | Revenue trends, margins, peer comparison |
| [`pit_backtest.py`](examples/python/pit_backtest.py) | Intermediate | Correct PIT discipline, restatement impact |
| [`survivorship_bias.py`](examples/python/survivorship_bias.py) | Intermediate | Delisted companies, index membership, bias quantification |
| [`production-ready.py`](examples/python/production-ready.py) | Advanced | Service pattern for FastAPI / Celery / Airflow integrations |

Run any example:

```bash
# Sample tier — no token needed
python examples/python/getting_started.py

# Paid tier
VALUEIN_API_KEY=xxx python examples/python/pit_backtest.py
```

### Jupyter notebooks ([`examples/notebooks/`](examples/notebooks/))

| Notebook | Open in Colab |
|---|---|
| [Quickstart](examples/notebooks/quickstart.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/quickstart.ipynb) |
| [Fundamental Analysis](examples/notebooks/fundamental_analysis.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/fundamental_analysis.ipynb) |
| [PIT Backtest](examples/notebooks/pit_backtest.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/pit_backtest.ipynb) |
| [Survivorship Bias](examples/notebooks/survivorship_bias.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/survivorship_bias.ipynb) |

---

## 🛡️ Error Handling

The SDK exposes typed exceptions so your code can react appropriately to each failure mode:

```python
from valuein_sdk import (
    ValueinClient,
    ValueinAuthError,      # HTTP 401/403 — invalid or expired token
    ValueinPlanError,      # HTTP 403 — endpoint requires a higher plan
    ValueinNotFoundError,  # HTTP 404 — table or endpoint does not exist
    ValueinRateLimitError, # HTTP 429 — includes .retry_after (seconds)
    ValueinAPIError,       # HTTP 5xx — includes .status_code
)

with ValueinClient() as client:
    try:
        df = client.query("SELECT * FROM fact LIMIT 1000")
    except ValueinAuthError:
        print("Check your VALUEIN_API_KEY — it may be expired or invalid.")
    except ValueinPlanError:
        print("This query requires a higher-tier plan. Upgrade at valuein.biz.")
    except ValueinRateLimitError as e:
        print(f"Rate limited. Retry allowed in {e.retry_after}s.")
    except ValueinAPIError as e:
        print(f"Gateway error (status {e.status_code}).")
```

---

## 📊 Excel Integration

Stream SEC fundamentals straight into Excel via Power Query — no Python, no scripts.

**Requirements:** Microsoft 365 (build 16.0.17531+) and an active API token.

**Quick path:**

1. **Get the template** — follow the download link in [`docs/excel-guide.md`](docs/excel-guide.md)
2. **Open in Excel** — enable editing and content
3. **Paste your token** into the **START HERE** sheet
4. **Click** `Data > Refresh All`

The workbook ships with **8 pre-configured sheets**: Income Statement, Balance Sheet, Cash Flow, Entities, Securities, Filings, Index Membership, and the Data Dictionary. The full walkthrough — including token setup, Named Ranges, refresh troubleshooting, and the Power Query M-language internals — is in [`docs/excel-guide.md`](docs/excel-guide.md).

On Excel 2019 or earlier, `Parquet.Document()` is unavailable; email [support@valuein.biz](mailto:support@valuein.biz) for CSV exports.

---

## 🤖 MCP Discovery — AI Agents

Valuein's MCP server exposes SEC EDGAR fundamentals to any MCP-capable AI agent (Claude, Cursor, Codex, and the wider agent ecosystem).

- **Endpoint:** `https://mcp.valuein.biz/mcp` (Streamable HTTP, MCP spec 2025-11-25)
- **Auth:** `Authorization: Bearer <your_api_token>` — the same token used by the SDK and Excel
- **Manifest:** [`server.json`](server.json) in this repo is the source of truth for the registry listing
- **Registry:** [registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io) — search for `io.github.valuein/mcp-sec-edgar`

### Tools exposed

| Tool | Description | Available in |
|---|---|---|
| `search_companies` | Ticker / name / CIK lookup | All plans |
| `get_sec_filing_links` | Direct links to 10-K, 10-Q, 8-K, 20-F on SEC EDGAR | All plans |
| `get_company_fundamentals` | Annual (all plans) or quarterly + extended history (Pro) | Free → Pro |
| `get_financial_ratios` | Margins, returns, leverage, efficiency ratios | Pro |
| `get_dcf_inputs` | Raw inputs for two-stage DCF + DDM models | Enterprise |

### Configure in an AI client

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "valuein": {
      "url": "https://mcp.valuein.biz/mcp",
      "headers": { "Authorization": "Bearer YOUR_VALUEIN_API_KEY" }
    }
  }
}
```

Any MCP-compliant client that supports Streamable HTTP remotes will work with the same URL + Bearer token.

---

## 📚 Documentation

Everything in [`docs/`](docs/) is kept in sync with the production data.

| Document | What's in it |
|---|---|
| [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) | Sourcing, PIT architecture, restatement handling, XBRL normalization |
| [`docs/COMPLIANCE_AND_DDQ.md`](docs/COMPLIANCE_AND_DDQ.md) | Data provenance, MNPI policy, PIT integrity, security, SLA summary |
| [`docs/SLA.md`](docs/SLA.md) | Uptime targets, data freshness, support response times, SLA credits |
| [`docs/excel-guide.md`](docs/excel-guide.md) | Full Excel / Power Query setup walkthrough |
| [`docs/data_catalog.md`](docs/data_catalog.md) | Canonical `standard_concept` names and definitions |
| [`docs/DATA_CATALOG.xlsx`](docs/DATA_CATALOG.xlsx) | Same catalog as a workbook — columns, types, sample values |
| [`docs/schema.json`](docs/schema.json) | Machine-readable table + column schema |

---

## 💬 Support & Community

GitHub Issues is the primary support channel. Four templates cover the common cases:

| I want to… | Open |
|---|---|
| Report incorrect or suspicious data | [Data Quality Report](.github/ISSUE_TEMPLATE/01_data_quality_report.md) |
| Request a feature, concept, or dataset | [Feature Request](.github/ISSUE_TEMPLATE/02_feature_request.md) |
| Report an outage or degraded service | [Service Outage](.github/ISSUE_TEMPLATE/03_service_outage.md) |
| Ask a general question | [General Question](.github/ISSUE_TEMPLATE/04_general_question.md) |

For private or contractual matters (DPAs, procurement, DDQs, enterprise SLAs): **[support@valuein.biz](mailto:support@valuein.biz)**.

Contributions — examples, notebook improvements, documentation fixes — are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the workflow and style guide.

---

## 📄 License & Disclosure

[Apache 2.0](LICENSE). See [NOTICE](NOTICE) for attribution.

This repository is provided for research and educational purposes. It is not investment advice. No warranty of fitness for any particular trading, investment, or regulatory purpose is implied.
