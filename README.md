[![Valuein](https://www.valuein.biz/valuein/twitter-rounded.png)](https://valuein.biz)

[![PyPI version](https://img.shields.io/pypi/v/valuein-sdk?cacheSeconds=300)](https://pypi.org/project/valuein-sdk/)
[![PyPI downloads](https://img.shields.io/pypi/dm/valuein-sdk?label=pypi%20downloads&cacheSeconds=3600)](https://pypi.org/project/valuein-sdk/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/valuein-sdk/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/valuein/valuein?style=flat&cacheSeconds=3600)](https://github.com/valuein/valuein/stargazers)
[![MCP Registry](https://img.shields.io/badge/MCP-registry.modelcontextprotocol.io-blue)](https://registry.modelcontextprotocol.io)
[![Docs](https://img.shields.io/badge/docs-valuein.biz-purple)](https://valuein.biz/developers/catalog)

# Valuein — SEC EDGAR fundamentals for analysts, quants, and AI agents

> **Survivorship-bias-free, point-in-time US fundamentals — streamed as Parquet, queried with DuckDB or natural language.**

This repository is the **public home and discovery hub** for the Valuein data platform. It hosts the documentation, examples, notebooks, and the [MCP registry manifest](server.json) used by AI agents to find us. Source code for the SDK, MCP server, and data pipeline lives in dedicated repositories — this is the front door.

```bash
pip install valuein-sdk          # data for code
# or add this URL to any MCP-capable AI client:
# https://mcp.valuein.biz/mcp     # data for agents
```

---

## What's in here

| You want to… | Go to |
|---|---|
| Try the SDK in 30 seconds without a token | [Quickstart](#quickstart-30-seconds-no-token) |
| See every channel we ship through | [Distribution channels](#distribution-channels) |
| Check pricing and what each plan unlocks | [Plans & access](#plans--access) |
| Connect an AI agent (Claude, Cursor, Codex…) | [MCP for AI agents](#mcp-for-ai-agents) |
| Set up the Workspace by role (analyst, PM, quant, creator) | [`docs/WORKSPACE_GUIDE.md`](docs/WORKSPACE_GUIDE.md) |
| Read the data model | [Data model](#data-model) |
| Find a quick recipe by role | [Recipes by role](#recipes-by-role) |
| Run end-to-end Python examples | [`examples/python/`](examples/python/) |
| Run interactive notebooks (Colab) | [`examples/notebooks/`](examples/notebooks/) |
| Read the methodology / SLA / compliance | [Documentation](#documentation) |
| Report a data error or request a feature | [Support & community](#support--community) |
| Contribute an example or notebook | [`CONTRIBUTING.md`](CONTRIBUTING.md) |

---

## The data product

Survivorship-bias-free, point-in-time US fundamentals sourced directly from SEC EDGAR.

- **12M+ filings** — 10-K, 10-Q, 8-K, 20-F, 40-F, and amendments since **1993**
- **105M+ standardized facts** across **19,000+** active and delisted US public-company entities
- **11,966 raw XBRL tags** normalized to **~286 canonical `standard_concept`** values (95%+ coverage)
- **Cloud Parquet** on Cloudflare R2 — stream with DuckDB; no database setup, no local downloads
- **PIT-correct** — every fact carries `filing_date` and millisecond-precision `accepted_at`
- **Semantic core** — every 10-K / 10-Q / 20-F's narrative sections (Risk Factors, MD&A, Business, Legal, Controls) chunked and indexed for natural-language search via the MCP server

### Why it's different

| Property | What it means for you |
|---|---|
| 🕒 **Point-in-time** | `filing_date <= trade_date` removes look-ahead bias. `accepted_at` gives intraday resolution for same-day signals. |
| ⚖️ **Survivorship-bias free** | Delisted, bankrupt, and acquired companies remain in every snapshot — your backtest sees the universe the market saw. |
| 📊 **Standardized concepts** | Both the raw XBRL tag (`fact.concept`) and the canonical name (`fact.standard_concept`) are on every row. No hidden mapping table. |
| 🔍 **CPA-verified catalog** | Every `standard_concept` carries a `review_confidence` — `1.0` once an accountant has signed off on its name, statement and rule (then it's locked; the pipeline only ever adds new concepts, never mutates a verified one), `0.7` while provisional. Filter `review_confidence >= 1.0` for the labels analysts, quants and AI models can agree on and train against. |
| 🚀 **DuckDB-native** | Millisecond analytics over remote Parquet via `httpfs`. Zero database provisioning. |
| 🔁 **Append-only restatements** | A `10-K/A` adds a new row — the original stays. Reconstruct the as-reported view of any historical date. |
| 🔐 **One token, every channel** | The same Bearer token authenticates the SDK, MCP server, and bulk-data API. |

---

## Distribution channels

The same dataset, delivered four ways so it lands where you already work.

| Channel | Audience | Endpoint / install |
|---|---|---|
| **Python SDK** | Quants, engineers, data scientists | `pip install valuein-sdk` · [PyPI](https://pypi.org/project/valuein-sdk/) |
| **MCP server** | AI agents (Claude, Cursor, Codex, custom) | `https://mcp.valuein.biz/mcp` · [server.json](server.json) |
| **Web dashboard** | Retail, executives, non-technical users | [valuein.biz](https://valuein.biz) |
| **Bulk data API** | B2B partners, fintech platforms | `https://data.valuein.biz` · [contact us](mailto:sales@valuein.biz) |

A single Stripe-issued token unlocks every channel at your tier — no per-channel billing.

---

## Plans & access

Pricing and feature scope are mirrored from [valuein.biz/pricing](https://valuein.biz/pricing) — the website is the source of truth and our checkout flow routes to the correct Stripe product.

| Plan | Universe | History | Data freshness | Price | Get it |
|---|---|---|---|---|---|
| **Sample** | S&P 500 (~500 tickers) | 5-year window | Quarterly snapshots | **Free** · no signup | Just `pip install valuein-sdk` |
| **Free** | S&P 500 (~500 tickers) | 1993 – present | Daily | **Free** · register | [Register](https://valuein.biz/signup/free) |
| **Pro** | Full active + delisted US universe (19,000+ entities) — fundamentals dataset only | 15-year rolling (2011 → present) | 24h after SEC | **$49 / mo** · $490 / yr | [Subscribe](https://valuein.biz/checkout?tier=pro&billing=monthly) |
| **Institutional** | Same universe + **smart-money dataset** (insider transactions on Forms 3/4/5/144 + institutional ownership on Forms 13F/13D/13G) | 1993 – present (unlimited) | 4h priority + filing-event webhooks | **$499 / mo** · $4,790 / yr | [Subscribe](https://valuein.biz/checkout?tier=full&billing=monthly) |
| **Enterprise** | Negotiated · dedicated infrastructure · expanded redistribution scope | Custom | Real-time 8-K + zero-retention option | Talk to us | [sales@valuein.biz](mailto:sales@valuein.biz) |

Each tier removes a *different* buyer objection — Pro removes the universe + history limits on the fundamentals dataset; Institutional adds the smart-money dataset (insider transactions + institutional ownership), unlimited history back to 1993, filing-event webhooks, and a commercial redistribution license under a business-hours SLA; Enterprise adds dedicated infrastructure and bespoke contracts.

### Pay-per-call (MPP)

Autonomous AI agents that hit a rate or tier limit can pay per request using **Stripe card tokens** — no human checkout loop. Payment uses the [Machine Payment Protocol](https://mpp.dev). The agent quotes a price, charges a card Shared Payment Token, then retries the MCP call with the confirmed token.

**Payment is card-only today.** Fetch `https://api.valuein.biz/api/mpp/well-known` to see which networks are live before paying.

| Category | Examples | Price |
|---|---|---|
| Provenance / schema | `describe_schema`, `verify_fact_lineage` | Free |
| Discovery | `search_companies`, `get_sec_filing_links` | **$0.01 / entity** |
| Fundamentals | `get_company_fundamentals`, `get_financial_ratios` | **$0.10 / entity** |
| Analytics | `get_valuation_metrics`, `get_peer_comparables`, `compare_periods`, `get_capital_allocation_profile` | **$0.50 / entity** |
| Compute | `compute_dcf`, `forensic_audit`, `generate_dcf_xlsx`, `generate_research_brief_docx`, `generate_comps_xlsx` | **$2.50 / call** |
| Screens / universe | `screen_universe`, `get_pit_universe` | **$5.00 / call** |
| Smart money (Institutional dataset) | `get_insider_transactions`, `get_insider_sentiment`, `get_institutional_holdings`, `get_manager_portfolio`, `get_blockholders`, `get_top_holders`, `get_smart_money_flow` | **$5.00 / entity** |

PAYG is priced at 5× the subscription-equivalent rate — steady-state agent usage is almost always cheaper with a [Pro or Institutional subscription](https://valuein.biz/pricing). Daily spend caps exist per token as abuse protection; caps are raisable on request. See [`AGENTS.md`](AGENTS.md) for the full three-step MPP flow.

Rate limits per tier (canonical at `https://data.valuein.biz/v1/plans`):

| Plan | Per minute | Per hour |
|---|---:|---:|
| Sample (anonymous) | 15 | 150 |
| Free | 60 | 1,000 |
| Pro | 100 | 3,000 |
| Institutional / Enterprise | 300 | 10,000 |

---

## Quickstart (30 seconds, no token)

Pick whichever Python workflow you already use — both work in any virtual environment, and both run the same code below:

```bash
# Option A — pip (universal, ships with Python)
python -m venv .venv && source .venv/bin/activate
pip install valuein-sdk
```

```bash
# Option B — uv (10–100× faster; install from https://docs.astral.sh/uv/)
uv venv && source .venv/bin/activate
uv pip install valuein-sdk
```

> **Zero-friction by design.** No `VALUEIN_API_KEY`? No problem. The SDK detects the missing token and falls back to the SAMPLE dataset (S&P 500, last 5 years); the edge gateway does the same — `GET /v1/{sp500,pro,full}/:table` with no `Authorization` header automatically 302-redirects to `/v1/sample/:table`. The snippet below runs as-is.

```python
from valuein_sdk import ValueinClient

with ValueinClient() as client:
    print(client.me())               # {plan, status, email, createdAt}
    print(client.manifest())         # snapshot id, last_updated, tables
    print(client.tables())           # currently loaded tables

    df = client.run_query("""
        SELECT r.symbol, r.name, r.sector
        FROM   "references" r
        JOIN   index_membership im ON im.cik = r.cik
        WHERE  im.index_name = 'SP500'
          AND  im.removal_date IS NULL
          AND  r.is_active = TRUE
        ORDER  BY r.name
        LIMIT  10
    """)
    print(df)
```

That's a real query against the live S&P 500 sample. Add a token only when you need full universe or full history:

```bash
# optional — sample tier works without a key
echo 'VALUEIN_API_KEY="your_token_here"' >> .env
```

The same code now reads from your tier — no other changes.

### Production pattern — context manager, typed errors, pre-built templates

```python
from valuein_sdk import (
    ValueinClient,
    ValueinAuthError,
    ValueinPlanError,
    ValueinRateLimitError,
    ValueinAPIError,
    ValueinError,
)

# Two-level try/except is intentional:
#   outer = init errors raised by ValueinClient.__enter__ (auth, manifest, 503)
#   inner = per-query errors raised by run_query / run_template (rate-limit,
#           plan denial, bad SQL). Each level dispatches by exception type so
#           you can act on the right cause — exit on auth, sleep on rate-limit,
#           upsell on plan, log + skip on a single bad row.

try:
    with ValueinClient() as client:
        try:
            # 1) Build & run a raw SQL query → pandas DataFrame
            sql = "SELECT COUNT(cik) FROM entity"
            result = client.run_query(sql)
            print(result)

            # 2) Run a named SQL template with kwargs (the SDK quotes safely)
            df = client.run_template(
                "fundamentals_by_ticker",
                ticker="AAPL",
                start_date="2020-01-01",
                end_date="2024-12-31",
                form_types=["10-K", "10-Q"],
                metrics=["TotalRevenue", "NetIncome", "OperatingCashFlow"],
            )
            print(df.head())
        except ValueinPlanError:
            print("This query needs a higher plan — see valuein.biz/pricing.")
        except ValueinRateLimitError as e:
            print(f"Rate limited; retry in {e.retry_after}s.")
        except ValueinError as ve:
            # Catch-all for any other per-query failure (validation, bad SQL, etc.)
            print(f"Query failed: {ve}")
except ValueinAuthError:
    raise SystemExit("Token missing or expired — set VALUEIN_API_KEY.")
except ValueinAPIError as e:
    print(f"Gateway error during init (HTTP {e.status_code}).")
except Exception as e:
    print(f"Initialization failed: {e}")
```

The SDK ships **54 named SQL templates** for the most common screens, ratios, and PIT backtests. List them:

```python
from valuein_sdk import ValueinClient
with ValueinClient() as c:
    print(c.list_templates())
```

Reference: [`docs/QUERY_COOKBOOK.md`](docs/QUERY_COOKBOOK.md) (DuckDB recipes) · [`docs/data_catalog.md`](docs/data_catalog.md) (canonical concepts) · [PyPI README](https://pypi.org/project/valuein-sdk/) (SDK quickstart).

---

## Recipes by role

Every link below points to a runnable script in [`examples/python/`](examples/python/) (mirror notebook in [`examples/notebooks/`](examples/notebooks/)). The Sample tier runs every example — no token, no signup.

| You are a… | Start with | What you'll see |
|---|---|---|
| **Financial analyst** | [`financial_analysis.py`](examples/python/financial_analysis.py) | Revenue trend, margin walk, peer comparison from one ticker |
| **Quant / researcher** | [`pit_backtest.py`](examples/python/pit_backtest.py) | PIT-correct factor query, restatement impact, common mistakes |
| **Portfolio manager** | [`factor_screen.py`](examples/python/factor_screen.py) | Quality + Growth + Efficiency composite z-score over the S&P 500 |
| **Trader / signals** | [`earnings_momentum.py`](examples/python/earnings_momentum.py) | YoY revenue & earnings acceleration ranking |
| **Asset manager** | [`survivorship_bias.py`](examples/python/survivorship_bias.py) | Quantify how survivorship bias inflates returns |
| **Valuation modeler** | [`dcf_inputs.py`](examples/python/dcf_inputs.py) | Free-cash-flow assembly, balance sheet, Valuein's pre-computed DCF |
| **Data engineer** | [`production-ready.py`](examples/python/production-ready.py) | Service pattern for FastAPI / Celery / Airflow |
| **First-time user** | [`getting_started.py`](examples/python/getting_started.py) | First query, token check, sector counts |
| **Building an AI agent** | [MCP for AI agents](#mcp-for-ai-agents) | Use natural language — no SDK required |

Run any of them:

```bash
# Sample tier — works without a token
python examples/python/getting_started.py

# Paid tier
VALUEIN_API_KEY=xxx python examples/python/factor_screen.py
```

---

## Data model

Full schema in [`docs/schema.json`](docs/schema.json) (machine-readable) and [`docs/data_catalog.md`](docs/data_catalog.md) (canonical concept names).

| Table | What it is | Why it matters |
|---|---|---|
| **`references`** | **Start here.** Flat join of `entity` + `security`. One row per security with `cik`, `is_active`, sector, exchange, FIGI. For membership, JOIN `index_membership` on `cik = cik`. | One scan for cross-company metadata; index membership stays in its own table so historical entry/exit is preserved. |
| `entity` | Company metadata — CIK, name, sector, SIC, status, fiscal year end | The legal entity dimension. |
| `security` | Ticker history (SCD Type 2 with `valid_from` / `valid_to`) | Resolve historical tickers, share classes, exchanges. |
| `filing` | Filing metadata — `accession_id`, `filing_date`, `report_date`, form type, amendment flag | The "what was filed when" dimension. |
| `fact` | Standardized financial facts — both raw `concept` and canonical `standard_concept` on every row | The numbers. PIT-safe via `accepted_at`. |
| `ratio` | Pipeline-computed financial ratios per filing | Skip the SQL — margins, returns, leverage, efficiency pre-calculated. |
| `valuation` | Two-stage DCF + DDM intrinsic values per entity per period | Cross-check your model against ours. |
| `taxonomy_guide` | 2026 US GAAP Taxonomy | Definitions for every `standard_concept`. |
| `index_membership` | Historical index constituents (SP500, RUSSELL1000, RUSSELL2000, RUSSELL3000) — keyed on `cik`, with `effective_date` / `removal_date` half-open windows | Reconstruct any index on any historical date. JOIN `references.cik = index_membership.cik` for company metadata. |
| `filing_text` | Narrative chunks from 10-K / 10-Q / 20-F TextBlocks (Risk Factors, MD&A, Business, Legal, Controls) | Source of the Vectorize index that powers semantic search via MCP. |

### Date columns — which to use when

| Column | Table | Use for |
|---|---|---|
| `report_date` / `period_end` | `filing` / `fact` | Aligning to the fiscal calendar |
| `filing_date` | `filing` | **PIT backtest filter** — when the SEC received it |
| `accepted_at` | `fact`, `valuation`, `filing_text` | Millisecond-precision PIT for intraday research |

> For any cross-company backtest, **always** filter by `filing_date <= trade_date`. Filtering by `report_date` introduces look-ahead bias.

### Three patterns that pay off in DuckDB

**1. Start from `references`** (one join for cross-company filters; membership is in `index_membership`):

```sql
SELECT r.symbol, r.name, r.sector
FROM   "references" r
JOIN   index_membership im ON im.cik = r.cik
WHERE  im.index_name = 'SP500'
  AND  im.removal_date IS NULL          -- current member
  AND  r.is_active     = TRUE
  AND  r.sector ILIKE '%technology%'
```

**2. `LATERAL` for the latest filing per company:**

```sql
JOIN LATERAL (
    SELECT accession_id, filing_date FROM filing
    WHERE  entity_id = r.cik AND form_type = '10-K'
    ORDER  BY filing_date DESC LIMIT 1
) f ON TRUE
```

**3. Pivot multiple concepts in one `fact` scan:**

```sql
SELECT
    MAX(CASE WHEN standard_concept = 'TotalRevenue'       THEN numeric_value END) AS revenue,
    MAX(CASE WHEN standard_concept = 'StockholdersEquity' THEN numeric_value END) AS equity
FROM   fact
WHERE  standard_concept IN ('TotalRevenue', 'StockholdersEquity')
GROUP  BY accession_id
```

> Quarterly cash flows: use `COALESCE(derived_quarterly_value, numeric_value)` — Q2/Q3 10-Qs report YTD; this column isolates the single quarter. CAPEX sign varies by filer — always `ABS(capex)`.

The full cookbook — 20 recipes, 8 anti-patterns, end-to-end factor screen — lives in [`docs/QUERY_COOKBOOK.md`](docs/QUERY_COOKBOOK.md).

### Canonical concept names

Query `fact.standard_concept` with canonical names like `'TotalRevenue'`, `'NetIncome'`, `'OperatingCashFlow'`, `'CAPEX'`, `'StockholdersEquity'` — **not** raw XBRL tags (`'Revenues'`, `'NetIncomeLoss'`, `'Assets'`). The full list lives in [`docs/data_catalog.md`](docs/data_catalog.md) and the machine-readable form is in [`docs/data_catalog.json`](docs/data_catalog.json).

---

## MCP for AI agents

Valuein ships a remote Model Context Protocol server so any MCP-capable agent (Claude Desktop, Cursor, Codex, custom) can answer fundamentals questions without writing code.

- **Endpoint:** `https://mcp.valuein.biz/mcp` (Streamable HTTP, MCP spec 2025-11-25)
- **Auth:** `Authorization: Bearer <your_api_token>` — same token as the SDK and bulk-data API
- **Manifest:** [`server.json`](server.json) — published to [registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io) as `io.github.valuein/mcp-sec-edgar`
- **Reference:** [`docs/MCP_TOOLS.md`](docs/MCP_TOOLS.md) — every tool, every parameter, every tier gate

### Tools

<!-- GEN:mcp-summary -->
The server exposes **68 live tools + 1 stub** (69 total), plus **22 agentic SOP prompts** (two flagship cross-persona briefs — `equity_research_brief` and `screen_and_shortlist` — plus specialised chains for analyst, PM, quant, ratio, smart-money, and workflow personas) and **3 data resources** (`schema://{table}`, `reference://sp500`, `pricing://current`). Tier gating happens at the data layer — Sample / Free tokens see Sample / S&P 500 data; Pro sees the full 19,000+-entity universe with a 15-year point-in-time window (2011 → present); Institutional unlocks the smart-money tools (insider transactions on Forms 3 / 4 / 5 / 144 + institutional ownership on Forms 13F / 13D / 13G), unlimited history back to 1993, filing-event webhooks, and the commercial redistribution license.
<!-- /GEN:mcp-summary -->

**Discovery & schema**

| Tool | What it does |
|---|---|
| `search_companies` | Look up tickers, names, CIKs; filter by sector, S&P 500, active status |
| `describe_schema` | Return columns, types, and descriptions for any table |
| `get_pit_universe` | The live constituent list (S&P 500 or all) for any historical `as_of_date` |

**Fundamentals & ratios**

| Tool | What it does |
|---|---|
| `get_company_fundamentals` | Income statement, balance sheet, cash flow per ticker per period |
| `get_financial_ratios` | Margins, returns, leverage, efficiency, FCF yield (per category) |
| `get_valuation_metrics` | Margins + ROIC + DCF inputs + Valuein's pre-computed valuations |
| `get_capital_allocation_profile` | CapEx intensity, buyback yield, dividend history |

**Filings & lineage**

| Tool | What it does |
|---|---|
| `get_sec_filing_links` | Direct EDGAR URLs for 10-K / 10-Q / 8-K / 20-F / 40-F |
| `verify_fact_lineage` | Trace any number back to the exact filing + accession ID it came from |

**Comparison & analytics**

| Tool | What it does |
|---|---|
| `compare_periods` | Side-by-side comparison across periods with material-change flags |
| `get_peer_comparables` | Peer set + comparable metrics by sector |
| `screen_universe` | Multi-factor screen across the universe |

**Bulk & semantic**

| Tool | What it does |
|---|---|
| `get_compute_ready_stream` | Issue presigned R2 URLs for direct Parquet streaming (skip the gateway) |
| `search_filing_text` | Semantic search over Risk Factors / MD&A / Business across every 10-K / 10-Q / 20-F (rolling out — Vectorize backfill in progress) |

**Smart money — Institutional tier and above**

The smart-money bundle replaces Bloomberg's INSIDER\<GO\> / OWNER\<GO\> / HDS\<GO\> screens with a single Valuein token. Each tool reads a per-CIK Parquet partition and returns structured rows with the `lineage` envelope for one-click SEC verification.

| Tool | What it does |
|---|---|
| `get_insider_transactions` | Form 3 / 4 / 5 / 144 line items per issuer — joined to insider_party for name + role |
| `get_institutional_holdings` | Form 13F top holders for one issuer with HHI concentration + 13F-lag staleness flag |
| `get_manager_portfolio` | Form 13F filer's full portfolio with QoQ deltas (new / increased / decreased / exited) |
| `get_blockholders` | SC 13D / 13G with the first-class `going_active` flag (13G→13D = control-change signal) |

### Configure in Claude Desktop

Add to `claude_desktop_config.json`:

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

Same URL + Bearer token works for any MCP client that supports Streamable HTTP remotes — Cursor, Codex, your own LangGraph / CrewAI agent.

---

## Examples in this repository

Every script and notebook works against the SDK published on PyPI. The Sample tier runs without a token; add `VALUEIN_API_KEY` to use a paid tier.

### Python scripts ([`examples/python/`](examples/python/))

| Script | Level | What it shows |
|---|---|---|
| [`getting_started.py`](examples/python/getting_started.py) | Beginner | First query, auth check, entity counts by sector |
| [`usage.py`](examples/python/usage.py) | Reference | Every public SDK method demonstrated end-to-end |
| [`entity_screening.py`](examples/python/entity_screening.py) | Beginner | Screen by sector, SIC code, active vs inactive |
| [`financial_analysis.py`](examples/python/financial_analysis.py) | Intermediate | Revenue trends, margins, concept normalization, peer comparison |
| [`pit_backtest.py`](examples/python/pit_backtest.py) | Intermediate | PIT discipline, restatement impact, `filing_date` vs `report_date` |
| [`survivorship_bias.py`](examples/python/survivorship_bias.py) | Intermediate | Delisted companies, index membership, bias quantification |
| [`factor_screen.py`](examples/python/factor_screen.py) | Intermediate | Composite Quality + Growth + Efficiency z-score ranking |
| [`earnings_momentum.py`](examples/python/earnings_momentum.py) | Intermediate | YoY revenue & earnings acceleration across the S&P 500 |
| [`dcf_inputs.py`](examples/python/dcf_inputs.py) | Intermediate | FCF history, balance sheet, Valuein's pre-computed DCF |
| [`production-ready.py`](examples/python/production-ready.py) | Advanced | Service pattern for FastAPI / Celery / Airflow integrations |

### Jupyter notebooks ([`examples/notebooks/`](examples/notebooks/))

| Notebook | Open in Colab |
|---|---|
| [Quickstart](examples/notebooks/quickstart.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/quickstart.ipynb) |
| [Fundamental Analysis](examples/notebooks/fundamental_analysis.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/fundamental_analysis.ipynb) |
| [PIT Backtest](examples/notebooks/pit_backtest.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/pit_backtest.ipynb) |
| [Survivorship Bias](examples/notebooks/survivorship_bias.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/survivorship_bias.ipynb) |
| [Factor Screen](examples/notebooks/factor_screen.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/factor_screen.ipynb) |
| [Earnings Momentum](examples/notebooks/earnings_momentum.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/earnings_momentum.ipynb) |
| [DCF Inputs](examples/notebooks/dcf_inputs.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/dcf_inputs.ipynb) |

---

## Documentation

Everything in [`docs/`](docs/) is kept in sync with the production data and the SDK on PyPI.

| Document | What's in it |
|---|---|
| [`docs/WORKSPACE_GUIDE.md`](docs/WORKSPACE_GUIDE.md) | Workspace welcome guide — 15-minute setup + daily/weekly/monthly playbooks per role (analyst, PM, quant, creator) |
| [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) | Sourcing, PIT architecture, restatement handling, XBRL normalization, valuation models |
| [`docs/accuracy/`](docs/accuracy/) | **Accuracy proof** — 99.58% on 12,048 S&P 500 FY filings, citable to FactSet PIT / FASB ASC / Penman, reproducible via `duckdb -c ".read scripts/accuracy/accuracy_check.sql"` |
| [`docs/QUERY_COOKBOOK.md`](docs/QUERY_COOKBOOK.md) | 20 copy-pasteable DuckDB recipes — `LATERAL`, pivots, PIT, factor screens |
| [`docs/MCP_TOOLS.md`](docs/MCP_TOOLS.md) | Reference for every MCP tool — parameters, tier gates, examples |
| [`docs/data_catalog.md`](docs/data_catalog.md) | Canonical `standard_concept` names and definitions |
| [`docs/DATA_CATALOG.xlsx`](docs/DATA_CATALOG.xlsx) | Same catalog as a workbook — columns, types, sample values |
| [`docs/data_catalog.json`](docs/data_catalog.json) | Machine-readable catalog (used by SDK metadata + docs sites) |
| [`docs/schema.json`](docs/schema.json) | Machine-readable table + column schema |
| [`docs/COMPLIANCE_AND_DDQ.md`](docs/COMPLIANCE_AND_DDQ.md) | Data provenance, MNPI policy, PIT integrity, security, SLA summary |
| [`docs/SLA.md`](docs/SLA.md) | Uptime targets, data freshness, support response times, SLA credits |

---

## Support & community

GitHub Issues is the primary support channel. Use the right template — it routes correctly and gets faster triage.

| I want to… | Open |
|---|---|
| Report incorrect or suspicious data | [Data Quality Report](https://github.com/valuein/valuein/issues/new?template=01_data_quality_report.yml) |
| Request a feature, concept, or dataset | [Feature Request](https://github.com/valuein/valuein/issues/new?template=02_feature_request.yml) |
| Report an outage or degraded service | [Service Outage](https://github.com/valuein/valuein/issues/new?template=03_service_outage.yml) |
| Ask a general question | [Q&A](https://github.com/valuein/valuein/issues/new?template=04_general_question.yml) |
| Report a security issue privately | See [`SECURITY.md`](SECURITY.md) |
| Get general help | See [`SUPPORT.md`](SUPPORT.md) |

For private or contractual matters (DPAs, procurement, DDQs, enterprise SLAs): **[support@valuein.biz](mailto:support@valuein.biz)**.

Contributions — examples, notebook improvements, documentation fixes, query recipes — are very welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the workflow and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community standards.

---

## License & disclosure

[Apache 2.0](LICENSE). See [NOTICE](NOTICE) for attribution.

This repository is provided for research and educational purposes. **It is not investment advice.** No warranty of fitness for any particular trading, investment, or regulatory purpose is implied.
