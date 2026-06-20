# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What this repo is (and isn't)

`github.com/valuein/valuein` is the **public-facing docs, examples, and MCP-registry manifest** for
Valuein. It is the landing page a prospective user hits from PyPI, Smithery, or a Show HN post.

**This repo contains:**
- `README.md` / `CONTRIBUTING.md` / `LICENSE` / `NOTICE` — marketing + OSS governance
- `docs/` — methodology, compliance/DDQ, SLA, data catalog (md / json / xlsx), `schema.json`,
  `MCP_TOOLS.md`, `QUERY_COOKBOOK.md`, `WORKSPACE_GUIDE.md`, `accuracy/` (measured accuracy proof),
  and `arelle_config/arelle/` (XBRL tooling config, not code)
- `examples/python/` — 12 standalone scripts that `import valuein_sdk`
- `examples/notebooks/` — 8 Jupyter notebooks mirroring the Python examples
- `scripts/generate_catalog.py` — generator that writes `docs/data_catalog.md`, `data_catalog.json`,
  and updates `DATA_CATALOG.xlsx` from canonical concepts defined inline in the script
  (current output: `concept_count=291`, `ratio_count=164` — 77 FY+TTM, 87 annual-only)
- `server.json` — MCP server manifest for registry.modelcontextprotocol.io (v2.15.0)
- `.github/workflows/` — `publish-mcp.yml` (registry publish), `sync-mcp-manifest.yml`
  (nightly + `repository_dispatch` sync of `server.json` + README from the `mcp` repo manifest),
  `doc-integrity.yml` (CI gate: IP-leak + accuracy-drift, on every push/PR)
- `.github/ISSUE_TEMPLATE/` — data-quality report, feature request, outage, question

**This repo does NOT contain** the SDK, the MCP server, the pipeline, or any tests.
If a request mentions those, the target repo is almost certainly a sibling (see below).

---

## Sibling repos — where the actual code lives

The examples here are consumers of code published from other repos. Cross-cutting changes usually
need to start upstream, then propagate here. The legacy `~/PycharmProjects/quants` repo no longer
exists — SDK and MCP are now standalone repos.

| If you're asked to… | Go to |
|---|---|
| Modify SDK internals (`ValueinClient`, `transport.py`, alpha factors, SQL templates) | `~/PycharmProjects/sdk` → `valuein_sdk/` |
| Modify the MCP Worker code (`mcp.valuein.biz`, 68 live tools + 1 stub `search_filing_text` (69 total visible; a 13th marketplace category stays hidden until Phase 2), 22 agentic SOPs, 3 resources, auth) | `~/WebstormProjects/mcp` |
| Change what `fact.standard_concept` values exist, or add a concept | `~/PycharmProjects/data-pipeline` → `services/accounting/definitions.py` (`STANDARD_DEFINITIONS`), **then** re-run `scripts/generate_catalog.py` here |
| Change R2 layout, add/rename tables | `~/PycharmProjects/data-pipeline` → `run_exports.py` + `parquet_schema.py`; then propagate to the SDK + MCP (both read the schema from the R2 manifest at runtime — the SDK no longer bundles `schema.json` since v3.2.0), `cloudflare/edge-gateway` (validates tables dynamically from the manifest), and regenerate `docs/schema.json` here last |
| Change token schema, gateway routing, Stripe webhook, agent-pay | `~/WebstormProjects/cloudflare` |
| Edit the frontend dashboard | `~/WebstormProjects/frontend` |
| Bump the MCP server version listed in the public registry | `server.json` here — push to main triggers `.github/workflows/publish-mcp.yml` |

When a user adds or renames a canonical concept in the pipeline, the flow here is:
pipeline `STANDARD_DEFINITIONS` → update `CONCEPTS` in `scripts/generate_catalog.py` → re-run it →
commit regenerated `docs/data_catalog.{md,json}` and `DATA_CATALOG.xlsx` (sheet "5. Standardized
Concepts" and the Overview "generated on" date are updated in place; other sheets preserved).

---

## Commands

```bash
# Lint + format examples and scripts (line length 100; ruff config inherited from ~/.claude defaults)
uv run ruff check examples/ scripts/ --fix && uv run ruff format examples/ scripts/

# Run an example end-to-end (sample tier works without a token)
uv run python examples/python/getting_started.py

# With a paid/sp500 token
VALUEIN_API_KEY=xxx uv run python examples/python/pit_backtest.py

# Regenerate the data catalog (md + json + xlsx) from inline CONCEPTS
uv run python scripts/generate_catalog.py
# Run from repo root — outputs to docs/data_catalog.md, data_catalog.json, DATA_CATALOG.xlsx

# Publish the MCP server manifest to registry.modelcontextprotocol.io
# This is automated: any push to main that changes server.json triggers .github/workflows/publish-mcp.yml
# To trigger manually: bump "version" in server.json, commit, push main
# server.json is also kept in lockstep with the mcp repo manifest by sync-mcp-manifest.yml
# (nightly cron + repository_dispatch [mcp-manifest-updated]); its commits then trigger publish-mcp.yml

# Open a Jupyter notebook
uv run jupyter lab examples/notebooks/quickstart.ipynb
```

**Always** use `uv run python …`, never bare `python` / `python3`.

There is no `pyproject.toml`, no `tests/`, no `release.sh`, no `pytest` suite in this repo. Tests
for the SDK live in `~/PycharmProjects/sdk` (the `valuein-sdk` PyPI package). Treat example scripts
as the smoke test — if `getting_started.py` runs cleanly on the sample tier, the published SDK
version is healthy from a user's perspective.

**CI gate — `doc-integrity.yml`** runs on every push/PR (plus `workflow_dispatch`) and is the
front-door's guardrail. Two checks: (a) **IP-leak gate** — greps `docs/schema.json`, `README.md`,
and `docs/MCP_TOOLS.md` for proprietary signal names (`factor_scores|earnings_signals|composite_rank|eps_trend_est`)
and fails the build if any appear; (b) **accuracy-drift gate** — parses every `NN.NN%` in `README.md`
and `docs/accuracy/*` and fails if it drifts >1.0pt from the honest measured figures in
`docs/accuracy/baseline.json`. Never reintroduce a scrubbed signal name and never inflate an
accuracy headline — both are mechanically blocked.

---

## MCP registry publishing

`server.json` lists the remote MCP server at `https://mcp.valuein.biz/mcp` with the identifier
`io.github.valuein/mcp-sec-edgar`. The Worker code lives in `~/WebstormProjects/mcp` (the
retired `quants/mcp/` path is gone); this file just tells the public MCP registry where to
find it.

Publishing flow (`.github/workflows/publish-mcp.yml`):
1. Workflow triggers on `push` to `main` that touches `server.json`
2. Installs the `mcp-publisher` binary from the official release
3. `mcp-publisher login github` uses the workflow's OIDC `id-token: write` to authenticate
4. `mcp-publisher publish ./server.json` pushes to registry.modelcontextprotocol.io

Version bumps in `server.json` should match the Worker's deployed version in
`~/WebstormProjects/mcp`. Bumping here without shipping the corresponding Worker change is a
silent lie to the registry.

---

## Examples — contribution rules (from `CONTRIBUTING.md`)

- Filename: `snake_case.py`, no numeric prefix
- Must import `from valuein_sdk import ValueinClient` (public PyPI package)
- Use `tables=[...]` to load only what's needed
- Must run standalone: `VALUEIN_API_KEY=xxx uv run python examples/python/file.py`
- Keep under 150 lines, one concept per file
- No hardcoded API keys, bucket names, or internal URLs
- `print()` is fine in `examples/` and `scripts/` (unlike the SDK repo, which requires `logging`)
- Before PR: `uv run ruff check examples/ --fix && uv run ruff format examples/`

When the SDK publishes a new public method or template, add an example here that exercises it —
this repo is how users discover SDK features.

---

## Data primer — what the examples assume

The examples query data shaped by the pipeline and exposed by the SDK. The schema contract here is
`docs/schema.json` (machine-readable, regenerated from `parquet_schema.py`) and `docs/data_catalog.md`
(human-readable). The SDK/MCP read the live schema from the R2 manifest at runtime — `docs/schema.json`'s
own `version` field (currently **2.16.0**) tracks the manifest/regeneration, not `parquet_schema.py`'s semver.

### Tables surfaced to users

`docs/schema.json` lists **16 tables**: `references` · `entity` · `security` · `filing` · `fact` ·
`valuation` · `index_membership` · `standard_concept` · `taxonomy_guide` · `ratio` + the 6
smart-money tables (`insider_party` · `insider_filing` · `insider_transaction` ·
`institutional_filing` · `institutional_holding` · `insider_ownership`, Institutional/`full` tier).
The `ratio` table carries `accepted_at` (PIT vintage, append-on-restatement) — filter
`accepted_at <= as_of` for look-ahead-safe, restatement-aware ratios.

Start cross-company queries from `references` (denormalized entity + security flat join, one row per
security; carries `cik`, `symbol`, `name`, `sector`, `is_active`). Never start from the 3-table join.

The `references.is_sp500` flag was **dropped in 2026-05-02** (data-pipeline commit `2a9ff95` —
"Path B: rename entity_id→cik, drop is_sp500"). For ANY membership question — current OR
historical — JOIN with `index_membership` ON `references.cik = im.cik` (same column name on both
sides post-migration 0015). This is a single-index, snapshot-only footgun that we explicitly
removed.

### PIT and survivorship discipline — preserve in every example

- Filter by `filing_date <= trade_date`, **never** `report_date` (look-ahead bias)
- Use `accepted_at` for millisecond-precision PIT in intraday research
- Survivorship-bias-free → include delisted/acquired; use `status != 'ACTIVE'` (other values exist
  beyond `'INACTIVE'`/`'DELISTED'`) and `security.valid_to IS NOT NULL` for historical tickers
- Current SP500 membership: `JOIN index_membership im ON r.cik = im.cik WHERE im.index_name = 'SP500' AND im.removal_date IS NULL`
- Historical membership on a date: `WHERE $date >= im.effective_date AND ($date < im.removal_date OR im.removal_date IS NULL)`

### `fact.standard_concept` — canonical names only

Examples must use canonical names (e.g. `'TotalRevenue'`, `'NetIncome'`, `'OperatingCashFlow'`,
`'CAPEX'`, `'StockholdersEquity'`), not raw XBRL tags (`'Revenues'`, `'NetIncomeLoss'`, `'Assets'`).
The raw tag is in `fact.concept`; the canonical form is in `fact.standard_concept`. Both columns are
on the same table — no mapping join needed, and `concept_mapping` is **internal, never show it**.

See `docs/data_catalog.md` for the canonical concept list. The source of truth is `CONCEPTS` in
`scripts/generate_catalog.py`, which must mirror `STANDARD_DEFINITIONS` in the pipeline.

### Accuracy — measured, not aspirational

There is **no hard 95% coverage gate** — unmapped raw tags fall through to `Other`. The honest,
reproducible accuracy figures live in `docs/accuracy/baseline.json`: **88.96% modern-era (≥2010,
11,423 filings) / 93.55% overall (19,617 S&P 500 FY filings)**, measured 2026-06-06 and re-derivable
via `duckdb scripts/accuracy/accuracy_check.sql`. The `doc-integrity.yml` accuracy gate pins every
public `NN.NN%` to within 1pt of these. The legacy "≥95% coverage target" string still lingering in
`scripts/generate_catalog.py` / the catalog is aspirational and contradicts these measured figures —
do not amplify it.

### DuckDB query patterns examples should follow

- `LATERAL (… ORDER BY filing_date DESC LIMIT 1)` for latest filing per company
- `MAX(CASE WHEN standard_concept = '…' THEN … END)` to pivot multiple concepts in one `fact` scan
- `QUALIFY ROW_NUMBER() OVER (…) = 1` for latest-row filtering
- `COALESCE(derived_quarterly_value, numeric_value)` for cash flow metrics (Q2/Q3 10-Qs report YTD)
- `ABS(capex)` (sign varies by filer) and `NULLIF(denominator, 0)` on every ratio

---

## Style

- Python 3.10+, line length 100, ruff for lint + format, Google-style docstrings
- Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`
- No CUSIPs anywhere (licensing risk); use FIGI and LEI
- Notebooks must mirror the matching Python script — if you change `pit_backtest.py`, update
  `pit_backtest.ipynb` in the same PR
