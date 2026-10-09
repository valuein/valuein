[![Valuein](https://www.valuein.biz/valuein/twitter-rounded.png)](https://valuein.biz)

[![PyPI version](https://img.shields.io/pypi/v/valuein-sdk?cacheSeconds=300)](https://pypi.org/project/valuein-sdk/)
[![PyPI downloads](https://img.shields.io/pypi/dm/valuein-sdk?label=pypi%20downloads&cacheSeconds=3600)](https://pypi.org/project/valuein-sdk/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/valuein-sdk/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/valuein/valuein?style=flat&cacheSeconds=3600)](https://github.com/valuein/valuein/stargazers)
[![MCP Registry](https://img.shields.io/badge/MCP-registry.modelcontextprotocol.io-blue)](https://registry.modelcontextprotocol.io)
[![Docs](https://img.shields.io/badge/docs-valuein.biz-purple)](https://valuein.biz/developers/catalog)

# Valuein — SEC EDGAR fundamentals for analysts, quants, and AI agents

> **Point-in-time, survivorship-free SEC fundamentals — built for AI agents, safe enough for institutions that fear AI.** Every number is born in a filing and carries a `fact_id`; the model never mints a digit. Streamed as Parquet, queried with DuckDB or natural language, reproducible run to run.

This repository is the **public home and discovery hub** for the Valuein data platform. It hosts the documentation, examples, notebooks, and the [MCP registry manifest](server.json) used by AI agents to find us. Source code for the SDK, MCP server, and data pipeline lives in dedicated repositories — this is the front door.

```bash
pip install "valuein-sdk>=7.0.0" # data for code
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
| See why AI agents are first-class citizens here | [Built for AI agents](#built-for-ai-agents) |
| Connect an AI agent (Claude, Copilot, ChatGPT, Cursor…) | [MCP for AI agents](#mcp-for-ai-agents) |
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

- **Every SEC-reporting US public company since 1993** — 10-K, 10-Q, 8-K, 20-F, 40-F, and amendments, for active and delisted companies alike: every bankruptcy, merger, and delisting stays in
- **Raw XBRL tags normalized to canonical `standard_concept` names** plus materialized financial ratios (FY + TTM); unmapped tags are exposed under `'Other'` rather than dropped
- **Parquet tables** — fundamentals, ratios, index membership, restatement events, price history with a total-return index, plus the smart-money and Form ADV adviser tables on the Institutional tier
- **Cloud Parquet** on Cloudflare R2 — stream with DuckDB; no database setup, no local downloads
- **PIT-correct** — every fact carries `filing_date` and millisecond-precision `accepted_at`

Counts move with every snapshot, so this page does not copy them; read them live. `client.manifest()` returns the snapshot id, `last_updated` and your plan's tables; `curl -s https://data.valuein.biz/v1/sample/manifest.json | jq .schema_version` prints the live schema version; `https://data.valuein.biz/v1/plans` gives each plan's universe size and history window; [`docs/data_catalog.md`](docs/data_catalog.md) lists the canonical concepts and ratios.

### Why it's different

| Property | What it means for you |
|---|---|
| 🕒 **Point-in-time** | `filing_date <= trade_date` removes look-ahead bias. `accepted_at` gives intraday resolution for same-day signals. |
| ⚖️ **Survivorship-bias free** | Delisted, bankrupt, and acquired companies remain in every snapshot — your backtest sees the universe the market saw. |
| 📊 **Standardized concepts** | Both the raw XBRL tag (`fact.concept`) and the canonical name (`fact.standard_concept`) are on every row. No hidden mapping table. |
| 🔍 **CPA-verified catalog** | Every `standard_concept` carries a `review_confidence` — `1.0` once an accountant has signed off on its name, statement and rule (then it's locked; the pipeline only ever adds new concepts, never mutates a verified one), `0.7` while provisional. Filter `review_confidence >= 1.0` for the labels analysts, quants and AI models can agree on and train against. |
| 🚀 **DuckDB-native** | Millisecond analytics over remote Parquet via `httpfs`. Zero database provisioning. |
| 🔁 **Append-only restatements** | A `10-K/A` adds a new row — the original stays. Reconstruct the as-reported view of any historical date. |
| 🧾 **Measured, published accuracy** | Mathematical consistency checked against published, cited accounting identities — CI-gated, and re-derivable yourself with one DuckDB command. The current measured figure lives in [`docs/accuracy/baseline.json`](docs/accuracy/baseline.json). |
| 🔐 **One token, every channel** | The same Bearer token authenticates the SDK, MCP server, and bulk-data API. |

---

## Built for AI agents

Valuein is MCP-first and agent-agnostic: the same typed tool surface works in Claude, Copilot, ChatGPT, Perplexity, Gemini, Grok, Cursor, or your own LangGraph / CrewAI agent. The design goal is simple — **the model never mints a number**. Numbers are born in tools, carried as provenance-tagged facts, and the model is only allowed to arrange words around figures it was handed.

| Guarantee | How it's enforced |
|---|---|
| **Fact-level lineage** | Every figure a tool returns carries a `fact_id` and its source filing; `verify_fact_lineage` round-trips any `fact_id` back to the exact SEC filing URL in one call. |
| **Zero look-ahead** | Every time-series tool accepts `as_of_date` and reconstructs the information set as of that date — the same PIT discipline the Parquet layer enforces for backtests. |
| **Reproducible runs** | Deterministic, idempotent tools: same inputs, same output. No rolling windows, no hidden "latest". Agents can cache, retry, and replay; you can reproduce a run later. |
| **Agent-agnostic state** | Theses, claims, watchlists, signals, and reports persist server-side across sessions *and across clients* — save a thesis from Claude today, list it from Cursor tomorrow. |
| **Human-on-the-loop (HOTL)** | Mutating and outward-facing tool actions go through a staged-action approval ledger: the agent proposes, a human approves, and the decision lands in an immutable audit entry. Read-only tools never stage. |
| **Governed managed runs** | Server-side managed agent runs execute at temperature 0 with a model allow-list and destructive-tool stripping — reproducible research, not improvisation. |
| **Graded track records** | Saved theses and claims are scored against subsequent fundamentals and prices; publishing builds a public, verifiable track record — your agent keeps score. |

The full tool reference is in [`docs/MCP_TOOLS.md`](docs/MCP_TOOLS.md); agent-facing runtime instructions are in [`AGENTS.md`](AGENTS.md).

---

## Distribution channels

The same dataset, delivered four ways so it lands where you already work.

| Channel | Audience | Endpoint / install |
|---|---|---|
| **Python SDK** | Quants, engineers, data scientists | `pip install valuein-sdk` · [PyPI](https://pypi.org/project/valuein-sdk/) |
| **MCP server** | AI agents (Claude, Copilot, ChatGPT, Cursor, custom) | `https://mcp.valuein.biz/mcp` · [server.json](server.json) |
| **Web dashboard** | Retail, executives, non-technical users | [valuein.biz](https://valuein.biz) |
| **Bulk data API** | B2B partners, fintech platforms | `https://data.valuein.biz` · [contact us](mailto:sales@valuein.biz) |

A single Stripe-issued token unlocks every channel at your tier — no per-channel billing.

---

## Plans & access

Pricing and feature scope are mirrored from [valuein.biz/pricing](https://valuein.biz/pricing) — the website is the source of truth and our checkout flow routes to the correct Stripe product.

| Plan | Universe | History | Get it |
|---|---|---|---|
| **Sample** | S&P 500 companies | Recent years | **Free**, no signup: `pip install "valuein-sdk>=7.0.0"` |
| **Benchmark** | S&P 500 companies | Full history | **Free**, [register](https://valuein.biz/register) |
| **Pro** | Full active + delisted US universe, fundamentals dataset | Rolling point-in-time window | [Subscribe](https://valuein.biz/checkout?tier=pro&billing=monthly) |
| **Institutional** | Same universe + **smart-money dataset** (insider transactions on Forms 3/4/5/144 + institutional ownership on Forms 13F/13D/13G) | Full history back to 1993 | [Subscribe](https://valuein.biz/checkout?tier=full&billing=monthly) |
| **Enterprise** | Negotiated · dedicated infrastructure · expanded redistribution scope | Custom | [sales@valuein.biz](mailto:sales@valuein.biz) |

Prices, universe sizes, history windows and rate limits are served live; read them instead of a copy:

```bash
curl -s https://data.valuein.biz/v1/plans \
  | jq '.plans[] | {displayName, priceUsd, universeSize, earliestYear, perMinute, perHour}'
```

Each tier removes a *different* buyer objection — Pro removes the universe + history limits on the fundamentals dataset; Institutional adds the smart-money dataset (insider transactions + institutional ownership), unlimited history back to 1993, filing-event webhooks, and a commercial redistribution license under a business-hours SLA; Enterprise adds dedicated infrastructure and bespoke contracts.

### Pay-per-call (MPP)

Autonomous AI agents that hit a rate or tier limit can pay per request using **Stripe card tokens** — no human checkout loop. Payment uses the [Machine Payment Protocol](https://mpp.dev). The agent quotes a price, charges a card Shared Payment Token, then retries the MCP call with the confirmed token.

**Payment is card-only today.** Fetch `https://api.valuein.biz/api/mpp/well-known` to see which networks are live before paying.

| Category | Examples | Billed |
|---|---|---|
| Provenance / schema | `describe_schema`, `verify_fact_lineage` | Free |
| Discovery | `search_companies`, `get_sec_filing_links` | per entity |
| Fundamentals | `get_company_fundamentals`, `get_financial_ratios` | per entity |
| Analytics | `get_valuation_metrics`, `get_peer_comparables`, `compare_periods`, `get_capital_allocation_profile` | per entity |
| Compute | `compute_dcf`, `forensic_audit`, `generate_dcf_xlsx`, `generate_research_brief_docx`, `generate_comps_xlsx` | per call |
| Screens / universe | `screen_universe`, `get_pit_universe` | per call |
| Smart money (Institutional dataset) | `get_insider_transactions`, `get_insider_sentiment`, `get_institutional_holdings`, `get_manager_portfolio`, `get_blockholders`, `get_top_holders`, `get_smart_money_flow` | per entity |

Live prices: `curl -s https://data.valuein.biz/v1/plans | jq '.paygRates, .toolToMeter'` (the meter each tool bills to, and its USD rate); a `402` quotes the exact price before anything is authorized. Per call, PAYG costs more than a subscription, so steady-state agent usage is almost always cheaper on a [Pro or Institutional subscription](https://valuein.biz/pricing). See [`AGENTS.md`](AGENTS.md) for the full three-step MPP flow.

**The whole pattern — an agent that buys its own data, safely** — is written up as a reference implementation in **[`docs/AGENT_ECONOMY_RAIL.md`](docs/AGENT_ECONOMY_RAIL.md)**: the two live consent models (a human-authorized bounded budget that auto-charges and serves inline; or per-call MPP for wallet-holding agents), why it's the safe default, and a runnable demo — [`examples/python/agent_buys_its_own_data.py`](examples/python/agent_buys_its_own_data.py) — that discovers the rail and reads back a live quote for free.

Rate limits per tier are the `perMinute` / `perHour` fields of `https://data.valuein.biz/v1/plans` (the `jq` command under [Plans & access](#plans--access) prints them).

---

## Quickstart (30 seconds, no token)

Pick whichever Python workflow you already use — both work in any virtual environment, and both run the same code below:

```bash
# Option A — pip (universal, ships with Python)
python -m venv .venv && source .venv/bin/activate
pip install "valuein-sdk>=7.0.0"
```

```bash
# Option B — uv (10–100× faster; install from https://docs.astral.sh/uv/)
uv venv && source .venv/bin/activate
uv pip install "valuein-sdk>=7.0.0"
```

> **Zero-friction by design.** No `VALUEIN_API_KEY`? No problem. The SDK detects the missing token and falls back to the SAMPLE dataset (S&P 500, last 5 years); the edge gateway does the same — `GET /v1/{sp500,pro,full}/:table` with no `Authorization` header automatically 302-redirects to `/v1/sample/:table`. The snippet below runs as-is.

```python
from valuein_sdk import ValueinClient

with ValueinClient() as client:
    print(client.me())               # {plan, status, email, createdAt}
    print(client.manifest())         # snapshot id, last_updated, tables
    print(client.tables())           # tables your plan can read (they load on first use)

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

The SDK ships named SQL templates for the most common screens, ratios, and PIT backtests. List the ones your installed version carries:

```python
from valuein_sdk import ValueinClient
with ValueinClient() as c:
    print(c.list_templates())
```

Reference: [`docs/QUERY_COOKBOOK.md`](docs/QUERY_COOKBOOK.md) (DuckDB recipes) · [`docs/data_catalog.md`](docs/data_catalog.md) (canonical concepts) · [PyPI README](https://pypi.org/project/valuein-sdk/) (SDK quickstart).

---

## Recipes by role

Every link below points to a runnable script in [`examples/python/`](examples/python/); most pair with a notebook in [`examples/notebooks/`](examples/notebooks/). The Sample tier runs every example except the Institutional smart-money screen — no token, no signup.

| You are a… | Start with | What you'll see |
|---|---|---|
| **Financial analyst** | [`financial_analysis.py`](examples/python/financial_analysis.py) | Revenue trend, margin walk, peer comparison from one ticker |
| **Quant / researcher** | [`factor_backtest.py`](examples/python/factor_backtest.py) | Point-in-time, survivorship-free quantile backtest with costs and IC |
| **Portfolio manager** | [`entity_screening.py`](examples/python/entity_screening.py) | Screen the S&P 500 as it stood on a past date, including later-removed members |
| **Forensic analyst** | [`restatement_radar.py`](examples/python/restatement_radar.py) | Every restated number, how it was disclosed, both filings to verify |
| **Asset manager** | [`survivorship_bias.py`](examples/python/survivorship_bias.py) | Quantify how survivorship bias inflates returns |
| **Valuation modeler** | [`dcf_inputs.py`](examples/python/dcf_inputs.py) | `client.dcf()`: a two-stage DCF with your assumptions, every input traced to its filing |
| **Auditor / compliance** | [`filing_provenance.py`](examples/python/filing_provenance.py) | Click-through SEC EDGAR links per filing — open the iXBRL viewer on the exact source document behind a number |
| **Data engineer** | [`production_service.py`](examples/python/production_service.py) | Scheduled point-in-time extract to Parquet: limits, logging, exit codes |
| **First-time user** | [`getting_started.py`](examples/python/getting_started.py) | Plan check, ticker → CIK, first fundamentals query |
| **Building an AI agent** | [MCP for AI agents](#mcp-for-ai-agents) | Use natural language — no SDK required |

Run any of them:

```bash
# Sample tier — works without a token
python examples/python/getting_started.py

# Paid tier
VALUEIN_API_KEY=xxx python examples/python/factor_backtest.py
```

---

## Data model

Full schema in [`docs/schema.json`](docs/schema.json) (machine-readable) and [`docs/data_catalog.md`](docs/data_catalog.md) (canonical concept names). Every tier reads the core tables below; the Institutional tier adds the smart-money tables (`insider_party` / `insider_filing` / `insider_transaction` / `institutional_filing` / `institutional_holding` / `insider_ownership`) and the Form ADV adviser tables. `client.tables()` lists what your plan reads; `curl -s https://data.valuein.biz/v1/sample/manifest.json | jq .schema_version` prints the live schema version.

| Table | What it is | Why it matters |
|---|---|---|
| **`references`** | **Start here.** Flat join of `entity` + `security`. One row per security with `cik`, `is_active`, sector, exchange, FIGI. For membership, JOIN `index_membership` on `cik = cik`. | One scan for cross-company metadata; index membership stays in its own table so historical entry/exit is preserved. |
| `entity` | Company metadata — CIK, name, sector, SIC, status, fiscal year end | The legal entity dimension. |
| `security` | Ticker history (SCD Type 2 with `valid_from` / `valid_to`) | Resolve historical tickers, share classes, exchanges. |
| `filing` | Filing metadata — `accession_id`, `filing_date`, `report_date`, form type, amendment flag | The "what was filed when" dimension. |
| `fact` | Standardized financial facts — both raw `concept` and canonical `standard_concept` on every row | The numbers. PIT-safe via `accepted_at`. |
| `ratio` | Pipeline-computed financial ratios per filing | Skip the SQL — margins, returns, leverage, efficiency pre-calculated. |
| `taxonomy_guide` | The US GAAP taxonomy guide | Definitions for every `standard_concept`. |
| `index_membership` | Index constituents keyed on `cik`, with `effective_date` / `removal_date` half-open windows. **SP500 is survivorship-free back to 1996** (`confidence='high'`) — real entry/exit spells including long-delisted registrants. **RUSSELL1000 / RUSSELL2000 / RUSSELL3000 go back to 2000-09-30** (`confidence='medium'`, `source='fund_holdings'`) — reconstructed from the publicly disclosed portfolio holdings of large funds tracking each index, so a fund proxies rather than defines the index, and a join or leave date is only as precise as the interval between observations (roughly one to four a year through 2006, monthly from 2007). Graded against the index provider's published reconstitution lists, which we use to measure and never redistribute: **recall 96.5–98.3%, precision 93.6–98.6%**. No Russell data before 2000-09-30, and no holdings observation between 2016-12-30 and 2017-07-31. | Reconstruct the **S&P 500** or a **Russell** index on a historical date. Branch on `confidence` — `medium` means approximate, not authoritative. JOIN `references.cik = index_membership.cik` for company metadata. |
| `standard_concept` | The canonical concept catalog itself — names, statements, mapping rules, CPA review status | The ground truth behind `fact.standard_concept`. |
| `stock_price` | Coarse price series per entity — one close per fiscal period-end and per month-end, with `total_return_index` on every row (every tier) | Value-vs-price overlays and monthly-rebalanced backtests on any tier: `tri_b / tri_a - 1` between two month-end rows is the holder's total return for that span, dividends included. |
| `stock_price_daily` | **Institutional and Pro only** — full daily OHLCV bar series per listing, with `total_return_index` and the raw corporate-action factors (`div_cash`, `split_factor`) | Backtest-safe price legs — pair with fundamentals for PIT valuation multiples. Use `total_return_index` for total return: it is forward-compounded, so unlike a back-adjusted series a later split never restates it. `adjusted_close` is a vendor passthrough and is null on the large majority of bars. Grain is one row per security per day — add `WHERE is_primary_listing` for one row per company. Prices are licensed market data, not EDGAR, so they do NOT share the 1993 fundamentals floor: no bars exist in 1993 and the earliest bar differs per security, 1994 onward. |

### Date columns — which to use when

| Column | Table | Use for |
|---|---|---|
| `report_date` / `period_end` | `filing` / `fact` | Aligning to the fiscal calendar |
| `filing_date` | `filing` | **PIT backtest filter** — when the SEC received it |
| `accepted_at` | `fact`, `filing`, `ratio` (+ smart-money and price tables) | Millisecond-precision PIT for intraday research |

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

The full cookbook — recipes, anti-patterns, an end-to-end factor screen — lives in [`docs/QUERY_COOKBOOK.md`](docs/QUERY_COOKBOOK.md).

### Canonical concept names

Query `fact.standard_concept` with canonical names like `'TotalRevenue'`, `'NetIncome'`, `'OperatingCashFlow'`, `'CAPEX'`, `'StockholdersEquity'` — **not** raw XBRL tags (`'Revenues'`, `'NetIncomeLoss'`, `'Assets'`). The full list lives in [`docs/data_catalog.md`](docs/data_catalog.md) and the machine-readable form is in [`docs/data_catalog.json`](docs/data_catalog.json).

---

## MCP for AI agents

Valuein ships a remote, protocol-native Model Context Protocol server so any MCP-capable agent (Claude, Copilot, ChatGPT, Cursor, custom) can answer fundamentals questions — and keep persistent, auditable research state — without writing code.

- **Endpoint:** `https://mcp.valuein.biz/mcp` (Streamable HTTP, MCP spec 2025-11-25)
- **Auth:** `Authorization: Bearer <your_api_token>` — same token as the SDK and bulk-data API
- **Manifest:** [`server.json`](server.json) — published to [registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io) as `io.github.valuein/mcp-sec-edgar`
- **Reference:** [`docs/MCP_TOOLS.md`](docs/MCP_TOOLS.md) — every tool, every parameter, every tier gate

### Tools

<!-- GEN:mcp-summary -->
The server exposes **121 live tools**, plus **39 agentic SOP prompts** (two flagship cross-persona briefs — `equity_research_brief` and `screen_and_shortlist` — plus specialised chains for analyst, PM, quant, ratio, smart-money, and workflow personas) and **3 data resources** (`schema://{table}`, `reference://sp500`, `pricing://current`). Tier gating happens at the data layer — Sample / Benchmark tokens see the Sample / Benchmark slices (S&P 500 constituents); Pro sees the full 19,000+-entity universe with a 15-year point-in-time window (2011 → present); Institutional unlocks the smart-money tools (insider transactions on Forms 3 / 4 / 5 / 144 + institutional ownership on Forms 13F / 13D / 13G), unlimited history back to 1993, filing-event webhooks, and the commercial redistribution license.
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
| `get_valuation_metrics` | What a company trades at, plus parameter-free reference points; intrinsic value comes from `compute_dcf` with assumptions you state |
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

**Bulk data**

| Tool | What it does |
|---|---|
| `get_compute_ready_stream` | Issue signed, expiring download URLs for direct Parquet streaming (skip the gateway) |

**Smart money — Institutional tier and above**

The smart-money bundle replaces Bloomberg's INSIDER\<GO\> / OWNER\<GO\> / HDS\<GO\> screens with a single Valuein token. Each tool reads a per-CIK Parquet partition and returns structured rows with the `lineage` envelope for one-click SEC verification.

| Tool | What it does |
|---|---|
| `get_insider_transactions` | Form 3 / 4 / 5 / 144 line items per issuer — joined to insider_party for name + role |
| `get_institutional_holdings` | Form 13F top holders for one issuer with HHI concentration + 13F-lag staleness flag |
| `get_manager_portfolio` | Form 13F filer's full portfolio with QoQ deltas (new / increased / decreased / exited) |
| `get_blockholders` | SC 13D / 13G with the first-class `going_active` flag (13G→13D = control-change signal) |
| `get_insider_sentiment` · `get_top_holders` · `get_smart_money_flow` | Aggregated insider buy/sell signal, largest holders, and net institutional flow per issuer |

**Persistent, agent-agnostic research state (all MCP clients)**

Research objects live server-side, keyed to your token — save from one AI client, read from another, score later.

| Family | Tools (representative) | What it does |
|---|---|---|
| Theses & claims | `save_thesis`, `save_claim`, `score_thesis_outcome`, `score_claim` | Time-stamped calls with provenance-bound claims, auto-graded against subsequent fundamentals **and prices** |
| Watchlists & signals | `save_watchlist`, `create_signal`, `list_signal_inbox` | Standing monitors on price moves, fundamental changes, and filings — delivered to email, webhook, dashboard inbox, or an `agent_run` that fires a standing agent team |
| Reports | `create_report`, `render_report`, `save_freeform_report` | Durable, versioned research artifacts with branded md/docx export |
| Deferral & rules | `schedule_task`, `create_rule`, `test_rule` | "Re-check AAPL margins in 30 days" → a real scheduled re-run; trigger→action rules (signal fired, inbox item, task wake, schedule tick) |
| Approvals (HOTL) | `stage_action`, `list_pending_approvals`, `approve_staged_action` | Mutating/destructive actions stage for human approval with an immutable audit entry |
| Backtesting | `run_backtest`, `get_pit_valuation_ratios`, `get_price_history` | Bounded PIT factor grids and backtest-safe valuation multiples on any historical date |
| Briefing | `get_morning_brief`, `list_agent_runs` | Read your daily brief and managed-run history from any MCP client |

**Public publishing — free reputation building (all tiers)**

Publish your saved research to a public `@handle` profile — free to build a public track record and reputation. Reports become a shareable `/r/[slug]` page discoverable via keyword catalog search (no semantic search yet); theses and claims get the same free `publish` / `unpublish` visibility toggle. This is publishing, not selling; the paid report-marketplace tools (`purchase_report`, `list_my_purchases`, `connect_stripe_account`) remain unreleased.

| Tool | What it does |
|---|---|
| `publish_report` | Publish a saved report to your public profile (`@handle`) as a shareable `/r/[slug]` page |
| `unpublish_report` | Take a previously published report private again |
| `search_reports` | Search the public report catalog by ticker, author, or keyword (keyword catalog search) |
| `publish_thesis` / `unpublish_thesis` | Toggle a saved thesis public / private on your profile — parity with `publish_report` |
| `publish_claim` / `unpublish_claim` | Toggle a saved claim public / private on your profile — parity with `publish_report` |

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

Same URL + Bearer token works for any MCP client that supports Streamable HTTP remotes — Copilot, ChatGPT, Cursor, your own LangGraph / CrewAI agent.

---

## Examples in this repository

Every script and notebook works against the SDK published on PyPI. The Sample tier runs without a token; add `VALUEIN_API_KEY` to use a paid tier.

The full learning path, with who each item is for and the plan it needs: [`examples/README.md`](examples/README.md).

### Python scripts ([`examples/python/`](examples/python/))

| Script | Level | What it shows |
|---|---|---|
| [`getting_started.py`](examples/python/getting_started.py) | Beginner | Plan, snapshot, ticker → CIK, annual revenue and net income |
| [`financial_analysis.py`](examples/python/financial_analysis.py) | Beginner | Income statement and margins, single-quarter cash flow, peer ratios |
| [`pit_backtest.py`](examples/python/pit_backtest.py) | Intermediate | The same query at two `as_of` dates gives two answers (a real restatement) |
| [`entity_screening.py`](examples/python/entity_screening.py) | Intermediate | Screen the S&P 500 as it stood on a past date |
| [`survivorship_bias.py`](examples/python/survivorship_bias.py) | Intermediate | Honest vs survivor-only equal-weight return |
| [`factor_backtest.py`](examples/python/factor_backtest.py) | Advanced | Universe → signal → forward returns → quantile backtest with costs |
| [`pit_factor_dataset.py`](examples/python/pit_factor_dataset.py) | Advanced | Point-in-time, survivorship-free factor file to Parquet and CSV |
| [`price_total_return.py`](examples/python/price_total_return.py) | Intermediate | Split and dividend effects on returns; daily helpers on Pro |
| [`restatement_radar.py`](examples/python/restatement_radar.py) | Intermediate | Disclosure mix, one verified revision, recent Item 4.02 revisions |
| [`smart_money_screen.py`](examples/python/smart_money_screen.py) | Intermediate | Insider trades, 13F holders, blockholders (Institutional) |
| [`filing_provenance.py`](examples/python/filing_provenance.py) | Beginner | A number, its recomputed `fact_id`, and links to its SEC filing |
| [`dcf_inputs.py`](examples/python/dcf_inputs.py) | Intermediate | `client.dcf()` with traced inputs, value per share, implied growth |
| [`production_service.py`](examples/python/production_service.py) | Advanced | Scheduled point-in-time extract to Parquet with limits, logging, exit codes |
| [`agent_buys_its_own_data.py`](examples/python/agent_buys_its_own_data.py) | Advanced | An agent discovers the payment rail and reads a live price quote |

### Jupyter notebooks ([`examples/notebooks/`](examples/notebooks/))

Executed on the free sample tier and committed with their output.

| Notebook | Open in Colab |
|---|---|
| [Quickstart](examples/notebooks/01_quickstart.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/01_quickstart.ipynb) |
| [Fundamentals as of a date](examples/notebooks/02_fundamentals_as_of_a_date.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/02_fundamentals_as_of_a_date.ipynb) |
| [Survivorship-free screening](examples/notebooks/03_survivorship_free_screening.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/03_survivorship_free_screening.ipynb) |
| [Point-in-time factor backtest](examples/notebooks/04_pit_factor_backtest.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/04_pit_factor_backtest.ipynb) |
| [Prices and total return](examples/notebooks/05_prices_and_total_return.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/05_prices_and_total_return.ipynb) |
| [Restatements](examples/notebooks/06_restatements.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/06_restatements.ipynb) |
| [Smart money (Institutional)](examples/notebooks/07_smart_money.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/07_smart_money.ipynb) |
| [Verify a number](examples/notebooks/08_verify_a_number.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/08_verify_a_number.ipynb) |
| [Use it from an AI assistant](examples/notebooks/09_ai_assistant.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/09_ai_assistant.ipynb) |
| [DCF valuation](examples/notebooks/10_dcf_valuation.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/10_dcf_valuation.ipynb) |
| [Piotroski F-score screen](examples/notebooks/11_piotroski_screen.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/11_piotroski_screen.ipynb) |
| [Earnings quality](examples/notebooks/12_earnings_quality.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/12_earnings_quality.ipynb) |
| [Sector comparison](examples/notebooks/13_sector_comparison.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/13_sector_comparison.ipynb) |
| [Restatement alpha](examples/notebooks/14_restatement_alpha.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/14_restatement_alpha.ipynb) |
| [Capital allocation](examples/notebooks/15_capital_allocation.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/15_capital_allocation.ipynb) |
| [Filing delay](examples/notebooks/16_filing_delay.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/valuein/valuein/blob/main/examples/notebooks/16_filing_delay.ipynb) |

---

## Documentation

Everything in [`docs/`](docs/) is kept in sync with the production data and the SDK on PyPI.

| Document | What's in it |
|---|---|
| [`docs/WORKSPACE_GUIDE.md`](docs/WORKSPACE_GUIDE.md) | Workspace welcome guide — 15-minute setup + daily/weekly/monthly playbooks per role (analyst, PM, quant, creator) |
| [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) | Sourcing, PIT architecture, restatement handling, XBRL normalization, the DCF model |
| [`docs/accuracy/`](docs/accuracy/) | **Accuracy proof** — measured source of truth is [`docs/accuracy/baseline.json`](docs/accuracy/baseline.json) (current snapshot: see baseline.json for the latest figure on modern-era ≥2010 S&P 500 FY filings), citable to FactSet PIT / FASB ASC / Penman, reproducible via `duckdb -c ".read scripts/accuracy/accuracy_check.sql"` |
| [`docs/QUERY_COOKBOOK.md`](docs/QUERY_COOKBOOK.md) | Copy-pasteable DuckDB recipes — `LATERAL`, pivots, PIT, factor screens |
| [`docs/SDK_USE_CASES.md`](docs/SDK_USE_CASES.md) | The most common SDK use cases, easiest → advanced, each linked to a notebook executed on the free tier |
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
