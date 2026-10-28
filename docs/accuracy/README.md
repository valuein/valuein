# Accuracy proof

Public, reproducible evidence for the accuracy claims in the Valuein
README and pricing page. Three files, all citable, all runnable:

| File | Purpose |
|---|---|
| [`methodology.md`](methodology.md) | Narrative — definitions, the identity rules, how we calibrate up from the raw baseline, limitations |
| [`identities.json`](identities.json) | Machine-readable catalog of every identity (formula, tolerance, severity, citation) — generated from the engine's catalogue; its error-severity rules are the set `baseline.json` was graded against |
| [`baseline.json`](baseline.json) | **The measured source of truth.** Latest snapshot (S&P 500 universe, evaluable filings only, "clean" = passes every error-severity identity): 91.46 % modern-era (≥ 2010), 93.31 % overall, 18,385 annual filings. Regenerated from a production run; the exact filing counts and figures are always in the file itself. |
| [`../../scripts/accuracy/accuracy_check.sql`](../../scripts/accuracy/accuracy_check.sql) | Self-contained DuckDB script that reproduces the measurement — defaults to the free sample tier |

## TL;DR for customers

> *"Valuein measures mathematical consistency on S&P 500 annual filings against SEC's own canonical `companyfacts` API — see [`baseline.json`](baseline.json) for the current measured figure (the honest ≥ 2010 modern-era result). Each tolerance choice is citable to FactSet PIT methodology, FASB ASC, or Penman §8-10, and re-running the measurement is one DuckDB command."*

```bash
# Get a free token first (lead-capture, 30 seconds): https://valuein.biz/signup/free
# VALUEIN_TOKEN is just the shell variable these DuckDB commands read (the SDK reads VALUEIN_API_KEY);
# both hold the same token.
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

> **`identities.json` is generated.** `scripts/generate_identities.py` builds it from the QA engine's identity catalogue (`scripts/QA/identities.sql` upstream), active identities only. Its error-severity rules and tolerances equal `baseline.json` `identity_set` (pinned by `tests/test_generate_identities.py`), so the published copy is the set the headline figure was graded against.

* **How should I read the headline?** As the share of evaluable S&P 500-universe annual filings that pass every error-severity identity (91.46 % modern-era, 93.31 % overall at the 2026-10-24 measurement), never as a claim about the full 19,000+ universe. The identities use the NCI-inclusive equity concept (`StockholdersEquityIncludingNCI`), as consolidated statements are prepared. The failing identities are ranked in `baseline.json` `top_remaining_pareto`. The current figure is always in [`baseline.json`](baseline.json); re-derive it yourself with the SQL.

* **Why isn't unstandardized accuracy higher?** Because there are still us-gaap tag aliases (`SalesRevenueNet`, `CashAndCashEquivalentsPeriodIncreaseDecrease`, etc.) that should be in our catalog but aren't yet, plus genuine long-tail XBRL disclosures. The current mapping-gap rate is reported in [`baseline.json`](baseline.json) (`unstandardized_facts`); closing it is ongoing pipeline work.

* **Where can I run this against the full universe?** With a Pro or Institutional token from valuein.biz, set `valuein_bucket_base` to your tier's bucket prefix and re-run the same script.

* **What if I disagree with a tolerance?** Fork [`identities.json`](identities.json), tighten the values you care about, re-run the script. You'll see how much of the measured accuracy in [`baseline.json`](baseline.json) survives your stricter rules. That's the whole point of publishing the file.
