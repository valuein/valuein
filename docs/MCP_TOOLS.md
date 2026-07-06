# Valuein MCP — Tool Reference

Valuein's MCP server exposes SEC EDGAR fundamentals to any MCP-capable AI client (Claude, Copilot, ChatGPT, Cursor, custom agents). It speaks the **Streamable HTTP** transport from MCP spec **2025-11-25**.

- **Endpoint:** `https://mcp.valuein.biz/mcp`
- **Auth:** `Authorization: Bearer <your_api_token>` — same Stripe-issued token as the SDK and bulk-data API
- **Registry:** `io.github.valuein/mcp-sec-edgar` on [registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io)
- **Manifest in this repo:** [`server.json`](../server.json)

The server registers **95 live tools** across its data-lookup, screening, price & market data, smart-money, persisted-state (theses / claims / watchlists / citation-overrides / alerts CRUD / reports / scheduled tasks / rules / staged-action approvals / morning brief & agent runs), report-publishing, compute (DCF / forensic audit / bounded PIT backtest), and document-generation categories. Free visibility-toggle tools let any user build a public `@handle` profile and reputation: `publish_report` / `unpublish_report` / `search_reports` for reports, plus matching `publish_thesis` / `unpublish_thesis` and `publish_claim` / `unpublish_claim` parity for theses and claims. Reports are discovered via keyword catalog search (`search_reports`, pure-D1) — there is no semantic search yet. A separate selling category (3 tools — `purchase_report`, `list_my_purchases`, `connect_stripe_account`) ships hidden until the paid report marketplace launches. **28 analyst SOP prompts** (three flagship cross-persona workflows + specialised chains, daily flows, and state-lifecycle playbooks) and **3 reference resources** round out the surface. Tier gating happens at the data layer — Sample / Free tokens see Sample / S&P 500 data; Pro sees the full 19,000+-entity US universe with a 15-year rolling point-in-time window (2011 → present, 10-K / 10-Q / 8-K / 20-F / 40-F + amendments); Institutional unlocks the smart-money dataset (insider transactions on Forms 3 / 4 / 5 / 144 + institutional ownership on Forms 13F / 13D / 13G), unlimited history back to 1993, filing-event webhooks, and the commercial redistribution license; Enterprise (custom contract) adds dedicated infrastructure and bespoke SLA.

This document covers the core data tools in detail; the full 95-tool surface (including the persisted-state, approval-ledger, scheduled-task, and rule-engine families summarised below) is advertised by the live server's `tools/list` and mirrored in [`server.json`](../server.json).

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

### Cursor / Copilot / any Streamable-HTTP MCP client

Same URL + Bearer token. The server advertises tool, prompt, and resource listings on the standard MCP discovery endpoints — no extra configuration needed.

### Sample token

The Sample tier works without a token but only against the S&P 500 sample slice. To explore the full universe and history, [register](https://valuein.biz/signup/free) (Free, S&P 500 only) or [subscribe](https://valuein.biz/pricing) (Pro / Institutional).

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
| `table` | string | yes — any published table, e.g. `references`, `entity`, `security`, `filing`, `fact`, `ratio`, `valuation`, `taxonomy_guide`, `index_membership`, `standard_concept`, `stock_price`, `stock_price_daily` (+ the smart-money tables on Institutional). The valid set is resolved from the live manifest — see [`schema.json`](schema.json). |

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
| `form_types` | string[] | optional — any of `10-K`, `10-Q`, `8-K`, `20-F`, `40-F`, `10-K/A`, `10-Q/A`, `20-F/A`, `40-F/A` |
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

Returns: `[{ticker, name, sector, scores: {...}}]`.

---

## Bulk data

### `get_compute_ready_stream`

Issue a signed, expiring download URL for direct Parquet streaming — bypass the gateway when the agent needs to push data into its own DuckDB or PyArrow context. The URL is Range-enabled, so DuckDB / Polars `httpfs` can read it like any remote Parquet file.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `table` | string | yes | One of the partitioned tables: `fact`, `ratio`, `filing`, `valuation` |
| `entity_ids` | string[] | optional | Limit to specific CIKs |
| `expires_in_seconds` | integer | optional | Default 600, max 3600 |

Returns: `{download_url, expires_at, schema_url}`. The agent should fetch the schema URL too — it lists column types and the partition layout.

---

## Persistent research state, approvals, and automation (summary)

Beyond the data tools above, the server persists research objects server-side, keyed to your token — save from one AI client (Claude), read from another (Cursor), score later. Representative tools per family; the authoritative list is the live `tools/list`:

| Family | Representative tools | Notes |
|---|---|---|
| Price & market data | `get_stock_price`, `get_price_history`, `get_pit_valuation_ratios` | Daily OHLCV with `adjusted_close`; backtest-safe P/E, P/S, P/B, EV/EBITDA, FCF yield on any historical date |
| Theses | `save_thesis`, `list_theses`, `score_thesis_outcome`, `publish_thesis` | Time-stamped bull/bear/neutral calls, auto-graded against subsequent fundamentals and prices |
| Claims ledger | `save_claim`, `link_claim_to_thesis`, `score_claim`, `publish_claim` | Provenance-bound, individually scoreable claims — the unit of a public track record |
| Watchlists & alerts | `save_watchlist`, `create_alert`, `test_alert`, `list_alert_inbox` | `price_move` and `fundamental_change` conditions; delivery via email, HMAC-signed webhook, dashboard inbox, or an `agent_run` that fires a standing agent team |
| Reports | `create_report`, `render_report`, `save_freeform_report`, `list_report_versions` | Durable, versioned artifacts with branded md/docx export |
| Scheduled tasks | `schedule_task`, `list_scheduled_tasks`, `cancel_scheduled_task` | Agent deferral — "re-check AAPL margins in 30 days" wakes a real managed re-run |
| Rules engine | `create_rule`, `list_rules`, `test_rule` | Trigger→action automation; live triggers: `alert_fired`, `inbox_item`, `scheduled_task_wake`, `schedule_tick` (each rule reports its `trigger_wiring_status`) |
| Approvals (HOTL) | `stage_action`, `list_pending_approvals`, `approve_staged_action`, `reject_staged_action` | Mutating/destructive actions stage for human approval; every decision is an immutable audit entry |
| Briefing & runs | `get_morning_brief`, `list_agent_runs`, `get_agent_run` | Read your daily brief and managed-run history from any MCP client |
| Compute | `compute_dcf`, `forensic_audit`, `run_backtest` | Deterministic in-server compute; `run_backtest` is a bounded PIT factor grid with an honest stream-fallback over threshold |
| Document generation | `generate_dcf_xlsx`, `generate_comps_xlsx`, `generate_research_brief_docx` | Pro+; branded OOXML artifacts with server-side figure verification |

---

## Public publishing — free reputation building (reports, theses, claims)

These tools are **free on every tier**. They let an agent (or a creator working through one) turn saved work into a public, citable research track record linked from the author's `@handle` profile. This is **publishing to build a public profile and reputation, not selling** — there is no charge to the author or the reader, and the agent never mints a number (every published figure keeps its `fact_id` lineage). Reports become a shareable `/r/[slug]` page discoverable via keyword catalog search (`search_reports`, pure-D1 — there is no semantic search yet). Theses and claims get the same free `publish` / `unpublish` visibility toggle so a full public track record (report + supporting theses + scored claims) can be built with one consistent pattern. The paid report-marketplace tools (`purchase_report`, `list_my_purchases`, `connect_stripe_account`) remain **unreleased** until the marketplace launches.

### `publish_report`

Publish a saved report to the author's public profile as a shareable `/r/[slug]` page indexed for the public catalog and AI-search citation.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `report_id` | string | yes | A report you own (created via `create_report` / persisted-state tools) |
| `slug` | string | optional | Custom URL slug; auto-derived from the title if omitted |
| `summary` | string | optional | Short public-facing description shown in the catalog |

Returns: `{report_id, slug, public_url, handle, published_at}`.

### `unpublish_report`

Take a previously published report private again. The `/r/[slug]` page returns to a not-found state and the report leaves the public catalog.

| Parameter | Type | Required |
|---|---|---|
| `report_id` | string | yes — a published report you own |

Returns: `{report_id, slug, unpublished_at}`.

### `search_reports`

Search the public report catalog by ticker, author handle, or free-text keyword. Useful for discovering existing research before writing a new brief, or for surfacing a creator's body of work.

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `query` | string | optional | Free-text across title, summary, ticker, author |
| `ticker` | string | optional | Restrict to reports covering a ticker |
| `handle` | string | optional | Restrict to one author's public profile |
| `limit` | integer | optional | Default 25, max 100 |

Returns: `[{report_id, slug, public_url, title, summary, handle, tickers, published_at}]`.

### `publish_thesis`

Make a saved thesis public on the author's `@handle` profile — the same free visibility toggle as `publish_report`, applied to a thesis. Owner-scoped; flips the thesis to public so it appears in `list_public_theses_by_user`. Builds a verifiable public track record (sp500+).

| Parameter | Type | Required |
|---|---|---|
| `thesis_id` | string | yes — a thesis you own |

Returns: `{thesis_id, visibility, published_at}`.

### `unpublish_thesis`

Revert a published thesis back to private. Owner-scoped, idempotent — it drops out of the public profile feed (sp500+).

| Parameter | Type | Required |
|---|---|---|
| `thesis_id` | string | yes — a published thesis you own |

Returns: `{thesis_id, visibility, unpublished_at}`.

### `publish_claim`

Make a saved claim public on the author's `@handle` profile — publish/unpublish parity with reports and theses, applied to a provenance-bound, scoreable claim. Owner-scoped; the claim appears in `list_public_claims_by_user` so a public track record can carry its individual scored claims (sp500+).

| Parameter | Type | Required |
|---|---|---|
| `claim_id` | string | yes — a claim you own |

Returns: `{claim_id, visibility, published_at}`.

### `unpublish_claim`

Revert a published claim back to private. Owner-scoped, idempotent (sp500+).

| Parameter | Type | Required |
|---|---|---|
| `claim_id` | string | yes — a published claim you own |

Returns: `{claim_id, visibility, unpublished_at}`.

---

## Prompts (analyst SOPs)

These are pre-written multi-step instructions an MCP-aware agent can invoke as a single high-level command. Each chains the right tools in the right order.

The three **⭐ flagship** prompts are the canonical end-to-end workflows — `equity_research_brief` for single-ticker analysis, `screen_and_shortlist` for idea generation, and `deferred_research_loop` for research that follows up on itself. The remaining specialised SOPs underneath are narrower single-purpose chains, daily flows, and state-lifecycle playbooks. Below is a representative selection; the full set of **28 SOPs** is advertised by the live server's `prompts/list`.

| Prompt | What it does |
|---|---|
| `equity_research_brief` ⭐ | Full single-ticker institutional research brief in markdown. Three depth modes: `quick` (≈3 tool calls — snapshot), `full` (≈8 calls — default, the institutional brief), `forensic` (≈11 calls — adds restatement audit + fact-level SEC verification). Renders as an artifact you can export to Word / PDF directly from Claude Desktop or claude.ai. PIT-safe via `as_of_date` for backtests. |
| `screen_and_shortlist` ⭐ | PM-style idea generation. Builds a survivorship-free universe, ranks it on a chosen factor objective (`quality` / `value` / `growth` / `balanced`), QCs the leaders with a period-over-period change check, and hands off the top picks to `equity_research_brief` for full write-ups. Survivorship-free historical screening via `as_of_date`. |
| `deferred_research_loop` ⭐ | Research that follows up on itself. Chains initial research → `save_thesis` → a deliberate choice between a one-shot deferred check (`schedule_task`) and a standing monitor (`create_rule`) → `test_rule` dry-run → confirmation. The wake fires a real managed re-run when opted in. |
| `margin_and_moat_teardown` | Decompose a company's margin structure and quantify its moat using ratios + peer comparables |
| `peer_benchmarking_memo` | Generate a sector peer-benchmarking memo — financials, ratios, valuation gap |
| `quality_and_risk_audit` | Earnings-quality and accruals audit, plus restatement and 8-K event scan |
| `capital_allocation_review` | Multi-year review of capex / buyback / dividend trade-offs and ROIC trend |
| `ratio_deep_dive` | DuPont decomposition + Piotroski + Altman + interest coverage on one ticker |
| `sector_ratio_screen` | Sector-relative outlier screen across the ratio table |
| `survivorship_free_backtest` | Construct a survivorship-bias-free universe and run a factor-rebalance backtest |
| `pit_factor_constructor` | Build a PIT-correct factor (with `filing_date <= trade_date` discipline) |
| `publish_to_build_reputation` | Build-in-public flow — publish a report + thesis + claims to grow a verifiable public `@handle` track record |
| `watchlist_and_alert_setup` | Stand up monitoring — create a watchlist, attach alerts, test-fire them, and read the inbox |
| `claims_ledger_lifecycle` | Run a claim end-to-end — record → link to a thesis → grade → publish a provenance-bound claim |
| `thesis_state_machine` | Drive a thesis through its lifecycle — save → grade → score outcome → read |
| `multi_factor_signal` | PIT-disciplined composite signal — `get_pit_universe` → compute stream → screen → ratios |

Invoke a prompt the same way as a tool — most clients surface them in the same picker. The flagship prompts include built-in plan-aware fallback (returns "🔒 Pro / Institutional unlocks this" inline rather than aborting on tier-gated sections), data-freshness lines, automatic restatement flagging on any row where `lineage.restated = true`, and a not-investment-advice disclaimer.

---

## Resources

The server exposes three read-only reference resources for grounding the agent, plus a per-user alert feed:

| URI | What it is |
|---|---|
| `schema://{table}` | Column-level schema for any of the published tables |
| `reference://sp500` | Current S&P 500 constituent list |
| `pricing://current` | Current plan matrix and per-call pricing |
| `valuein://alerts/feed` | The authenticated user's alert inbox — lets an agent read and triage fired alerts |

Resources are cheaper to read than tool calls — agents that just need schema or a ticker list should pull from these.

---

## Tier matrix at a glance

All tools are callable on every paid tier. **What changes is the data the tool can see:**

| Tier | Data the agent sees |
|---|---|
| Sample (anonymous) | S&P 500 sample · 5-year window |
| Free | S&P 500 · 1993 – present |
| Pro | Full 19,000+-entity US universe · 15-year rolling window (2011 → present) · 24h freshness · fundamentals only |
| Institutional | Full universe · 1993 – present (unlimited) · **smart-money dataset unlocked** (Forms 3/4/5/144 + 13F/13D/13G) · 4h priority + filing-event webhooks · redistribution license |
| Enterprise | Negotiated scope · sub-minute real-time 8-K push · dedicated infrastructure · zero-retention option |

A `ValueinPlanError`-equivalent MCP error is raised when a tool call needs data outside the bound tier — the agent should suggest the user upgrade at [valuein.biz/pricing](https://valuein.biz/pricing).

---

## Pay-per-call (MPP)

Valuein supports **machine-to-machine pay-per-call** via the [Machine Payment Protocol](https://mpp.dev) (MPP). An agent that hits a rate limit or tier gate can pay per request in real time using a Stripe card Shared Payment Token — no human is needed in the loop.

**Payment is card-only today.** Fetch `GET https://api.valuein.biz/api/mpp/well-known` to confirm which networks are active before initiating a payment.

### Three-step flow

```
1. Quote
   GET https://api.valuein.biz/api/mpp/quote?tool=<tool_name>&tickers=<CSV>
   → { amount_usd, amount_usdc, nonce, accept: ["link-card"], expires_at }

2. Charge
   POST https://api.valuein.biz/api/mpp/charge
   Header:
     Payment: <base64url(JSON)>   where JSON =
       {
         "protocol_version": "1",
         "network": "link-card",
         "nonce": "<nonce from step 1>",
         "amount_usd_cents":  <round(amount_usd  * 100)>,
         "amount_usdc_cents": <round(amount_usdc * 100)>,
         "signed_payload": "spt_<your card Shared Payment Token>"
       }
   → { retry_token, retry_expires_at }

3. Retry the original MCP tool call with two added headers:
     x-valuein-payg-confirm: 1
     x-valuein-retry-token: <retry_token from step 2>
```

Pay whatever `/api/mpp/quote` returns (it applies plan caps + the $0.50 Stripe minimum) — don't hardcode prices.

### Per-call rate card (indicative — the authoritative price is `/api/mpp/quote`)

| Category | Tools | Price |
|---|---|---|
| Provenance / schema | `describe_schema`, `verify_fact_lineage` | Free |
| Discovery | `search_companies`, `get_sec_filing_links` | **$0.01 / entity** |
| Fundamentals | `get_company_fundamentals`, `get_financial_ratios` | **$0.10 / entity** |
| Analytics | `get_valuation_metrics`, `get_peer_comparables`, `compare_periods`, `get_capital_allocation_profile` | **$0.50 / entity** |
| Compute | `compute_dcf`, `forensic_audit`, `generate_dcf_xlsx`, `generate_research_brief_docx`, `generate_comps_xlsx` | **$2.50 / call** |
| Screens / universe | `screen_universe`, `get_pit_universe` | **$5.00 / call** |
| Smart money (Institutional dataset) | `get_insider_transactions`, `get_insider_sentiment`, `get_institutional_holdings`, `get_manager_portfolio`, `get_blockholders`, `get_top_holders`, `get_smart_money_flow` | **$5.00 / entity** |

Daily spend caps apply per identity as abuse protection (raisable on request); subscribers buying overflow within their tier get a discount on non-premium tools.

For steady-state agent usage a [Pro or Institutional subscription](https://valuein.biz/pricing) is significantly cheaper — a single Stripe token unlocks every channel at the subscribed tier.

---

## Versioning & registry

The published manifest in [`server.json`](../server.json) at the root of this repo is the source of truth for the MCP registry. Any push to `main` that touches `server.json` triggers `.github/workflows/publish-mcp.yml`, which authenticates with GitHub OIDC and publishes to `registry.modelcontextprotocol.io`. The `version` field must always match the deployed Worker version.

Server identifier: `io.github.valuein/mcp-sec-edgar` · Repository: `https://github.com/valuein/valuein`.
