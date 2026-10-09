# CLAUDE.md

Public hub of Valuein: docs, examples, notebooks, MCP-registry manifest; no SDK, MCP, pipeline or app code. Cross-repo rules and approvals live in `~/.claude/CLAUDE.md`. Every rule below names the code or test that makes it true; if the code moves, fix the rule. Repo map: `ARCHITECTURE.md` (its purpose, goals and guardrails mirror this file: change both in one PR).

⚠️ PUBLIC repo: nothing internal or unannounced (tokens, infrastructure ids, customer data, unshipped products). The SDK, MCP, pipeline and infrastructure repos are private: never link them (`CONTRIBUTING.md` "What goes here vs. upstream"). Updated LAST: it documents what shipped.

## Read before you touch (on demand, not auto-loaded)

| Touching | Read first |
|---|---|
| `server.json`, README `GEN:mcp-summary` block, registry publish | header comments of `.github/workflows/sync-mcp-manifest.yml` + `publish-mcp.yml`; docstrings of `scripts/sync_mcp_manifest.py`, `scripts/check_registry_sync.py` |
| A public number or accuracy claim, `docs/accuracy/*` | `docs/accuracy/README.md`, `docs/accuracy/baseline.json` (`_definition`, `measured_at`) |
| An example or notebook | `CONTRIBUTING.md` "Examples — contribution rules", `docs/QUERY_COOKBOOK.md` |
| `docs/schema.json`, the data catalog | `scripts/generate_catalog.py` docstring; `data-pipeline:parquet_schema.py` (authoritative) |

## Stack & layout

- Docs, examples and CI only: no pyproject, no app code; `tests/` holds only the publish guard.
- `README.md` · `AGENTS.md` · `CONTRIBUTING.md` · `docs/` (guides, `schema.json`, data catalog, `accuracy/`, `arelle_config/` XBRL tool config) · `examples/python/` + `examples/notebooks/` · `scripts/` · `server.json`.
- Four channels, one Bearer token: SDK (PyPI `valuein-sdk`), MCP, Bulk Data API, web dashboard (no Excel/Power Query channel). Plans, prices, limits: `cloudflare:shared/plans.ts`, live `https://data.valuein.biz/v1/plans`; never copy them.

## Commands — run off the dev box (`~/.claude/CLAUDE.md`)

```bash
# always uv run, never bare python; no ruff config is checked in, so pass the line length (CONTRIBUTING.md: 100)
uv run ruff check examples/ scripts/ --fix --line-length 100 && uv run ruff format examples/ scripts/ --line-length 100
uv run --with 'pytest>=8,<10' pytest tests -q            # publish guard, as in CI
uv run python scripts/generate_catalog.py                # network; rewrites docs/data_catalog.{md,json} + DATA_CATALOG.xlsx
uv run python scripts/sync_mcp_manifest.py --check       # exit 1 stale, 3 publish guard refused
uv run python scripts/check_registry_sync.py --check     # exit 1 registry drift, 2 indeterminate
```

## Branches, CI, deploy

- Branch `feat|fix|docs/short-description` from `main`, PR to `main`, squash merge, conventional commits; never push to `main` (only the sync bot does). There is no deploy: a merge is public at once and the registry publish is the only release.
- `.github/workflows/doc-integrity.yml` (every push/PR, `workflow_dispatch`):
  - IP-leak: greps EVERY tracked file for the proprietary-signal denylist `factor_scores|earnings_signals|composite_rank|eps_trend_est`; only lines quoting that exact string are exempt (the published tool `get_earnings_signals` passes). ⚠️ Never regenerate `docs/schema.json` wholesale from `data-pipeline:parquet_schema.py` (the gate says so).
  - Accuracy drift: any `NN.NN%` (two decimals, 50 to 100) in `README.md` or `docs/accuracy/*.{md,json}` must sit within 1 pt of `baseline.json` `overall`, `modern_2010_onward` or `unstandardized_facts` (pre-2010 is deliberately excluded). Whole-number percents are not checked: cite the file.
- `server.json` is bot-written: `sync-mcp-manifest.yml` (cron 03:00 UTC, `repository_dispatch` `mcp-manifest-updated` from the MCP prod deploy, `workflow_dispatch`) rewrites `version`, `tools_summary` and the README block from `https://mcp.valuein.biz/manifest.json`. ⚠️ Never hand-edit them: a registry version is immutable (a second publish is rejected), and a hand bump falsely claims what is deployed. ⚠️ A local `sync_mcp_manifest.py` run prefers a sibling `~/WebstormProjects/mcp/manifest.json` over the live manifest (`load_manifest`): never commit its output.
- ⚠️ A `GITHUB_TOKEN` push never fires `publish-mcp.yml`'s `push` trigger, so the sync calls it via `workflow_call` with the pushed SHA, only when `check_registry_sync.py` reports the registry stale. Never gate publishing on a repo diff: after one failed publish nothing diffs and publishing is skipped forever. Drift is registry vs live Worker, never file vs Worker.
- Publish guard (`doc-integrity.yml` runs `pytest tests`; `tests/test_sync_mcp_manifest.py`): `HIDDEN_TOOLS` in `scripts/sync_mcp_manifest.py`: a manifest listing one (any status), unjudgeable counts, or a `server.json` naming one exits 3 and writes nothing. Remove a name only when that tool ships.

## Accuracy and data claims

- Accuracy figures come only from `docs/accuracy/baseline.json`, quoted with its qualifiers: S&P 500 universe, evaluable filings only, "clean" = passes every active error-severity identity (`standardized_facts._definition`). `data-pipeline:.github/workflows/publish-accuracy-baseline.yml` rewrites it after each successful pipeline run (weekly, not nightly); a missed publish is silent: check `measured_at`.
- ⚠️ `docs/accuracy/identities.json` lags `data-pipeline:scripts/QA/identities.sql`: `baseline.json` `top_remaining_pareto` names identity keys (`bs_07_ppe_net`) the catalog lacks. Never call it "exactly the set evaluated".
- ⚠️ The "95% coverage target" strings in `scripts/generate_catalog.py` (`_write_markdown`, `_write_json`) contradict the measured figures: never repeat them.
- `scripts/generate_catalog.py` takes concept names from the live manifest (`DEFAULT_MANIFEST_URL`, override `VALUEIN_MANIFEST_URL`); only ratios are inline (`RATIOS`).
- No CUSIP/CINS/ISIN anywhere: FIGI and LEI (`docs/METHODOLOGY.md`, `sdk:tests/test_identifier_policy.py`). `concept_mapping` is internal: never document it.
- Restatement `disclosure_class` is `non_reliance` | `amended` | `undisclosed`; never call the third "silent" or "hidden" (`docs/schema.json`, `frontend:src/lib/workspace/radar.test.ts`).

## Data primer — what examples and docs assume

Columns: `docs/schema.json` (public subset); query patterns: `docs/QUERY_COOKBOOK.md`.

- Start cross-company queries from `references` (one row per security: `cik`, `symbol`, `name`, `sector`, `status`, `is_active`), never the 3-table join.
- ⚠️ No `is_sp500` flag: membership is `JOIN index_membership ON cik`, half-open (`effective_date <= D < removal_date`; NULL `removal_date` = current).
- ⚠️ PIT: filter `filing_date <= trade_date` (`accepted_at` for intraday), never `report_date`/`period_end`. `ratio.accepted_at` is the vintage (append-on-restatement): filter `<= as_of`, then keep the latest vintage.
- ⚠️ `ratio` holds FY and TTM rows: filter `is_ttm`/`fiscal_period` or screens double-count (`scripts/generate_catalog.py` `_RATIO_FY_TTM_NOTE`).
- ⚠️ `fact.restated` is computed on the warehouse's current state, not PIT: informational only (`docs/schema.json`).
- Survivorship-free: keep non-`ACTIVE` `entity.status` rows and securities with `valid_to IS NOT NULL`; do not restrict history to `is_active`.
- ⚠️ `stock_price_daily` is per SECURITY: filter `security_id` (or `is_primary_listing`), use `total_return_index`, never `close`. Prices are licensed data from 1994 at the earliest, not EDGAR's 1993 floor.
- Use canonical `fact.standard_concept` names (`TotalRevenue`, `NetIncome`, `OperatingCashFlow`, `CAPEX`, `StockholdersEquity`; list in `docs/data_catalog.md`), not raw tags (`fact.concept`). `COALESCE(derived_quarterly_value, numeric_value)` for cash flow, `ABS(capex)`, `NULLIF(denominator, 0)`.
- ⚠️ The `valuation` table is gone (schema 3.0.0, `data-pipeline:parquet_schema.py`): write no example against it; DCFs come from `client.dcf()` (local, every input traced; notebook 10) or MCP `compute_dcf`. SDK 7.0 removed the `generate_*` document proxies: files come from the Workspace or the MCP tools.

## Examples and notebooks

- Scripts: one concept per file, snake_case names (no numeric prefix), under 150 lines, `from valuein_sdk import ValueinClient`, `with ValueinClient() as client:`, module docstring, no keys, bucket names or internal URLs (`CONTRIBUTING.md`). The client is lazy (a table downloads on first use); `tables=[...]` forces an eager load, so do not add it for speed.
- Notebooks: `NN_snake_case.ipynb` (the numeric prefix is the learning-path order indexed in `examples/README.md`), committed with outputs executed on the sample tier.
- Standalone on the sample tier, or the docstring states the minimum tier (`smart_money_screen.py` needs `full`; daily-bar sections need Pro). ⚠️ `ValueinClient()` silently picks up `VALUEIN_API_KEY` or a `.env` found upward from the cwd: pass `api_key=""` to force the sample tier (`sdk:valuein_sdk/client.py`).
- `client.run_query(sql)`, `client.run_template(name, **kwargs)`: kwargs only, bare ticker; `client.query()` is gone (SDK 3.0.0); pinned by `sdk:tests/test_run_template.py` `TestCallingConvention`.
- A script and its paired notebook (pairs listed in `examples/README.md`, e.g. `01_quickstart.ipynb` = `getting_started.py`) change together in one PR.
- Only `pit_factor_dataset.py` runs in automation (`sdk:.github/workflows/example-live-smoke.yml`, non-blocking): run any other example you touch.

## AGENTS.md

External-agent-facing product document, not Claude instructions: `cloudflare:workers/agent-pay/src/routes/discovery.ts` (`AGENTS_MD_URL`) links agents to its GitHub URL, so keep its path, purpose and audience. Sources: tiers, prices, rate card `cloudflare:shared/plans.ts` (`PLANS`, `PAYG_TOOL_PRICING`); payment behaviour `cloudflare:workers/agent-pay/src/routes/mpp-{call,receipt}.ts`; MCP tools `mcp:manifest.json`; SDK calls `sdk:valuein_sdk/client.py`. No hardcoded counts or versions, no internal repos. Never promise "not charged" beyond `mpp-call` (`PAYMENT_STATE_UNKNOWN`, receipt `unconfirmed`). It moves with `CONTRIBUTING.md`.

## Docs & git

- Update `README.md` only for upstream changes; its MCP counts are bot-written.
- Conventional commits; a PR says what was wrong, what is right now, and the source of truth.
