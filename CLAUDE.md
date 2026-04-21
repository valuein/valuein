# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What this repo is (and isn't)

`github.com/valuein/valuein` is the **public-facing docs, examples, and MCP-registry manifest** for
Valuein. It is the landing page a prospective user hits from PyPI, Smithery, or a Show HN post.

**This repo contains:**
- `README.md` / `CONTRIBUTING.md` / `LICENSE` / `NOTICE` — marketing + OSS governance
- `docs/` — methodology, compliance, SLA, Excel guide, data catalog (md / json / xlsx), `schema.json`,
  and `arelle_config/arelle/` (XBRL tooling config, not code)
- `examples/python/` — 7 standalone scripts that `import valuein_sdk`
- `examples/notebooks/` — 4 Jupyter notebooks mirroring the Python examples
- `scripts/generate_catalog.py` — generator that writes `docs/data_catalog.md`, `data_catalog.json`,
  and updates `DATA_CATALOG.xlsx` from canonical concepts defined inline in the script
- `server.json` — MCP server manifest for registry.modelcontextprotocol.io
- `.github/workflows/publish-mcp.yml` — publishes `server.json` on push
- `.github/ISSUE_TEMPLATE/` — data-quality report, feature request, outage, question

**This repo does NOT contain** the SDK, the MCP server, the pipeline, or any tests.
If a request mentions those, the target repo is almost certainly a sibling (see below).

---

## Sibling repos — where the actual code lives

The examples here are consumers of code published from other repos. Cross-cutting changes usually
need to start upstream, then propagate here.

| If you're asked to… | Go to |
|---|---|
| Modify SDK internals (`ValueinClient`, `transport.py`, alpha factors, SQL templates) | `~/PycharmProjects/quants` → `valuein_sdk/` |
| Modify the MCP Worker code (`mcp.valuein.biz`, 5 tools, auth) | `~/PycharmProjects/quants` → `mcp/` (or standalone at `~/WebstormProjects/mcp`) |
| Change what `fact.standard_concept` values exist, or add a concept | `~/PycharmProjects/data-pipeline` → `services/accounting/definitions.py` (`STANDARD_DEFINITIONS`), **then** re-run `scripts/generate_catalog.py` here |
| Change R2 layout, add/rename tables | `~/PycharmProjects/data-pipeline` → `run_exports.py`; update `docs/schema.json` here if public-facing |
| Change token schema, gateway routing, Stripe webhook | `~/WebstormProjects/cloudflare` |
| Edit the frontend dashboard | `~/WebstormProjects/frontend` |

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

# Open a Jupyter notebook
uv run jupyter lab examples/notebooks/quickstart.ipynb
```

**Always** use `uv run python …`, never bare `python` / `python3`.

There is no `pyproject.toml`, no `tests/`, no `release.sh`, no `pytest` suite in this repo. Tests
for the SDK live in the `quants` repo. Treat example scripts as the smoke test — if `getting_started.py`
runs cleanly on the sample tier, the published SDK version is healthy from a user's perspective.

---

## MCP registry publishing

`server.json` lists the remote MCP server at `https://mcp.valuein.biz/mcp` with the identifier
`io.github.valuein/mcp-sec-edgar`. The actual Worker code is elsewhere (`quants/mcp/` or
`~/WebstormProjects/mcp`); this file just tells the public MCP registry where to find it.

Publishing flow (`.github/workflows/publish-mcp.yml`):
1. Workflow triggers on `push` to `main` that touches `server.json`
2. Installs the `mcp-publisher` binary from the official release
3. `mcp-publisher login github` uses the workflow's OIDC `id-token: write` to authenticate
4. `mcp-publisher publish ./server.json` pushes to registry.modelcontextprotocol.io

Version bumps in `server.json` should match the Worker's deployed version in `quants/mcp/`.
Bumping here without shipping the corresponding Worker change is a silent lie to the registry.

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
`docs/schema.json` (machine-readable) and `docs/data_catalog.md` (human-readable). Both must stay in
sync with the SDK's bundled schema.

### Tables surfaced to users

`references` · `entity` · `security` · `filing` · `fact` · `valuation` · `taxonomy_guide` · `index_membership`

Start cross-company queries from `references` (denormalized entity + security + index_membership,
one row per security, boolean `is_sp500` flag). Never start from the 3-table join.

### PIT and survivorship discipline — preserve in every example

- Filter by `filing_date <= trade_date`, **never** `report_date` (look-ahead bias)
- Use `knowledge_at` for millisecond-precision PIT in intraday research
- Survivorship-bias-free → include delisted/acquired; use `status != 'ACTIVE'` (other values exist
  beyond `'INACTIVE'`/`'DELISTED'`) and `security.valid_to IS NOT NULL` for historical tickers
- `references.is_sp500` = current membership; `index_membership` = historical entry/exit dates

### `fact.standard_concept` — canonical names only

Examples must use canonical names (e.g. `'TotalRevenue'`, `'NetIncome'`, `'OperatingCashFlow'`,
`'CAPEX'`, `'StockholdersEquity'`), not raw XBRL tags (`'Revenues'`, `'NetIncomeLoss'`, `'Assets'`).
The raw tag is in `fact.concept`; the canonical form is in `fact.standard_concept`. Both columns are
on the same table — no mapping join needed, and `concept_mapping` is **internal, never show it**.

See `docs/data_catalog.md` for the canonical concept list. The source of truth is `CONCEPTS` in
`scripts/generate_catalog.py`, which must mirror `STANDARD_DEFINITIONS` in the pipeline.

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
