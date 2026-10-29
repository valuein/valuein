# Compliance & Due Diligence Questionnaire (DDQ)

Valuein provides institutional-grade SEC fundamental data. This document addresses common due diligence questions from compliance officers, risk managers, and quantitative researchers.

---

## 1. Data Sourcing & Provenance

- **Source:** All financial statements, ownership and insider data come from SEC filings, through the U.S. Securities and Exchange Commission's EDGAR system: fundamentals, ratios, filings, insider transactions, institutional-ownership disclosures and investment-adviser (Form ADV) filings. Market prices (`stock_price`, `stock_price_daily`) are not SEC data: prices come from a commercial end-of-day market-data provider, and no price bar exists before 1994 (each security's first bar is in 1994 or later). Fundamentals coverage runs from 1993 to present across 28,000+ active and delisted SEC-reporting companies (current figure: [valuein.biz/pricing](https://valuein.biz/pricing)). The fundamentals dataset is served on every tier, within each plan's company universe and history window; the smart-money dataset (insider transactions and institutional-ownership disclosures) is included in the Institutional tier, and MCP pay-per-call can also buy it one company per call.
- **Index membership:** `index_membership` is Valuein's own reconstruction from public sources. Valuein holds no licence with any index provider, does not receive or license constituent data from one, and does not fetch data from any index provider's website. Membership dates are a reconstruction and can differ from an index provider's official records. Every row carries `source` (the mechanism that produced it, never a publisher) and `confidence` (`high` / `medium` / `low`).
  - *S&P 500, from 1996:* reconstructed from public information: publicly available constituent lists, public reports of index changes, and SEC filings (`source` = `public_constituent_list` / `historical_seed` / `succession_config`). The table holds fewer members than the index had in its early years (383 at the end of 1996, 451 at the end of 2000 and 482 at the end of 2006, against roughly 500; measured 2026-10-29), and `high`-confidence rows make up less than half of the members at every year end before 2007.
  - *Russell 1000 / 2000 / 3000, from 2000-09-30:* reconstructed from the portfolio holdings that funds tracking each index disclose, in their SEC filings and in the holdings files their sponsors publish (`source = 'fund_holdings'`). A tracking fund only approximates its index, so these rows are always `medium` confidence.
  - The MCP's `get_pit_universe` reports `pit_safe = true` only when every matched row is `high` confidence; treat any other answer as approximate.
- **Transformations:** Data undergoes normalization to resolve XBRL tag discrepancies across filers and fiscal years. Raw XBRL tags (the `taxonomy_guide` reference lists 11,966) are mapped to 350+ canonical `standard_concept` values (live count: the `standard_concept` table) by deterministic, ordered tag rules; `fact.priority` marks the tag elected for each fact in each filing. A fact whose tag is not mapped is kept under `'Other'`, never dropped. Reported values are not smoothed or imputed. The exceptions are flagged on the row with `is_estimated = TRUE`: a monetary scale inferred for a pre-2001 EX-27 schedule that omitted it, and a filer's units slip in a share count or EPS corrected by an exact power of 1,000 against independent evidence (the filer's original string stays in `value`). `data_quality` records how each number was obtained (XBRL, EX-27, parsed from the filing's statements, or human-verified against the filing). Derived figures such as `derived_quarterly_value` sit in their own columns. Both the raw tag (`concept`) and the canonical name (`standard_concept`) are present on every row of the `fact` table for traceability.
- **Survivorship Bias:** Delisted, bankrupt, merged and acquired companies stay in the dataset with their filing history; a company is never dropped for leaving the market. Pro and Institutional carry the full SEC universe; the free tiers cover the large-cap US benchmark universe within their history window.

---

## 2. Material Non-Public Information (MNPI)

- **Policy:** Valuein data contains **no** Material Non-Public Information (MNPI).
- **Latency:** Filing data is ingested, processed, and published to the R2 snapshot only after the filing has been publicly disseminated by the SEC EDGAR system. The `accepted_at` field on the `fact`, `filing`, and `ratio` tables is EDGAR's acceptance date-time for the filing (for `ratio`, the latest acceptance time among its inputs; where EDGAR records only a date, the later, conservative bound). `filing.filing_date` is EDGAR's filing date, a calendar date that can differ from the acceptance day. Neither reflects Valuein's internal ingestion time (`ingested_at`).
- **No alternative data:** No satellite imagery, credit-card transaction data or web-traffic data is included. Apart from SEC filings, the inputs are: end-of-day prices from a commercial end-of-day market-data provider; for index membership, the public information described in Section 1 (publicly available constituent lists, public reports of index changes, and the portfolio holdings that index-tracking funds disclose); FIGI security identifiers from the OpenFIGI mapping service; and the published XBRL taxonomies (tag definitions). Valuein does not fetch data from any index provider's website.

---

## 3. Point-in-Time (PIT) Integrity

To prevent look-ahead bias, filing-derived data is append-only and stamped with the SEC's acceptance time:

- Each filing-derived row carries `accepted_at`, the moment SEC EDGAR accepted the filing that reported it. Derived rows carry the latest `accepted_at` of their inputs; price rows carry the market close.
- A restatement never overwrites the earlier value. The amending or later filing (e.g., `10-K/A`) adds its own rows under its own `accession_id`, preserving the exact "as-reported" state of any prior date; `fact.value_as_filed` and `fact.value_current` show the first and the latest value side by side, and `ratio` keeps one row per vintage.
- Clients can reconstruct the information set available to the market on any historical date by filtering `accepted_at <= as_of` (for `ratio`, then keeping the latest vintage).
- Not every field is point-in-time: `references.sector` and `references.industry` are current values (use `industry_classification` for as-of industry), `fact.restated` is computed on today's data, and `index_membership` dates carry the confidence its `confidence` column states (Section 1).

---

## 4. Security & Infrastructure

| Control | Detail |
|---|---|
| **Delivery** | Cloudflare R2 Object Storage over HTTPS |
| **Authentication** | Bearer tokens: 256-bit cryptographically random values, generated per client and rotatable at any time (the old token stops working at once). A token reads data at its plan's tier and cannot modify the published dataset |
| **IP Allowlisting** | Not available as a product feature today; an Enterprise Agreement can include it |
| **PII** | The published dataset holds no customer data. It does reproduce the names of individuals that appear in public SEC filings (insiders, beneficial owners, investment-adviser personnel). Account data is personal information: email address, display name and sign-in method (Google or LinkedIn sign-in, or a one-time code sent by email; no passwords are stored), plan and Stripe customer identifier (Stripe holds card details), usage records, and request logs with IP address and user agent. What is collected, why and for how long: [Privacy Policy](https://valuein.biz/privacy) |
| **Data residency** | Published datasets: Cloudflare R2 buckets located in Eastern North America (location hint `ENAM`, no jurisdiction restriction), served through Cloudflare's global network. Account data is processed in the United States and in the other countries where Cloudflare operates its network |

---

## 5. AI & Agentic Governance

Valuein's AI surface (the MCP server and the Workspace) is designed for institutions that want AI with controls, not autonomy. All of the following are shipped and enforced in code:

| Control | Detail |
|---|---|
| **The model never mints a number** | Financial figures originate only in typed, deterministic tools. Every figure taken from a filing carries a `fact_id` and its source SEC filing, and `verify_fact_lineage` resolves any `fact_id` back to that filing for one-click audit; a figure a tool computes carries a `derived_id` that traces to its inputs. Server instructions forbid the model from computing or estimating figures itself. |
| **Point-in-time discipline** | Every time-series tool accepts an `as_of_date` and reconstructs the information set as of that date — no look-ahead in AI-generated research, same as in backtests. |
| **Reproducible runs** | Data tools are deterministic: the same inputs against the same data snapshot return the same output. Managed agent runs use temperature 0 on every model that accepts a sampling temperature (newer models reject it and run without one), with a model allow-list and wall-clock and output-token caps. |
| **Human-on-the-loop approvals** | Managed agents are offered only tools annotated read-only, plus one private-draft tool (`save_freeform_report`, an unsigned draft visible only to its owner). Every other mutating or outward-facing action is withheld from direct use and staged in an approval ledger — the agent proposes, a human approves or rejects, and every decision is written once to an append-only audit log (a later Undo is recorded beside it, never over it). |
| **Your key or ours; no training** | Workspace customers use their own model key (Anthropic, OpenAI or OpenRouter) or Valuein's managed lane (Anthropic, under Valuein's commercial account). A connected key is sealed with AES-GCM and never stored in plaintext: by default the sealed key is kept server-side so scheduled agents can run; the customer can instead choose a cookie-only mode (a 24-hour sealed cookie, nothing kept server-side). Customer prompts, uploads, research and AI output are never used to train, fine-tune or evaluate any model. Each provider applies its own retention policy; Valuein has no zero-data-retention arrangement with any provider, and keeps Workspace chats on its servers for 30 days unless pinned (see the [Privacy Policy](https://valuein.biz/privacy)). |
| **Availability honesty** | A figure that is not reported, not mapped, or suppressed is returned with an explicit availability status — never silently substituted or estimated. A tier limitation returns a structured error, never an empty result posing as data. |

---

## 6. Service Levels

- **No SLA on self-serve plans:** Sample, Benchmark, Pro and Institutional carry no service level agreement and no uptime commitment; the Service is provided "as is" and "as available" ([Terms](https://valuein.biz/terms)). Service levels exist only where a signed Enterprise Agreement sets them. A Pro or Institutional subscription taken before October 15, 2026 under a plan that included a service level keeps it until the end of its then-current billing term.
- **Support:** response targets, not guarantees, are listed per plan on [valuein.biz/pricing](https://valuein.biz/pricing); Institutional has a 4-hour response target during business hours (09:00–18:00 ET).
- **Data freshness (targets):** Fundamentals snapshot published weekly (Saturday); market prices each weekday. Per-table timestamps: `table_last_updated` in the manifest

---

## 7. Contact

For compliance inquiries, vendor questionnaires, or enterprise agreements, contact:
**compliance@valuein.biz** (formal legal notices under the Terms: **legal@valuein.biz**)

---

_Index names are trademarks of their owners; Valuein is not affiliated with or endorsed by any index provider._
