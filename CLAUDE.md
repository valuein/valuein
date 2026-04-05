# CLAUDE.md

This file provides guidance to Claude Code when working with the `quants` repository.

---

## Commands

```bash
# Install all dependencies (includes dev + polars)
uv sync --group dev

# Lint and format — always run together before committing
uv run ruff check . --fix && uv run ruff format .

# Run offline tests (no API key required — use this in CI and before every commit)
uv run pytest tests/ -k "not integration"

# Run integration tests (hits live API — requires VALUEIN_API_KEY)
uv run pytest -m integration

# Release (bumps version in pyproject.toml, commits, tags, pushes to PyPI)
./release.sh [major|minor|patch]

# MCP: regenerate TypeScript types from schema.json
cd mcp && npm run generate:schema

# MCP: verify committed types are up to date (runs in CI)
cd mcp && npm run check:schema
```

**Important:** Always use `uv run python ...` — never `python` or `python3` directly.

---

## Distribution Channels — Architecture

This repo ships **two parallel distribution channels**. They are independent consumers of the same R2 data, not a dependency chain.

```
[Cloudflare R2 Buckets]
  sec-data-sample   (public)
  sec-data-sp500    (sp500 plan)
  sec-data-full     (full plan)
         │
         ├── monolithic Parquet ──────────────────► edge-gateway ──► Python SDK
         │   entity / security / filing /           data.valuein.biz  (analytical SQL)
         │   fact / valuation / references / ...
         │
         └── per-entity Parquet ──────────────────► MCP Worker ────► AI Agents
             fact/{CIK}.parquet                     mcp.valuein.com   (single-company tools)
```

**SDK** (`valuein_sdk/`) — Python, DuckDB, monolithic Parquet, cross-company analytical queries.
**MCP** (`mcp/`) — TypeScript, Cloudflare Workers, per-entity Parquet, single-company tool responses.

Both share the same `TOKENS` KV namespace for auth. One Stripe token works for both.

**Schema contracts** prevent drift: `valuein_sdk/schema.json` is the single source of truth.
`mcp/src/types/schema.ts` is auto-generated from it. When `schema.json` changes, `mcp-ci.yml`
runs `npm run check:schema` and fails if `schema.ts` is stale — forcing regeneration.

### What each channel does and does NOT do

| | Python SDK | MCP Server |
|---|---|---|
| Query shape | Cross-company SQL (`SELECT ... FROM fact WHERE sector = ...`) | Single-company tool (`get_company_fundamentals("AAPL")`) |
| Engine | DuckDB (in-process) | Parquet-wasm (in-Worker V8) |
| Auth path | Bearer → edge-gateway → R2 presign | Bearer → KV → R2 Worker binding |
| Data layout | Monolithic Parquet (8 files) | Per-entity `fact/{CIK}.parquet` |
| Can use Python SDK? | — | **No** — different runtime (V8, not CPython) |

---

## MCP Server (`mcp/`)

- **Runtime**: Cloudflare Workers (TypeScript)
- **Transport**: Streamable HTTP — single `POST /mcp` (MCP spec 2025-11-25)
- **Endpoint**: `https://mcp.valuein.com/mcp`
- **Auth**: Bearer token → direct KV lookup on `TOKENS` namespace (shared with edge-gateway)
- **Tools** (5, hard limit ≤10): `search_companies`, `get_sec_filing_links`,
  `get_company_fundamentals`, `get_financial_ratios`, `get_dcf_inputs`
- **Schema types**: auto-generated to `mcp/src/types/schema.ts` from `schema.json`

**Authoritative docs**: `mcp/CLAUDE.md` and `mcp/AGENTS.md` — always read before working in `mcp/`.

**Cross-repo dependency**: if `data-pipeline/run_exports.py` changes R2 layout or table names,
update `mcp/src/data/manifest.ts` AND regenerate `mcp/src/types/schema.ts`.

---

## Business Context

**Product:** US Core Fundamentals — cleaned, standardized, point-in-time (PIT) financial data
from SEC EDGAR (10-K, 10-Q, 8-K, 20-F + amendments). 1990–present, ~108M facts, 10,000+ entities.

**Tiers:**
| Tier | Bucket | Coverage | Price |
|---|---|---|---|
| Sample | `sec-data-sample` | S&P 500, last 5 years | Free, no auth |
| sp500 | `sec-data-sp500` | ~605 current + historical S&P 500 members, full history | Free (Stripe lead capture) |
| full | `sec-data-full` | All 10,000+ entities 1990+, active + inactive | Paid subscription |

**Competitive advantages — preserve in all code and docs:**
- **Point-in-Time (PIT):** `knowledge_at` on every fact. History never overwritten. No look-ahead bias.
- **Survivorship-Bias Free:** Delisted, acquired, bankrupt companies included. Use `status != 'ACTIVE'`.
- **Standardized Concepts:** 11,966 XBRL tags → canonical `standard_concept`. Both columns on `fact`.
- **Cloud-Native:** Parquet on R2. DuckDB httpfs queries without downloading. Zero egress for large tables.

**Target customers:** Quant funds, prop shops, academic researchers, fintech startups, financial
analysts, family offices, individual algo traders.

---

## SDK Architecture

### `ValueinClient` init sequence

```
1.  load_dotenv()
2.  Transport(api_key, gateway_url) — httpx, 30s connect / 120s read, 3× exponential backoff
3.  No API key → sample mode (UserWarning, stub manifest, no network auth)
4.  GET /v1/manifest → snapshot metadata (cached 5 min via _manifest_fetched_at)
5.  GET /v1/me → plan: "sp500" | "full"
6.  _setup_duckdb():
      - memory_limit, temp_directory, max_temp_directory_size, threads (ValueinConfig)
      - INSTALL httpfs; LOAD httpfs (non-fatal — sets _httpfs_available flag)
      - SET enable_http_metadata_cache = true; SET enable_object_cache = true
7.  _load_tables():
      - Large tables (fact, filing) on authenticated plans + httpfs available:
          GET /v1/presign/{table}?expires_in=3600
          → CREATE VIEW {table} AS SELECT * FROM read_parquet('{presigned_url}')
          → stored in _remote_view_expiry (auto-refreshed within 2 min of expiry)
      - Small tables and fallback:
          GET /v1/{plan}/{table} → download → local temp dir → CREATE VIEW
8.  _build_query_map() → scans queries/*.sql → query_cache dict
9.  _init_jinja() → Jinja2 env with sql_list/sql_identifier/sql_quote filters
                    + instance-scoped lru_cache on _load_jinja_template
```

**Presign refresh**: `_maybe_refresh_remote_views()` is called before every `query()` and `stream()`
call. It silently re-mounts any view with < 120s remaining on its 1-hour presigned URL.

### SDK modules

| Path | Purpose |
|---|---|
| `client.py` | `ValueinClient`, `ValueinConfig` — public API, DuckDB setup, table mounting |
| `transport.py` | httpx HTTP layer — retries, exponential backoff, HTTP code → exception mapping |
| `exceptions.py` | Exception hierarchy (9 types) |
| `py.typed` | PEP 561 typed-package marker |
| `queries/` | 39 pre-built SQL templates (`.format()` placeholders) |
| `alpha/` | Alpha factor framework (`AlphaEngine`, `AlphaResult`, `AlphaFactor`, 7 built-ins) |

### Exception hierarchy

```
ValueinError (base)
  ├── ValueinAuthError        HTTP 401/403 — invalid/expired token
  ├── ValueinPlanError        HTTP 403 — tier insufficient
  ├── ValueinNotFoundError    HTTP 404
  ├── ValueinRateLimitError   HTTP 429 — includes .retry_after (seconds)
  ├── ValueinAPIError         HTTP 5xx — includes .status_code
  ├── ValueinDataError        parse failures, SQL errors, stream errors
  ├── ValueinConnectionError  network/DNS failures at init
  └── ValueinConfigError      invalid ValueinConfig parameters
```

### API Endpoints (edge-gateway at `data.valuein.biz`)

| Endpoint | Description | Access |
|---|---|---|
| `GET /v1/me` | Token metadata (plan, status, email) | Any valid token |
| `GET /v1/manifest` | Snapshot metadata + table list | Any valid token |
| `GET /v1/{plan}/{table}` | Serve monolithic Parquet (small tables) | plan-matched token |
| `GET /v1/presign/{table}` | SigV4 presigned R2 URL (large tables) | Any valid token |
| `GET /v1/sample/{file}` | Public sample data (no auth) | None |

### Public API surface

| Method | Returns | Notes |
|---|---|---|
| `client.query(sql)` | `pd.DataFrame` | Refreshes remote views before executing |
| `client.to_arrow(sql)` | `pyarrow.Table` | DuckDB native `fetch_arrow_table()`, zero-copy |
| `client.to_polars(sql)` | `polars.DataFrame` | Chains through Arrow; requires `pip install polars` |
| `client.stream(sql, batch_size)` | `Iterator[pd.DataFrame]` | Arrow chunks via `fetch_df_chunk`, ~2048 rows/vector |
| `client.get(table)` | `pd.DataFrame` | Always downloads fresh via transport |
| `client.run_template(name, **kwargs)` | `pd.DataFrame` | Python `.format()` render + SQL injection safe list expansion |
| `client.get_schema(table)` | `dict[str, str]` | DuckDB DESCRIBE for loaded tables; bundled schema.json fallback |
| `client.me()` | `dict` | Cached from init |
| `client.manifest()` | `dict` | Network refresh if > 5 min stale |
| `client.tables()` | `list[str]` | Sorted list of loaded table names |
| `client.health()` | `dict` | Gateway health (sample mode returns static response) |

---

## Alpha Factor Framework (`valuein_sdk/alpha/`)

The alpha framework computes fundamental factor signals across a company universe.

```python
from valuein_sdk.alpha import AlphaEngine, AlphaResult, AlphaFactor
from valuein_sdk.alpha.factors import ROE, GROSS_MARGIN, DEBT_TO_EQUITY, BUILTIN_FACTORS

# Build and compute
engine = AlphaEngine(client).add_factors(*BUILTIN_FACTORS)
result = engine.compute(
    as_of="2024-01-01",   # PIT filter: only data known before this date
    universe=["AAPL", "MSFT", "JNJ"],  # None = sp500 plan default (is_sp500=TRUE)
    min_factors=3,        # exclude companies with < 3 non-null factors
)

# Transform and score
scores = result.rank().combine()        # percentile rank → equal-weight composite
scores = result.zscore().combine(       # z-score → custom weights
    weights={"roe": 0.4, "gross_margin": 0.3, "debt_to_equity": 0.3}
)

# Export
arrow_table = result.to_arrow()         # pyarrow.Table
polars_df   = result.to_polars()        # polars.DataFrame
```

### `AlphaFactor` SQL requirements

Every factor SQL template must:
1. Return exactly four columns: `cik, symbol, name, <factor_name>`
2. Use `references` as the entry point (has `is_active`, `is_sp500`, `symbol`)
3. Contain `{as_of_filter}` inside LATERAL subquery WHERE clause
4. Contain `{universe_filter}` in the outer WHERE clause

```sql
-- Minimal factor template
SELECT r.cik, r.symbol, r.name,
    MAX(...) / NULLIF(MAX(...), 0) AS my_factor
FROM references r
JOIN LATERAL (
    SELECT accession_id FROM filing
    WHERE entity_id = r.cik AND form_type = '10-K'
    {as_of_filter}                      -- e.g. AND filing_date <= '2024-01-01'
    ORDER BY filing_date DESC LIMIT 1
) lf ON TRUE
JOIN fact f ON f.accession_id = lf.accession_id
    AND f.standard_concept IN (...)
WHERE r.is_active = TRUE {universe_filter}   -- e.g. AND r.is_sp500 = TRUE
GROUP BY r.cik, r.symbol, r.name
HAVING my_factor IS NOT NULL
```

**Security**: `as_of` is validated against `^\d{4}-\d{2}-\d{2}$` regex; tickers are
single-quote escaped before injection. No raw user input reaches SQL.

### Built-in factors

| Factor | Signal | `higher_is_better` |
|---|---|---|
| `ROE` | NetIncome / StockholdersEquity | `True` |
| `GROSS_MARGIN` | GrossProfit / TotalRevenue | `True` |
| `OPERATING_MARGIN` | OperatingIncome / TotalRevenue | `True` |
| `REVENUE_GROWTH_YOY` | (latest − prior) / prior revenue (2 × 10-K) | `True` |
| `FCF_TO_ASSETS` | (OperatingCashFlow − \|CAPEX\|) / TotalAssets | `True` |
| `DEBT_TO_EQUITY` | TotalLiabilities / StockholdersEquity | `False` |
| `ASSET_TURNOVER` | TotalRevenue / TotalAssets | `True` |

### `AlphaResult` transforms

- `rank(pct=True)` — cross-sectional percentile rank; `higher_is_better=True` → ascending rank
  (high value → pct 1.0); `higher_is_better=False` → descending rank (low value → pct 1.0)
- `zscore()` — standardize per factor (mean 0, std 1); constant columns → 0.0
- `combine(weights=None)` — weighted composite `pd.Series` indexed by symbol, sorted descending

---

## Data Schema

**Available tables:** `references`, `entity`, `security`, `filing`, `fact`, `valuation`,
`taxonomy_guide`, `index_membership`

> `concept_mapping` is internal — never expose in examples or docs. Users use
> `fact.concept` (raw XBRL) and `fact.standard_concept` (canonical).

### Core table gotchas

- **`entity.status`** — use `!= 'ACTIVE'` not `IN ('INACTIVE', 'DELISTED')` (other values exist)
- **`security.is_active`** — generated column (`valid_to IS NULL`); for delisted: `valid_to IS NOT NULL`
- **`fact` 10-K comparative periods** — `QUALIFY ROW_NUMBER() OVER (PARTITION BY fiscal_year ORDER BY period_end DESC) = 1`
- **`derived_quarterly_value`** — use `COALESCE(derived_quarterly_value, numeric_value)` for cash flow; Q2/Q3 10-Qs report YTD
- **`CAPEX` sign** — varies by filer; always `ABS(capex)`
- **`references.is_sp500`** — current S&P 500 membership; use `index_membership` only for historical entry/exit dates

### Canonical `standard_concept` names

Use these exact strings in `fact.standard_concept` queries:

| Concept | `standard_concept` | Statement |
|---|---|---|
| Revenue | `'TotalRevenue'` | IncomeStatement |
| COGS | `'CostOfRevenue'` | IncomeStatement |
| Gross Profit | `'GrossProfit'` | IncomeStatement |
| Operating Expenses | `'OperatingExpenses'` | IncomeStatement |
| R&D | `'ResearchAndDevelopment'` | IncomeStatement |
| SG&A | `'SellingGeneralAdmin'` | IncomeStatement |
| EBIT | `'OperatingIncome'` | IncomeStatement |
| Net Income | `'NetIncome'` | IncomeStatement |
| EPS Basic | `'EPS_Basic'` | IncomeStatement |
| EPS Diluted | `'EPS_Diluted'` | IncomeStatement |
| Cash | `'CashAndEquivalents'` | BalanceSheet |
| Total Assets | `'TotalAssets'` | BalanceSheet |
| Current Assets | `'CurrentAssets'` | BalanceSheet |
| Total Liabilities | `'TotalLiabilities'` | BalanceSheet |
| Equity | `'StockholdersEquity'` | BalanceSheet |
| Operating Cash Flow | `'OperatingCashFlow'` | CashFlow |
| CapEx | `'CAPEX'` | CashFlow |

**Do NOT use** raw XBRL tags like `'Revenues'`, `'NetIncomeLoss'`, `'Assets'` — those are
`fact.concept` values, not `standard_concept`.

---

## SQL Templates (`valuein_sdk/queries/`)

39 `.sql` files. Python `.format()` placeholders: `{ticker}`, `{tickers}`, `{form_types}`,
`{metrics}`, `{start_date}`, `{end_date}`.

Template key = filename without `.sql`. `form_types` and `metrics` kwargs are validated by
`run_template()` before render (allowed form types checked, list type enforced).

| Group | Templates | Category |
|---|---|---|
| Data Access | `fundamentals_by_ticker`, `figi_to_fundamentals_mapping`, `peer_group_comparison`, `survivorship_bias_free_screen` | Data Access |
| Income Statement | `revenue_yoy_growth`, `trailing_twelve_months_ttm`, `margin_analysis`, `free_cash_flow`, `rnd_intensity` | Income Statement |
| Balance Sheet | `liquidity_ratios`, `solvency_debt_to_equity`, `interest_coverage`, `efficiency_cash_conversion`, `capex_to_revenue`, `comprehensive_income_volatility` | Balance Sheet |
| Investment Scores | `dupont_analysis_inputs`, `cross_sector_dupont_roe_breakdown`, `piotroski_f_score_inputs`, `altman_z_score_inputs`, `earnings_quality_accruals_anomaly` | Investment Scores (DuPont, Piotroski, Altman Z, accruals) |
| Valuation & Screening | `sector_relative_valuation_outperformers`, `industry_leader_vs_laggard_sic_ranking`, `geographic_fundamental_concentration`, `index_constituent_aggregate_fundamentals`, `shareholder_dilution`, `cross_exchange_arbitrage_filter` | Valuation & Screening |
| Short Signals | `late_reporter_short_signal`, `filing_delay_screener`, `restatement_negative_revision_alpha`, `restatement_history`, `8k_material_event_signal`, `8k_event_frequency`, `ghost_company_screener` | Short Signals (late filers, restatements, 8-K events, ghost companies) |
| Advanced Analytics | `true_point_in_time_backtest_engine`, `time_series_outlier_detection_zscore`, `seasonal_frame_based_extraction`, `high_confidence_data_screener`, `taxonomy_guide_automated_reporting`, `xbrl_mapping_lineage_audit` | Advanced Analytics & Data Quality |

**PIT discipline:** always filter by `filing_date <= trade_date`, never `report_date`.
Use `knowledge_at` for millisecond-precision PIT in intraday signal research.

---

## Project Structure

```
quants/
├── CLAUDE.md
├── pyproject.toml           # version, deps (polars optional), ruff config
├── release.sh               # bump version → commit → tag → PyPI
├── uv.lock
├── valuein_sdk/
│   ├── __init__.py          # top-level exports: client + alpha + exceptions
│   ├── client.py            # ValueinClient, ValueinConfig
│   ├── transport.py         # httpx HTTP layer, retry, error mapping
│   ├── exceptions.py        # 9-type exception hierarchy
│   ├── schema.json          # machine-readable table/column schema (source of truth)
│   ├── py.typed
│   ├── queries/             # 39 SQL templates (01–39) + SQL_CHEATSHEET.md
│   └── alpha/
│       ├── __init__.py      # exports AlphaEngine, AlphaResult, AlphaFactor, BUILTIN_FACTORS
│       ├── engine.py        # AlphaEngine (compute), AlphaResult (rank/zscore/combine/export)
│       └── factors.py       # AlphaFactor dataclass + 7 built-in factor instances
├── mcp/
│   ├── package.json         # scripts: generate:schema, check:schema, typecheck, test
│   ├── scripts/
│   │   └── generate_mcp_types.mjs  # reads schema.json → mcp/src/types/schema.ts
│   └── src/
│       ├── types.ts         # hand-crafted auth/env/tool-response interfaces
│       └── types/
│           └── schema.ts    # AUTO-GENERATED — run: cd mcp && npm run generate:schema
├── tests/
│   ├── conftest.py          # httpx.MockTransport fixtures, client/client_full fixtures
│   ├── fixtures/            # 5-row Parquet files for offline tests
│   ├── test_client.py       # ValueinClient unit tests
│   ├── test_transport.py
│   ├── test_exceptions.py
│   ├── test_alpha.py        # 42 tests: AlphaFactor/Engine/Result transforms + E2E pipeline
│   ├── test_export.py       # to_arrow / to_polars on client + AlphaResult
│   ├── test_examples.py     # importability smoke tests for examples/python/
│   ├── test_research.py     # importability + main() for all 16 research modules
│   ├── test_integration.py  # live API tests (requires VALUEIN_API_KEY)
│   └── queries_validator.py # SQL template integration tests
├── examples/
│   ├── python/              # 6 standalone scripts (getting_started → survivorship_bias)
│   └── notebooks/           # 4 Jupyter notebooks mirroring python/ scripts
├── research/
│   ├── fundamental/         # income_statement, balance_sheet, cash_flow, dupont, altman_z
│   ├── quantitative/        # pit_correctness_proof, survivorship_bias_proof, restatements
│   ├── data_engineering/    # concept_mapping_explorer, taxonomy_coverage, filing_timeline
│   └── quality_proof/       # pit_validation, balance_sheet_check, coverage_report
├── docs/                    # METHODOLOGY, COMPLIANCE_AND_DDQ, SLA, excel-guide, DATA_CATALOG
└── excel/                   # Power Query .xlsx templates
```

---

## Testing

### Offline tests (no API key)
```bash
uv run pytest tests/ -k "not integration"
```
Uses `httpx.MockTransport` + fixture Parquet files in `tests/fixtures/`. Must always pass.
Run before every commit. Coverage target: ≥80%.

### Integration tests
```bash
VALUEIN_API_KEY=xxx uv run pytest -m integration
```

### Key test patterns
- `conftest.py` — `mock_transport` monkeypatches `Transport.__init__`; `client` fixture is sp500 plan
- Fixture Parquet files: `tests/fixtures/{entity,security,filing,fact,...}.parquet` (5 rows each)
- Alpha tests monkeypatch `client.query` to return synthetic DataFrames — no fixture data needed
- `test_alpha.py` — 42 tests covering all transforms, compute paths, filter injection, E2E pipeline
- Regenerate fixtures: `uv run python tests/fixtures/generate.py`

### Lint
- Line length: **100** (not 88)
- `research/` excluded from ruff
- Rules: `E`, `F`, `I`, `UP`, `B`, `SIM`; `E501` ignored

---

## Known Gotchas

- **`load_dotenv()` in `__init__`** — monkeypatching `VALUEIN_API_KEY` env var alone is insufficient.
  Also patch `valuein_sdk.client.load_dotenv` to `lambda: None`.
- **DuckDB httpfs warnings in offline tests** — `_load_tables` attempts presign for fact/filing,
  gets a mock 404, falls back to local download. The codec warnings are expected and harmless.
- **Presigned URLs expire** — `_maybe_refresh_remote_views()` handles this transparently.
  Never store presigned URLs beyond the client's lifetime.
- **Alpha `rank()` direction** — `higher_is_better=True` → `ascending=True` → highest value → pct 1.0.
  `higher_is_better=False` → `ascending=False` → lowest value → pct 1.0. Do not invert.
- **AlphaFactor SQL must contain both placeholders** — `{as_of_filter}` and `{universe_filter}`.
  Missing either raises `KeyError` on compute.
- **`mcp/src/types/schema.ts` is auto-generated** — never edit it manually. Run `npm run generate:schema`.
- **`index_membership` duplicates** — use `references.is_sp500` for current membership;
  use `index_membership` only for historical entry/exit dates.
- **`concept_mapping` is private** — never expose in examples or user-facing docs.
- **`to_polars()` is optional** — polars is not a core dependency. Importing it without installing
  raises `ImportError` with a clear install message. It is included in the `dev` dependency group.

---

## DuckDB Query Patterns

**Use `references` as entry point** — never start cross-company queries with the 3-table join:
```sql
-- Correct
SELECT symbol, name FROM references WHERE is_sp500 = TRUE AND is_active = TRUE

-- Avoid
SELECT s.symbol, e.name FROM entity e
JOIN security s ON s.entity_id = e.cik AND s.is_active = TRUE
JOIN index_membership im ON im.security_id = s.id AND im.end_date IS NULL
```

**LATERAL for latest filing per company:**
```sql
JOIN LATERAL (
    SELECT accession_id FROM filing
    WHERE entity_id = r.cik AND form_type = '10-K'
    ORDER BY filing_date DESC LIMIT 1
) f ON TRUE
```

**Pivot multiple concepts in one `fact` scan:**
```sql
MAX(CASE WHEN standard_concept = 'OperatingCashFlow'
    THEN COALESCE(derived_quarterly_value, numeric_value) END) AS ocf,
MAX(CASE WHEN standard_concept = 'CAPEX'
    THEN COALESCE(derived_quarterly_value, numeric_value) END) AS capex
```

**QUALIFY for latest-row filtering (DuckDB-native):**
```sql
QUALIFY ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY filing_date DESC) = 1
```

**Always:** `NULLIF(denominator, 0)` on ratios. `ABS(capex)`. `COALESCE(derived_quarterly_value, numeric_value)` for cash flow.

---

## Style Guide

- **Formatter:** `ruff format` (100-char)
- **Linter:** `ruff check` — E, F, I, UP, B, SIM
- **Python version:** 3.10+
- **Imports:** stdlib → third-party → local (I001 enforced)
- **Docstrings:** Google style on all public functions
- **Commits:** Conventional (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`)
- **No `print()` in SDK code** — use `logging` (logger: `valuein_sdk` or `valuein_sdk.alpha`)
- **No CUSIPs** — use FIGI and LEI only (licensing risk)
- **No hardcoded absolute paths in tests** — use `Path(__file__).parent`

---

## Key Reminders

1. **3-minute test.** A new user must reach real data in under 3 minutes from `pip install`.
2. **PIT is the premium.** `filing_date <= trade_date`, never `report_date`. Reinforce everywhere.
3. **Survivorship-bias free.** `status != 'ACTIVE'` (not string literals). `index_membership` for index analysis.
4. **`standard_concept` is the moat.** 11,966 XBRL tags normalized. Never bypass or expose raw tags as canonical.
5. **DuckDB is the engine.** Zero-copy httpfs for large tables. Arrow path for all exports.
6. **Schema drift is silent.** Any `schema.json` change must trigger `npm run generate:schema` in `mcp/`.
7. **Channels are parallel.** SDK and MCP are independent consumers. SDK cannot run in V8. Do not conflate.
8. **Notebooks mirror Python files.** When an example changes, update its notebook. Run `ruff check .` after.
