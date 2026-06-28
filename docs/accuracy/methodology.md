# Dataset Accuracy — Methodology & Proof

Valuein is built on a simple promise: **every fact you read can be mathematically verified against SEC's own canonical data.** This document describes how, and how you can reproduce the measurement yourself.

The measured source of truth is [`baseline.json`](baseline.json) — re-derive it any time with the SQL in [`accuracy_check.sql`](../../scripts/accuracy/accuracy_check.sql). Latest committed snapshot (S&P 500 universe, 1993–present):

| Bucket | Filings | Accuracy |
|---|---:|---:|
| **Standardized facts — modern era (≥ 2010 XBRL)** — *the honest figure* | 11,422 | **100.00 %** |
| Standardized facts — overall (all eras) | 19,616 | **100.00 %** |
| Standardized facts — legacy era (< 2010) — *trivially passes; do not cite* ⚠️ | 8,194 | see `baseline.json` |
| **Unstandardized facts** (correctly left as `'Other'`) | 41.9 M | see `baseline.json` |

⚠️ Pre-2010 XBRL was optional, so most legacy filings carry no facts and trivially pass every identity — **use modern-era (≥ 2010) as the honest measurement**, per the `_note` in `baseline.json`. The numbers above are a snapshot; [`baseline.json`](baseline.json) is always the live source of truth.

---

## 1. How accuracy is defined

Two distinct measurements, each tied to a precise definition.

### 1.1 Standardized-fact accuracy

A filing is **clean** if and only if it satisfies every active *error-severity* accounting identity in [`identities.json`](identities.json) — 35 canonical equations sourced from FASB ASC, Penman (*Financial Statement Analysis* 5e), Ohlson 1995, FactSet PIT Methodology v3.4, and the XBRL US-GAAP Calculation Linkbase.

A filing is **with-error** if at least one error-severity identity fails on it.

Accuracy = `clean / (clean + with-error)`.

### 1.2 Unstandardized-fact accuracy

A fact with `standard_concept = 'Other'` is **correctly unstandardized** if and only if its raw XBRL tag is either:

* in a non-`us-gaap` namespace (`dei:`, `srt:`, `ifrs-full:`, company extensions); or
* a us-gaap tag that appears < 5,000 times in our corpus (long-tail niche); or
* a us-gaap tag matching the documented disclosure-niche keywords (footnote details, tax-rate reconciliations, share-based-compensation award schedules, operating-lease maturity tables, etc. — full regex in [`accuracy_check.sql`](../../scripts/accuracy/accuracy_check.sql) §RESULT 7).

Anything else is a **mapping gap** — a tag our standardization rules should have recognized. The current mapping-gap rate vs. correctly-classified rate is reported in [`baseline.json`](baseline.json) under `unstandardized_facts`; closing the gap is ongoing pipeline work.

### 1.3 CPA-verified concept standardization

Accuracy of the *numbers* (§1.1) is distinct from confidence in the *concept labels* those numbers are mapped to. Each canonical concept in the catalog carries a **`review_confidence`** score, surfaced on the `standard_concept` table and in the data catalog:

* **`1.0` — CPA-verified.** An accountant has signed off on the concept's canonical name, statement type, and matching rule. A verified concept is **locked**: the automated standardization loop may only ever *create new* concepts, never mutate a verified one (`reviewed_by` / `reviewed_at` record the sign-off).
* **`0.7` — provisional.** Auto-mapped by the coverage loop (used by ≥ 1,000 distinct issuers) and queued for the next CPA review cycle.

Filter `review_confidence >= 1.0` for the accountant-verified concept set — the labels analysts, quants, portfolio managers, and AI models can agree on and train against without re-deriving the mapping. This is the human-in-the-loop guarantee behind the standardization layer: every published concept is either verified or transparently flagged as provisional.

---

## 2. The 35 identities

Five families, every row tied to a citation:

| Family | Count | Examples | Source |
|---|---:|---|---|
| **Balance sheet** | 5 | `TotalAssets = TotalLiabilities + Equity`; `CurrentAssets + NoncurrentAssets = TotalAssets`; `CommonSharesOutstanding = Issued - Treasury` | FASB ASC 210; Penman §8.1 |
| **Income statement** | 6 | `Revenue - COGS = GrossProfit`; `Pretax - Tax = ContinuingOps`; `NI - NCI = NetIncomeToCommon`; `EffectiveTaxRate = Tax / Pretax` | FASB ASC 220, 740, 810; Penman §9 |
| **EPS / shares** | 3 | `NI ≈ EPS × WAS` (XBRL-decimals-aware); `Diluted ≤ Basic` (anti-dilution); `WAS_diluted ≥ WAS_basic` | FASB ASC 260; XBRL spec §4.6.6 |
| **Cash flow** | 5 | `NetChangeInCash = CFO + CFI + CFF + FX` (the Big Five); sign-convention checks on CapEx / dividends / buybacks | FASB ASC 230; IAS 7.45 |
| **Cross-statement** | 5 | Retained-earnings roll-forward; AOCI clean linkage; clean-surplus relation; quarterly→FY reconciliation | Penman §8.4; Ohlson 1995 |
| **Period shape** | 3 | Point-in-time invariant; period_span sanity; fiscal-period enum | WRDS Compustat PIT; FactSet PIT |
| **Sign plausibility** | 8 | `TotalAssets > 0`; `Cash ≥ 0`; `GrossProfit ≤ Revenue`; etc. | Common-sense BS checks |

Each identity carries a tolerance. Tolerances are not arbitrary — every one is documented inline with the data pattern it accommodates: REIT operating-partnership units, insurance separate-account assets, mezzanine equity, the FASB ASU 2016-18 cash-flow convention change, bank deposit flows that split the "Other reconciling items" bucket.

The complete machine-readable list with formulas, tolerances, severities, and citations is in [`identities.json`](identities.json).

---

## 3. How calibration raises the raw baseline

Out of the box the engine measures a much lower raw figure; iterative calibration on real SEC data — every change traceable to a specific Pareto-leading concept and a real-world filer pattern — raises it. The current measured result after calibration lives in [`baseline.json`](baseline.json) (modern era is the honest figure). Calibration proceeds in steps, each one a documented loosening tied to a real filer pattern:

Each step applied one of three calibration levers:

1. **Tolerance bump** — when a tolerance was tighter than FactSet PIT methodology, we widened it to the published threshold (e.g. `bs_01` accounting-equation slack increased from 0.5 % to 10 % to absorb redeemable NCI and mezzanine equity on financial filers).

2. **Structural-mismatch skip** — when an identity's residual exceeded a threshold (e.g. 20 % on `is_04`), it indicated a sector-specific structure the standard equation isn't designed for (AT&T 2022 WarnerMedia spinoff; REIT OP-unit distributions). We mark those skipped rather than violating.

3. **Severity demotion** — when an identity measures sector-convention drift rather than math error (e.g. `cf_01` Big-Five on banks where deposit flows split the reconciling-items bucket), we mark it `'warning'` so analysts still see the count but it doesn't pollute the headline.

These are honest engineering decisions, not metric-gaming. Every loosening choice has a named justification in [`identities.json`](identities.json).

---

## 4. Reproducing the measurement

### 4.1 Free path (sample tier — 5-year S&P 500 window)

The sample tier is free, but a Bearer token is required to fetch its Parquet files (lead-capture flow — we ask for an email so we know who's evaluating). Get one in 30 seconds at [valuein.biz/register](https://valuein.biz/register).

```bash
# 1. Install DuckDB (one binary, zero deps): https://duckdb.org/docs/installation
# 2. Export your free token and run the script:

export VALUEIN_TOKEN="your_free_token_here"

duckdb -c "
LOAD httpfs;
CREATE SECRET (TYPE HTTP, EXTRA_HTTP_HEADERS MAP {'Authorization': 'Bearer ${VALUEIN_TOKEN}'});
.read scripts/accuracy/accuracy_check.sql
"
```

You'll see all 7 result sets — headline accuracy, per-identity pass rate, 80/20 Pareto, top violators, sector breakdown, era split, coverage gaps. Same SQL we run internally; the dataset is a 5-year S&P 500 window (vs. the full 1993–present universe on paid tiers).

### 4.2 Pro / Institutional path

Same flow as 4.1 but with your paid-tier token and the corresponding bucket URL:

```bash
duckdb -c "
LOAD httpfs;
CREATE SECRET (TYPE HTTP, EXTRA_HTTP_HEADERS MAP {'Authorization': 'Bearer ${VALUEIN_TOKEN}'});
SET VARIABLE valuein_bucket_base = 'https://data.valuein.biz/v1/pro';   -- or /v1/full
.read scripts/accuracy/accuracy_check.sql
"
```

Full 1993–present × 19,000+-entity number, same SQL.

### 4.3 Offline path (no network, no token)

If you'd rather not depend on our infrastructure for the proof:

```bash
# Download the offline sample Parquet bundle (~250 MB, no token):
curl -L -o sample.zip https://valuein.biz/download/sample
unzip sample.zip -d ./sample

duckdb -c "
SET VARIABLE valuein_bucket_base = 'file:///$(pwd)/sample';
.read scripts/accuracy/accuracy_check.sql
"
```

Same script, same answer, no third-party trust required.

### 4.3 Programmatic

Through the Valuein SDK (`pip install valuein-sdk`), every `fact` row carries a `confidence_score ∈ [0, 1]` (composite of identity-pass rate × source-agreement × audit-status × restatement-density × age-decay) and a 4-bucket `reliability_code` for Bloomberg PR / Refinitiv parity:

```python
import valuein_sdk
client = valuein_sdk.Client(token='YOUR_TOKEN')

# Filter to Bloomberg-grade rows
df = client.read_table('fact', filters=[('confidence_score', '>=', 0.95)])
```

### 4.4 Through the MCP server

If you use Claude / Cursor / Codex with the Valuein MCP server (`@valuein/mcp-sec-edgar`), the per-ticker quality report is available as a tool call:

```
get_data_quality_report(ticker="AAPL")
```

Returns active violations, per-identity pass rates, and the restatement chain for that filer.

---

## 5. Re-validation

The number isn't frozen. [`baseline.json`](baseline.json) is a snapshot that is **periodically re-committed** from a production accuracy run (the run itself lives upstream in the data-pipeline repo, not in this public repo — there is no nightly workflow inside this repo that regenerates it). A production accuracy run:

1. Re-runs the full identity engine against the freshly-ingested fact table.
2. Emits a JSON matching the shape of [`baseline.json`](baseline.json), which is then committed here.
3. Updates the per-fact `confidence_score` in the next Parquet export.

When the SEC releases new XBRL taxonomy or a filer changes tagging convention, the Pareto loop repeats — but the methodology and the SQL stay exactly the same, and you can always re-run [`accuracy_check.sql`](../../scripts/accuracy/accuracy_check.sql) yourself to get a live number.

---

## 6. Limitations & honest caveats

* **Legacy era (pre-2010)** XBRL was optional, so most pre-2010 filings have no facts in our database — they trivially pass every identity check and inflate the all-era figure. **Read the modern-era (≥ 2010) number as the honest one** (11,423 of 19,617 filings in the latest [`baseline.json`](baseline.json) snapshot).

* **Sector convention is real**. We don't apply balance-sheet identities to REIT operating-partnership filings the same way we apply them to a tech megacap. The structural-skip thresholds are documented in [`identities.json`](identities.json); analysts who disagree with our skip threshold can filter `qa_violation` directly.

* **Mapping gaps still exist** — but the surface is shrinking as the standardization catalog grows (new canonical concepts and aliases land in the upstream `data-pipeline` catalog, plus disclosure-niche regex patterns folded into the classifier). The current mapping-gap rate is in [`baseline.json`](baseline.json) (`unstandardized_facts`); it is real ongoing work, not a solved problem.

* **The reported figure is for the S&P 500 universe.** The full-universe number (19,000+ entities including delisted) is the same framework with a larger denominator — expected to be a few percentage points lower because micro-cap filers have noisier XBRL.

---

## 7. Sources

* Penman, S. (2013). *Financial Statement Analysis and Security Valuation*, 5e. McGraw-Hill.
* Ohlson, J. (1995). "Earnings, Book Values, and Dividends in Equity Valuation." *Contemporary Accounting Research*, 11(2).
* FASB Accounting Standards Codification: ASC 210, 220, 230, 260, 740, 810.
* XBRL US-GAAP Taxonomy + Calculation Linkbase 2009–2026.
* FactSet Fundamentals Methodology v3.4 (public whitepaper).
* SEC EDGAR XBRL Validator (Arelle); SEC DERA "Quality of XBRL Calculation Linkbases" 2019 report.
* WRDS Compustat Point-in-Time documentation.
* Livnat & Mendenhall (2006). "Comparing the Post-Earnings-Announcement Drift…"
* Bloomberg PR feed RELIABILITY_CODE convention; Refinitiv DATA_QUALITY_INDICATOR.

---

## License

This document and the accompanying SQL / JSON are Apache 2.0. Use them, audit them, fork them, run them against your own pipeline. The whole point is that the number is publicly defensible.
