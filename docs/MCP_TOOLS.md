# Valuein MCP — Tool Reference

Valuein's MCP server exposes SEC EDGAR fundamentals to any MCP-capable AI client (Claude Desktop, Cursor, Codex, custom agents). It speaks the **Streamable HTTP** transport from MCP spec **2025-11-25**.

- **Endpoint:** `https://mcp.valuein.biz/mcp`
- **Auth:** `Authorization: Bearer <your_api_token>` — same Stripe-issued token as the SDK and Excel
- **Registry:** `io.github.valuein/mcp-sec-edgar` on [registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io)
- **Manifest in this repo:** [`server.json`](../server.json)

The server registers **14 live tools + 1 stub** (`search_filing_text`, rolling out as the Vectorize backfill completes), **8 analyst SOP prompts**, and **2 reference resources**. Tier gating happens at the data layer — Sample / Free tokens see Sample / S&P 500 data; Pro and Enterprise see the full universe and the full history.

---

## How to connect

### Claude Desktop

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

### Cursor / Codex / any Streamable-HTTP MCP client

Same URL + Bearer token. The server advertises tool, prompt, and resource listings on the standard MCP discovery endpoints — no extra configuration needed.

### Sample token

The Sample tier works without a token but only against the S&P 500 sample slice. To explore the full universe and history, [register](https://valuein.biz/signup/free) (Free, S&P 500 only) or [subscribe](https://valuein.biz/pricing) (Pro / Enterprise).

---

## Discovery & schema

### `search_companies`

Look up tickers, names, or CIKs and filter by sector, S&P 500 membership, and active status.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `query` | string | one of these is required | Free-text search across ticker, name, alias |
| `cik` | string | one of these is required | Exact CIK lookup |
| `sic_code` | string | optional | Filter by SIC industry code |
| `is_active` | boolean | optional | Default `true` |
| `is_sp500` | boolean | optional | Current S&P 500 membership |
| `limit` | integer | optional | Default 25, max 200 |

Returns: `[{cik, ticker, name, sector, industry, is_sp500, is_active}]`.

### `describe_schema`

Return the columns, types, and descriptions for any table. Useful when an agent needs to construct a custom query plan.

| Parameter | Type | Required |
|---|---|---|
| `table` | string | yes — one of `references`, `entity`, `security`, `filing`, `fact`, `ratio`, `valuation`, `taxonomy_guide`, `index_membership`, `filing_text` |

Returns: `{table, description, columns: [{name, type, description, primary_key?, references?}]}`.

### `get_pit_universe`

Reconstruct the index constituent list as it stood on a historical date. Use this for survivorship-bias-free backtests.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `as_of_date` | date | yes | The historical date (YYYY-MM-DD) |
| `universe` | string | optional | `sp500` (default) or `all` |
| `sector` | string | optional | Filter to a sector |

Returns: `[{ticker, cik, name, sector, included_since}]`.

---

## Fundamentals & ratios

### `get_company_fundamentals`

Income statement, balance sheet, and cash flow per ticker per period.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `ticker` | string | yes | |
| `period` | string | optional | `annual` (default) or `quarterly` |
| `fiscal_year` | integer | optional | Limit to one fiscal year |
| `as_of_date` | date | optional | PIT cutoff — filter by `filing_date <= as_of_date` |
| `limit` | integer | optional | Default 10, max 40 |

Returns: `{ticker, periods: [{fiscal_year, fiscal_period, period_end, filing_date, revenue, gross_profit, operating_income, net_income, eps_diluted, total_assets, total_liabilities, stockholders_equity, operating_cash_flow, capex, ...}]}`.

### `get_financial_ratios`

Pre-computed ratios by category. No SQL required.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `ticker` | string | yes | |
| `categories` | string[] | optional | Any of `profitability`, `liquidity`, `solvency`, `efficiency`, `valuation` |
| `period_end_before` | date | optional | PIT cutoff |
| `is_ttm` | boolean | optional | Trailing-twelve-months instead of fiscal-year |

Returns: `{ticker, period_end, ratios: {...}, source: {accession_id, filing_date}}`.

### `get_valuation_metrics`

Margins, returns, DCF inputs, and Valuein's pre-computed two-stage DCF + DDM valuations side by side. Useful when the agent needs to cross-check its own model.

| Parameter | Type | Required |
|---|---|---|
| `ticker` | string | yes |
| `period_end` | date | optional — defaults to latest fiscal year |
| `as_of_date` | date | optional — PIT cutoff |

Returns: `{ticker, period_end, margins, roic, dcf_inputs: {fcf_base, wacc, stage1_growth, stage1_years, terminal_growth}, valuations: {dcf_per_share, dcf_fcf_per_share, ddm_per_share, data_quality}}`.

### `get_capital_allocation_profile`

Where does the cash go — capex, buybacks, dividends? Pre-computed per period.

| Parameter | Type | Required |
|---|---|---|
| `ticker` | string | yes |
| `as_of_date` | date | optional — PIT cutoff |

Returns: `{ticker, capex_intensity_pct, buyback_yield_pct, dividend_history: [{period, dps, payout_ratio_pct}], net_issuance}`.

---

## Filings & lineage

### `get_sec_filing_links`

Direct EDGAR URLs for a company's filings.

| Parameter | Type | Required |
|---|---|---|
| `ticker` | string | yes |
| `form_types` | string[] | optional — any of `10-K`, `10-Q`, `8-K`, `20-F`, `10-K/A`, `10-Q/A` |
| `limit` | integer | optional — default 20 |

Returns: `[{accession_id, filing_date, form_type, url, is_amendment}]`.

### `verify_fact_lineage`

Trace any number we report back to the exact filing it came from. Critical for analysts and compliance reviewers.

| Parameter | Type | Required |
|---|---|---|
| `ticker` | string | yes |
| `concept` | string | yes — canonical `standard_concept` |
| `period_end` | date | yes |

Returns: `{value, raw_xbrl_tag, accession_id, form_type, filing_date, accepted_at, filing_url}`.

---

## Comparison & analytics

### `compare_periods`

Side-by-side comparison across periods with material-change flags.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `ticker` | string | yes | |
| `period_ends` | date[] | yes | Two or more period-end dates |
| `concepts` | string[] | yes | Canonical `standard_concept` names |

Returns: `{ticker, periods: [{period_end, values: {...}}], deltas: [{concept, abs_change, pct_change, flagged}], material_changes: [...]}`.

### `get_peer_comparables`

Peer set + comparable metrics by sector or SIC.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `ticker` | string | yes | |
| `sector` | string | optional | Defaults to the ticker's sector |
| `metric_category` | string | optional | `profitability`, `growth`, `valuation`, `quality` |
| `limit` | integer | optional | Default 10 |

Returns: `[{peer_ticker, peer_name, metrics: {...}}]`.

### `screen_universe`

Factor-score-driven screen. The MCP server pre-computes factor scores per period and exposes them via this tool — no need to send raw SQL.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `sector` | string | optional | |
| `sort_by` | string | optional | One of `quality`, `growth`, `value`, `momentum`, `composite` |
| `is_sp500` | boolean | optional | |
| `limit` | integer | optional | Default 25 |

Returns: `[{ticker, name, sector, factor_scores: {...}}]`.

### `get_earnings_signals`

EPS trends and surprise metrics around earnings releases.

| Parameter | Type | Required |
|---|---|---|
| `ticker` | string | yes |
| `as_of_date` | date | optional |

Returns: `{ticker, recent_quarters: [{period_end, eps_actual, eps_consensus_proxy, surprise_pct, post_release_volatility}]}`.

---

## Bulk & semantic

### `get_compute_ready_stream`

Issue a presigned R2 URL for direct Parquet streaming — bypass the gateway when the agent needs to push data into its own DuckDB or PyArrow context.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `table` | string | yes | One of the partitioned tables: `fact`, `ratio`, `filing`, `valuation` |
| `entity_ids` | string[] | optional | Limit to specific CIKs |
| `expires_in_seconds` | integer | optional | Default 600, max 3600 |

Returns: `{presigned_r2_url, expires_at, schema_url}`. The agent should fetch the schema URL too — it lists column types and the partition layout.

### `search_filing_text` *(rolling out)*

Semantic search over Risk Factors, MD&A, Business, Legal Proceedings, and Controls & Procedures sections of every 10-K / 10-Q / 20-F since 2019.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `query` | string | yes | Natural-language query (e.g. "supply chain fragility from Asia") |
| `sector` | string | optional | Filter |
| `as_of_date` | date | optional | PIT cutoff |

Returns: `[{ticker, accession_id, section, chunk_no, preview, score, filing_url}]`.

> **Status (April 2026):** the Vectorize backfill is in progress. Until backfill completes, the tool returns a "coming soon" status code so agents can fall back to `get_compute_ready_stream` against the `filing_text` table.

---

## Prompts (analyst SOPs)

These are pre-written multi-step instructions an MCP-aware agent can invoke as a single high-level command. Each chains the right tools in the right order.

| Prompt | What it does |
|---|---|
| `margin_and_moat_teardown` | Decompose a company's margin structure and quantify its moat using ratios + peer comparables |
| `peer_benchmarking_memo` | Generate a sector peer-benchmarking memo — financials, ratios, valuation gap |
| `quality_and_risk_audit` | Earnings-quality and accruals audit, plus restatement and 8-K event scan |
| `capital_allocation_review` | Multi-year review of capex / buyback / dividend trade-offs and ROIC trend |
| `ratio_deep_dive` | DuPont decomposition + Piotroski + Altman + interest coverage on one ticker |
| `sector_ratio_screen` | Sector-relative outlier screen across the ratio table |
| `survivorship_free_backtest` | Construct a survivorship-bias-free universe and run a factor-rebalance backtest |
| `pit_factor_constructor` | Build a PIT-correct factor (with `filing_date <= trade_date` discipline) |

Invoke a prompt the same way as a tool — most clients surface them in the same picker.

---

## Resources

The server exposes two read-only resources for grounding the agent:

| URI | What it is |
|---|---|
| `schema://{table}` | Column-level schema for any of the published tables |
| `reference://sp500` | Current S&P 500 constituent list |

Resources are cheaper to read than tool calls — agents that just need schema or a ticker list should pull from these.

---

## Tier matrix at a glance

All tools are callable on every paid tier. **What changes is the data the tool can see:**

| Tier | Data the agent sees |
|---|---|
| Sample (anonymous) | S&P 500 sample · 5-year window |
| Free | S&P 500 · 1994 – present |
| Pro | Full universe (16,000+ tickers) · 10-year history · 24h freshness |
| Enterprise | Full universe · 1994 – present · 4h priority freshness |
| Custom | Negotiated scope · real-time 8-K push · redistribution license |

A `ValueinPlanError`-equivalent MCP error is raised when a tool call needs data outside the bound tier — the agent should suggest the user upgrade at [valuein.biz/pricing](https://valuein.biz/pricing).

---

## Versioning & registry

The published manifest in [`server.json`](../server.json) at the root of this repo is the source of truth for the MCP registry. Any push to `main` that touches `server.json` triggers `.github/workflows/publish-mcp.yml`, which authenticates with GitHub OIDC and publishes to `registry.modelcontextprotocol.io`. The `version` field must always match the deployed Worker version.

Server identifier: `io.github.valuein/mcp-sec-edgar` · Repository: `https://github.com/valuein/valuein`.
