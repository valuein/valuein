# Valuein MCP — Tool Reference

Valuein's MCP server exposes SEC EDGAR fundamentals to any MCP-capable AI client (Claude, Copilot, ChatGPT, Cursor, custom agents). It speaks the stateless **Streamable HTTP** transport and serves clients of MCP spec **2025-11-25** and **2026-07-28**.

- **Endpoints:** three public ones, each a different surface:
  - `https://mcp.valuein.biz/mcp`: the full catalog; your plan decides the data. The only endpoint that offers agent payments (MPP).
  - `https://mcp.valuein.biz/research/mcp`: read-only research tools, no sign-in needed (sign-in optional), no payments. The surface listed in AI app directories.
  - `https://mcp.valuein.biz/workspace/mcp`: the data tools plus your Workspace (watchlists, signals, reports, agents); sign-in required.
- **Auth:** `Authorization: Bearer <your_api_token>` (same token as the SDK and bulk-data API), or sign in with OAuth: connect with no header and the client discovers the server's OAuth metadata and sends you to the valuein.biz login; the token it gets works only on the endpoint you connected. With no token at all, `/mcp` serves the free sample and `/research/mcp` its read-only tools.
- **Registry:** `biz.valuein/mcp` on [registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io)
- **Manifest in this repo:** [`server.json`](../server.json)
- **Live manifest:** `https://mcp.valuein.biz/manifest.json` — the source every table on this page is generated from. The tables below describe `/mcp`, the full catalog.

The server registers tools across data lookup, screening, point-in-time financials, smart money, persisted research state (watchlists, citation overrides, signals, reports, scheduled tasks, rules, staged-action approvals, the morning brief and agent runs), report publishing, compute (DCF, three-statement, LBO, accretion/dilution, forensic audit, bounded point-in-time backtest) and document generation, plus analyst SOP prompts and reference resources. Live counts: `curl -s https://mcp.valuein.biz/manifest.json | jq .counts` (mirrored, by a daily sync, in [`server.json`](../server.json)).

Tier gating happens at the data layer — Sample / Benchmark tokens see the Sample / Benchmark slices (S&P 500 members since 1996, former members included); Pro sees the full active + delisted US universe with a rolling point-in-time window (10-K / 10-Q / 8-K / 20-F / 40-F; live window and universe size: `https://data.valuein.biz/v1/plans`); Institutional adds amendments (10-K/A, 10-Q/A) and the smart-money dataset (insider transactions on Forms 3 / 4 / 5 / 144 + institutional ownership on Forms 13F / 13D / 13G), unlimited fundamentals history back to 1993, and filing-event webhooks, for single-seat internal use only (no redistribution); Enterprise (an Enterprise Agreement for organisations and teams) adds multi-seat use, display in your own products and client deliverables with attribution where the Order Form says so, dedicated infrastructure and a bespoke SLA. Redistribution, resale and white-label need a separate Redistribution Licence, which no plan includes.

Everything between `GEN` markers on this page is written by `scripts/sync_mcp_manifest.py` from the live manifest and checked on every push and pull request (`--check` fails on any difference); never edit it by hand.

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

The Sample tier works without a token but only against the sample slice. To explore the full universe and history, [register](https://valuein.biz/signup/free) (Free, S&P 500 members since 1996, former members included, only) or [subscribe](https://valuein.biz/pricing) (Pro / Institutional).

---

<!-- GEN:agent-contract -->
## Reading tool results: errors and paging

Agent contract v1, generated from the server's code. Live copy: `curl -s https://mcp.valuein.biz/manifest.json | jq .agent_contract`.

### Errors

A tool error is a result with `isError: true`. It carries **no `structuredContent`**: the error is one JSON object in the first text block.

```js
const { error } = JSON.parse(result.content[0].text);
if (error.code === "TICKER_NOT_FOUND") { /* resolve the company with search_companies */ }
```

| Field | Always present | Meaning |
|---|---|---|
| `code` | yes | Stable machine code; branch on this, never on the prose. |
| `title` | yes | Short human title for the code. |
| `detail` | yes | The sentence a person should read: what happened and what to do next. |
| `status` | yes | HTTP-style status. 429 and 503 are transient: retry after a pause. Any other 4xx fails the same way until the call changes (its arguments, the plan, or a payment). |
| `type` | yes | Documentation URI for the code. |
| `extensions` | yes | Code-specific fields, e.g. `required_plan`, `upgrade_url`, `remediation.options`, `retryable`. |
| `request_id` | no | Present when the request had an id; quote it to support. `instance` carries the same value. |
| `tool` | no | The tool that answered, when known. |

When the first text block is not JSON, the protocol layer answered instead of the tool; read it as plain text. `Input validation error` means the arguments do not match the tool's input schema: fix the call, since a retry fails the same way. `Tool … not found` means the tool name is wrong. `Output validation error` is a server fault: report it with `submit_feedback`.

| Code | Status | Title |
|---|---|---|
| `TICKER_NOT_FOUND` | 404 | Ticker not found |
| `TICKER_DELISTED` | 410 | Ticker delisted |
| `ENTITLEMENT_DENIED` | 403 | Data not available on current plan |
| `DATA_NOT_AVAILABLE_FOR_PERIOD` | 404 | No data for requested period |
| `NO_FACTS_BEFORE_AS_OF_DATE` | 404 | Temporal filter excluded all data |
| `FEATURE_NOT_AVAILABLE` | 501 | Feature not yet available |
| `INVALID_ARGUMENT` | 400 | Invalid argument |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `QUOTA_EXCEEDED` | 402 | Plan quota exceeded |
| `LIMIT_EXCEEDED` | 402 | Plan limit reached |
| `UPSTREAM_UNAVAILABLE` | 503 | Upstream data store unavailable |
| `STALE_SNAPSHOT` | 503 | Snapshot rotating; retry |
| `FILE_TOO_LARGE` | 413 | Partition exceeds Worker memory limit |
| `NOT_FOUND` | 404 | Resource not found |
| `FIGURES_UNVERIFIED` | 409 | Report contains contradicted figures |
| `PRICE_UNDATED` | 409 | Report holds an undated share price |
| `PRICE_SERIES_NOT_ALLOWED` | 409 | Report holds a price series |
| `VERIFICATION_UNAVAILABLE` | 503 | Verification service unavailable |
| `APPROVAL_REQUIRED` | 409 | Waiting for a person's approval |
| `INTERNAL_ERROR` | 500 | Internal server error |

### Paging

**Offset paging** (`get_pit_universe`, `screen_universe`): `limit` is the page size and `offset` is where the page starts. While rows remain, the result carries `truncation` with `next_offset`: call again with the same arguments and `offset` set to `truncation.next_offset`, until a result has no `truncation`.

**Cursor paging** (`list_citation_overrides`, `list_my_reports`, `list_pending_approvals`, `list_report_versions`, `list_restatements`, `list_rules`, `list_scheduled_tasks`, `list_signal_inbox`, `list_signals`, `list_watchlists`, `search_reports`): Pass the `next_cursor` of one result as `cursor` on the next call, with the same other arguments. A null `next_cursor` is the last page.

### The `_meta` envelope

Every success result carries `structuredContent._meta`. Each tool's outputSchema declares it once as an open object; its fields are documented here, not per tool. Read `source`, `pit_safe` and `as_of_date` for provenance and `fundamentals_as_of` (not `last_updated`) for how current the statements are. A field may be absent on a surface that does not serve it.

| Field | Always present | Meaning |
|---|---|---|
| `data_plan` | yes | Plan key the call ran on: sample (no sign-in), sp500 (Benchmark), pro (Pro), full (Institutional). |
| `schema_version` | yes | Parquet schema version from manifest.json |
| `snapshot` | yes | Snapshot directory name (e.g. snapshot_20260420) |
| `last_updated` | yes | ISO timestamp when the snapshot was exported |
| `fundamentals_as_of` | no | ISO timestamp when the FINANCIAL STATEMENTS were last rebuilt in bulk. Use THIS — not `last_updated` — when telling a user how current the cross-sectional fundamentals are. The snapshot can be republished while the statements are carried forward unchanged, so `last_updated` can be more recent than the numbers it sits next to. It is a floor for a single filer, not a ceiling: a filer with a live partition receives its filing, facts and ratios intraday (minutes after EDGAR dissemination), so an entity-scoped read may carry a filing newer than this; cross-sectional ranks (factor scores, earnings signals) refresh with the weekly bulk export. |
| `source` | yes | Always "SEC EDGAR" for a tool that reads filings. |
| `ticker` | no | The company the call was about, when it named one. |
| `as_of_date` | no | The point-in-time cutoff applied, or null when none was asked for. |
| `pit_safe` | yes | true iff a zero-look-ahead point-in-time cut was applied to every returned figure |
| `result_count` | no | Rows in this result. |
| `request_id` | no | Per-request correlation id (8-char) |
| `latency_ms` | no | Wall-clock milliseconds this tool call took, measured server-side around the handler. |
| `cost_usd` | no | Per-call cost transparency. Omitted for subscription-only and free tools, which have no MPP price. |
| `rate_limit` | no | Caller's remaining budget |
| `mpp_override` | no | Set when this single response was paid for over MPP: the payment's order was honoured for this call only, and the payment is captured only when this is present. |
| `mpp_verification` | no | Verification tools only, when some figures are outside the caller's plan. Figures the plan covers are always verified free; a Valuein account also verifies its first figures free, once, figures outside its plan included (the verification trial, size in pricing://current). served_free = own-plan figures plus trial figures; trial_used / trial_remaining = this run's draw and what the account has left; needs_payment = figures still to pay for (the paid verification run). A guest has no trial: note says how to get it. |
| `mpp_offer` | no | Present when figures still need payment: the MPP option (price, resource_url, request body) for the full run. |
| `data_quality` | no | Server-side invariants run on this response |
| `truncation` | no | Set when fewer rows were returned than requested — explains why and points to a remedy |
| `limit_warnings` | no | Soft-warning array for partial fulfillment. Each entry carries a stable subcode + remediation.options[]. AI agents pattern-match on subcode. |
<!-- /GEN:agent-contract -->

---

## Tools

<!-- GEN:mcp-tool-reference -->
_Generated from the MCP server manifest (v3.28.1) by `scripts/sync_mcp_manifest.py`. Do not edit by hand: the next sync overwrites it._

**113 tools**, in the server's registration order. Effect comes from each tool's MCP annotations (`readOnlyHint`, `destructiveHint`); paging is explained in the agent contract above. Descriptions are the manifest's summaries: the live `tools/list` response carries each tool's full description and JSON Schema.

Plan keys: `sample` = Sample · `sp500` = Benchmark (free) · `pro` = Pro · `full` = Institutional.

Identifiers shown as `[withheld]` name internal datasets and are left out of this public page; the live `tools/list` response carries them.

| Tool | Title | Min plan | Effect | Paging |
|---|---|---|---|---|
| [`search_companies`](#search_companies) | Search Companies | `sample` | read-only | none |
| [`get_company_fundamentals`](#get_company_fundamentals) | Company Fundamentals | `sample` | read-only | none |
| [`get_valuation_metrics`](#get_valuation_metrics) | Valuation Metrics | `sample` | read-only | none |
| [`get_financial_ratios`](#get_financial_ratios) | Financial Ratios | `sample` | read-only | none |
| [`get_sec_filing_links`](#get_sec_filing_links) | SEC Filing Links | `sample` | read-only | none |
| [`list_filing_forms`](#list_filing_forms) | Filed Form Types | `sample` | read-only | none |
| [`latest_filings`](#latest_filings) | Latest Filings | `sample` | read-only | none |
| [`list_filing_sections`](#list_filing_sections) | List Filing Sections | `sample` | read-only | none |
| [`read_filing_section`](#read_filing_section) | Read Filing Section | `sample` | read-only | none |
| [`find_in_filing`](#find_in_filing) | Find in Filing | `sample` | read-only | none |
| [`get_capital_allocation_profile`](#get_capital_allocation_profile) | Capital Allocation Profile | `sample` | read-only | none |
| [`get_peer_comparables`](#get_peer_comparables) | Peer Comparables | `sample` | read-only | none |
| [`get_pit_universe`](#get_pit_universe) | Point-in-Time Universe | `sample` | read-only | offset |
| [`get_compute_ready_stream`](#get_compute_ready_stream) | Compute-Ready Stream | `sample` | read-only | none |
| [`describe_schema`](#describe_schema) | Describe Data Schema | `sample` | read-only | none |
| [`list_sops`](#list_sops) | List Research Playbooks (SOPs) | `sample` | read-only | none |
| [`get_sop`](#get_sop) | Get Research Playbook (SOP) | `sample` | read-only | none |
| [`verify_fact_lineage`](#verify_fact_lineage) | Verify Fact Lineage | `sample` | read-only | none |
| [`verify_facts`](#verify_facts) | Verify Facts (batch) | `sample` | read-only | none |
| [`match_derived`](#match_derived) | Match Derived Figures | `sample` | read-only | none |
| [`verify_filing_figures`](#verify_filing_figures) | Verify Filing Figures | `sample` | read-only | none |
| [`compare_periods`](#compare_periods) | Compare Financial Periods | `sample` | read-only | none |
| [`screen_universe`](#screen_universe) | Screen Universe by Factor Scores | `sample` | read-only | offset |
| [`get_earnings_signals`](#get_earnings_signals) | Earnings Signals | `sample` | read-only | none |
| [`get_filing_review_pack`](#get_filing_review_pack) | Filing Review Pack | `sample` | read-only | none |
| [`get_company_brief_pack`](#get_company_brief_pack) | Company Brief Pack | `sample` | read-only | none |
| [`list_restatements`](#list_restatements) | Restatement Radar Feed | `sample` | read-only | cursor |
| [`explain_restatement`](#explain_restatement) | Explain a Restatement | `sample` | read-only | none |
| [`submit_feedback`](#submit_feedback) | Submit Feedback | `sample` | writes | none |
| [`submit_artifact_feedback`](#submit_artifact_feedback) | Submit Artifact Feedback | `sample` | writes | none |
| [`get_insider_transactions`](#get_insider_transactions) | Insider Transactions | `full` | read-only | none |
| [`get_institutional_holdings`](#get_institutional_holdings) | Institutional Holdings (by issuer) | `full` | read-only | none |
| [`get_manager_portfolio`](#get_manager_portfolio) | Manager Portfolio (13F by filer) | `full` | read-only | none |
| [`get_blockholders`](#get_blockholders) | Blockholders (SC 13D / 13G) | `full` | read-only | none |
| [`get_insider_sentiment`](#get_insider_sentiment) | Insider Sentiment (composite) | `full` | read-only | none |
| [`get_top_holders`](#get_top_holders) | Top Holders (composite, classified) | `full` | read-only | none |
| [`get_smart_money_flow`](#get_smart_money_flow) | Smart Money Flow (composite) | `full` | read-only | none |
| [`get_ownership_pack`](#get_ownership_pack) | Ownership Pack | `full` | read-only | none |
| [`restore_deleted`](#restore_deleted) | Restore a Deleted Item | `sp500` | writes | none |
| [`undo_change`](#undo_change) | Undo a Change | `sp500` | writes | none |
| [`run_workflow`](#run_workflow) | Run Saved Workflow | `sp500` | read-only | none |
| [`save_citation_override`](#save_citation_override) | Save Citation Override | `sp500` | writes | none |
| [`list_citation_overrides`](#list_citation_overrides) | List Citation Overrides | `sp500` | read-only | cursor |
| [`delete_citation_override`](#delete_citation_override) | Delete Citation Override | `sp500` | destructive | none |
| [`save_figure_review`](#save_figure_review) | Save Figure Review | `sp500` | writes | none |
| [`list_figure_reviews`](#list_figure_reviews) | List Figure Reviews | `sp500` | read-only | none |
| [`delete_figure_review`](#delete_figure_review) | Delete Figure Review | `sp500` | destructive | none |
| [`get_research_file`](#get_research_file) | Get Auditable Research File | `sp500` | read-only | none |
| [`sign_off_report`](#sign_off_report) | Sign Off Report | `sp500` | destructive | none |
| [`verify_report_figures`](#verify_report_figures) | Verify Report Figures | `sp500` | read-only | none |
| [`save_watchlist`](#save_watchlist) | Save Watchlist | `sp500` | writes | none |
| [`list_watchlists`](#list_watchlists) | List Watchlists | `sp500` | read-only | cursor |
| [`get_watchlist`](#get_watchlist) | Get Watchlist | `sp500` | read-only | none |
| [`delete_watchlist`](#delete_watchlist) | Archive Watchlist | `sp500` | destructive | none |
| [`set_agent_memory`](#set_agent_memory) | Set Agent Memory | `sp500` | writes | none |
| [`get_agent_memory`](#get_agent_memory) | Get Agent Memory | `sp500` | read-only | none |
| [`delete_agent_memory`](#delete_agent_memory) | Delete Agent Memory | `sp500` | destructive | none |
| [`watchlist_diff`](#watchlist_diff) | Watchlist Diff | `sp500` | read-only | none |
| [`create_signal`](#create_signal) | Create Signal | `sp500` | writes | none |
| [`update_signal`](#update_signal) | Update Signal | `sp500` | writes | none |
| [`list_signals`](#list_signals) | List Signals | `sp500` | read-only | cursor |
| [`delete_signal`](#delete_signal) | Delete Signal | `sp500` | destructive | none |
| [`test_signal`](#test_signal) | Test Signal (synthetic fire) | `sp500` | writes | none |
| [`list_signal_inbox`](#list_signal_inbox) | List Signal Inbox | `sp500` | read-only | cursor |
| [`mark_inbox_read`](#mark_inbox_read) | Mark Inbox Item Read | `sp500` | writes | none |
| [`dismiss_inbox_item`](#dismiss_inbox_item) | Dismiss Inbox Item | `sp500` | destructive | none |
| [`stage_action`](#stage_action) | Stage Action | `sp500` | writes | none |
| [`list_pending_approvals`](#list_pending_approvals) | List Pending Approvals | `sp500` | read-only | cursor |
| [`approve_staged_action`](#approve_staged_action) | Approve Staged Action | `sp500` | destructive | none |
| [`reject_staged_action`](#reject_staged_action) | Reject Staged Action | `sp500` | writes | none |
| [`schedule_task`](#schedule_task) | Schedule Task | `sp500` | writes | none |
| [`list_scheduled_tasks`](#list_scheduled_tasks) | List Scheduled Tasks | `sp500` | read-only | cursor |
| [`cancel_scheduled_task`](#cancel_scheduled_task) | Cancel Scheduled Task | `sp500` | destructive | none |
| [`create_rule`](#create_rule) | Create Rule | `sp500` | writes | none |
| [`list_rules`](#list_rules) | List Rules | `sp500` | read-only | cursor |
| [`delete_rule`](#delete_rule) | Delete Rule | `sp500` | destructive | none |
| [`test_rule`](#test_rule) | Test Rule (dry run) | `sp500` | read-only | none |
| [`get_morning_brief`](#get_morning_brief) | Get Morning Brief | `sp500` | read-only | none |
| [`list_agent_runs`](#list_agent_runs) | List Agent Runs | `sp500` | read-only | none |
| [`get_agent_run`](#get_agent_run) | Get Agent Run | `sp500` | read-only | none |
| [`save_agent`](#save_agent) | Save Agent | `sp500` | writes | none |
| [`list_agents`](#list_agents) | List Agents | `sp500` | read-only | none |
| [`get_agent`](#get_agent) | Get Agent | `sp500` | read-only | none |
| [`delete_agent`](#delete_agent) | Delete Agent | `sp500` | destructive | none |
| [`run_agent`](#run_agent) | Run Agent | `sp500` | writes | none |
| [`create_report`](#create_report) | Create Research Report | `sp500` | writes | none |
| [`get_report`](#get_report) | Get Research Report | `sp500` | read-only | none |
| [`check_report_figures_current`](#check_report_figures_current) | Check Report Figures Are Current | `sp500` | read-only | none |
| [`list_my_reports`](#list_my_reports) | List My Research Reports | `sp500` | read-only | cursor |
| [`delete_report`](#delete_report) | Delete (Soft) Research Report | `sp500` | destructive | none |
| [`publish_report`](#publish_report) | Publish Report (free) | `sp500` | writes | none |
| [`unpublish_report`](#unpublish_report) | Unpublish Report (back to private) | `sp500` | destructive | none |
| [`search_reports`](#search_reports) | Search Published Reports | `sample` | read-only | cursor |
| [`compute_dcf`](#compute_dcf) | Compute Forward DCF | `sp500` | read-only | none |
| [`forensic_audit`](#forensic_audit) | Forensic Audit (Beneish + Sloan + Solvency) | `sp500` | read-only | none |
| [`get_pit_valuation_ratios`](#get_pit_valuation_ratios) | Point-in-Time TTM Financials | `pro` | read-only | none |
| [`run_backtest`](#run_backtest) | Run Bounded Factor Backtest | `pro` | read-only | none |
| [`project_three_statement`](#project_three_statement) | Project Linked Three-Statement Model | `sp500` | read-only | none |
| [`compute_lbo`](#compute_lbo) | Compute LBO Returns (IRR + MOIC) | `sp500` | read-only | none |
| [`compute_accretion_dilution`](#compute_accretion_dilution) | Compute M&A Accretion/Dilution | `sp500` | read-only | none |
| [`compute_price_multiples`](#compute_price_multiples) | Compute Multiples on Your Price | `sp500` | read-only | none |
| [`update_report`](#update_report) | Update Report Sections | `sp500` | writes | none |
| [`list_report_versions`](#list_report_versions) | List Report Versions | `sample` | read-only | cursor |
| [`get_report_version`](#get_report_version) | Get Report Version | `sample` | read-only | none |
| [`render_report`](#render_report) | Render Report Download URL | `sample` | writes | none |
| [`save_freeform_report`](#save_freeform_report) | Save Markdown as a Draft Report | `sp500` | writes | none |
| [`get_uploaded_document`](#get_uploaded_document) | Read an Uploaded Document | `sp500` | read-only | none |
| [`list_uploaded_documents`](#list_uploaded_documents) | List Uploaded Documents | `sp500` | read-only | none |
| [`delete_uploaded_document`](#delete_uploaded_document) | Delete an Uploaded Document | `sp500` | destructive | none |
| [`generate_dcf_xlsx`](#generate_dcf_xlsx) | Generate DCF Workbook (xlsx) | `pro` | writes | none |
| [`generate_research_brief_docx`](#generate_research_brief_docx) | Generate Research Brief (docx) | `pro` | writes | none |
| [`generate_comps_xlsx`](#generate_comps_xlsx) | Generate Peer Comparables Workbook (xlsx) | `pro` | writes | none |
| [`generate_lbo_xlsx`](#generate_lbo_xlsx) | Generate LBO Workbook (xlsx) | `pro` | writes | none |

### `search_companies`

**Search Companies** · min plan `sample` · read-only · paging: none

Search for US public companies by name, ticker symbol, CIK (SEC identifier), or SIC industry code. Returns ticker, company name, sector, industry, exchange, and current S&P 500 membership status. Use this tool to resolve a company name to ticker/CIK before calling `get_company...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `query` | string | no | — | Free-text search over company name and ticker. Case-insensitive. E.g. 'Apple', 'AAPL', 'Microsoft', 'semiconductor'. |
| `cik` | string | no | — | SEC CIK identifier (exact match). E.g. '0000320193' for Apple. |
| `sic_code` | string | no | — | 4-digit SIC industry code. E.g. '7372' for Prepackaged Software. |
| `is_active` | boolean | no | — | Filter on whether the LISTING is current. true = currently trading; false = superseded listings only (delisted, or a ticker that moved to a new registrant). Omit to return both. |
| `is_sp500` | boolean | no | — | Filter to current S&P 500 members only. |
| `include_inactive` | boolean | no | default `true` | Whether delisted / superseded listings may appear in results. Defaults to true — this is a survivorship-free product, so a search must not silently hide dead companies by default. Set to false to restrict to currently-active listings only (equivalent to `is_active: true`, but as a search-scope toggle rather than a hard filter). If `is_active` is also supplied, `is_active` wins. |
| `limit` | integer | no | default `25` | Maximum number of results to return (1–50). Defaults to 25. |

**Output fields:** `query`, `results_returned`, `companies`

### `get_company_fundamentals`

**Company Fundamentals** · min plan `sample` · read-only · paging: none

Retrieve standardized SEC EDGAR fundamental financial metrics for a US public company. Returns revenue, gross profit, operating income, net income, EPS (diluted), total assets, total liabilities, stockholders' equity, cash & equivalents, total debt, operating cash flow, and ca...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol, e.g. AAPL, MSFT, BRK.B — or a CIK (SEC identifier), e.g. '0000320193'. |
| `fiscal_year` | integer | no | — | Fiscal year (YYYY). Omit to return the most recent available years. |
| `period` | enum | no | one of `annual`, `quarterly`; default `annual` | Filing period granularity. Annual uses 10-K; quarterly uses 10-Q. |
| `as_of_date` | string | no | — | Point-in-time date (YYYY-MM-DD). Only returns facts with accepted_at on or before this date — eliminates look-ahead bias for backtesting. Omit for the full dataset. |
| `limit` | integer | no | default `5` | Maximum number of periods to return (1–40). Defaults to 5. |
| `strict` | boolean | no | default `false` | When true, fail with LIMIT_EXCEEDED (subcode DEPTH_LIMIT_EXCEEDED) if the plan cannot satisfy the requested limit. Default false: return what's available and explain the gap in _meta.truncation. |
| `lineage_detail` | enum | no | one of `off`, `compact`, `full`; default `compact` | Per-period provenance envelope + per-metric availability/provenance sidecars. 'compact' (default) returns source_filing + source_url (the SEC Inline-XBRL viewer with every tagged fact highlighted when the filing is iXBRL, else the rendered document, else the filing index) + sec_url/document_url/inline_viewer_url + restated flag, plus lean per-metric availability + fact_id + source_filing. 'full' adds first_filed_at + accepted_at + per-metric source_url + computed inputs[]. 'off' omits all provenance. |
| `response_format` | enum | no | one of `flat`, `envelope`; default `flat` | Output shape. 'flat' (default) returns the legacy `metrics` object plus the additive `metrics_availability`/`metrics_provenance`/`metrics_display` sidecars — `metrics_display` holds each figure already rendered for prose ("$402.83B"), and you should quote it verbatim rather than reformatting `metrics` yourself. 'envelope' additionally attaches `metric_envelopes` — one canonical {metric,value,unit,scale,period,availability,provenance,display} object per metric. Both shapes carry the same display strings. |
| `min_confidence` | number | no | — | Withhold any metric whose backing fact scores below this confidence [0, 1]. The score is a PENALTY FROM EVIDENCE — every fact starts at 1.0 and is docked only for something checkable: a failed accounting identity (-0.40), a later filing that revised the number (-0.20), an unaudited filing (-0.05). It is NOT a function of age: a clean 1995 fact scores the same as a clean 2026 one. Guide: 0.95 = 'no evidence against this number' (the normal case, in every year); 0.80 = tolerate a fact a later filing revised; 0.60 = tolerate a filing whose accounting identities failed. A withheld metric is reported as availability:'suppressed' — never dropped silently, and never as 'not_reported', which would claim the company did not file it. Facts with no confidence score are withheld too (fail closed). |

**Output fields:** `ticker`, `company_name`, `cik`, `period`, `as_of_date`, `years_returned`, `data`

### `get_valuation_metrics`

**Valuation Metrics** · min plan `sample` · read-only · paging: none

Get the profitability, cash-flow and leverage metrics of a US public company, plus two parameter-free reference points. No price-based multiple is published, so none is returned and you must never compute one; if the user needs a price, ask for it and label it user-supplied. T...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol, e.g. AAPL, MSFT — or a CIK (SEC identifier), e.g. '0000320193'. |
| `fiscal_year` | integer | no | — | Fiscal year (YYYY). Omit to return most recent periods. |
| `period` | enum | no | one of `annual`, `quarterly`; default `annual` | Filing period granularity. Annual uses 10-K; quarterly uses 10-Q. |
| `as_of_date` | string | no | — | Point-in-time date (YYYY-MM-DD). Only returns data with accepted_at on or before this date. Eliminates look-ahead bias for backtesting. |
| `limit` | integer | no | default `5` | Maximum number of periods to return (1–40). Defaults to 5. |

**Output fields:** `ticker`, `period`, `as_of_date`, `periods_returned`, `data`

### `get_financial_ratios`

**Financial Ratios** · min plan `sample` · read-only · paging: none

Financial ratios Valuein precomputes from each company's SEC filings. A bare call returns the ${DEFAULT_RATIO_PERIODS} most recent periods and every category except growth and rank (both large); pass `categories` (e.g. ["growth","rank"]) to get them and `limit` (up to 20) for ...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol, e.g. AAPL, MSFT — or a CIK (SEC identifier), e.g. '0000320193'. |
| `categories` | array | no | — | Ratio categories to include (see the enum). Omit to return every category this ticker has except growth and rank, which are returned only when named here. `valuation` (graham_number, ncav_per_share) are precomputed at each fiscal period end. Availability is per-ticker (the envelope lists this ticker's available_categories). |
| `fiscal_period` | enum | no | one of `FY`, `TTM`, `Q1`, `Q2`, `Q3`, `Q4` | Filter to a specific fiscal period type. Use 'TTM' for trailing twelve months. Omit to return both annual (FY) and TTM rows. |
| `as_of_date` | string | no | — | Historical cutoff (canonical cross-tool date param). PIT by SEC accepted_at when the ratio data carries it (latest value knowable on/before the date, zero look-ahead, _meta.pit_safe=true), else by ratio.period_end (pit_safe=false). For guaranteed accepted_at PIT use get_company_fundamentals. |
| `period_end_before` | string | no | — | Alias of as_of_date (as_of_date preferred — the canonical name). Returns ratios with period_end on or before this date. |
| `limit` | integer | no | default `2` | Number of distinct period_end dates to return (1–20). Defaults to 2. Within each period, all matching ratio_names are included. |

**Output fields:** `ticker`, `plan`, `note`, `periods_returned`, `data`, `lineage`

### `get_sec_filing_links`

**SEC Filing Links** · min plan `sample` · read-only · paging: none

Get direct links to original SEC EDGAR filings for any US public company. Returns four per-filing deep links: `sec_url` (the EDGAR filing-index page listing every document), `viewer_url` (the cgi-bin Financial-Report viewer for the specific accession), `inline_viewer_url` (the...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol, e.g. AAPL, MSFT — or a CIK (SEC identifier), e.g. '0000320193'. |
| `form_types` | array | no | default `["10-K", "10-Q"]` | Filing form types to include. Defaults to 10-K and 10-Q. |
| `start_date` | string | no | — | Inclusive lower bound on filing_date (YYYY-MM-DD). E.g. '2023-01-01'. |
| `end_date` | string | no | — | Inclusive upper bound on filing_date (YYYY-MM-DD). E.g. '2023-12-31'. |
| `event_types` | array | no | — | 8-K item codes to filter by. E.g. ['1.01'] for material agreements, ['2.01'] for asset acquisitions, ['5.02'] for director/officer changes. Only relevant when form_types includes '8-K'. |
| `limit` | integer | no | default `10` | Maximum number of filings to return (1–50). Defaults to 10. |

**Output fields:** `ticker`, `resolved_cik`, `other_ciks_for_ticker`, `filings_returned`, `filings`, `note`

### `list_filing_forms`

**Filed Form Types** · min plan `sample` · read-only · paging: none

Which SEC form types each of up to 200 companies filed in the last N months (default 24), as a count per form, in ONE call. Use it to offer only forms a company set actually files (10-K, 10-Q, 20-F, 40-F, 6-K, 8-K, DEF 14A, ...). Amendments count toward their base form (10-K/A...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `tickers` | array | yes | — | Tickers or CIKs, at most 200. |
| `months` | integer | no | default `24` | Look-back window in months. Defaults to 24. |

**Output fields:** `since`, `companies`

### `latest_filings`

**Latest Filings** · min plan `sample` · read-only · paging: none

The newest SEC filing per company per form, for up to 50 companies in ONE call: ticker, cik, form (as filed, `10-Q/A` when an amendment is the newest), accession and SEC `accepted_at`. Pass base forms (`10-K`, `10-Q`, `8-K`, `20-F`, `40-F`); amendments count toward their base ...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `tickers` | array | yes | — | Tickers or CIKs, at most 50. |
| `forms` | array | yes | — | Base form codes, e.g. ['10-K', '10-Q']. A trailing /A is folded into the base form. |

**Output fields:** `readable`, `filings`, `unknown_tickers`, `not_on_plan`, `unresolved_tickers`, `unreadable_tickers`, `note`

### `list_filing_sections`

**List Filing Sections** · min plan `sample` · read-only · paging: none

Table of contents of a 10-K / 10-Q / 8-K (or 10-K/A, 10-Q/A, 8-K/A) so an agent can read the filing's WORDS: returns the form, filing/period/acceptance dates, the primary-document URL, and every section found with its `key`, `title`, `char_count` and a short `first_line`. 10-K...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker, e.g. AAPL — or a CIK (SEC identifier), e.g. '0000320193'. A CIK is the stable identifier. |
| `accession` | string | yes | — | EDGAR accession number of the 10-K / 10-Q / 8-K, e.g. '0000320193-19-000119'. Take it from get_sec_filing_links. |
| `as_of_date` | string | no | — | Point-in-time guard (YYYY-MM-DD). A filing is its own as-of: if it was accepted by the SEC after this date the call is refused rather than reading text that did not exist yet. |

**Output fields:** `ticker`, `accession_id`, `form_type`, `filing_date`, `report_date`, `accepted_at`, `source_url`, `sec_url`, `total_chars`, `sections`, `notes`, `unread_documents`, `provenance_note`

### `read_filing_section`

**Read Filing Section** · min plan `sample` · read-only · paging: none

Read one section of a 10-K / 10-Q / 8-K (or amendment) as plain text: MD&A (10-K `7`, 10-Q `I-2`), Risk Factors (`1A`, `II-1A`), Legal Proceedings, Controls, a financial-statement note (`note-3`), an 8-K Item (`2.02`, `5.02`) or its press-release exhibit (`ex-99.1`), or the wh...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker, e.g. AAPL — or a CIK (SEC identifier), e.g. '0000320193'. A CIK is the stable identifier. |
| `accession` | string | yes | — | EDGAR accession number of the 10-K / 10-Q / 8-K, e.g. '0000320193-19-000119'. Take it from get_sec_filing_links. |
| `as_of_date` | string | no | — | Point-in-time guard (YYYY-MM-DD). A filing is its own as-of: if it was accepted by the SEC after this date the call is refused rather than reading text that did not exist yet. |
| `key` | string | yes | — | Section key from list_filing_sections: '7', '1A', 'I-2', 'II-1A', 'note-3', 'explanatory-note', '2.02', 'ex-99.1', 'document'. |
| `offset` | integer | no | default `0` | Character offset to start from; use the previous page's next_offset. |
| `max_chars` | integer | no | default `20000` | Page size in characters (1000-60000). Defaults to 20000. |

**Output fields:** `ticker`, `accession_id`, `form_type`, `filing_date`, `key`, `title`, `text`, `offset`, `returned_chars`, `next_offset`, `total_chars`, `source_url`, `provenance_note`

### `find_in_filing`

**Find in Filing** · min plan `sample` · read-only · paging: none

Find a statement, note, heading or phrase inside a 10-K / 10-Q / 8-K (or amendment; an 8-K's EX-99 exhibits included) and get where to read it, like grep over the filing: 'Consolidated Balance Sheets', 'goodwill impairment', 'Note 7', 'Risk Factors'. Searches the same text rea...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker, e.g. AAPL — or a CIK (SEC identifier), e.g. '0000320193'. A CIK is the stable identifier. |
| `accession` | string | yes | — | EDGAR accession number of the 10-K / 10-Q / 8-K, e.g. '0000320193-19-000119'. Take it from get_sec_filing_links. |
| `as_of_date` | string | no | — | Point-in-time guard (YYYY-MM-DD). A filing is its own as-of: if it was accepted by the SEC after this date the call is refused rather than reading text that did not exist yet. |
| `query` | string | yes | — | Words or a phrase to find, e.g. 'Consolidated Balance Sheets', 'Note 7', 'goodwill impairment'. Separate alternatives with '\|'. |
| `match` | enum | no | one of `phrase`, `all_words`; default `phrase` | 'phrase' (default): the words in order. 'all_words': every word within 300 characters, any order. |
| `section` | string | no | — | Search only this section key from list_filing_sections ('7', 'II-1A', 'note-3', 'ex-99.1'). Omit to search the whole filing. |
| `kinds` | array | no | — | Keep only these hit kinds, e.g. ['heading'] for section and statement titles. Omit for every kind. |
| `case_sensitive` | boolean | no | default `false` | Match letter case exactly. Default false. |
| `whole_word` | boolean | no | default `false` | Match each word whole: 'sheet' no longer finds 'Sheets'. Default false. |
| `sort` | enum | no | one of `relevance`, `position`; default `relevance` | 'relevance' (default): best place to read first. 'position': document order. |
| `max_results` | integer | no | default `10` | Hits returned (1-50). Defaults to 10; total_matches still counts every hit. |
| `context_chars` | integer | no | default `200` | Characters of text either side of each match in its snippet (0-600). Defaults to 200. |

**Output fields:** `ticker`, `accession_id`, `form_type`, `filing_date`, `query`, `searched`, `total_matches`, `complete`, `kind_counts`, `hits`, `note`, `source_url`, `provenance_note`

### `get_capital_allocation_profile`

**Capital Allocation Profile** · min plan `sample` · read-only · paging: none

Get a multi-year capital allocation breakdown for a US public company. Shows how management deploys cash across all six categories — capex, R&D, M&A, dividends, buybacks, and debt — plus pre-computed deployment ratios (% of operating cash flow) and over-distribution flags. Use...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol, e.g. AAPL, MSFT — or a CIK (SEC identifier), e.g. '0000320193'. |
| `lookback_years` | integer | no | default `5` | Number of fiscal years to look back from the most recent filing (1–20). Defaults to 5 years for a full capital allocation cycle. |
| `as_of_date` | string | no | — | Point-in-time date (YYYY-MM-DD). Only returns facts with accepted_at on or before this date — eliminates look-ahead bias. |

**Output fields:** `ticker`, `lookback_years`, `as_of_date`, `periods_returned`, `note`, `data`

### `get_peer_comparables`

**Peer Comparables** · min plan `sample` · read-only · paging: none

Get ratio-based peer comparison for a company and its closest competitors by SIC industry code. Returns pipeline-computed ratios from up to 10 peers alongside the subject company for direct benchmarking. Ratio categories: profitability, liquidity, leverage, efficiency, per_sha...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Subject company ticker or CIK, e.g. AAPL or '0000320193'. Peers are auto-selected by SIC code. |
| `categories` | array | no | default `["profitability", "valuation", "leverage"]` | Ratio categories to include in the comparison. Defaults to profitability, valuation, and leverage. |
| `as_of_date` | string | no | — | Historical date (canonical cross-tool date param). Peers are the companies listed on this date, including ones delisted since, ranked by S&P 500 membership on this date. Figures are point-in-time by SEC acceptance time when the ratio data carries it (_meta.pit_safe=true), else limited to periods ending on or before this date (_meta.pit_safe=false). |
| `period_end_before` | string | no | — | Alias of as_of_date (as_of_date preferred — the canonical name). Only include ratios with period_end on or before this date. |
| `limit` | integer | no | default `5` | Maximum number of peers to return alongside the subject company (1–10). Defaults to 5. |
| `peer_universe` | enum | no | one of `sic`, `sp500_sector` | Where peers come from: 'sic' (default) matches SIC industry codes; 'sp500_sector' uses S&P 500 members in the subject's own sector, in ticker order. |

**Output fields:** `subject`, `categories`, `as_of_date`, `period_end_before`, `peers_returned`, `peers_omitted_no_data`, `note`, `data`, `subject_ratios`, `lineage`

### `get_pit_universe`

**Point-in-Time Universe** · min plan `sample` · read-only · paging: offset

Historical index membership, survivorship-free: who was in an index on `as_of_date` (companies that existed and belonged on that exact date, including ones delisted since; no hindsight). Use it INSTEAD OF `search_companies` for any past date ("Was X in the S&P 500 on Y?"); `se...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `index` | enum | no | one of `sp500`, `russell1000`, `russell2000`, `russell3000` | Index filter. 'sp500' (~500 large caps; reconstructed history from 1996, incomplete before ~2007, check pit_safe), 'russell1000' (~1000 large/mid), 'russell2000' (~2000 small caps), 'russell3000' (~3000 broad market) — the three Russell indices carry fund-derived history back to 2000-09-30 at medium confidence, with observation spacing that widens before 2007. Omit for no index filter (sector-only or full universe queries). |
| `sector` | string | no | — | Sector filter (case-insensitive substring) over the SIC-derived, GICS-aligned label (not licensed GICS — see tool description). E.g. 'Technology', 'Energy'. |
| `as_of_date` | string | no | — | Historical date (YYYY-MM-DD) for survivorship-free construction. Index queries use index_membership join/leave dates (entrants after the date excluded, later-removed members kept); sector queries use security valid_from/valid_to. Omit for the current universe. |
| `is_active` | boolean | no | — | Filter to active (currently trading) companies only. Omit to include all. WARNING: setting this to true on a HISTORICAL query reintroduces survivorship bias — companies that were active on as_of_date but later went bankrupt or got acquired will be filtered out.  Leave unset for true PIT backtests. |
| `include_share_classes` | boolean | no | default `false` | false (default) collapses to one row per CIK (index-provider convention — BRK counts once, not BRK-A + BRK-B). true returns every share-class row (GOOG and GOOGL separately) — for security-level analysis only. |
| `ticker` | string | no | — | Check ONE company: a ticker or a CIK (SEC identifier), e.g. 'AAPL' or '0000320193'. Returns that company's row if it was a member on as_of_date, none if it was not. A ticker matches the symbol listed ON that date, and a since-delisted member can carry no ticker at all (enriched=false), so prefer the CIK for historical checks. Omit to list the universe. |
| `limit` | integer | no | default `100` | Rows per page (1–3500; at most 250 are inlined per call). Defaults to 100. `universe_size` always states the full matched count; when more rows remain after this page the response carries a `truncation` envelope — call again with `offset` = its `next_offset`. Universe is deduped to one row per CIK (SP500 ~505, Russell 3000 ~3050). |
| `offset` | integer | no | default `0` | Zero-based row offset where this page starts. Pass the previous response's `truncation.next_offset` to fetch the next page. Defaults to 0. |

**Output fields:** `as_of_date`, `index`, `sector`, `universe_size`, `returned_rows`, `complete`, `limit_truncated`, `survivorship_free`, `coverage_gap`, `coverage`, `confidence_summary`, `note`, `truncation`, `companies`

### `get_compute_ready_stream`

**Compute-Ready Stream** · min plan `sample` · read-only · paging: none

Returns a short-lived (5-min) download URL for a bulk Parquet object that can be piped directly into Python/DuckDB/Polars for high-throughput computation that exceeds the MCP context window. The URL streams the object straight from Valuein storage and supports HTTP range reads...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `dataset_type` | enum | yes | one of `fact`, `ratio`, `filing`, `references`, `index_membership` | Dataset to access. 'fact' requires ticker (per-entity partition). All others are full-universe tables. |
| `ticker` | string | no | — | Required when dataset_type is 'fact'. Resolves to the per-entity fact/{CIK}.parquet partition for that company. |

**Output fields:** `dataset_type`, `ticker`, `bucket`, `object_key`, `url`, `scope`, `expires_at`, `expires_in_seconds`, `url_hash`, `format`, `usage`

### `describe_schema`

**Describe Data Schema** · min plan `sample` · read-only · paging: none

Describes the Valuein SEC data warehouse. With no arguments it lists every table with a one-line description and its column count; pass `table` (e.g. 'fact') for that table's columns, types, primary keys and foreign-key references. Use this tool to understand the data model be...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `table` | string | no | — | A single table name (e.g. 'fact', 'entity', 'references') to return its full column definitions. Omit to list every table with a one-line description and column count. |

**Output fields:** `schema_version`, `table`, `description`, `columns`, `project`, `tables`, `note`

### `list_sops`

**List Research Playbooks (SOPs)** · min plan `sample` · read-only · paging: none

List Valuein's expert research playbooks — the step-by-step procedures a senior equity analyst follows, each encoding the exact tool sequence, parallel-wave grouping, and output structure for one task (research brief, screen and shortlist, forensic quality audit, capital-alloc...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `filter` | string | no | — | Case-insensitive substring matched against each playbook's name, title, and description — e.g. 'smart money', 'thesis', 'backtest'. Omit to list all. |

**Output fields:** `content_type`, `sop_count`, `sops`

### `get_sop`

**Get Research Playbook (SOP)** · min plan `sample` · read-only · paging: none

Load one expert research playbook by name (discover names with `list_sops`). Returns the full procedure: the ordered tool sequence, which calls to group into parallel waves, the provenance and citation rules, and the exact output structure. Supply the playbook's arguments (e.g...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `name` | string | yes | — | SOP slug from list_sops, e.g. 'equity_research_brief'. |
| `args` | object | no | — | Playbook arguments as string values, e.g. { ticker: 'AAPL', depth: 'full' }. Omit to read the generic template with {{ARG}} placeholders. |

**Output fields:** `content_type`, `name`, `title`, `description`, `args`, `instantiated`, `placeholder_args`, `body`, `retired`, `replacement`

### `verify_fact_lineage`

**Verify Fact Lineage** · min plan `sample` · read-only · paging: none

Which verifier: one fact_id → verify_fact_lineage; a list of fact_ids or derived_ids → verify_facts; a number with no id → match_derived; a number quoted from filing text or insider/13F rows → verify_filing_figures; every number in a saved report → verify_report_figures; figur...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | no | — | Stock ticker symbol, e.g. AAPL, MSFT, BRK.B — or a CIK (SEC identifier), e.g. '0000320193'. Required with `fact_id` or `concept`: a fact_id is unique within its company's filings, so pass the company it came from (every result that gives you a fact_id also names the company's CIK). Not needed with `derived_id`. |
| `fact_id` | string | no | — | Deterministic fact identity hash: SHA-256(entity_id\|accession_id\|concept\|period_end\|unit). 64-char lowercase hex. Use this when you already have the hash from a previous query. Provide either fact_id OR concept (not both required, but at least one must be set). |
| `concept` | enum | no | one of `TotalRevenue`, `CostOfRevenue`, `GrossProfit`, `OperatingIncome`, `OperatingExpenses`, `ResearchAndDevelopment`, `NetIncome`, `EPSDiluted`, `TotalAssets`, `TotalLiabilities`, `ParentEquity`, `TotalEquity`, `StockholdersEquity`, `StockholdersEquityIncludingNCI`, `CashAndEquivalents`, `TotalDebt`, `OperatingCashFlow`, `CAPEX`, `Dividends`, `ShareBuyback`, `DebtIssuance`, `DebtRepayment`, `Acquisitions`, `Divestitures` | Standard concept to look up the most recently known fact for (see the enum for the full fundamentals + capital-allocation set). Use this when you don't have a fact_id. Provide either concept OR fact_id. |
| `period_end` | string | no | — | [DEPRECATED — pass `as_of_date` instead.] Filing-acceptance cutoff (YYYY-MM-DD) used with `concept`; despite the name it filters on filing accepted_at, not the returned fact's period_end. Kept one release for back-compat. |
| `as_of_date` | string | no | — | Point-in-time cutoff (YYYY-MM-DD) used with `concept` — returns the latest fact whose 10-K/10-Q was accepted by SEC on or before this date (true PIT, no lookahead; any calendar date works). Canonical name across the suite; supersedes the legacy `period_end`. |
| `derived_id` | string | no | — | Citation id of a computed figure (`drv1:...`), exactly as a tool result gave it to you. Re-derived from its input facts; `as_of_date` applies the point-in-time cut to every input. |

**Output fields:** `verified`, `lookup_by`, `lineage`, `derived`, `error`

### `verify_facts`

**Verify Facts (batch)** · min plan `sample` · read-only · paging: none

Which verifier: one fact_id → verify_fact_lineage; a list of fact_ids or derived_ids → verify_facts; a number with no id → match_derived; a number quoted from filing text or insider/13F rows → verify_filing_figures; every number in a saved report → verify_report_figures; figur...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `facts` | array | yes | — | The facts to verify, 1–50 of them. Group a report's whole citation list here rather than calling once per figure. Duplicate (ticker, fact_id) pairs are resolved once and returned once, in first-seen order. |
| `as_of_date` | string | no | — | Point-in-time cut (YYYY-MM-DD) for `derived_id` items: an input whose filing was accepted after this date is INPUT_NOT_FOUND. Fact items are unaffected. |

**Output fields:** `results`, `summary`

### `match_derived`

**Match Derived Figures** · min plan `sample` · read-only · paging: none

Which verifier: one fact_id → verify_fact_lineage; a list of fact_ids or derived_ids → verify_facts; a number with no id → match_derived; a number quoted from filing text or insider/13F rows → verify_filing_figures; every number in a saved report → verify_report_figures; figur...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `items` | array | yes | — | The figures to check, 1–50; one call per report, not one per figure. |
| `as_of_date` | string | no | — | Point-in-time cut (YYYY-MM-DD): a cited fact accepted after this date is not used. |

**Output fields:** `results`, `summary`

### `verify_filing_figures`

**Verify Filing Figures** · min plan `sample` · read-only · paging: none

Which verifier: one fact_id → verify_fact_lineage; a list of fact_ids or derived_ids → verify_facts; a number with no id → match_derived; a number quoted from filing text or insider/13F rows → verify_filing_figures; every number in a saved report → verify_report_figures; figur...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `items` | array | yes | — | The figures to check, 1-50, of at most 5 companies. |

**Output fields:** `results`, `summary`

### `compare_periods`

**Compare Financial Periods** · min plan `sample` · read-only · paging: none

Compare a company's core financial metrics across two fiscal periods side-by-side. Shows absolute and percentage changes with significance classification (minor &lt; 5%, notable 5–15%, significant > 15%). The response includes a `material_changes` count: this is the number of met...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol, e.g. AAPL, MSFT, BRK.B — or a CIK (SEC identifier), e.g. '0000320193'. |
| `period_a` | string | yes | — | Earlier fiscal period. Format: 'FY2023' for annual or 'Q1-2023' for quarterly. |
| `period_b` | string | yes | — | Later fiscal period. Format: 'FY2024' for annual or 'Q1-2024' for quarterly. |
| `as_of_date` | string | no | — | Point-in-time date (YYYY-MM-DD). Only returns facts with accepted_at on or before this date — eliminates look-ahead bias for backtesting. |

**Output fields:** `ticker`, `company_name`, `period_a`, `period_b`, `as_of_date`, `swapped`, `total_metrics`, `material_changes`, `changes`

### `screen_universe`

**Screen Universe by Factor Scores** · min plan `sample` · read-only · paging: offset

Rank companies by cross-sectional factor scores from [withheld]. Returns the underlying factors (roe, gross_margin, operating_margin, net_profit_margin, revenue_growth_yoy, fcf_to_assets, debt_to_equity, asset_turnover, current_ratio, piotroski_f_score) plus their p...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | no | — | If provided, show only this ticker's factor scores (single-entity mode). Omit to screen the full universe. |
| `sector` | string | no | — | Filter to a specific sector (case-insensitive partial match). E.g. 'Technology', 'Healthcare'. |
| `sort_by` | enum | no | one of `roe_rank`, `gross_margin_rank`, `operating_margin_rank`, `net_profit_margin_rank`, `revenue_growth_yoy_rank`, `fcf_to_assets_rank`, `debt_to_equity_rank`, `asset_turnover_rank`, `current_ratio_rank`, `piotroski_f_score_rank` + 1 [withheld]; default [withheld] | Which factor rank to sort by (see the enum). Defaults to [withheld]. An unrecognized column is rejected with INVALID_ARGUMENT (no silent fallback). |
| `limit` | integer | no | default `25` | Number of results to return (1-100). Defaults to 25. |
| `offset` | integer | no | default `0` | Zero-based row offset for paging within the requested `limit` window. At most 250 rows are inlined per call; if the response carries a `truncation` envelope, pass its `next_offset` here. Defaults to 0. |
| `as_of_date` | string | no | — | Point-in-time cutoff (YYYY-MM-DD). When set, the screen is reconstructed as of this date via [withheld] — each entity ranked at its latest-knowable period, zero look-ahead, survivorship-free. Omit for the latest snapshot. |
| `exclude_outliers` | boolean | no | default `false` | Optional data-quality guard (default false). When true, additionally drops rows with implausible raw factor values (non-finite, or e.g. asset_turnover > 50x, \|FCF/assets\| > 10) from shell companies with near-zero denominators. Rows that do not join to a company (null symbol) are ALWAYS omitted in full-universe mode, regardless of this flag. |

**Output fields:** `plan`, `sort_by`, `sector_filter`, `ticker`, `as_of_date`, `pit_safe`, `results_returned`, `note`, `truncation`, `data`, `lineage`

### `get_earnings_signals`

**Earnings Signals** · min plan `sample` · read-only · paging: none

Reported earnings results and a model-derived earnings-trend signal for a company, by fiscal period: actual reported EPS, a trailing-trend EPS estimate ([withheld]), the deviation of actual vs that trend (`eps_surprise_pct`), reported revenue, and year-over-year revenue g...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol, e.g. AAPL, MSFT — or a CIK (SEC identifier), e.g. '0000320193'. |
| `as_of_date` | string | no | — | Point-in-time filter: only return signals with accepted_at on or before this date. Use for backtesting to avoid look-ahead bias. |
| `limit` | integer | no | default `8` | Maximum number of periods to return (1–40), most recent first. Defaults to 8 — covers 2 years of quarterly signals plus their TTM equivalents. [withheld] currently emits one row per (entity, period_end); older rows surface here as more historical periods are published. |

**Output fields:** `ticker`, `plan`, `as_of_date`, `periods_returned`, `note`, `estimate_basis`, `data`

### `get_filing_review_pack`

**Filing Review Pack** · min plan `sample` · read-only · paging: none

Everything for a 10-K / 10-Q case in ONE call, already cited: the company and the filing (form, accession, period, filed date), this period against the prior comparable period (`compare_periods`, with `derived_id`s), key ratios, earnings signals, forensic flags (`forensic_audi...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Company ticker or CIK (SEC identifier), e.g. 'AAPL' or '0000320193'. A CIK is the stable identifier. |
| `accession` | string | no | — | A specific 10-K / 10-Q to review. Omit for the latest. |
| `period` | string | no | default `latest` | 'latest', 'FY2024' or 'Q3-2024'. Ignored when `accession` is given. |
| `as_of_date` | string | no | — | Point-in-time cutoff: every section reads only what the SEC had accepted by this date. A section that cannot honour it is not run and says so. |

**Output fields:** `pack`, `company`, `as_of_date`, `degraded`, `note`, `filing`, `sections`, `reading_list`

### `get_company_brief_pack`

**Company Brief Pack** · min plan `sample` · read-only · paging: none

The starting bundle for a company case in ONE call, already cited: latest annual and latest quarterly fundamentals, peers (by SIC) with their ratios, and valuation metrics. Each section is the underlying tool's output unchanged (`value`, `fact_id`, `availability`, `metrics_dis...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Company ticker or CIK (SEC identifier), e.g. 'AAPL' or '0000320193'. A CIK is the stable identifier. |
| `as_of_date` | string | no | — | Point-in-time cutoff: every section reads only what the SEC had accepted by this date. A section that cannot honour it is not run and says so. |

**Output fields:** `pack`, `company`, `as_of_date`, `degraded`, `note`, `sections`

### `list_restatements`

**Restatement Radar Feed** · min plan `sample` · read-only · paging: cursor

List financial-statement restatements — facts a later SEC filing materially changed from what was originally reported. Each event carries the as-reported value, the restated value, the signed delta, a severity bucket, the RAW XBRL tag both filings used (the diff is same-tag, s...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `event_id` | string | no | — | Fetch exactly one event by its id (from a prior response). |
| `ticker` | string | no | — | Restrict to one company — ticker (e.g. 'AAPL') or CIK (e.g. '0000320193'). |
| `sector` | string | no | — | Restrict to one GICS-style sector (e.g. 'Technology'). |
| `severity` | enum | no | one of `high`, `medium`, `low` | Size of the change: high (largest), medium or low. |
| `min_abs_delta_pct` | number | no | — | Only events whose absolute restatement is at least this percent (e.g. 5 = ≥5% swings). |
| `max_importance` | integer | no | — | Only lines at or above this importance tier: 1 = headline only (revenue, net income, EPS, total assets, operating cash flow), 2 = + primary statement lines, 3 = everything incl. footnotes. Severity says how far a number moved; importance says whether anyone cares. |
| `amendments_only` | boolean | no | — | Only restatements that arrived in an AMENDED filing (10-K/A, 10-Q/A) — the company formally telling the SEC it got a number wrong. The sharpest cut there is: it separates real restatements from routine re-files (a next-year 10-K carrying a revised comparative). |
| `disclosure` | array | no | — | Filter by HOW the company told the market. 'non_reliance' = it filed an 8-K Item 4.02 ('Non-Reliance on Previously Issued Financial Statements') — formally telling the SEC not to rely on what it already reported. The loudest signal in US disclosure, and rare. 'amended' = corrected in a 10-K/A or 10-Q/A. 'undisclosed' = the value changed inside a ROUTINE 10-Q or 10-K: no amendment, no 4.02, the old number is simply gone. ~94% of events. Anyone can parse an 8-K, so anyone can list what companies ANNOUNCED; finding what they didn't requires every vintage back to 1993. |
| `filed_since` | string | no | — | Only restatements FILED on or after this date — the 'what changed recently' window. |
| `as_of_date` | string | no | — | Point-in-time filter: only restatements whose restating filing was accepted (last_filed_at) on or before this day, inclusive. Results are point-in-time ONLY when this is passed — omit it and later restatements are included. Use for backtests and dated analyses to avoid look-ahead bias. |
| `sort` | enum | no | one of `recent`, `significance`; default `recent` | 'recent' = newest restating filing first (a market-wide radar). 'significance' = importance tier, then swing size (one company's history). |
| `limit` | integer | no | default `25` | Page size (1-100, default 25). With include_cause it is clamped to 25. |
| `include_cause` | boolean | no | default `false` | Add `cause`, `cause_quote` and `cause_state` to each event, read from the restating filing. Reads one filing per event, so the page is clamped to 25. Default false. |
| `cause` | array | no | — | Only with include_cause: keep events of these causes (error \| merger \| reclass \| none) from THIS PAGE. It filters the page returned, not the whole feed; `filtered_out` counts the rows dropped. |
| `cursor` | string | no | — | Opaque pagination cursor from a prior response's next_cursor. |

**Output fields:** `events`, `total`, `filtered_out`, `next_cursor`, `note`

### `explain_restatement`

**Explain a Restatement** · min plan `sample` · read-only · paging: none

Why did a restating filing change a number? Reads the RESTATING filing itself (the `current_accession` of a `list_restatements` event) and returns the sentence in which the company states the cause, with the section it sits in. `cause` is `error` (an error correction), `merger...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `cik` | string | yes | — | The restating filing's filer, from the event's `cik`. Padded to 10 digits. |
| `accession` | string | yes | — | The RESTATING filing's accession (the event's `current_accession`). |
| `disclosure_class` | enum | yes | one of `non_reliance`, `amended`, `undisclosed` | The event's `disclosure_class`. `non_reliance` makes the cause `error` by definition. |

**Output fields:** `state`, `cause`, `cause_quote`, `section`, `filing_url`

### `submit_feedback`

**Submit Feedback** · min plan `sample` · writes · paging: none

File product feedback to the Valuein team — a bug, feature request, experience note, or data-quality issue — directly from the agent surface. Plan: every plan, including no sign-in (no token required), so an agent can report a rough edge in-band without the human leaving the c...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `category` | enum | yes | one of `bug`, `feature_request`, `experience`, `data_quality`, `other` | What kind of feedback this is: 'bug' (something broke), 'feature_request' (something missing), 'experience' (UX / clarity / docs), 'data_quality' (a wrong/missing/stale figure), or 'other'. |
| `message` | string | yes | — | The feedback body (1–4000 chars). Be specific: what you expected, what happened, and any reproduction steps. Stored for triage and never used for arithmetic. The person's own words about the product, or yours; never a copy of their research. Do not paste research into it. |
| `subject` | string | no | — | Optional short title (≤140 chars) summarizing the feedback. |
| `severity` | enum | no | one of `low`, `medium`, `high` | Optional impact classification: 'low', 'medium', or 'high'. |
| `surface` | enum | no | one of `mcp`, `workspace`, `sdk`, `dashboard`, `api` | Optional product surface the feedback concerns: 'mcp', 'workspace', 'sdk', 'dashboard', or 'api'. |
| `context` | object | no | — | Optional free-form context object (stored as JSON), e.g. { tool: 'get_company_fundamentals', ticker: 'AAPL', request_id: 'abc123' }. Avoid secrets. |
| `idempotency_key` | string | no | — | Optional client-supplied key (1–64 chars). For authenticated callers, reusing the same key files the feedback exactly once — safe to retry on a network error. Ignored for guest/sample callers (no account to scope dedup to). |
| `sentiment` | enum | no | one of `positive`, `negative`, `correction` | Optional sentiment of this feedback: 'positive' (worked well), 'negative' (something was wrong), or 'correction' (you are supplying the right value). |
| `reason` | enum | no | one of `wrong_number`, `bad_citation`, `missing_data`, `wrong_company`, `formatting`, `hallucinated_fact`, `tool_error`, `coverage_gap`, `other` | Optional structured error-mode reason: 'wrong_number', 'bad_citation', 'missing_data', 'wrong_company', 'formatting', 'hallucinated_fact', 'tool_error', 'coverage_gap', or 'other'. |
| `target_type` | enum | no | one of `chat_message`, `report`, `tool_call`, `schema`, `other` | Optional kind of artifact the feedback targets: 'chat_message', 'report', 'tool_call', 'schema', or 'other'. |
| `target_id` | string | no | — | Optional id of the artifact this feedback targets (e.g. a report id). |
| `request_id` | string | no | — | Optional `_meta` request id of the turn that produced the artifact, for correlation. |
| `fact_id` | string | no | — | Optional disputed `fact_id` (for wrong_number / bad_citation feedback). |
| `expected_value` | string | no | — | Optional caller-asserted correct value, in your own words. Stored verbatim for triage — NEVER computed or trusted as data. The person's own words about the product, or yours; never a copy of their research. |

**Output fields:** `feedback`, `acknowledgment`

### `submit_artifact_feedback`

**Submit Artifact Feedback** · min plan `sample` · writes · paging: none

File EXPLICIT, structured feedback about a specific artifact you (or the model) produced — a chat message, a report, a tool call, or the schema.

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `target_type` | enum | yes | one of `chat_message`, `report`, `tool_call`, `schema`, `other` | REQUIRED. The kind of artifact this feedback is about: 'chat_message', 'report', 'tool_call', 'schema', or 'other'. |
| `target_id` | string | yes | — | REQUIRED. The id of the artifact this feedback targets (a report id, message id, tool-call id, or table/schema name). |
| `sentiment` | enum | yes | one of `positive`, `negative`, `correction` | REQUIRED. How you judge the artifact: 'positive' (it was right/useful), 'negative' (it was wrong/unhelpful), or 'correction' (you are supplying the right value via `expected_value`). |
| `reason` | enum | no | one of `wrong_number`, `bad_citation`, `missing_data`, `wrong_company`, `formatting`, `hallucinated_fact`, `tool_error`, `coverage_gap`, `other` | Optional structured error-mode: 'wrong_number', 'bad_citation', 'missing_data', 'wrong_company', 'formatting', 'hallucinated_fact', 'tool_error', 'coverage_gap', or 'other'. |
| `request_id` | string | no | — | Optional `_meta` request id of the turn that produced the artifact. Folded into the idempotency key so a retried submission of the same judgement files once. |
| `fact_id` | string | no | — | Optional disputed `fact_id` (most useful for wrong_number / bad_citation). |
| `ticker` | string | no | — | Optional ticker the disputed figure belongs to (e.g. 'AAPL', 'BRK.B'). ALWAYS send this alongside `fact_id` — a `fact_id` is a one-way hash that does not contain the symbol, so without it nobody can locate the filing and your report cannot be checked against the source. Supplying it is what turns a complaint into a verifiable one. |
| `expected_value` | string | no | — | Optional: what the value SHOULD have been, in your own words. Stored verbatim for triage — NEVER computed, restated, or trusted as data by Valuein. The person's own words about the product, or yours; never a copy of their research. |
| `message` | string | no | — | Optional free-text detail (≤4000 chars). What you expected and what happened. The person's own words about the product, or yours; never a copy of their research. |
| `idempotency_key` | string | no | — | Optional explicit dedupe key (1–64 chars). Used to dedupe when no `request_id` is supplied; safe to retry on a network error. |

**Output fields:** `feedback_id`, `status`

### `get_insider_transactions`

**Insider Transactions** · min plan `full` · read-only · paging: none

Form 3 / 4 / 5 / 144 line items for a US public company. Returns each transaction (or initial holding / proposed sale) with the insider's name, role, transaction code, share count, price, and notional. Filters by lookback window, transaction code (P=purchase, S=sale, A=grant, ...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol, e.g. AAPL, MSFT, BRK.B — or a CIK (SEC identifier), e.g. '0000320193'. |
| `lookback_days` | integer | no | default `90` | How many days back from today to scan transactions for. Ignored when as_of_date is set. |
| `transaction_codes` | array | no | — | SEC transaction codes to keep (uppercase, single-letter):  P=purchase, S=sale, A=grant, M=option exercise, F=tax withholding, G=gift, J=other.  Unknown codes are rejected.  Omit to include all codes. |
| `roles_in` | array | no | — | Insider roles to keep. Omit to include any role. |
| `min_shares` | number | no | — | Minimum \|shares\| per transaction. Omit for no floor. |
| `as_of_date` | string | no | — | Point-in-time date (YYYY-MM-DD).  Only returns transactions with accepted_at &lt;= this date — eliminates look-ahead bias.  When set, lookback_days is ignored. |
| `limit` | integer | no | default `100` | Maximum rows to return. Default 100, max 500. |
| `lineage_detail` | enum | no | one of `off`, `compact`, `full`; default `compact` | Per-row provenance envelope. 'compact' (default) returns source_filing + source_url. 'full' adds accepted_at. 'off' omits lineage. |

**Output fields:** `ticker`, `cik`, `company_name`, `data_age_days`, `staleness_warning`, `note`, `rows`

### `get_institutional_holdings`

**Institutional Holdings (by issuer)** · min plan `full` · read-only · paging: none

Returns top-N institutional holders of a US public company at a specific period_end (by default the latest period whose 45-day 13F filing window has closed), with aggregate institutional shares, total market value, holder count, and HHI concentration (sum of squared share-of-t...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol of the issuer — or a CIK (SEC identifier). |
| `period_end` | string | no | — | Quarter-end of the 13F reporting period (YYYY-MM-DD). Omit to use the latest period available. This is a REPORTING period, NOT a point-in-time cutoff — use as_of_date for that. |
| `as_of_date` | string | no | — | Point-in-time cutoff (YYYY-MM-DD): only 13F filings ACCEPTED by SEC on or before this date are considered, applied BEFORE the latest period is resolved. A 13F/A amendment or late filing accepted after this date is excluded (zero look-ahead) — use this for survivorship-free backtests. Omit for the latest knowable book. |
| `top_n` | integer | no | default `25` | Maximum holders to return, ranked by market_value_usd. Default 25, max 200. |
| `include_superseded` | boolean | no | default `false` | Default false: 13F-HR rows replaced by a later 13F-HR/A are hidden once the amendment is knowable (as of as_of_date when given), so an original and its amendment are never both counted. Set true to include the superseded originals. |
| `lineage_detail` | enum | no | one of `off`, `compact`, `full`; default `compact` | Per-row provenance envelope. compact / full / off. |

**Output fields:** `ticker`, `cik`, `company_name`, `period_end`, `as_of_date`, `data_age_days`, `staleness_warning`, `total_institutional_shares`, `total_market_value_usd`, `hhi_concentration`, `holders_count`, `options_positions_count`, `filing_window_open`, `filing_deadline`, `newer_period_in_filing_window`, `metrics_display`, `aggregate`, `rows`

### `get_manager_portfolio`

**Manager Portfolio (13F by filer)** · min plan `full` · read-only · paging: none

Returns a 13F filer's full portfolio at a specific period_end (latest by default), with QoQ deltas vs the prior quarter (new / increased / decreased / exited / unchanged). Specify the filer either by filer_cik (preferred) or filer_name (fuzzy match against entity.name; multipl...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `filer_cik` | string | no | — | CIK of the 13F filer (1-10 digits; will be zero-padded to 10).  Preferred over filer_name when known. |
| `filer_name` | string | no | — | Filer name to fuzzy-match against entity.name.  Case-insensitive substring match.  Multiple matches raise INVALID_ARGUMENT — use filer_cik in that case. |
| `period_end` | string | no | — | Quarter-end (YYYY-MM-DD).  Omit to use latest available.  This is a REPORTING period, NOT a point-in-time cutoff — use as_of_date for that. |
| `as_of_date` | string | no | — | Point-in-time cutoff (YYYY-MM-DD): only 13F filings ACCEPTED by SEC on or before this date are considered, applied BEFORE the latest + prior periods (and the QoQ basis) are resolved. A 13F/A amendment or late filing accepted after this date is excluded (zero look-ahead). Omit for the latest knowable portfolio. |
| `top_n` | integer | no | default `25` | Maximum positions to return, ranked by market_value_usd. Default 25. |
| `include_superseded` | boolean | no | default `false` | Default false: 13F-HR rows replaced by a later 13F-HR/A are hidden once the amendment is knowable (as of as_of_date when given), so an original and its amendment are never both counted. Set true to include the superseded originals. |
| `lineage_detail` | enum | no | one of `off`, `compact`, `full`; default `compact` | Per-row provenance envelope. |

**Output fields:** `filer_cik`, `filer_name`, `period_end`, `prior_period_end`, `as_of_date`, `data_age_days`, `staleness_warning`, `total_market_value_usd`, `positions_count`, `aggregate`, `rows`

### `get_blockholders`

**Blockholders (SC 13D / 13G)** · min plan `full` · read-only · paging: none

Returns SC 13D / SC 13G blockholder disclosures (5%+ stakes) for a US public company. Each row carries percent_owned, sole/shared voting + dispositive split, schedule_type, and the first-class ``going_active`` flag — TRUE when the same filer flipped 13G → 13D within the lookba...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol of the issuer — or a CIK (SEC identifier). |
| `schedule_filter` | enum | no | one of `13D`, `13G`, `both`; default `both` | Which schedule(s) to return.  '13D' = activist (intent to influence). '13G' = passive.  'both' = no filter. |
| `as_of_date` | string | no | — | PIT filter on accepted_at — only filings on or before this date. |
| `latest_only` | boolean | no | default `true` | When true (default), keep only the most recent filing per (filer, schedule prefix) — typically what analysts want.  Set false to see the full filing history. |
| `collapse_groups` | boolean | no | default `false` | When true, fold multi-reporting-person filings into a single row, with secondary persons in the ``persons[]`` field.  Default false: each person stays as its own row. |
| `lookback_days` | integer | no | default `365` | Window for the going_active (13G → 13D) detection. Default 365 days. |
| `lineage_detail` | enum | no | one of `off`, `compact`, `full`; default `compact` | Per-row provenance envelope. |

**Output fields:** `ticker`, `cik`, `company_name`, `data_age_days`, `staleness_warning`, `rows`

### `get_insider_sentiment`

**Insider Sentiment (composite)** · min plan `full` · read-only · paging: none

Role-weighted insider sentiment score on a fixed [-100, +100] scale for a single issuer over a lookback window. Role weights: CEO/CFO = 3.0 (via officer_title pattern), other NEO Officer = 2.0, 10%-Owner = 1.5, Director = 1.0. P = +1, S = -1; option exercises, grants, and tax ...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Issuer ticker symbol — or a CIK (SEC identifier). |
| `lookback_days` | integer | no | default `180` | Days back from today to scan transactions for. Default 180. |
| `cluster_window_days` | integer | no | default `30` | Sliding window for the cluster_flag detection. Default 30 days. |

**Output fields:** `ticker`, `cik`, `company_name`, `lookback_days`, `sentiment_score`, `buy_count`, `sell_count`, `total_buy_shares`, `total_sell_shares`, `total_buy_usd`, `total_sell_usd`, `cluster_flag`, `top_contributors`, `metrics_display`

### `get_top_holders`

**Top Holders (composite, classified)** · min plan `full` · read-only · paging: none

Classification-aware UNION across insider transactions (latest post_transaction_shares per insider), 13F institutional holdings, and SC 13D / 13G blockholder filings for one issuer. Each row carries holder_class ∈ {insider, institutional, blockholder_13D, blockholder_13G}. Ded...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Issuer ticker symbol — or a CIK (SEC identifier). |
| `top_n` | integer | no | default `25` | Maximum holders to return, ranked by shares. Default 25. |
| `period_end` | string | no | — | 13F REPORTING period_end. Omit for latest. NOT a point-in-time cutoff — use as_of_date. |
| `as_of_date` | string | no | — | Point-in-time cutoff (YYYY-MM-DD): only filings ACCEPTED by SEC on or before this date are considered across all three sources (institutional via accepted_at, insider via accepted_at, blockholders via accepted_at). Excludes amendments/late filings accepted after this date (zero look-ahead). Omit for the latest knowable cap table. |
| `include_superseded` | boolean | no | default `false` | Default false: 13F-HR rows replaced by a later 13F-HR/A are hidden once the amendment is knowable (as of as_of_date when given), so an original and its amendment are never both counted. Set true to include the superseded originals. |

**Output fields:** `ticker`, `cik`, `company_name`, `period_end`, `as_of_date`, `sources_breakdown`, `staleness`, `rows`

### `get_smart_money_flow`

**Smart Money Flow (composite)** · min plan `full` · read-only · paging: none

Composite flow score on [-100, +100] aggregating insider transactions, 13F institutional Δ-shares vs the prior quarter, and SC 13D/13G blockholder changes over a lookback window. Each component normalised independently, then combined with configurable weights (default: institu...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Issuer ticker symbol — or a CIK (SEC identifier). |
| `lookback_days` | integer | no | default `90` | Lookback window for insider + blockholder components. Default 90. |
| `weight_institutional` | number | no | default `0.4` | Weight applied to the institutional component (0–1). |
| `weight_blockholder` | number | no | default `0.4` | Weight applied to the blockholder component (0–1). |
| `weight_insider` | number | no | default `0.2` | Weight applied to the insider component (0–1). |
| `as_of_date` | string | no | — | Point-in-time cutoff (YYYY-MM-DD) applied to all three legs (institutional, insider, blockholder) via SEC accepted_at — filings accepted after this date are excluded so the composite is computed with zero look-ahead. Omit for the latest knowable signal. |

**Output fields:** `ticker`, `cik`, `company_name`, `period_end`, `as_of_date`, `composite_score`, `insider_component`, `institutional_component`, `blockholder_component`, `weights`, `components`, `coverage`, `metrics_display`

### `get_ownership_pack`

**Ownership Pack** · min plan `full` · read-only · paging: none

Who owns the company and who is moving, in ONE call, already cited: top holders (13F, insiders, 13D/13G), recent insider transactions and insider sentiment, blockholders including 13G to 13D flips (`going_active`), and the smart-money flow composite. Each section is the underl...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Company ticker or CIK (SEC identifier), e.g. 'AAPL' or '0000320193'. A CIK is the stable identifier. |
| `lookback_days` | integer | no | default `180` | Window for insider transactions and flow. Default 180. Ignored for insiders when `as_of_date` is set. |
| `as_of_date` | string | no | — | Point-in-time cutoff: every section reads only what the SEC had accepted by this date. A section that cannot honour it is not run and says so. |

**Output fields:** `pack`, `company`, `as_of_date`, `degraded`, `note`, `sections`

### `restore_deleted`

**Restore a Deleted Item** · min plan `sp500` · writes · paging: none

Undo a delete: restores a watchlist, signal or report that `delete_*` archived, a rule, citation override or uploaded document that `delete_*` removed, a memory entry removed by `delete_agent_memory` (id = its key), an inbox item hidden by `dismiss_inbox_item` (id = inbox_id),...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `kind` | enum | yes | one of `watchlist`, `signal`, `report`, `rule`, `citation_override`, `uploaded_document`, `agent_memory`, `inbox_item`, `scheduled_task`, `agent` | Which record type to restore. |
| `id` | string | yes | — | The record's id. For a watchlist this is the `watchlist_id` returned by `delete_watchlist` — NOT its name, because deleting a watchlist frees its name for reuse. For a rule, the `rule_id`; for a citation override, its `fact_id`; for an uploaded document, its `upload_id`; for agent_memory the memory key (up to 128 chars); for inbox_item the `inbox_id`; for scheduled_task the `task_id`; for agent the `agent_id`. |

**Output fields:** `kind`, `id`, `status`, `prior_status_known`

### `undo_change`

**Undo a Change** · min plan `sp500` · writes · paging: none

Put a record back as it was before one write. Pass the `change_id` from the `undo` field of `update_signal`, `update_report`, `mark_inbox_read` (item becomes unread again) or `stage_action` (the proposal is withdrawn as rejected, only while still pending; the target tool never...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `change_id` | string | yes | — | The `undo.args.change_id` a reversible write returned. A client cannot supply any other state. |

**Output fields:** `undone`, `kind`, `ids`, `undo`

### `run_workflow`

**Run Saved Workflow** · min plan `sp500` · read-only · paging: none

Resolve a saved workflow by id and return a structured execution plan for a single ticker. Each plan entry names a real MCP tool or SOP plus its ticker-substituted arguments; the calling agent invokes them in order, applying any `skip_if` predicate against the previous step's ...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `workflow_id` | string | yes | — | Workflow id from the user's Valuein Workspace (valuein.biz/workspace/workflows); ask the user for it. |
| `ticker` | string | no | — | US-listed ticker the workflow should run against, e.g. 'AAPL'. Pass either `ticker` (single) or `tickers` (batch up to 50). Exactly one is required. |
| `tickers` | array | no | — | Batch mode — array of US-listed tickers, up to 50. When provided, the response has `plans[]` (one plan per ticker) instead of `plan`. Parity with the frontend batch-runner so agents can request 'plan over my watchlist' in a single call. |

**Output fields:** `meta`, `workflow`, `ticker`, `plan`, `plans`, `instructions`

### `save_citation_override`

**Save Citation Override** · min plan `sp500` · writes · paging: none

Persist a correction of a citation value. The correction is keyed on the canonical `fact_id` (a stable hash of CIK + accession + concept + period) so it applies to every report that references that same fact — including agent-regenerated reports. Re-saving the same fact_id rep...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `fact_id` | string | yes | — | Canonical fact identifier — usually returned in a citation's `fact_ids` array by get_report or any compute tool. Stable across report regenerations. Verified against live SEC data (scoped to `ticker`) before persistence — a fabricated or unresolvable fact_id is rejected. |
| `corrected_value` | string | yes | — | User-corrected value, stringified. The frontend interprets it based on the fact's known datatype (number, string, ISO date). |
| `ticker` | string | yes | — | Ticker the fact belongs to (REQUIRED) — scopes fact_id resolution against live SEC data and denormalises the row for fast filtering (the workspace UI's 'my corrections on AAPL' view). |
| `source_report_id` | string | no | — | Optional report id the user was viewing when they applied the correction (provenance). |
| `notes` | string | no | — | Optional free-form rationale, ≤500 chars. |

**Output fields:** `override`, `created`, `capacity`

### `list_citation_overrides`

**List Citation Overrides** · min plan `sp500` · read-only · paging: cursor

Author-only newest-first listing of the caller's citation corrections. Filterable by ticker (e.g. all AAPL corrections) or by a single fact_id (returns 0 or 1 row). Pair with `save_citation_override` and `delete_citation_override`. Sample tier rejected. Agent use: call with `t...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | no | — | Optional ticker filter, case-insensitive. Uppercased internally. |
| `fact_id` | string | no | — | Optional fact_id filter — returns at most one row. |
| `limit` | integer | no | default `20` | Maximum number of citation overrides to return (1–100). Defaults to 20. |
| `cursor` | integer | no | — | Cursor from the previous response's `next_cursor` — the updated_at of the last row on that page. Omit for first page. |

**Output fields:** `overrides`, `next_cursor`, `total_count`

### `delete_citation_override`

**Delete Citation Override** · min plan `sp500` · destructive · paging: none

Remove a user-authored citation correction by fact_id. Idempotent — deleting a missing override returns deleted=false without error. UNDOABLE: restore_deleted with kind 'citation_override' brings it back (unless a new save for the same fact_id replaced it). Once deleted, repor...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `fact_id` | string | yes | — | Fact identifier whose citation override should be removed, as returned by save_citation_override or list_citation_overrides. |

**Output fields:** `fact_id`, `deleted`

### `save_figure_review`

**Save Figure Review** · min plan `sp500` · writes · paging: none

Record (or update) the review state of ONE figure inside a report — the durable answer to 'has a human traced this number back to its filing?' Upsert keyed on (report_id, figure_key): re-reviewing a figure REPLACES its prior mark, it never appends, so this is always the figure...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Identifier of the report the figure belongs to, as returned by create_report / list_my_reports / save_freeform_report. |
| `figure_key` | string | yes | — | Opaque id you mint for one figure inside the report. Never parsed or validated beyond length — use the exact same key to update this figure's review later. Shape for a dataset-backed figure: 'fact:{fact_id}#{figure}', the figure lowercased and whitespace-collapsed as the report writes it ('fact:f_rev#$402.83b'); the Workspace mints 'raw:{hash}' for a figure with no fact, which only it can compute. |
| `state` | enum | yes | one of `verified`, `corrected`, `external`, `rejected` | verified = traced to its filing and correct. corrected = wrong (supply corrected_value). external = legitimately not from Valuein data (analyst's own source). rejected = unsupported, should be removed from the report. |
| `note` | string | no | — | Optional free-text reviewer note (e.g. what was checked, or why it was rejected). |
| `corrected_value` | string | no | — | The correct value. REQUIRED when state='corrected'; must be omitted for every other state (a corrected_value on a non-corrected review is rejected). |

**Output fields:** `ok`, `review`

### `list_figure_reviews`

**List Figure Reviews** · min plan `sp500` · read-only · paging: none

List every figure review recorded for one report, plus a state-count summary — the coverage view for 'which figures in this report still need a human?' A report with no reviews yet returns an empty list and an all-zero summary; that is a legitimate answer, not an error. Owner-...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Identifier of the report to list figure reviews for. |

**Output fields:** `report_id`, `reviews`, `summary`

### `delete_figure_review`

**Delete Figure Review** · min plan `sp500` · destructive · paging: none

Remove your own review mark for ONE figure in a report (Undo for save_figure_review), so the figure needs review again. Keyed on (report_id, figure_key). Idempotent: `deleted` is false when no mark existed. Owner-scoped — only your own marks are reachable; a report you do not ...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Identifier of the report the figure belongs to. |
| `figure_key` | string | yes | — | The exact figure_key the review was saved under. |

**Output fields:** `deleted`, `report_id`, `figure_key`

### `get_research_file`

**Get Auditable Research File** · min plan `sp500` · read-only · paging: none

Fetch the Auditable Research File behind one of the caller's own agent runs — the complete evidence chain an examiner asks for: the originating prompt, every tool the agent called in order, every `fact_id` it cited, every human approval, and which models were used. Assembled f...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | no | — | Report identifier — from create_report, list_my_reports or search_reports. Resolves the run behind that report and adds the human_review + sources sections. Pass this OR run_id, not both. |
| `run_id` | string | no | — | Run identifier, as returned by list_agent_runs. Pass this OR report_id, not both. |
| `format` | enum | no | one of `json`, `pdf`; default `json` | json (default) = the assembled file inline. pdf = a presigned download URL for the branded compliance PDF — the human-facing artifact; rendered fresh on every call, never cached. |

**Output fields:** `found`, `run_id`, `file`, `url`, `filename`, `content_type`, `size_bytes`, `expires_in_seconds`, `expires_at`

### `sign_off_report`

**Sign Off Report** · min plan `sp500` · destructive · paging: none

Request a Valuein compliance certificate for one of the caller's OWN reports — a signed, publicly verifiable attestation at valuein.biz/verify/{id} that every fact the report cited was knowable at the time it was used (absence of lookahead bias). It attests provenance ONLY: it...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Identifier of the report to certify, as returned by create_report / list_my_reports / save_freeform_report. Must be authored by the calling customer. |

**Output fields:** `ok`, `code`, `message`, `coverage`, `verdict`, `reason`, `certificate`

### `verify_report_figures`

**Verify Report Figures** · min plan `sp500` · read-only · paging: none

Which verifier: one fact_id → verify_fact_lineage; a list of fact_ids or derived_ids → verify_facts; a number with no id → match_derived; a number quoted from filing text or insider/13F rows → verify_filing_figures; every number in a saved report → verify_report_figures; figur...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Identifier of the report to verify, as returned by create_report / list_my_reports / save_freeform_report. Must be authored by the calling customer. |

**Output fields:** `report_id`, `version`, `figures`, `coverage`, `summary`, `lineage`, `statements`

### `save_watchlist`

**Save Watchlist** · min plan `sp500` · writes · paging: none

Upsert a named watchlist with a list of tickers. Replace semantics — the full ticker list is the source of truth for that name. Use this for both creation AND modification (delete + recreate is not required for edits). 500-ticker cap per list. Names are case-insensitive unique...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `name` | string | yes | — | Unique-per-user display name. |
| `tickers` | array | yes | — | US tickers. Normalised to uppercase, deduped. |
| `criteria` | string | no | — | Optional free-form screening criteria description. |
| `weights` | object\|null | no | — | Optional relative position weights, ticker → number (e.g. {"AAPL": 40, "MSFT": 60}). They need NOT sum to 1 or 100 — normalisation is a display decision. Any ticker not in `tickers` is dropped. Omit to leave existing weights untouched; pass null to clear them. |

**Output fields:** `watchlist`, `created`

### `list_watchlists`

**List Watchlists** · min plan `sp500` · read-only · paging: cursor

Paginated newest-first listing of the caller's watchlists (id, name, tickers, status, counts). Filter by `status` (active/archived/all). Returns metadata only — use get_watchlist for one list's full ticker set, or watchlist_diff for new filings across a list. Plan: Benchmark a...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `status` | enum | no | one of `active`, `archived`, `all`; default `active` | Filter by state; defaults to `active`. Use `all` to include archived watchlists. |
| `limit` | integer | no | default `20` | Maximum number of watchlists to return (1–100). Defaults to 20. |
| `cursor` | string | no | — | Opaque pagination cursor from a previous response; omit for the first page. |

**Output fields:** `watchlists`, `next_cursor`, `total_count`

### `get_watchlist`

**Get Watchlist** · min plan `sp500` · read-only · paging: none

Fetch a single watchlist (full ticker set + criteria) by its name, not an id (case-insensitive). NOT_FOUND if the name is unknown to this user. Plan: Benchmark and above (a free account).

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `name` | string | yes | — | Watchlist name to fetch (case-insensitive, 1–80 chars). |

**Output fields:** `watchlist`

### `delete_watchlist`

**Archive Watchlist** · min plan `sp500` · destructive · paging: none

Soft-delete a watchlist by its name (not id): status flips to `archived` (still readable via list_watchlists status=all/archived). The name is freed for reuse by a new save_watchlist. Idempotent. Plan: Benchmark and above (a free account).

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `name` | string | yes | — | Watchlist name to soft-delete (case-insensitive, 1–80 chars); frees the name for reuse. |

**Output fields:** `watchlist_id`, `status`

### `set_agent_memory`

**Set Agent Memory** · min plan `sp500` · writes · paging: none

Store or update ONE durable memory entry (key → value) for this user so context survives across sessions — preferences, prior conclusions, working context. Replace semantics per key (reusing a key overwrites it). Do NOT store a number you would later cite as a fact: financial ...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `key` | string | yes | — | Memory key (1–128 chars). Reusing an existing key overwrites its value. |
| `value` | string | yes | — | The note to remember (≤8000 chars). Never store a figure you would cite as a fact — those come from data tools. |

**Output fields:** `memory`, `created`, `prior_value`

### `get_agent_memory`

**Get Agent Memory** · min plan `sp500` · read-only · paging: none

Recall this user's durable memory. Omit `key` (or pass null) to read EVERYTHING you have remembered, newest-first — do this at the START of a task to re-ground yourself. Pass a specific `key` to fetch one entry. An absent key returns an empty list, never an error (absence is a...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `key` | string\|null | no | — | A specific key to fetch, or omit/null to recall all memory (newest-first). |

**Output fields:** `memories`

### `delete_agent_memory`

**Delete Agent Memory** · min plan `sp500` · destructive · paging: none

Forget ONE durable memory entry by key — use it when a note you stored is now wrong, superseded, or was only ever scratch. Every entry is re-read into your context at the start of every future run, so leaving a stale one behind means re-grounding yourself in something false; d...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `key` | string | yes | — | The memory key to forget. Discover keys with get_agent_memory (no key = list all). |

**Output fields:** `key`, `deleted`

### `watchlist_diff`

**Watchlist Diff** · min plan `sp500` · read-only · paging: none

Return new SEC filings across a set of companies since a given date. Name the companies with `name` (one watchlist you have already saved), `names` (several saved watchlists scanned together, companies de-duplicated; a name that does not exist is listed in `watchlists_not_foun...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `name` | string | no | — | Name of a watchlist the caller has already saved. Pass exactly one of `name`, `names`, `tickers`. |
| `names` | array | no | — | Names of saved watchlists to scan together; their companies are de-duplicated. A name that is not found is skipped and listed in `watchlists_not_found`. Pass exactly one of `name`, `names`, `tickers`. |
| `tickers` | array | no | — | Tickers or CIKs to scan, passed directly. Use this for an ad-hoc question — do NOT create a watchlist in order to ask one, since that writes a durable record into the user's account. Pass exactly one of `name`, `names`, `tickers`. |
| `since` | string | yes | — | Cutoff date (YYYY-MM-DD); the diff returns SEC filings whose filing_date is on or after this date. |
| `form_types` | array | no | — | Filing forms to include. Defaults to 10-K + 10-Q + 8-K. |

**Output fields:** `watchlist_name`, `watchlists_not_found`, `since`, `tickers_scanned`, `tickers_requested`, `truncated`, `tickers_failed`, `filings`

### `create_signal`

**Create Signal** · min plan `sp500` · writes · paging: none

Signals alert a person when a data condition holds; for a trigger → action automation use the *_rule tools. Persist a signal and register it with the firing pipeline. Four condition shapes: * `filing_event` — fire when a ticker files a chosen form type (8-K, 10-K, etc.). * `ra...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `name` | string | yes | — | Human-readable label. |
| `condition` | object | yes | — | Condition evaluated each cron tick — a discriminated union of `filing_event` (a watched ticker files a new form), `ratio_threshold` (a financial ratio crosses a comparator/threshold), `watchlist_change` (any ticker in a named watchlist files), or `fundamental_change` (Pro+ — a standard_concept reports a new period or gets restated). |
| `channel` | object | no | — | ONE delivery channel for a match — `email` (filing conditions: the morning digest; other conditions: one transactional email per signal per UTC day, the rest go to the inbox), `webhook` (HMAC-SHA256-signed POST to your URL), `slack` (POST to a hooks.slack.com incoming-webhook URL), `dashboard` (in-app inbox, readable via list_signal_inbox), or `agent_run` (runs a standing agent identified by its id, delivering the finished artifact to your inbox). Use `channels` instead to deliver to several at once; one of the two is required. |
| `channels` | array | no | — | SEVERAL delivery channels for a match, in order (up to 4, each a distinct type+target) — e.g. `[{type:'dashboard'},{type:'email',target:'you@fund.com'}]` to get the inbox item AND the email. The first entry is what `channel` reports. Takes precedence over `channel` when both are given. |
| `replaces_signal_id` | string | no | — | Optional. The id of a signal this call REPLACES with a NEW one. Prefer `update_signal`, which edits in place and keeps the fire history; use this only when you deliberately want a fresh record. A verified live record you own is discounted from the tier cap so the swap is cap-neutral; an unknown, deleted, or foreign id is ignored and the cap applies normally. |

**Output fields:** `signal`, `cron_indexed`

### `update_signal`

**Update Signal** · min plan `sp500` · writes · paging: none

Edit an existing signal IN PLACE — rename it, change what it watches, or change where it delivers — keeping its id, its fire history (`trigger_count`, `last_triggered_at`) and every inbox item and delivery already tied to it. Pass only the fields to change; omitted fields keep...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `alert_id` | string | yes | — | The signal's `id` from `list_signals` / `create_signal`. |
| `name` | string | no | — | New human-readable label. |
| `condition` | object | no | — | New condition — the same discriminated union `create_signal` takes. Replaces the stored condition entirely. |
| `channels` | array | no | — | New delivery list (up to 4, each a distinct type+target). Replaces the stored list entirely; the first entry becomes `channel`. |

**Output fields:** `signal`, `cron_indexed`, `undo`

### `list_signals`

**List Signals** · min plan `sp500` · read-only · paging: cursor

Signals alert a person when a data condition holds; for a trigger → action automation use the *_rule tools. Paginated newest-first listing of the caller's signals (id, condition, channel, status, trigger_count, evaluator health). Filter by `status` (active/paused/deleted/all)....

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `status` | enum | no | one of `active`, `paused`, `deleted`, `all`; default `active` | Filter by lifecycle state; defaults to `active`. Use `all` to include paused and soft-deleted signals. |
| `limit` | integer | no | default `20` | Maximum number of signals to return (1–100). Defaults to 20. |
| `cursor` | string | no | — | Opaque pagination cursor from a previous response; omit for the first page. |

**Output fields:** `signals`, `next_cursor`, `total_count`

### `delete_signal`

**Delete Signal** · min plan `sp500` · destructive · paging: none

Signals alert a person when a data condition holds; for a trigger → action automation use the *_rule tools. Soft-delete a signal by its id (from create_signal/list_signals): status flips to `deleted` and it is removed from the cron evaluator index so it stops firing. To change...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `signal_id` | string | yes | — | Identifier of the signal to soft-delete, as returned by create_signal or list_signals. |

**Output fields:** `signal_id`, `status`

### `test_signal`

**Test Signal (synthetic fire)** · min plan `sp500` · writes · paging: none

Signals alert a person when a data condition holds; for a trigger → action automation use the *_rule tools. Fire a synthetic notification through EVERY channel the signal is configured with. Use this immediately after `create_signal` to verify the channels (email address valid...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `signal_id` | string | yes | — | Identifier of the signal to fire a synthetic test notification through, as returned by create_signal or list_signals. |

**Output fields:** `signal_id`, `outcome`, `channel_type`, `status_code`, `error_message`, `channel_results`

### `list_signal_inbox`

**List Signal Inbox** · min plan `sp500` · read-only · paging: cursor

Newest-first listing of the caller's in-app inbox. Items are signal FIRES with a `dashboard` channel — written by the cron evaluator (or `test_signal`) — plus platform notifications written by the edge-gateway (agent run completions, morning briefs, skipped runs); use list_sig...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `unread_only` | boolean | no | default `false` | When true, return only items where read_at IS NULL. |
| `include_dismissed` | boolean | no | default `false` | When true, also return items the caller previously dismissed. |
| `limit` | integer | no | default `20` | Maximum number of inbox items to return (1–100). Defaults to 20. |
| `cursor` | integer | no | — | Pagination cursor — the `fired_at` of the last item on the previous page. |

**Output fields:** `items`, `next_cursor`, `unread_count`

### `mark_inbox_read`

**Mark Inbox Item Read** · min plan `sp500` · writes · paging: none

Set `read_at` on a single inbox item by its id (from list_signal_inbox or the signals feed resource) — not a signal id. Idempotent — re-marking does NOT reset the first-read timestamp; there is no unmark. Returns the new unread_count so the agent/UI can update its badge withou...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `inbox_id` | string | yes | — | Identifier of the inbox item to mark read, as returned by list_signal_inbox or the signals feed resource. |

**Output fields:** `inbox_id`, `marked_read`, `unread_count`, `undo`

### `dismiss_inbox_item`

**Dismiss Inbox Item** · min plan `sp500` · destructive · paging: none

Soft-delete a single inbox item by its id (from list_signal_inbox) — not a signal id; sets `dismissed_at`. The row stays queryable via `list_signal_inbox(include_dismissed=true)` for audit. Undoable: `restore_deleted` with kind `inbox_item` and this inbox_id un-dismisses it. I...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `inbox_id` | string | yes | — | Identifier of the inbox item to dismiss (soft-delete), as returned by list_signal_inbox. |

**Output fields:** `inbox_id`, `dismissed`, `unread_count`

### `stage_action`

**Stage Action** · min plan `sp500` · writes · paging: none

Propose an MCP tool call for human approval BEFORE running it. Call this — instead of calling the tool directly — whenever an autonomous or unattended caller (a scheduled standing agent, an unattended agent-runner run, or any MCP client operating without a human watching) is a...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `tool_name` | string | yes | — | The MCP tool this action would call once approved (e.g. 'save_thesis', 'create_signal', 'publish_report'). |
| `tool_args` | object | no | default `{}` | The exact arguments to replay through that tool if/when a human approves. |
| `origin` | string | yes | — | Free-form label identifying who/what is proposing this action — e.g. 'agent-runner:managed', 'claude-connector', 'cursor', or any caller-supplied identifier. Lets a human distinguish which session/agent proposed a given write. |

**Output fields:** `result`, `risk_tier`, `staged_action_id`, `staged_action`, `undo`

### `list_pending_approvals`

**List Pending Approvals** · min plan `sp500` · read-only · paging: cursor

List the caller's own staged actions still awaiting a human decision (status='proposed'), newest-first. Use this to check what an autonomous run has queued up before you approve or reject it with `approve_staged_action` / `reject_staged_action`. Plan: Benchmark and above (a fr...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `limit` | integer | no | default `25` | Page size (max 100). |
| `cursor` | string | no | — | Pagination cursor from a previous page's next_cursor. |

**Output fields:** `staged_actions`, `next_cursor`, `total_count`

### `approve_staged_action`

**Approve Staged Action** · min plan `sp500` · destructive · paging: none

Approve a staged action by id and RUN the underlying tool call it proposed, using the caller's own current credentials — never the original proposer's. Idempotent and race-safe: an action already decided (approved by a concurrent call, rejected, executed, or failed) is NEVER r...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `staged_action_id` | string | yes | — | Id of the staged action to approve, from stage_action or list_pending_approvals. |

**Output fields:** `staged_action`, `executed_now`, `tool_result`

### `reject_staged_action`

**Reject Staged Action** · min plan `sp500` · writes · paging: none

Reject a staged action by id. Terminal — the underlying tool is NEVER called, and a rejected (or otherwise already-decided) action can never be flipped back by a later approve/reject call; `transitioned` tells you whether THIS call is what moved it to 'rejected' or whether it ...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `staged_action_id` | string | yes | — | Id of the staged action to reject. |
| `reason` | string | no | — | Optional free-text reason recorded on the staged action. |

**Output fields:** `staged_action`, `transitioned`

### `schedule_task`

**Schedule Task** · min plan `sp500` · writes · paging: none

Defer a follow-up task ("re-check AAPL margin compression in 30 days") for up to ${MAX_WAKE_HORIZON_DAYS} days. This is an AGENT-facing primitive — call it mid-conversation/mid-run when you decide something is worth re-checking later; it is NOT a human-authorable "new task" fo...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `task` | string | yes | — | Human-readable description of the deferred work. |
| `wake_in_days` | number | yes | — | How many days from now this task becomes due (0 &lt; n &lt;= 90). |
| `context` | object | no | — | Saved thesis/claim/report ids and any other state needed to reconstitute a fresh prompt at wake time. Set `managed: true` + `team_id: "<standing_agent id>"` to also kick off a live managed re-run of that team at wake time (see description). |

**Output fields:** `task_id`, `wake_at`, `status`

### `list_scheduled_tasks`

**List Scheduled Tasks** · min plan `sp500` · read-only · paging: cursor

Paginated newest-first listing of the caller's own scheduled (deferred) tasks — transparency into what an agent has queued for the future. Filter by `status` (pending/completed/cancelled/cancelled_owner_inactive/all). Plan: Benchmark and above (a free account).

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `status` | enum | no | one of `pending`, `completed`, `cancelled`, `cancelled_owner_inactive`, `all`; default `pending` | Filter by lifecycle state; defaults to `pending`. |
| `limit` | integer | no | default `20` | Tasks per page, 1 to 100; defaults to 20. |
| `cursor` | integer | no | — | Pagination cursor from a previous response's next_cursor. |

**Output fields:** `tasks`, `next_cursor`

### `cancel_scheduled_task`

**Cancel Scheduled Task** · min plan `sp500` · destructive · paging: none

Cancel a pending scheduled task by id (from schedule_task or list_scheduled_tasks). Only a `pending` task can be cancelled — one that already woke (completed) cannot be un-woken. Idempotent: cancelling an already-cancelled task is a no-op. Undoable: `restore_deleted` with kind...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `task_id` | string | yes | — | Identifier of the scheduled task to cancel. |

**Output fields:** `task_id`, `cancelled`

### `create_rule`

**Create Rule** · min plan `sp500` · writes · paging: none

Persist a trigger -> action automation rule (an alert to a person is create_signal). Live trigger types x five action types, with an optional single-comparison condition_expr evaluated against the trigger payload. Read the returned rule's trigger_wiring_status, and test_rule t...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `name` | string | yes | — | Human-readable label. |
| `trigger` | object | yes | — | Discriminated union — which live event fires this rule. |
| `condition_expr` | string | no | — | Optional single comparison against the trigger payload, e.g. "ratio_value gt 5". Omit to fire on the trigger alone. |
| `action` | object | yes | — | Discriminated union — what happens when the rule fires. |
| `replaces_rule_id` | string | no | — | Optional. The id of a signal this call REPLACES — set it when saving an edit, which is stored as create-then-delete because neither engine has an update tool. A verified live record you own is discounted from the tier cap so an edit is cap-neutral; an unknown, deleted, or foreign id is ignored and the cap applies normally. |

**Output fields:** `rule`, `warning`

### `list_rules`

**List Rules** · min plan `sp500` · read-only · paging: cursor

Rules automate (trigger → action); to alert a person when a data condition holds use the *_signal tools. Paginated newest-first listing of the caller's own rules. Plan: Benchmark and above (a free account).

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `limit` | integer | no | default `20` | Rules per page, 1 to 100; defaults to 20. |
| `cursor` | integer | no | — | Pagination cursor from a previous response's next_cursor. |

**Output fields:** `rules`, `next_cursor`

### `delete_rule`

**Delete Rule** · min plan `sp500` · destructive · paging: none

Rules automate (trigger → action); to alert a person when a data condition holds use the *_signal tools. Delete a rule by id (from create_rule/list_rules) — hides it from the catalog and removes it from the evaluator's scan index, so it stops firing immediately. UNDOABLE: rest...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `rule_id` | string | yes | — | Identifier of the rule to delete. |

**Output fields:** `rule_id`, `status`

### `test_rule`

**Test Rule (dry run)** · min plan `sp500` · read-only · paging: none

Rules automate (trigger → action); to alert a person when a data condition holds use the *_signal tools. Dry-run a rule's condition_expr against a SYNTHETIC trigger payload — reports whether it WOULD have fired, but NEVER dispatches the action (no report generated, no team run...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `rule_id` | string | yes | — | Identifier of the rule to dry-run, from create_rule or list_rules. |
| `sample_payload_override` | object | no | — | Merged over the built-in synthetic payload for this rule's trigger_type — lets you test a specific value. |

**Output fields:** `rule_id`, `would_fire`, `reason`, `synthetic_payload`, `action_type`, `note`

### `get_morning_brief`

**Get Morning Brief** · min plan `sp500` · read-only · paging: none

Read the caller's Morning Brief — a daily AI-generated market digest covering overnight moves across the customer's own watchlists and theses, produced by the Workspace. Omit `day` to get the most recent brief available (not necessarily today's); pass a specific `day` (YYYY-MM...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `day` | string | no | — | Specific day to fetch (YYYY-MM-DD). Omit to get the most recent brief available for this customer. |

**Output fields:** `found`, `day`, `status`, `body_markdown`, `model`, `provider`, `created_at`

### `list_agent_runs`

**List Agent Runs** · min plan `sp500` · read-only · paging: none

List the caller's own standing-agent runs, newest first — status, goal, cost, and timing for each. A run may have been kicked off by this same agent (e.g. via create_rule's run_team action, a schedule_task wake, or run_agent) OR by the customer's own Workspace UI; this tool le...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `limit` | integer | no | — | Max runs to return (1-50, default 10). |
| `status` | string | no | — | Filter to an exact status match. |
| `agent_id` | string | no | — | Filter to runs belonging to one agent (from save_agent/list_agents). |

**Output fields:** `runs`

### `get_agent_run`

**Get Agent Run** · min plan `sp500` · read-only · paging: none

Fetch full detail for one of the caller's own standing-agent runs by id (from list_agent_runs) — status, goal, tickers, cost, artifact ids, role breakdown, and any error. A run may have been triggered by this same agent or by the customer's own Workspace; this tool works eithe...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `run_id` | string | yes | — | Run identifier, from list_agent_runs. |

**Output fields:** `found`, `run`

### `save_agent`

**Save Agent** · min plan `sp500` · writes · paging: none

Create or update a standing agent — a saved {goal + tickers + schedule} that fires either a fixed step recipe (agent_type="workflow", free/deterministic) or an AI-directed team (agent_type="autonomous", charged — settles against the owner's BYO key first, falling back to the m...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `agent_id` | string | no | — | Omit to create a new agent; pass an existing agent's id (from save_agent/list_agents/get_agent) to update it. |
| `name` | string | yes | — | Human-readable label. |
| `goal` | string | yes | — | What this agent is trying to accomplish — drives an autonomous agent's AI-directed team, and documents intent for a workflow agent's fixed steps. |
| `tickers` | array | yes | — | US tickers this agent operates over. Normalised to uppercase. |
| `agent_type` | enum | yes | one of `workflow`, `autonomous` | STRUCTURAL and immutable. "workflow" = fixed step recipe, free/deterministic, requires `steps`. "autonomous" = AI-directed team, charged, may set `managed_model`. |
| `when` | enum | yes | one of `manual`, `schedule` | Trigger mode. "manual" fires only via run_agent/the UI; "schedule" requires the `schedule` object. |
| `schedule` | object | no | — | Required when when="schedule"; ignored otherwise. |
| `managed_model` | string | no | — | Managed-lane model override for agent_type="autonomous" only (e.g. when no BYO key is connected). Omit to use the account default. |
| `steps` | array | no | — | Fixed step recipe for agent_type="workflow". Required + non-empty when CREATING a workflow agent; must be omitted for agent_type="autonomous". |

**Output fields:** `agent`, `created`

### `list_agents`

**List Agents** · min plan `sp500` · read-only · paging: none

List the caller's own standing agents (id, name, goal, tickers, agent_type, trigger config, schedule, enabled state, last/next run). Optionally filter by `agent_type` ("workflow" or "autonomous"). Use get_agent for one agent's full detail, list_agent_runs for run history, or r...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `limit` | integer | no | default `20` | Max agents to return (1-50, default 20). |
| `agent_type` | enum | no | one of `workflow`, `autonomous` | Filter to one agent_type. |

**Output fields:** `agents`

### `get_agent`

**Get Agent** · min plan `sp500` · read-only · paging: none

Fetch full detail for one of the caller's own standing agents by id (from save_agent/list_agents). Returns `found: false` (not an error) for an unknown id OR an id belonging to another customer — there is no distinguishing signal, by design, matching get_agent_run's posture. P...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `agent_id` | string | yes | — | Agent identifier, from save_agent or list_agents. |

**Output fields:** `found`, `agent`

### `delete_agent`

**Delete Agent** · min plan `sp500` · destructive · paging: none

Delete one of the caller's own standing agents by id. Undoable: `restore_deleted` with kind `agent` and this agent_id brings it back as it was (enabled or paused). System agents (is_system:true on get_agent/list_agents — built-in agents the platform provisions) cannot be delet...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `agent_id` | string | yes | — | Identifier of the agent to delete. |

**Output fields:** `agent_id`, `status`

### `run_agent`

**Run Agent** · min plan `sp500` · writes · paging: none

Fire one of the caller's own standing agents now, out of band from its schedule. For agent_type="autonomous" this costs money — it settles against the owner's own BYO LLM key first, falling back to the managed wallet only if funded; agent_type="workflow" runs are free/determin...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `agent_id` | string | yes | — | Identifier of the agent to run now. |

**Output fields:** `run_id`, `recipe_id`

### `create_report`

**Create Research Report** · min plan `sp500` · writes · paging: none

Synchronously generate a research report and persist it under the caller's authorship. One subtype, `reverse_dcf`: • `reverse_dcf` — solves the stage-1 free-cash-flow growth rate a user-supplied price implies, with a 5×5 sensitivity grid across WACC × terminal-growth assumptio...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_type` | enum | yes | one of `reverse_dcf` | Subtype. Only `reverse_dcf` is created now (requires ticker + params); thesis reports were retired in 3.14.0 and stored ones still read. |
| `ticker` | string | no | — | US-listed ticker — required for report_type=reverse_dcf. Case-insensitive. |
| `params` | object | no | — | Reverse-DCF parameters — required for report_type=reverse_dcf. |
| `title` | string | no | — | Optional human-supplied title; auto-generated when omitted. |
| `idempotency_key` | string | no | — | Optional key for at-most-once semantics. Same key from the same user always yields the same report id. |

**Output fields:** `report`, `sections`, `citations`, `structured`, `markdown`

### `get_report`

**Get Research Report** · min plan `sp500` · read-only · paging: none

Fetch the current HEAD of a report by id. `format=markdown` returns the rendered body, `format=json` returns the full structured payload (sections + citations + report-type-specific data), `format=preview` returns abstract-only. Authors see any of their own reports; non-author...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Id from `create_report` or `list_my_reports`. |
| `format` | enum | no | one of `markdown`, `json`, `preview`; default `markdown` | Response shape. Defaults to markdown. |

**Output fields:** `report`, `format`, `markdown`, `sections`, `citations`, `structured`

### `check_report_figures_current`

**Check Report Figures Are Current** · min plan `sp500` · read-only · paging: none

Which verifier: one fact_id → verify_fact_lineage; a list of fact_ids or derived_ids → verify_facts; a number with no id → match_derived; a number quoted from filing text or insider/13F rows → verify_filing_figures; every number in a saved report → verify_report_figures; figur...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Id from `create_report` or `list_my_reports`. |
| `include_cause` | boolean | no | default `false` | Also read WHY each figure was revised from the restating filing (adds one filing read per revised figure). Default false. |

**Output fields:** `report_id`, `basis`, `checked`, `degraded`, `revised`

### `list_my_reports`

**List My Research Reports** · min plan `sp500` · read-only · paging: cursor

Cursor-paginated newest-first listing of the caller's own reports (owner-scoped). Filters compose with AND; `status` defaults to 'ready' so pass status='draft' or 'all' to see drafts. Use `cursor` from the previous response's `next_cursor` to fetch the next page (limit max 100...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `status` | enum | no | one of `draft`, `ready`, `listed`, `delisted`, `all`; default `ready` | Filter by status. Default 'ready' (excludes drafts + delisted). |
| `report_type` | enum | no | one of `reverse_dcf` | Filter by report type. |
| `ticker` | string | no | — | Filter to a single ticker (case-insensitive). |
| `limit` | integer | no | default `20` | Page size. |
| `cursor` | string | no | — | Cursor from previous `next_cursor`. |

**Output fields:** `reports`, `next_cursor`

### `delete_report`

**Delete (Soft) Research Report** · min plan `sp500` · destructive · paging: none

Soft-delete a report owned by the caller: status flips to `delisted`, visibility to `private` — not a hard delete, the row and R2 artifact are preserved (90-day audit window). Idempotent (deleting an already-delisted report succeeds). Sample tier rejected.

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Id from `create_report` or `list_my_reports`. |

**Output fields:** `report_id`, `status`

### `publish_report`

**Publish Report (free)** · min plan `sp500` · writes · paging: none

Publish a report for FREE at `listed` or `unlisted` visibility to build your public author profile. `listed` makes it discoverable via `search_reports` (keyword catalog search); `unlisted` keeps it out of the catalog but accessible by direct id (shareable link). Author can set...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Id of one of your reports, from `create_report`, `save_freeform_report` or `list_my_reports`. |
| `visibility` | enum | no | one of `unlisted`, `listed`; default `listed` | `listed`: found by `search_reports`. `unlisted`: readable only by its link. Default `listed`. |
| `price_cents` | integer | no | — | Currently must be omitted or 0 — all listings are free. A non-zero value is rejected until paid listings ship. |
| `tier_required` | enum | no | one of `sample`, `sp500`, `pro`, `full` | Minimum subscriber tier to read the full body. Defaults to the author's plan. |

**Output fields:** `report`

### `unpublish_report`

**Unpublish Report (back to private)** · min plan `sp500` · destructive · paging: none

Revert a published report (listed or unlisted) back to `private` visibility, removing it from the public catalog. Author-only. Idempotent. Plan: Benchmark and above.

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Id of your published report, from `list_my_reports`. |

**Output fields:** `report`

### `search_reports`

**Search Published Reports** · min plan `sample` · read-only · paging: cursor

Search the catalog of published research reports. All listings are free to read. Filters: free-text (matches title + abstract), ticker, report_type. Sort: `newest` (default) or `oldest`. Tier-gated: callers only see reports their plan tier can read.

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `query` | string | no | — | Free-text query over title + abstract (case-insensitive). |
| `ticker` | string | no | — | Filter to a single subject ticker. |
| `report_type` | enum | no | one of `reverse_dcf` | Filter by report type. |
| `price_max_cents` | integer | no | — | Reserved for future paid listings; currently ignored (all reports are free). |
| `sort` | enum | no | one of `newest`, `oldest`; default `newest` | Order by publish time. Default `newest`. |
| `limit` | integer | no | default `20` | Reports per page (1–100). Default 20. |
| `cursor` | string | no | — | `next_cursor` from the previous page; omit for the first page. |

**Output fields:** `reports`, `next_cursor`

### `compute_dcf`

**Compute Forward DCF** · min plan `sp500` · read-only · paging: none

Forward discounted-cash-flow valuation (two-stage Gordon-growth model) under YOUR assumptions: you give stage-1 growth, WACC, terminal growth and horizon; it returns the per-share intrinsic value (`value_per_share_cents`, cents of `result.reporting_currency`, never converted) ...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol of the company to value, e.g. AAPL, MSFT, BRK.B. |
| `stage1_growth_rate` | number | yes | — | Stage-1 FCF growth rate (e.g. 0.12 = 12%/yr). |
| `wacc` | number | no | default `0.09` | Discount rate. Default 0.09. |
| `terminal_growth_rate` | number | no | default `0.025` | Long-run growth. Default 0.025. |
| `stage1_years` | integer | no | default `5` | Number of explicit high-growth projection years before the terminal stage (3–15). Defaults to 5. |
| `fcf_base_override` | number | no | — | Override the auto-pulled FCF base (USD). Leave unset to use R2-derived. |
| `shares_override` | number | no | — | Override shares outstanding. Leave unset to use R2-derived. |
| `as_of_date` | string | no | — | Point-in-time cutoff (YYYY-MM-DD) for the auto-pulled inputs. Fundamentals are filtered by SEC accepted_at (strict PIT). Omit to use the latest knowable inputs. |
| `share_price` | object | no | — | Optional share price YOU supply (never from memory) for the company valued, same fields as a `compute_price_multiples` row (cik optional, ticker not used). Adds `result.upside_pct`: the DCF value per share against your price, with the price and its date in the figure's `derived_id`. Call it your price, user-supplied, with its date. |
| `fcf_source` | enum | no | one of `trend`, `three_statement`; default `trend` | "trend" (default): compound fcf_base by stage1_growth_rate every year (unchanged original behavior). "three_statement": derive the FCF stream from a full linked 3-statement projection instead — see the tool description for details. |
| `three_statement_assumptions` | object | no | — | Only used when fcf_source is "three_statement". Overrides for the underlying projection; unset fields use project_three_statement's defaults. |

**Output fields:** `ticker`, `result`

### `forensic_audit`

**Forensic Audit (Beneish + Sloan + Solvency)** · min plan `sp500` · read-only · paging: none

Deterministic forensic-accounting scores for a single ticker: partial Beneish M-Score, Sloan accruals, and a solvency snapshot. Returns a red-flag narrative ranked by severity, with citations to source filings. Used by the `forensic_earnings_brief` SOP. Note: full Beneish need...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol of the company to audit, e.g. AAPL, MSFT, BRK.B. |

**Output fields:** `ticker`, `period_end`, `prior_period_end`, `source_filing`, `sec_url`, `result`, `metrics_display`

### `get_pit_valuation_ratios`

**Point-in-Time TTM Financials** · min plan `pro` · read-only · paging: none

Point-in-time trailing-twelve-month (TTM) financials for a company on a historical date, safe for backtesting: every figure comes from SEC filings accepted on or before `as_of_date`, so no later information leaks in. TTM sums the four most recent standalone quarters (or uses t...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol, e.g. AAPL, MSFT — or a CIK (SEC identifier), e.g. '0000320193'. |
| `as_of_date` | string | yes | — | The historical date for the snapshot (YYYY-MM-DD). Only filings accepted on or before this date are read. Use a recent date for the latest figures, or any date back to 1993 (subject to your plan's history window) for the figures as they were observable then. |

**Output fields:** `ticker`, `cik`, `company_name`, `as_of_date`, `reporting_currency`, `ttm_period_end`, `financials_accepted_at`, `ttm_revenue`, `ttm_gross_profit`, `ttm_operating_income`, `ttm_ebitda`, `ttm_net_income`, `ttm_ocf`, `ttm_capex`, `ttm_fcf`, `shares_diluted`, `cash`, `total_debt`, `net_debt`, `book_equity`, `gross_margin_pct`, `operating_margin_pct`, `net_margin_pct`, `note`

### `run_backtest`

**Run Bounded Factor Backtest** · min plan `pro` · read-only · paging: none

A SMALL, BOUNDED, in-Worker sanity-check backtest — NOT a full-universe backtesting engine. Answers a quick question like 'does this factor actually work on these 5 names over the last year' inline, mid-conversation, without leaving MCP. Composes two existing tools (`get_pit_u...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `tickers` | array | yes | — | 1-10 stock ticker symbols, e.g. ["AAPL","MSFT"]. |
| `rebalance_dates` | array | yes | — | 1-12 historical dates (YYYY-MM-DD) to snapshot TTM margins on. Order does not matter — the tool sorts them chronologically. Forward return is computed from each date to the NEXT one in the sorted list. |
| `factors` | array | no | — | Which of get_pit_valuation_ratios's own output fields to include as factor_values. One or more of: gross_margin_pct, operating_margin_pct, net_margin_pct. Omit to include all of them. |

**Output fields:** `method`, `grid_cells`, `cells_computed`, `pit_safe`, `capped`, `source_tools_used`, `caveats`, `tickers`, `rebalance_dates`, `factors`, `dropped`, `cells`, `summary`, `streams`, `next_step`, `note`

### `project_three_statement`

**Project Linked Three-Statement Model** · min plan `sp500` · read-only · paging: none

Linked forward Income Statement / Balance Sheet / Cash Flow projection, seeded from the company's latest historical annual period. The balance sheet ties out (assets == liabilities + equity) EVERY projected year by algebraic construction — each year's `tie_out_ok` field is a l...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol, e.g. AAPL, MSFT, BRK.B. |
| `years` | integer | no | default `5` | Projection horizon in years (1-15). Defaults to 5. |
| `revenue_growth_rate` | number | yes | — | Flat annual revenue growth rate applied every year (e.g. 0.08 = 8%/yr). |
| `interest_rate_on_debt` | number | no | default `0.06` | Annual interest rate on beginning-of-period debt. Assumption — default 0.06. |
| `tax_rate` | number | no | default `0.21` | Effective tax rate on positive pretax income. Default 0.21 (US statutory). |
| `gross_margin_pct_override` | number | no | — | Override the seed period's gross margin (held flat across all years). Leave unset to use the historical ratio. |
| `operating_margin_pct_override` | number | no | — | Override the seed period's operating margin. Leave unset to use the historical ratio. |
| `capex_pct_of_revenue_override` | number | no | — | Override the seed period's capex-as-%-of-revenue ratio. Leave unset to use the historical ratio. |
| `cash_sweep_pct` | number | no | default `0` | Fraction (0-1) of each year's free cash flow swept to debt paydown. Default 0 (going-concern; use ~1.0 for an LBO-style paydown). |
| `dividend_payout_pct` | number | no | default `0` | Fraction (0-1) of net income paid out as dividends each year. Default 0. |
| `new_debt_draw_year1` | number | no | default `0` | New debt drawn at year 1 only (absolute USD) — e.g. acquisition financing. Default 0. |
| `new_equity_draw_year1` | number | no | default `0` | New equity contributed at year 1 only (absolute USD) — hits cash + equity symmetrically. Default 0. |
| `as_of_date` | string | no | — | Point-in-time cutoff (YYYY-MM-DD) for the seed period. Omit to use the latest knowable annual period. |

**Output fields:** `ticker`, `seed_period_end`, `result`

### `compute_lbo`

**Compute LBO Returns (IRR + MOIC)** · min plan `sp500` · read-only · paging: none

Leveraged buyout returns analysis: caller provides entry/exit multiples, leverage, and a hold period; the tool builds a Day-1 pro-forma opening balance sheet from the deal's own sources & uses (cash-free, debt-free convention — entry_debt = leverage_multiple x EBITDA, sponsor_...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol of the LBO target, e.g. AAPL. |
| `entry_multiple` | number | yes | — | EV/EBITDA multiple paid at entry (e.g. 10 = 10x). |
| `exit_multiple` | number | no | — | EV/EBITDA multiple assumed at exit. Defaults to entry_multiple (no multiple expansion/contraction) when omitted. |
| `leverage_multiple` | number | yes | — | Debt/EBITDA raised at entry (e.g. 5 = 5x leverage). |
| `hold_period_years` | integer | no | default `5` | Hold period in years (1-10). Defaults to 5. |
| `revenue_growth_rate` | number | yes | — | Flat annual revenue growth rate applied every year of the hold (e.g. 0.05 = 5%/yr). |
| `interest_rate_on_debt` | number | no | default `0.08` | Annual interest rate on beginning-of-period LBO debt. Default 0.08 (leveraged debt typically prices above IG). |
| `tax_rate` | number | no | default `0.21` | Effective tax rate on positive pretax income. Default 0.21. |
| `cash_sweep_pct` | number | no | default `1` | Fraction (0-1) of each year's FCF swept to debt paydown. Default 1.0 (standard LBO — 100% sweep). |
| `dividend_payout_pct` | number | no | default `0` | Fraction (0-1) of net income distributed to the sponsor each year (dividend recap style). Default 0 — most LBOs return capital only at exit. |
| `minimum_cash` | number | no | default `0` | Minimum operating cash left on the pro-forma opening balance sheet. Default 0. |
| `entry_ebitda_override` | number | no | — | Override the EBITDA figure used for both entry and exit multiples. Without this, EBITDA is proxied by operating income. |
| `as_of_date` | string | no | — | Point-in-time cutoff (YYYY-MM-DD) for the seed period. Omit to use the latest knowable annual period. |

**Output fields:** `ticker`, `seed_period_end`, `result`

### `compute_accretion_dilution`

**Compute M&A Accretion/Dilution** · min plan `sp500` · read-only · paging: none

M&A accretion/dilution: the standard sell-side/banker quick-screen for whether a proposed acquisition adds to (accretive) or subtracts from (dilutive) the acquirer's EPS in the first pro-forma year. Pulls net income + shares outstanding for both companies. A share price is nev...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `acquirer_ticker` | string | yes | — | Acquirer's stock ticker symbol, e.g. MSFT. |
| `target_ticker` | string | yes | — | Target's stock ticker symbol, e.g. ATVI. |
| `offer_price_per_share` | number | yes | — | Offer price per target share (USD). |
| `cash_pct` | number | yes | — | Fraction (0-1) of deal value paid in cash; the remainder (1 - cash_pct) is paid in acquirer stock. |
| `synergies_pretax` | number | no | default `0` | Pretax annual run-rate cost/revenue synergies (USD). Default 0. |
| `cash_financing_source` | enum | no | one of `new_debt`, `balance_sheet_cash`; default `new_debt` | Where the cash consideration is funded from. "new_debt" (default) applies an after-tax interest drag; "balance_sheet_cash" applies none. |
| `new_debt_interest_rate` | number | no | default `0.06` | Annual interest rate on new acquisition debt (only used when cash_financing_source is "new_debt"). Default 0.06. |
| `tax_rate` | number | no | default `0.21` | Effective tax rate applied to synergies and the interest drag. Default 0.21. |
| `acquirer_share_price_override` | number | no | — | The acquirer's share price in USD, supplied by you. Required when cash_pct &lt; 1. |
| `target_share_price_override` | number | no | — | The target's share price in USD, supplied by you (used only for the disclosed premium). Leave unset to skip the premium. |
| `as_of_date` | string | no | — | Point-in-time cutoff (YYYY-MM-DD) for both companies' fundamentals. Omit to use the latest knowable data. |

**Output fields:** `acquirer_ticker`, `target_ticker`, `result`

### `compute_price_multiples`

**Compute Multiples on Your Price** · min plan `sp500` · read-only · paging: none

Market cap, P/E, P/B, P/S, EV/EBITDA, EV/revenue and dividend yield on a share price YOU supply (1 to 25 per call), joined to point-in-time SEC EDGAR filings. A share price is never a Valuein figure: pass one only when the user gave it to you, or a tool the user connected retu...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `prices` | array | yes | — | 1 to 25 prices, one per company and date. |
| `as_of_date` | string | no | — | Optional cap, YYYY-MM-DD: only filings accepted before the end of this day are used, even when a price is later. |

**Output fields:** `results`, `price_inputs_echo`, `warnings`

### `update_report`

**Update Report Sections** · min plan `sp500` · writes · paging: none

Replace one or more sections of an existing report owned by the caller. Useful for authoring workflows where the agent's first draft (`create_report`) is refined by additional analysis before publishing. Pass `citations` for figures in the edited prose — they are MERGED into t...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Identifier of the report to update, as returned by create_report or list_my_reports. |
| `title` | string | no | — | Optional new title. |
| `abstract` | string | no | — | Optional new abstract. |
| `sections` | array | yes | — | Sections to replace. Sections not listed are preserved — to DELETE one, name it in `remove_section_ids`. Section ids must match the existing payload. |
| `remove_section_ids` | array | no | — | Section ids to DELETE outright. Without this, a merge-only update cannot express a deletion: an editor that drops a section simply omits it, the omitted section is preserved, and the caller sees a bumped version with the deleted content still there — a save that reports success and changed nothing. Ids must exist, and the last remaining section cannot be removed (a report with no sections is unreadable); remove the report instead with delete_report. |
| `citations` | array | no | — | Lineage for figures in the edited sections. MERGED into the report's existing citations (first claim wins), never replacing them — so an editor autosave that sends none preserves every citation the report already had. |
| `expected_version` | integer | no | — | Optimistic concurrency check. If supplied and the current HEAD version is different, the call returns a `version_conflict` error WITHOUT writing. Pass the version you loaded so a concurrent agent edit produces a 'conflict — review' UX instead of silently overwriting (eng review A3A). |
| `drafts_only` | boolean | no | — | Pass true when editing a private draft: the call is refused with `not_a_draft` (nothing written) unless the report is private, never published and not signed off. Lets a client run the edit without asking, because a draft edit is undoable and reaches no reader. |

**Output fields:** `report`, `version`, `previous_version`, `archived`, `undo`

### `list_report_versions`

**List Report Versions** · min plan `sample` · read-only · paging: cursor

Author-only newest-first listing of a report's archived version history. Each entry summarises what changed (sections edited, etc.) so the workspace UI can render a clickable history without loading every artifact. Pair with `get_report_version` to fetch a specific version's c...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Identifier of the report whose version history to list, as returned by create_report or list_my_reports. |
| `limit` | integer | no | default `20` | Maximum number of archived versions to return (1–100). Defaults to 20. |
| `cursor` | integer | no | — | Cursor from the previous response's `next_cursor` — the smallest version number on the previous page. Omit for the first page. |

**Output fields:** `versions`, `next_cursor`

### `get_report_version`

**Get Report Version** · min plan `sample` · read-only · paging: none

Author-only fetch of a specific archived version of one of your reports, by positive-integer `version`. Returns metadata + the full payload (sections, citations, structured, markdown) — enough to render a diff against the current HEAD in the workspace editor. Use after `list_r...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Identifier of the report whose archived version to fetch, as returned by create_report or list_my_reports. |
| `version` | integer | yes | — | Version number to fetch (from list_report_versions). |

**Output fields:** `version`, `payload`

### `render_report`

**Render Report Download URL** · min plan `sample` · writes · paging: none

Return a 15-minute presigned download URL for a report in the requested binary format. `format=md` presigns the cached markdown — instant, no compute. `format=docx` and `format=pdf` return the SAME branded research-note design in the two media: a masthead-first page 1 (Valuein...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `report_id` | string | yes | — | Id from create_report or list_my_reports. |
| `format` | enum | yes | one of `md`, `docx`, `pdf` | md = raw markdown (the same body the editor renders). docx = branded Word document; pdf = the same branded research-note design as a shareable PDF (Geist faces embedded, clickable citation links). |
| `force_regenerate` | boolean | no | default `false` | If true, ignore the cached DOCX/PDF and re-render. No effect on md (markdown is canonical). |
| `author_name` | string | no | — | Display name of the report's author, shown as a named byline ('By {name}') on the masthead — the way a real research note credits an analyst. Omit to show 'Valuein Research'. Only affects the binary formats; ignored on a cache hit (the cached file keeps whatever byline was baked in on first render — pass `force_regenerate: true` to refresh it). |

**Output fields:** `url`, `format`, `filename`, `content_type`, `size_bytes`, `expires_in_seconds`, `expires_at`, `from_cache`

### `save_freeform_report`

**Save Markdown as a Draft Report** · min plan `sp500` · writes · paging: none

Save free-form markdown (e.g. a chat synthesis) as a DRAFT report you can refine in the editor and export to Word/PDF. Unlike `create_report` (which computes a structured reverse_dcf or thesis report), this accepts raw markdown and splits it into sections. PASS `citations` wit...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `title` | string | yes | — | Report title. |
| `markdown` | string | yes | — | Free-form markdown body (≤100k chars). Headings become sections. |
| `ticker` | string | no | — | Optional ticker for context/catalog. Case-insensitive. |
| `abstract` | string | no | — | Optional 1–2 sentence summary. |
| `idempotency_key` | string | no | — | Optional key for at-most-once semantics. Same key from the same user always yields the same report id. |
| `citations` | array | no | — | Lineage you already hold for the figures in `markdown` — pass it rather than dropping it. Each claim should quote the figure exactly as the prose writes it, so figure review can link the two. Every `fact_ids` entry must be a whole id copied exactly as a tool returned it (a 64-hex fact_id or a `drv1:` derived id): a truncated or annotated id rejects the call and nothing is saved. Ids are shape-checked only, NOT resolved here; sign-off re-resolves every fact_id before certifying. |

**Output fields:** `report`, `report_id`, `status`, `version`

### `get_uploaded_document`

**Read an Uploaded Document** · min plan `sp500` · read-only · paging: none

Read the extracted text of a file uploaded via POST /v1/uploads (a plain REST route, not this JSON-RPC endpoint). Use this to pull a user-attached document's content into context by its upload_id. Uploads are ephemeral (24h) and owner-scoped — an expired or missing id both rea...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `upload_id` | string | yes | — | The upload_id returned by POST /v1/uploads. |

**Output fields:** `upload`

### `list_uploaded_documents`

**List Uploaded Documents** · min plan `sp500` · read-only · paging: none

List the caller's currently-active uploaded documents (filename, size, char count — no full text; call get_uploaded_document for that). Uploads expire 24h after upload. Plan: Benchmark and above (a free account); a caller without sign-in is refused.

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `limit` | integer | no | — | Max uploads to return (default 20, the same cap as MAX_ACTIVE_UPLOADS_PER_CUSTOMER). |

**Output fields:** `uploads`

### `delete_uploaded_document`

**Delete an Uploaded Document** · min plan `sp500` · destructive · paging: none

Delete an uploaded document before its 24h TTL. UNDOABLE: restore_deleted with kind 'uploaded_document' brings it back while it is still within its 24h TTL and its file exists. Deleting a missing/already-expired/foreign id returns deleted:false rather than an error. Plan: Benc...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `upload_id` | string | yes | — | The upload_id returned by POST /v1/uploads. |

**Output fields:** `deleted`

### `generate_dcf_xlsx`

**Generate DCF Workbook (xlsx)** · min plan `pro` · writes · paging: none

Render a forward DCF result into a professional Excel workbook (Summary + 5×5 Sensitivity heatmap + Inputs sheet). Native conditional formatting — no chart images needed. Returns a 15-minute presigned R2 download URL. SERVER-TRUST: the DCF is re-derived in-Worker from the supp...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol of the company the DCF workbook is built for, e.g. AAPL. |
| `company_name` | string | no | — | Optional — surfaces on the cover row. Falls back to ticker only. |
| `dcf_result` | object | yes | — | Structured DCF result — typically the `result` field returned by `compute_dcf`. |

**Output fields:** `url`, `r2_key`, `filename`, `content_type`, `size_bytes`, `expires_in_seconds`, `expires_at`, `verification`

### `generate_research_brief_docx`

**Generate Research Brief (docx)** · min plan `pro` · writes · paging: none

Render a structured research brief into a professionally-styled Word document — a branded masthead-first page (Valuein letterhead: brand rule, wordmark, 'EQUITY RESEARCH' kicker + date, then the ticker eyebrow, the title as hero, and the named analyst's byline), the body (abst...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol the brief covers, e.g. AAPL, MSFT, BRK.B. |
| `company_name` | string | no | — | Optional display name shown in the masthead subtitle; falls back to the ticker if omitted. |
| `title` | string | yes | — | Document title rendered in the page-1 masthead (1–200 chars). |
| `abstract` | string | no | — | Optional executive-summary paragraph (≤2000 chars) shown after the masthead. |
| `snapshot` | array | no | default `[]` | Optional at-a-glance metric rows (≤20) rendered as the snapshot table. |
| `sections` | array | yes | — | Ordered body sections of the brief (1–20); each has a heading and body text. |
| `citations` | array | no | default `[]` | Optional source citations (≤60) rendered as a table with clickable SEC EDGAR hyperlinks. |
| `author_name` | string | no | — | Display name of the analyst producing this brief, shown as a named byline ('By {name}') on the masthead — the way a real research note credits an analyst. Omit to show just the date. |

**Output fields:** `url`, `r2_key`, `filename`, `content_type`, `size_bytes`, `expires_in_seconds`, `expires_at`, `verification`

### `generate_comps_xlsx`

**Generate Peer Comparables Workbook (xlsx)** · min plan `pro` · writes · paging: none

Render a peer comparables table into an Excel workbook. The Comps sheet is formatted as a named Excel Table (`ValueinPeerComps`) so the user gets one-click Insert Chart on any column — the cleanest workaround for not embedding chart objects server-side. Subject-row highlight m...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `subject_ticker` | string | yes | — | Stock ticker symbol of the subject company the comps sheet is built around, e.g. AAPL. |
| `subject_company_name` | string | no | — | Optional display name for the subject company; falls back to the ticker if omitted. |
| `peers` | array | yes | — | Peer companies to tabulate against the subject (1–50 rows); each row carries the peer's ticker, name, and comparable ratio values. |
| `notes` | string | no | — | Optional free-text note (≤500 chars) rendered on the Summary sheet. |

**Output fields:** `url`, `r2_key`, `filename`, `content_type`, `size_bytes`, `expires_in_seconds`, `expires_at`, `verification`

### `generate_lbo_xlsx`

**Generate LBO Workbook (xlsx)** · min plan `pro` · writes · paging: none

Render an LBO result into a professional Excel workbook (Summary + year-by-year Projection table + Inputs sheet). Returns a 15-minute presigned R2 download URL. SERVER-TRUST: the deal is re-derived in-Worker from the supplied `lbo_result.inputs_echo` (the math is pure + determ...

| Input | Type | Required | Values | Description |
|---|---|---|---|---|
| `ticker` | string | yes | — | Stock ticker symbol of the LBO target, e.g. AAPL. |
| `company_name` | string | no | — | Optional — surfaces on the cover row. Falls back to ticker only. |
| `lbo_result` | object | yes | — | Structured LBO result — typically the `result` field returned by `compute_lbo`. |

**Output fields:** `url`, `r2_key`, `filename`, `content_type`, `size_bytes`, `expires_in_seconds`, `expires_at`, `verification`
<!-- /GEN:mcp-tool-reference -->

---

## Public publishing — free reputation building (reports, theses, claims)

The publishing tools cost nothing on any plan; they need a signed-in token (each tool's minimum plan is in the reference above). They let an agent (or a creator working through one) turn saved work into a public, citable research track record linked from the author's `@handle` profile. This is **publishing to build a public profile and reputation, not selling** — there is no charge to the author or the reader, and the agent never mints a number (every published figure keeps its `fact_id` lineage). Reports become a shareable `/r/[slug]` page discoverable via keyword catalog search (`search_reports`; there is no semantic search). Theses and claims get the same `publish` / `unpublish` visibility toggle (`publish_thesis` / `unpublish_thesis`, `publish_claim` / `unpublish_claim`), so a full public track record (report + supporting theses + scored claims) is built with one consistent pattern.

---

## Prompts (analyst SOPs)

These are pre-written multi-step instructions an MCP-aware agent can invoke as a single high-level command. Each chains the right tools in the right order. `equity_research_brief` (single-ticker analysis), `screen_and_shortlist` (idea generation) and `deferred_research_loop` (research that follows up on itself) are the end-to-end flagships; the rest are narrower chains, daily flows, and state-lifecycle playbooks. `list_sops` and `get_sop` return the same catalog to an agent that cannot read prompts.

Invoke a prompt the same way as a tool — most clients surface them in the same picker.

<!-- GEN:mcp-prompts -->
_Generated from the MCP server manifest (v3.28.1); 30 prompts._

| Prompt | Title | Min plan | Summary |
|---|---|---|---|
| `margin_and_moat_teardown` | Margin & Moat Teardown | `sample` | Systematic 10-year analysis of a company's operational efficiency and competitive moat. Chains fundamentals → valuation metrics → peer comparables to produce a structured teardown covering revenue quality, margin trends, ROIC level and persistence (a moat is a trajectory, not ... |
| `peer_benchmarking_memo` | Peer Benchmarking Memo | `sample` | Produces a structured benchmarking memo comparing a company to its closest peers. Chains search_companies → get_peer_comparables → get_valuation_metrics → get_financial_ratios to output an investment committee-ready comparison table of margins, ROIC, leverage and capital effic... |
| `survivorship_free_backtest` | Survivorship-Free Backtest | `sample` | Sets up a bias-free quantitative backtest: survivorship-free universe (effective-date membership), a quick bounded in-Worker validation grid, then Parquet URLs for bulk out-of-core compute. Chains get_pit_universe → run_backtest (≤120-cell PIT sanity grid) → get_compute_ready_... |
| `pit_factor_constructor` | Point-in-Time Factor Constructor | `sample` | Guides construction of a quantitative factor (Quality, Value, Momentum) across a sector universe using ratio.parquet data. Chains get_pit_universe → get_financial_ratios → get_compute_ready_stream to produce normalized factor scores. |
| `quality_and_risk_audit` | Quality & Risk Audit | `sample` | Evaluates capital structure safety and dividend sustainability from the filed figures. Chains fundamentals → capital_allocation → valuation_metrics → financial_ratios (leverage/liquidity) to produce a structured risk scorecard. |
| `capital_allocation_review` | Capital Allocation Review | `sample` | Evaluates management's capital allocation decisions over a multi-year period. Chains capital_allocation_profile → valuation_metrics → financial_ratios to produce a management quality scorecard: does management create value with retained earnings? |
| `ratio_deep_dive` | Ratio Deep Dive | `sample` | Comprehensive ratio profile for a single company spanning all 7 ratio categories (profitability, liquidity, leverage, efficiency, per_share, owner_earnings, valuation). Includes TTM and 5-year annual history with trend analysis. |
| `sector_ratio_screen` | Sector Ratio Screen | `sample` | Cross-sectional ratio ranking across a sector to surface the highest-quality or best-value companies. Chains get_pit_universe → get_compute_ready_stream to screen the full sector using pipeline-computed ratios. |
| `equity_research_brief` | Equity Research Brief | `sample` | Single-ticker end-to-end research brief in markdown — fundamentals, valuation, ratios, capital allocation, peer comparison, recent catalysts, and SEC lineage. Three depth modes: 'quick' (3 tools, snapshot), 'full' (8 tools, default — institutional brief), 'forensic' (adds rest... |
| `screen_and_shortlist` | Screen and Shortlist | `sample` | PM idea-generation workflow: build a PIT universe, factor-rank it, QC the leaders with a period-over-period change check, and hand off the top-ranked names to equity_research_brief for full write-ups. Survivorship-free via get_pit_universe; renders as a markdown shortlist arti... |
| `smart_money_brief` | Smart Money Brief | `full` | Single-ticker smart-money brief: composite flow score, top holders (classified), 13F deltas, activist blockholders, and insider sentiment overlay. Three depth modes: 'quick' (3 composites only), 'standard' (default, + 13F + blockholders), 'deep' (+ insider transactions + compa... |
| `activist_surveillance` | Activist Surveillance | `full` | Event-driven surveillance for activist target / takeover candidates. Surfaces filers flipping 13G → 13D within the lookback window (the strongest activist signal in the dataset), then cross-references defensive insider activity and 8-K item 1.01 filings to check whether a corp... |
| `forensic_earnings_brief` | Forensic Earnings-Quality Brief | `sample` | Hedge-fund-grade earnings-quality red-flag brief for a single ticker. Chains forensic_audit (deterministic Beneish M-Score + solvency-distress proxy + Sloan accruals) → restatement diff → Risk-Factor delta to surface earnings-quality flags and anomalies worth review. These are... |
| `morning_briefing` | Morning Briefing | `sample` | Daily overnight digest: material SEC filings across the caller's watchlist since the last close. Ranks by likely impact (M-score change candidates, 8-K item types, amendment flags). |
| `earnings_pulse` | Earnings Pulse | `sample` | Pre-earnings pulse for a single ticker. Pulls last 8 quarters of fundamentals + the existing get_earnings_signals trend + management-credibility cross-check (promise-vs-delivery on key segments). Output: 1-page pre-read for an analyst attending the call. |
| `restatement_radar` | Restatement Radar | `sample` | Daily/weekly sweep for 10-K/A and 10-Q/A amendments across a watchlist (or the caller's full ticker set). Surfaces amendments that materially changed reported revenue, cash flow, or earnings — the highest-signal restatement events for a forensic analyst. |
| `earnings_war_room` | Earnings-Day War Room | `sample` | The moment a company files (10-Q / 10-K / 8-K), grade the expectations you hold on that ticker (agent memory, your reports) against the fresh numbers and draft a cited 'what changed' memo — before the earnings call. Turns a filing into a cited record: what resolved, what surpr... |
| `screen_to_thesis` | Screen → Thesis Pipeline | `sample` | End-to-end idea-generation pipeline: screen → forensic audit → shortlist of the top N candidates. Wraps existing screen_universe + forensic_audit; ends in a saved watchlist of the survivors. |
| `smart_money_pulse` | Smart-Money Pulse | `full` | PM digest: 13F + insider activity across the caller's watchlist. Surfaces top fund accumulators, recent insider clusters, and 13D/13G activist filings worth investigating. Institutional plan only. |
| `activist_radar` | Activist Radar | `full` | Detect new SC 13D / 13G filings across the watchlist and pull the activist's historical playbook stats. Surfaces 13G→13D conversions (the strongest 'going active' signal). Institutional plan only. |
| `sector_overview_flow` | Sector Overview | `sample` | Comprehensive sector / industry landscape brief — market dynamics, top 5-10 players, competitive structure, valuation context, and investment debate. Distinct from `sector_ratio_screen` (which is just a screen) and `screen_and_shortlist` (single-theme idea generation) — this i... |
| `dcf_build_flow` | DCF Build (Disciplined) | `sample` | Disciplined forward-DCF construction for a single ticker — pulls reported history, justifies each assumption (growth, a WACC the user gives or you state, terminal growth) against history + peers, calls `compute_dcf`, and renders the full per-share value + 5×5 sensitivity grid.... |
| `watchlist_and_signal_setup` | Watchlist & Signal Setup | `sample` | Operational monitoring setup for a PM/analyst: create a watchlist, attach signal rules, dry-run them, and confirm the inbox is wired. Chains save_watchlist → create_signal → test_signal → list_signals → list_signal_inbox. Tier: sp500+ (watchlists + signals are persisted user s... |
| `review_and_signoff` | Review & Sign-off | `sp500` | Figure-level review coverage loop for one report. Chains verify_report_figures (the machine verdict on every figure in the prose — start here) → get_report (read citations) → list_figure_reviews (see what's already reviewed) → verify_facts (check every unreviewed figure agains... |
| `multi_factor_signal` | Multi-Factor Signal | `sample` | Builds a point-in-time-disciplined composite signal across the cross-section. Chains get_pit_universe → get_compute_ready_stream → screen_universe → get_financial_ratios for per-name verification → run_backtest for a bounded forward-return sanity grid on the decile extremes. E... |
| `fundamental_deep_dive` | Fundamental Deep Dive (10-K Teardown) | `sample` | The annual-report deep-read ritual as one run: a 10-year financial spread (revenue, margins, FCF, ROIC, share count, leverage) with every figure filing-cited, a quality-of-earnings read (OCF vs net income), the full restatement history with before→after diffs, capital-allocati... |
| `dividend_sustainability_review` | Dividend Sustainability Review | `sample` | Dividend safety from cash-flow articulation, not yield-chasing: 10 years of payout history, FCF coverage trajectory, deployment flags (debt-funded distributions), leverage headroom, and the revision record on the cash-flow concepts — ending in a SAFE / STRETCHED / AT-RISK read... |
| `initiation_of_coverage` | Initiation of Coverage | `sp500` | The full idea → IC-ready initiation pipeline: 10-year history, moat evidence, peer positioning, valuation with labelled assumptions (DCF + reverse-DCF expectations read), ranked risks with pre-committed kill criteria, and a variant view — ending in a persisted, citation-carryi... |
| `value_screen_pipeline` | Value Screen Pipeline | `sp500` | The value investor's screen-to-thesis pipeline: survivorship-free universe → cash-flow-yield screen → quality + earnings-quality gates → owner-earnings read (maintenance-capex honesty) → margin-of-safety via reverse-DCF expectations read → a saved, monitored watchlist. Chains ... |
| `standing_research_desk` | Standing Research Desk | `sp500` | Stand up the whole monitoring desk in one run: watchlist → filing/restatement signal tripwires (dry-run-verified) → a filing-event rule posting to the inbox → a scheduled standing agent for the daily sweep → confirm the plumbing (list_signals/list_rules/list_agents, a smoke ru... |
<!-- /GEN:mcp-prompts -->

---

## Resources

Read-only reference resources for grounding the agent. Resources are cheaper to read than tool calls — agents that just need schema or a ticker list should pull from these.

<!-- GEN:mcp-resources -->
_Generated from the MCP server manifest (v3.28.1); 3 resources._

| Resource | Title | Min plan | Summary |
|---|---|---|---|
| `schema` | Parquet table schema | `sample` | Column-level contract for every R2 Parquet table the server reads (types, primary keys, foreign-key references). Read schema://{table} to learn the exact columns and types before writing a query — e.g. schema://fact (raw observations), schema://ratio (derived ratios), schema:/... |
| `sp500-universe` | S&P 500 universe | `sample` | Current S&P 500 members as a single JSON roster — ticker, CIK, company name, sector, industry, and primary exchange for every active constituent. Reads as the latest membership snapshot from the references table; for survivorship-free historical universes use the get_pit_unive... |
| `pricing-current` | Pricing & plan tiers | `sample` | Full tier ladder (Sample → Benchmark (free) → Pro → Institutional → Enterprise) with prices, (a subscription buys data; a separate balance pays for AI compute, with no run limits), Stripe SKUs, breadth/depth coverage, filing types, and feature flags. Plus the MPP price book (c... |
<!-- /GEN:mcp-resources -->

The URIs are `schema://{table}`, `reference://sp500` and `pricing://current`. A signed-in caller also gets `valuein://signals/feed`, its own signal inbox, so an agent can read and triage fired signals.

---

## Tier matrix at a glance

Most tools are callable from the Sample tier up, and **what changes is the data the tool can see**. Some tools have a higher floor — saving research state, compute, document generation, smart money: each tool's floor is its **min plan** in the reference above (`min_plan` in the manifest).

| Tier | Data the agent sees |
|---|---|
| Sample (anonymous) | Curated sample slice · recent years |
| Benchmark (free, registered) | Every S&P 500 member since 1996, former members included · 1993 – present |
| Pro | Full active + delisted US universe · rolling point-in-time window · no smart-money dataset |
| Institutional | Full universe · 1993 – present (unlimited) · **smart-money dataset unlocked** (Forms 3/4/5/144 + 13F/13D/13G) · 4h priority + filing-event webhooks · single-seat internal use, no redistribution (Redistribution Licence only) |
| Enterprise | Organisations and teams, by Enterprise Agreement · multi-seat · display in your own products and client deliverables, with attribution, where the Order Form says so · negotiated scope · sub-minute real-time 8-K push · dedicated infrastructure · zero-retention option · redistribution, resale and white-label: separate Redistribution Licence |

Live universe sizes and history windows: `curl -s https://data.valuein.biz/v1/plans | jq '.plans[] | {displayName, priceUsd, universeSize, earliestYear}'`.

A call that needs data outside the caller's plan returns an `ENTITLEMENT_DENIED` error (see the agent contract above) whose `extensions` carry `required_plan` and `upgrade_url` — the agent should suggest the user upgrade at [valuein.biz/pricing](https://valuein.biz/pricing).

---

## Agent payments (MPP)

Valuein supports **machine-to-machine payments** via the [Machine Payments Protocol](https://mpp.dev) (MPP), on the full endpoint `https://mcp.valuein.biz/mcp` only. An agent that hits a rate limit or tier gate can pay in real time with a Stripe card Shared Payment Token — no human in the loop, no account, no minimum.

**Payment is card-only today.** Fetch `GET https://api.valuein.biz/api/mpp/well-known` to confirm which networks are active before initiating a payment.

There is one paid route, `POST https://api.valuein.biz/api/mpp/call` (unpaid → `402` challenge → pay → retry the same URL with `Authorization: Payment <credential>` → `200` with the tool result inline), described in [`AGENTS.md`](../AGENTS.md#agent-payments-mpp-company-passes-and-per-run-fees) and [`docs/AGENT_ECONOMY_RAIL.md`](AGENT_ECONOMY_RAIL.md). Funds are held, the delivery is verified, and only then captured; otherwise the hold is released and nothing is charged.

### Company passes and run fees

The payment buys a **company pass**: one company at one level (`pro` $1.00, `full` $5.00) for 24 hours, returned in the `X-Valuein-Mpp-Pass` header. Send it as `x-valuein-mpp-pass` on later `/mcp` calls to read that company's data at that level until the pass expires. Compute runs (`compute_dcf`, document generation, …) and verification runs cost $1.00 each plus a pass for each company they read that you do not already cover; universe runs (`screen_universe`, `get_pit_universe`, `run_backtest`) cost $5.00. Any Valuein token, the free Benchmark one included, pays 50% less (send it in `X-Valuein-Authorization`), and each account verifies its first 100 figures free, once. Workspace tools and bulk streaming are not sold per call.

### Prices

`GET https://api.valuein.biz/api/mpp/tools` lists every payable tool and the price book; `GET https://api.valuein.biz/api/mpp/quote?tool=…&tickers=…&level=pro|full` is a free price lookup, and the `402` states the exact amount before anything is authorized. For steady-state agent usage a [Pro or Institutional subscription](https://valuein.biz/pricing) is significantly cheaper — a single Stripe token unlocks every channel at the subscribed tier.


---

## Versioning & registry

The published manifest in [`server.json`](../server.json) at the root of this repo is the source of truth for the MCP registry. Any push to `main` that touches `server.json` triggers `.github/workflows/publish-mcp.yml`, which authenticates with GitHub OIDC and publishes to `registry.modelcontextprotocol.io`. The `version` field must always match the deployed Worker version.

Server identifier: `biz.valuein/mcp` · Repository: `https://github.com/valuein/valuein`.

## Trademarks

Index names are trademarks of their owners; Valuein is not affiliated with or endorsed by any index provider.
