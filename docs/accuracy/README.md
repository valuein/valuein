# Accuracy proof

Public, reproducible evidence for the accuracy claims in the Valuein
README and pricing page. Three files, all citable, all runnable:

| File | Purpose |
|---|---|
| [`methodology.md`](methodology.md) | Narrative — definitions, 35 identities, how we got from 69 % baseline to 99.58 %, limitations |
| [`identities.json`](identities.json) | Machine-readable catalog of every identity (formula, tolerance, severity, citation) — exactly the set the engine evaluates |
| [`baseline.json`](baseline.json) | The measured headline number on 12,048 S&P 500 FY filings (re-derived nightly) |
| [`../../scripts/accuracy/accuracy_check.sql`](../../scripts/accuracy/accuracy_check.sql) | Self-contained DuckDB script that reproduces the measurement — defaults to the free sample tier |

## TL;DR for customers

> *"Valuein guarantees 99.58 % mathematical consistency on S&P 500 annual filings, audited against SEC's own canonical `companyfacts` API, with each tolerance choice citable to FactSet PIT methodology, FASB ASC, or Penman §8-10. Re-running the measurement is one DuckDB command."*

```bash
duckdb -c ".read scripts/accuracy/accuracy_check.sql"
```

That command targets the free `sec-data-sample` bucket (5 years of S&P 500 data, no token required). Pro / Institutional tier customers point it at their own bucket via a session variable — same SQL, larger universe.

## How this differs from other data vendors

* **The SQL is open.** Every other commercial financial data vendor publishes accuracy claims you can't independently verify. Ours runs against their data + ours, in DuckDB, in front of you.
* **The identities are cited.** Each tolerance is anchored to a public source (FactSet PIT v3.4, FASB ASC, Penman, Ohlson 1995) — not "internal best practices".
* **The skips are documented.** When we declare an identity doesn't apply to a sector (e.g. `cf_01` Big-Five on banks), it's in `identities.json` with the reason. No silent thresholds.
* **The number is continuous.** Nightly pipeline runs re-derive the figure. If a sector convention changes or a filer breaks the tagging, you'll see it before we tell you.

## Questions

* **Why 99.58 % and not 100 %?** Because some real filings have real data errors (12-month forward hedge reclassifications mis-tagged; share-class structures the standard EPS identity wasn't designed for). We surface those in `qa_violation` and you can audit any of them via the MCP `get_data_quality_report` tool.

* **Why is unstandardized accuracy 97.21 % and not higher?** Because we identified 17 us-gaap tag aliases (`SalesRevenueNet`, `CashAndCashEquivalentsPeriodIncreaseDecrease`, etc.) that should be in our catalog but aren't yet. They'll land in the next pipeline release; the remaining ~3 % gap is genuine long-tail XBRL disclosures.

* **Where can I run this against the full universe?** With a Pro or Institutional token from valuein.biz, set `valuein_bucket_base` to your tier's bucket prefix and re-run the same script.

* **What if I disagree with a tolerance?** Fork [`identities.json`](identities.json), tighten the values you care about, re-run the script. You'll see how much of our 99.58 % survives your stricter rules. That's the whole point of publishing the file.
