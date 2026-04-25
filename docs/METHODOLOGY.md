# Data Methodology & Standardization

Transparency is foundational to the Valuein product. This document describes how raw SEC EDGAR XBRL data is processed into standardized, point-in-time accurate financial time series.

The data product covers **12,000+** active and delisted US entities, **12M+** filings, and **108M+** standardized facts since **1994**. The full schema is in [`schema.json`](schema.json) (machine-readable) and [`data_catalog.md`](data_catalog.md) (canonical concept names).

---

## 1. Sourcing & lineage

1. **Ingestion.** Raw XBRL instances are pulled directly from the SEC EDGAR RSS feed within ~60 seconds of acceptance.
2. **Validation.** Each filing's `accession_id` is verified against the EDGAR submission registry.
3. **Parsing.** Facts are extracted using the US GAAP Taxonomy (2009 – 2026) and mapped to canonical `standard_concept` values before being written to the `fact` table.

100% of the data originates from the U.S. Securities and Exchange Commission (SEC) EDGAR system. We add no alternative-data sources, no surveys, and no estimated overrides.

---

## 2. Point-in-Time (PIT) architecture

To prevent look-ahead bias in quantitative backtesting, Valuein strictly preserves the timeline of information availability using three timestamps:

| Field | Table | Meaning |
|---|---|---|
| `report_date` / `period_end` | `filing` / `fact` | The fiscal period end as reported by the company (e.g. 2024-12-31) |
| `filing_date` | `filing` | The date the SEC accepted the filing (e.g. 2025-02-14) |
| `accepted_at` | `fact`, `valuation`, `filing_text` | Millisecond-precision timestamp of SEC acceptance — equal to EDGAR's `acceptedDateTime` for the parent filing |
| `ingested_at` | most tables | When the row entered our database (operational metric — not for PIT filters) |

**The PIT rule:** for any backtest, filter by `filing_date <= trade_date`. For intraday research, use `accepted_at <= trade_timestamp` instead.

> Filtering by `report_date` would include data the market did not yet have, and is the single most common cause of look-ahead bias in backtests. See [QUERY_COOKBOOK.md §9](QUERY_COOKBOOK.md#9-anti-pattern-filtering-by-report_date).

---

## 3. Restatement handling

Valuein uses an **append-only** strategy. Historical rows are never modified or deleted.

When a company restates prior-period results (10-K/A, 10-Q/A):

1. The original row remains untouched.
2. A new row is inserted with the restated value and the later `filing_date` and `accepted_at`.

This preserves the as-reported state of the dataset on any historical date and enables accurate PIT backtesting across restatement events. To get the **latest known value** for any concept, take the row with the maximum `accepted_at` per `(entity_id, period_end, concept)`. To get the **first-disclosed value**, take the minimum.

The `data_quality` field on each fact distinguishes the original disclosure from later revisions; `is_estimated` flags concepts that the pipeline derived rather than read directly from XBRL.

---

## 4. Standardization logic

11,966 unique raw XBRL tags are mapped to ~150 canonical `standard_concept` values using a waterfall approach. Each concept resolves in priority order — if a direct tag is unavailable, calculated alternatives are attempted.

Both the raw and canonical names are on every fact row:

- `fact.concept` — the raw US-GAAP tag (e.g. `us-gaap:Revenues`, `us-gaap:NetIncomeLoss`)
- `fact.standard_concept` — the Valuein canonical name (e.g. `'TotalRevenue'`, `'NetIncome'`)

No mapping join is required. Use `standard_concept` for cross-company analytics; inspect `concept` only when debugging unusual filers.

### Example: `OperatingIncome`

Resolution order:

1. **Direct tag:** `us-gaap:OperatingIncomeLoss`
2. **Calculation:** `GrossProfit − OperatingExpenses`
3. **Calculation:** `Revenues − CostOfRevenue − OperatingExpenses`

If all paths fail, the value is recorded as `NULL` rather than zero-filled or interpolated, to maintain statistical integrity.

The full canonical concept list is in [`data_catalog.md`](data_catalog.md). Definitions are also available at runtime via the `taxonomy_guide` table.

---

## 5. Fiscal calendar alignment

Companies report on varying fiscal calendars. Valuein preserves both the company-reported period and a calendar-normalized equivalent on the `fact` table:

| Field | Description |
|---|---|
| `fiscal_year` | The fiscal year as reported (`'2024'`) |
| `fiscal_period` | The fiscal period as reported (`'FY'`, `'Q1'`, `'Q2'`, `'Q3'`) |
| `frame` | The calendar-normalized frame string (`'CY2023Q4'`) |

A retailer whose Q4 ends January 31, 2024 shows `fiscal_year='2024' fiscal_period='Q4'` and `frame='CY2023Q4'`. This enables consistent cross-company comparisons without manual alignment.

---

## 6. Quarterly vs YTD cash flows

10-Q filings report cash flows on a year-to-date basis: Q2 reports H1, Q3 reports the first nine months, Q4 (10-K) reports the full year. To get the isolated quarter the pipeline pre-computes `derived_quarterly_value` on every `fact` row that needs it. The recommended pattern in DuckDB:

```sql
COALESCE(derived_quarterly_value, numeric_value) AS quarterly
```

Use this whenever you need quarterly cash flow, change in working capital, or any other YTD-reported concept.

---

## 7. Valuation models

Valuein computes three intrinsic value estimates per entity per fiscal period. All inputs and outputs are stored on the `valuation` table for auditability.

### Two-stage DCF

Both DCF variants share the same discounting framework — a high-growth stage of 5 years at the observed historical CAGR followed by perpetuity at a fixed terminal growth rate. They differ only in the earnings input.

| `model_type` | Earnings input | Philosophy |
|---|---|---|
| `dcf` | Owner earnings per diluted share | Conservative — Buffett / Greenwald |
| `dcf_fcf` | Free cash flow per diluted share | Wall Street consensus |

**Owner earnings** (Valuein proprietary) adjusts net income for the cash economics of the business:

```
owner_earnings = net_income + D&A + SBC + Δ working_capital − maintenance_capex
```

**Free cash flow** uses the conventional formula:

```
fcf = operating_cash_flow − |capital_expenditures|
```

For most companies `dcf_fcf > dcf`. A large gap signals heavy reinvestment needs (growth capex embedded in CapEx that the FCF model does not strip out).

### Dividend Discount Model (DDM)

Applied only to dividend-paying entities. Uses the Gordon Growth Model with the 5-year average dividend per diluted share and the 5-year dividend CAGR. Intrinsic value reflects only the present value of future dividends.

### Data quality flag

The `data_quality` field on each valuation row indicates input reliability:

| Value | Meaning |
|---|---|
| `reported` | Growth rate derived from observed historical data |
| `estimated` | Growth rate unavailable; defaulted to 0% (conservative floor) |
| `provisional` | Inputs are preliminary and may be revised |

---

## 8. Coverage

| Dimension | Detail |
|---|---|
| **Entities** | 12,000+ active and delisted US-listed companies (the Pro and Enterprise tiers see all of them) |
| **History** | 1994 – present |
| **Filings** | 12M+ (10-K, 10-Q, 8-K, 20-F, and amendments) |
| **Facts** | 108M+ standardized financial data points |
| **XBRL coverage** | 95% of all SEC EDGAR financial facts mapped to a canonical `standard_concept`; the remainder is exposed under `'Other'` for transparency |
| **Update frequency** | Daily snapshot for Free / Pro tiers; 4-hour priority freshness for Enterprise; real-time 8-K alerts on Custom |
| **Latency** | Filings appear in our pipeline within ~60 seconds of SEC acceptance; the snapshot publication SLA is in [`SLA.md`](SLA.md) |

---

## 9. Survivorship-bias-free design

Every snapshot retains all historical filings, including those from delisted, bankrupt, merged, or acquired entities. No entity is ever removed from the archive. Common universe filters:

```sql
-- Active companies only (NOT survivorship-bias-free)
WHERE r.is_active = TRUE

-- Survivorship-bias-free universe (recommended for backtests)
WHERE r.is_active = TRUE OR r.valid_to IS NOT NULL

-- Historical S&P 500 reconstruction at a date
WHERE im.start_date <= :as_of AND (im.end_date IS NULL OR im.end_date > :as_of)
```

See [QUERY_COOKBOOK.md §10–12](QUERY_COOKBOOK.md#universe-construction) for full universe-construction recipes.

---

## 10. What we don't do

- **No Material Non-Public Information (MNPI).** Data is published only after the SEC has publicly disseminated the underlying filing.
- **No alternative data.** No web scraping, satellite imagery, credit-card transactions, or social-media signals.
- **No imputation or smoothing.** When a concept cannot be resolved from the filing or from valid calculations, the value is `NULL`. We never fabricate.
- **No PII.** The dataset contains only corporate financial metrics from public filings.
- **No CUSIPs.** We use FIGI and LEI for instrument and entity identifiers — CUSIPs carry licensing obligations.
