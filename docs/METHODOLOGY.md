# Data Methodology & Standardization

Transparency is foundational to the Valuein product. This document describes how raw SEC EDGAR XBRL data is processed into standardized, point-in-time accurate financial time series.

The data product covers every active and delisted US public company that files with the SEC, from **1993** on. Counts grow with every snapshot, so they are read live rather than printed here: `client.manifest()` (snapshot and tables), `curl -s https://data.valuein.biz/v1/sample/manifest.json | jq .schema_version` and `https://data.valuein.biz/v1/plans` (universe size and history window per plan). Accuracy is measured, published, and re-derivable — see [`accuracy/`](accuracy/) for the identity catalog, the CI-gated baseline, and the one-command DuckDB reproduction. The fundamentals dataset (10-K / 10-Q / 8-K / 20-F + amendments) is exposed on every paid tier; the smart-money dataset (insider transactions on Forms 3 / 4 / 5 / 144 and institutional ownership on Forms 13F / 13D / 13G) is exposed on the Institutional tier only. The full schema is in [`schema.json`](schema.json) (machine-readable) and [`data_catalog.md`](data_catalog.md) (canonical concept names).

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
| `accepted_at` | `fact`, `filing`, `ratio` (+ smart-money and price tables) | Millisecond-precision timestamp of SEC acceptance — equal to EDGAR's `acceptedDateTime` for the parent filing |
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

11,966 unique raw XBRL tags are mapped to 292 canonical `standard_concept` values using a waterfall approach. Each concept resolves in priority order — if a direct tag is unavailable, calculated alternatives are attempted.

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

## 7. DCF valuation

Valuein publishes the reported inputs of a valuation, not an opinion of value: there is no
stored intrinsic-value table (the `valuation` table was removed in schema 3.0.0). A DCF is
computed on request, with assumptions the caller states, by the SDK's `client.dcf()` (locally,
on the tables the client reads) and by the MCP `compute_dcf` tool. Both run the same model.

### Inputs

All inputs come from the latest annual filing (10-K / 20-F) accepted on or before the as-of
date, and each one carries its `fact_id` and filing accession so it can be traced to the filing:

```
fcf_base  = OperatingCashFlow − |CAPEX|
net_debt  = TotalDebt − (CashAndEquivalents + ShortTermInvestments)
shares    = CommonSharesOutstanding   (else NetIncome / EPSDiluted)
```

When an input is missing the result says so instead of inventing it: `net_debt_basis` is
`reported`, `cash_assumed_zero` (debt reported, no cash line) or `debt_undisclosed` (net debt
taken as 0, not a reported zero), and `shares_source` names where the share count came from.
A missing operating cash flow or share count raises rather than reading as zero.

### Model

A two-stage forward DCF. Stage 1 grows `fcf_base` at the caller's `stage1_growth_rate` for
`stage1_years` years, each year discounted at `wacc`. The terminal value is the following
year's FCF divided by `wacc − terminal_growth_rate`, discounted back `stage1_years`.
`equity = enterprise value − net_debt`; `value per share = equity / shares`.

The growth rate is required: the model never guesses one. `wacc`, `terminal_growth_rate` and
`stage1_years` have defaults, and the result flags every default it used. A non-positive FCF
base is not valued (the value fields are empty and `reason` says why) rather than reported as
zero. The result also carries a 5×5 sensitivity grid over the discount rate and terminal
growth, and the SDK adds the last close and the implied upside.

Walk-through: [`examples/notebooks/10_dcf_valuation.ipynb`](../examples/notebooks/10_dcf_valuation.ipynb).

---

## 8. Coverage

| Dimension | Detail |
|---|---|
| **Entities** | Every active and delisted US + Canadian public-company entity (the `entity_type='us_public_filer'` subset — CIKs with at least one 10-K / 10-Q / 8-K / 20-F / 40-F filing). The full `entity` table is larger because per-filing parsers (SC 13D/G, Form 3/4/5, Form 144, 13F-HR) emit stub rows for issuers named in smart-money filings; those rows are labelled `entity_type='smart_money_subject'` and are excluded from the universe count. Pro and Institutional ship the identical entity table — the differentiator is history depth (Pro = a rolling window; Institutional = full 1993→present) and access to the smart-money dataset. Live universe size: `universeSize` in `https://data.valuein.biz/v1/plans`. |
| **History** | Pro: a rolling window (its current first year is `earliestYear` in `https://data.valuein.biz/v1/plans`). Institutional: 1993 → present. |
| **Filings** | 10-K, 10-Q, 8-K, 20-F, 40-F (Canadian MJDS annuals), and their amendments. 6-K (FPI interims) is not currently in the ingest scope — most 6-K filings lack XBRL. |
| **Facts** | Standardized financial data points: every fact of every filing above, under its canonical `standard_concept` ([`data_catalog.md`](data_catalog.md)) |
| **XBRL coverage** | Facts that cannot be mapped to a canonical `standard_concept` are exposed under `'Other'` rather than dropped or imputed. The current measured mapping-gap rate is published in [`accuracy/baseline.json`](accuracy/baseline.json) (`unstandardized_facts`) and re-derivable with the open DuckDB script |
| **Update frequency** | Daily snapshot for Free / Pro tiers; 4-hour priority freshness + filing-event webhooks for Institutional; sub-minute real-time 8-K signals for Enterprise (custom contract) |
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
-- (index_membership keys on cik with effective_date / removal_date)
WHERE im.effective_date <= :as_of AND (im.removal_date IS NULL OR im.removal_date > :as_of)
```

See [QUERY_COOKBOOK.md §10–12](QUERY_COOKBOOK.md#universe-construction) for full universe-construction recipes.

---

## 10. What we don't do

- **No Material Non-Public Information (MNPI).** Data is published only after the SEC has publicly disseminated the underlying filing.
- **No alternative data.** No web scraping, satellite imagery, credit-card transactions, or social-media signals.
- **No imputation or smoothing.** When a concept cannot be resolved from the filing or from valid calculations, the value is `NULL`. We never fabricate.
- **No PII.** The dataset contains only corporate financial metrics from public filings.
- **No CUSIPs.** We use FIGI and LEI for instrument and entity identifiers — CUSIPs carry licensing obligations.
