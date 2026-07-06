# Compliance & Due Diligence Questionnaire (DDQ)

Valuein provides institutional-grade SEC fundamental data. This document addresses common due diligence questions from compliance officers, risk managers, and quantitative researchers.

---

## 1. Data Sourcing & Provenance

- **Source:** 100% of the data originates from the U.S. Securities and Exchange Commission (SEC) EDGAR system. Coverage runs from 1993 to present across 19,000+ active and delisted US-listed entities. The fundamentals dataset is exposed on every paid tier; the smart-money dataset (insider transactions and institutional ownership disclosures) is exposed on the Institutional tier only.
- **Transformations:** Data undergoes normalization to resolve XBRL tag discrepancies across filers and fiscal years. 11,966 raw XBRL tags are mapped to 292 canonical `standard_concept` values via a deterministic waterfall (direct tag → calculated alternative → null). Raw numeric facts are mathematically unaltered; no imputation or smoothing is applied. Both the raw and canonical names are present on every row of the `fact` table for traceability.
- **Survivorship Bias:** The dataset retains all historical filings, including those from delisted, bankrupt, merged, or acquired entities. No entity is ever removed from the archive.

---

## 2. Material Non-Public Information (MNPI)

- **Policy:** Valuein data contains **no** Material Non-Public Information (MNPI).
- **Latency:** Data is ingested, processed, and published to the R2 snapshot only after the filing has been publicly disseminated by the SEC EDGAR system. The `filing_date` field reflects the SEC's acceptance date; the millisecond-resolution `accepted_at` field on the `fact`, `filing`, and `ratio` tables corresponds to EDGAR's `acceptedDateTime`. Neither reflects Valuein's internal ingestion time.
- **No alternative data:** The dataset contains solely structured financial data extracted from public SEC filings. No web scraping, satellite imagery, or credit-card transaction data is included.

---

## 3. Point-in-Time (PIT) Integrity

To completely eliminate look-ahead bias, the Valuein data architecture uses immutable append-only snapshots:

- Each data point is timestamped with the `filing_date` on which it became publicly available via SEC EDGAR.
- Historical snapshots are never overwritten. Restatements are appended as new facts linked to the amended filing (e.g., `10-K/A`), preserving the exact "as-reported" state of any prior date.
- Clients can reconstruct the information set available to the market on any historical date by filtering `filing_date <= trade_date`.

---

## 4. Security & Infrastructure

| Control | Detail |
|---|---|
| **Delivery** | Cloudflare R2 Object Storage over HTTPS |
| **Authentication** | Read-only Bearer tokens; cryptographically generated per client |
| **IP Allowlisting** | Available on the Enterprise (custom contract) tier to restrict access to corporate VPN or VPC CIDR ranges |
| **PII** | Not present. The dataset contains only corporate financial metrics from public filings. |
| **Data residency** | U.S.-based Cloudflare R2 region |

---

## 5. AI & Agentic Governance

Valuein's AI surface (the MCP server and the BYO-LLM Workspace) is designed for institutions that want AI with controls, not autonomy. All of the following are shipped and enforced in code:

| Control | Detail |
|---|---|
| **The model never mints a number** | Financial figures originate only in typed, deterministic tools. Every figure carries a `fact_id` and its source SEC filing; `verify_fact_lineage` resolves any `fact_id` back to the filing URL for one-click audit. Server instructions forbid the model from computing or estimating figures itself. |
| **Point-in-time discipline** | Every time-series tool accepts an `as_of_date` and reconstructs the information set as of that date — no look-ahead in AI-generated research, same as in backtests. |
| **Reproducible runs** | Tools are deterministic and idempotent (same inputs → same output). Managed agent runs execute at temperature 0 with a model allow-list, wall-clock and output caps, and destructive-tool stripping. |
| **Human-on-the-loop approvals** | Mutating and outward-facing agent actions are staged in an approval ledger — the agent proposes, a human approves or rejects, and every decision is recorded as an immutable audit entry. Read-only tools never require approval. |
| **BYO-LLM, zero retention** | Workspace customers bring their own LLM key. The key is sealed in a short-lived encrypted cookie, is never persisted server-side in plaintext, and customer data is never used to train any model. An Enterprise zero-retention tier is available. |
| **Availability honesty** | A figure that is not reported, not mapped, or suppressed is returned with an explicit availability status — never silently substituted or estimated. A tier limitation returns a structured error, never an empty result posing as data. |

---

## 6. Service Level Agreement

See [`SLA.md`](SLA.md) for full commitments on uptime, data freshness latency, and support response times.

- **Uptime:** 99.9% monthly availability for the Cloudflare R2 storage layer
- **Data freshness:** New snapshot published daily by 06:00 UTC
- **Critical incidents:** Response within 2 hours, 24/7

---

## 7. Contact

For compliance inquiries, vendor questionnaires, or enterprise agreements, contact:
**compliance@valuein.biz**
