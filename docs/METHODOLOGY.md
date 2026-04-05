# Data Methodology & Standardization

Transparency is foundational to the Valuein FDE product. This document details how raw SEC XBRL data is processed into standardized, Point-in-Time accurate financial time series.

---

## 1. Data Sourcing & Lineage

1. **Ingestion:** Raw XBRL instances are pulled directly from the SEC EDGAR RSS feed within minutes of acceptance.
2. **Validation:** Each submission's `adsh` (Accession Number) is verified against the EDGAR submission registry.
3. **Parsing:** Facts are extracted using the US-GAAP Taxonomy (2020–2025) and mapped to internal concept IDs before standardization.

---

## 2. Point-in-Time (PIT) Architecture

To prevent look-ahead bias in quantitative backtesting, Valuein strictly preserves the timeline of information availability using three timestamps:

| Field | Meaning |
|---|---|
| `report_date` | The fiscal period end date as reported by the company (e.g., December 31, 2024) |
| `filing_date` | The date the filing was accepted by SEC EDGAR (e.g., February 14, 2025) |
| `ingested_at` | The UTC timestamp the row entered the Valuein database |

**PIT rule:** When backtesting, always filter by `filing_date <= trade_date`. This ensures that no data is used before the market could have observed it.

---

## 3. Restatement Handling

Valuein uses an **append-only** strategy. Historical rows are never modified or deleted.

When a company restates prior-period results:

1. The original row remains untouched in the database.
2. A new row is inserted with the restated value and the later `filing_date` (from the `10-K/A` or `10-Q/A` filing).

This preserves the "as-reported" state of the dataset on any historical date, enabling accurate PIT backtesting across restatement events.

---

## 4. Standardization Logic

Over 15,000 raw XBRL tags are mapped to approximately 150 standardized concepts using a **waterfall** approach. Each concept is resolved in priority order; if a direct tag is unavailable, calculated alternatives are attempted in sequence.

### Example: `OperatingIncomeLoss`

Resolution order:
1. **Direct tag:** `us-gaap:OperatingIncomeLoss`
2. **Calculation:** `GrossProfit − OperatingExpenses`
3. **Calculation:** `Revenues − CostOfRevenue − OperatingExpenses`

If all methods fail, the value is recorded as `NULL` rather than zero-filled or interpolated, to maintain statistical integrity and avoid introducing bias into downstream models.

All standardized concepts and their definitions are available in the `taxonomy_guide` table.

---

## 5. Fiscal Year Alignment

Companies report on varying fiscal calendars. Valuein preserves both the company-reported period and a calendar-normalized equivalent:

| Field | Description |
|---|---|
| `fiscal_period` | The period as reported by the company (e.g., `FY2024 Q1`) |
| `calendar_period` | Normalized to the standard calendar year (e.g., `CY2023 Q4`) |

**Example:** A fiscal quarter ending January 31, 2024 at a retailer (fiscal Q4) is mapped to `CY2023 Q4` in the calendar-period field. This enables consistent cross-company period comparisons without manual alignment.

---

## 6. Valuation Models

Valuein computes three intrinsic value estimates per entity per period. All results are stored in the `valuation` table with a full input snapshot for auditability.

### Two-stage DCF

Both DCF variants (`dcf`, `dcf_fcf`) use the same discounting framework: a high-growth stage of 5 years at the observed 5-year historical CAGR, followed by a perpetuity at a fixed terminal growth rate. The only difference is the earnings input:

| `model_type` | Earnings input | Philosophy |
|---|---|---|
| `dcf` | Owner earnings per diluted share | Conservative — Buffett/Greenwald |
| `dcf_fcf` | Free cash flow per diluted share | Consensus — Wall Street standard |

**Owner earnings** (proprietary) adjusts net income for the true cash economics of the business:
```
owner_earnings = net_income + D&A + SBC + Δworking_capital − maintenance_capex
```

**Free cash flow** uses the conventional formula without separating maintenance from growth capex:
```
fcf = operating_cash_flow − |capital_expenditures|
```

### Dividend Discount Model (DDM)

Applied only to dividend-paying entities. Uses the Gordon Growth Model with the 5-year average dividend per diluted share and the 5-year dividend CAGR. Intrinsic value reflects only the discounted present value of future dividends.

### Data quality flag

The `data_quality` field on each valuation row indicates input reliability:

| Value | Meaning |
|---|---|
| `reported` | Growth rate derived from observed historical data |
| `estimated` | Growth rate unavailable; defaulted to 0% (conservative floor) |
| `provisional` | Inputs are preliminary and may be revised |

---

## 7. Coverage

| Dimension | Detail |
|---|---|
| **Entities** | 20,000+ active and delisted US-listed companies |
| **History** | 1990 to present (earlier filings where EDGAR data is available) |
| **Facts** | ~105 million standardized facts |
| **Filing types** | 10-K, 10-Q, 8-K, 10-K/A, 10-Q/A, and selected proxy filings |
| **Update frequency** | Daily snapshot by 06:00 UTC |
