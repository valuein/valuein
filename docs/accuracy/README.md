# Accuracy proof

Public, reproducible evidence for the accuracy claims in the Valuein
README and pricing page. Three files, all citable, all runnable:

| File | Purpose |
|---|---|
| [`methodology.md`](methodology.md) | Narrative — definitions, 35 identities, how we calibrate up from the raw baseline, limitations |
| [`identities.json`](identities.json) | Machine-readable catalog of every identity (formula, tolerance, severity, citation) — exactly the set the engine evaluates |
| [`baseline.json`](baseline.json) | **The measured source of truth.** Latest snapshot: 88.96 % modern-era (≥ 2010) on 11,423 S&P 500 FY filings — the honest figure — and 93.55 % overall on 19,617. Periodically re-committed from a production run. |
| [`../../scripts/accuracy/accuracy_check.sql`](../../scripts/accuracy/accuracy_check.sql) | Self-contained DuckDB script that reproduces the measurement — defaults to the free sample tier |

## TL;DR for customers

> *"Valuein measures mathematical consistency on S&P 500 annual filings against SEC's own canonical `companyfacts` API — the honest modern-era (≥ 2010) figure is **88.96 %** (93.55 % across all eras; see [`baseline.json`](baseline.json), the measured source of truth). Each tolerance choice is citable to FactSet PIT methodology, FASB ASC, or Penman §8-10, and re-running the measurement is one DuckDB command."*

```bash
# Get a free token first (lead-capture, 30 seconds): https://valuein.biz/register
export VALUEIN_TOKEN="your_token"

duckdb -c "
  LOAD httpfs;
  CREATE SECRET (TYPE HTTP, EXTRA_HTTP_HEADERS MAP {'Authorization': 'Bearer ${VALUEIN_TOKEN}'});
  .read scripts/accuracy/accuracy_check.sql
"
```

Prefer zero third-party trust? Download the [offline sample bundle](https://valuein.biz/download/sample), point `valuein_bucket_base` at the local path, run the same script. Same SQL, same answer. Pro / Institutional tier customers swap the URL — same SQL, larger universe.

## How this differs from other data vendors

* **The SQL is open.** Every other commercial financial data vendor publishes accuracy claims you can't independently verify. Ours runs against their data + ours, in DuckDB, in front of you.
* **The identities are cited.** Each tolerance is anchored to a public source (FactSet PIT v3.4, FASB ASC, Penman, Ohlson 1995) — not "internal best practices".
* **The skips are documented.** When we declare an identity doesn't apply to a sector (e.g. `cf_01` Big-Five on banks), it's in `identities.json` with the reason. No silent thresholds.
* **The number is re-derivable.** [`baseline.json`](baseline.json) is a snapshot re-committed from a production accuracy run (the run itself lives upstream in the data-pipeline repo). Re-run the SQL yourself any time — if a sector convention changes or a filer breaks the tagging, the script shows it.

## Questions

* **Why not 100 %?** Because some real filings have real data errors (12-month forward hedge reclassifications mis-tagged; share-class structures the standard EPS identity wasn't designed for). We surface those in `qa_violation` and you can audit any of them via the MCP `get_data_quality_report` tool. The current measured headline is in [`baseline.json`](baseline.json).

* **Why isn't unstandardized accuracy higher?** Because there are still us-gaap tag aliases (`SalesRevenueNet`, `CashAndCashEquivalentsPeriodIncreaseDecrease`, etc.) that should be in our catalog but aren't yet, plus genuine long-tail XBRL disclosures. The current mapping-gap rate is reported in [`baseline.json`](baseline.json) (`unstandardized_facts`); closing it is ongoing pipeline work.

* **Where can I run this against the full universe?** With a Pro or Institutional token from valuein.biz, set `valuein_bucket_base` to your tier's bucket prefix and re-run the same script.

* **What if I disagree with a tolerance?** Fork [`identities.json`](identities.json), tighten the values you care about, re-run the script. You'll see how much of the measured accuracy in [`baseline.json`](baseline.json) survives your stricter rules. That's the whole point of publishing the file.
