# FinanceBench-style Benchmark Methodology

## Goal

Measure whether Valuein's MCP server can answer the kinds of factual questions about US public-company filings that a financial analyst routinely asks — and whether the answers are **lineage-traceable** (each number cites the originating SEC accession) and **point-in-time correct** (the answer reflects what was filed at the `as_of_date`, not the current state of the warehouse).

The benchmark is inspired by [FinanceBench](https://arxiv.org/abs/2311.11944) (Islam, Ahmad, et al., 2023). We do not redistribute their proprietary question set; we write our own questions in the same shape, scoped to US-listed S&P 500 names (so anyone with Valuein's free `sp500` tier can reproduce the run).

## Task shape

Each task is a JSON object in `tasks.jsonl`:

```json
{
  "id": "fbb-001",
  "category": "single-doc.income-statement",
  "ticker": "AAPL",
  "fiscal_year": 2023,
  "fiscal_period": "FY",
  "question": "What was Apple's total revenue for fiscal year 2023?",
  "expected_value": 383285000000,
  "expected_unit": "USD",
  "expected_accession": "0000320193-23-000106",
  "tolerance_pct": 0.005,
  "as_of_date": "2024-01-01",
  "mcp_tool": "get_company_fundamentals",
  "mcp_args": { "ticker": "AAPL", "fiscal_year": 2023, "period": "annual" },
  "extractor": "$.rows[0].metrics.revenue"
}
```

Field semantics:

| Field | Meaning |
|---|---|
| `id` | Stable identifier for citation. |
| `category` | `single-doc.<surface>` (one filing answers it) or `multi-doc.<surface>` (chains 10-K + 10-Q + 8-K). v1 ships single-doc only. |
| `ticker`, `fiscal_year`, `fiscal_period` | Anchor for verification. |
| `question` | Plain-English statement the task is testing. Not fed to an LLM — exists for human readability + audit. |
| `expected_value`, `expected_unit` | Ground truth. |
| `expected_accession` | The SEC accession that filed the value first (or last, if amendments apply — see below). |
| `tolerance_pct` | Allowed relative error. Default 0.5% to absorb SEC rounding-band variance. |
| `as_of_date` | Snapshot date. The MCP must return the value that was current at this date — restatements filed AFTER this date must NOT change the answer. |
| `mcp_tool` | Which Valuein MCP tool the runner calls. |
| `mcp_args` | Arguments passed to the tool. |
| `extractor` | JSONPath to pluck the value from the tool response. |

## Scoring

Each task scores three signals:

### 1. Numerical accuracy (weight 0.5)

`abs(returned - expected) / abs(expected) ≤ tolerance_pct` → pass.

Tolerance defaults to 0.5% to absorb SEC rounding-band drift. Tasks asking for percentages or ratios use a tighter band (0.1%) because those don't have rounding ambiguity in the source.

### 2. Lineage citation (weight 0.3)

The response's `lineage.source_filing` must equal `expected_accession` OR be the most recent restatement of that period (the warehouse may have a 10-K/A that updated the original — that's still a correct citation if the value was changed).

When `expected_accession` is set, the runner accepts any accession in the lineage chain — the test is "does the value trace to A real SEC filing" not "the exact accession I happened to find first".

### 3. Point-in-time correctness (weight 0.2)

If `as_of_date` is set, the runner passes `as_of_date` into the MCP tool call. Valuein's tools filter `accepted_at <= as_of_date` so values filed after the date are excluded.

Pass criterion: the returned value reflects the warehouse state at `as_of_date`. Failure mode: a restatement filed AFTER the date appears in the response.

### Per-task score

```
score = 0.5 * numerical_pass + 0.3 * lineage_pass + 0.2 * pit_pass
```

A perfect task = 1.0. A task that returns the right number but doesn't cite a filing = 0.5. A task that returns the wrong number with perfect citation = 0.3.

## Aggregate score

```
benchmark_score = mean(task_score for task in tasks)
```

We publish three numbers:
- **Overall** — mean across all tasks.
- **Single-doc** — mean across `category.startsWith("single-doc")`.
- **Lineage-only** — mean of `lineage_pass` across all tasks. Surfaces whether the MCP cites filings even when the value is wrong.

## What FinanceBench measured vs. what we measure

| | FinanceBench (Islam et al. 2023) | Valuein bench |
|---|---|---|
| **Surface** | Full LLM with RAG over 10-K PDFs | MCP tool calls returning structured rows |
| **Scoring** | Human + LLM verifier | Programmatic: numerical + lineage + PIT |
| **Question set** | 10,231 questions | 20 tasks (v1) — designed to be reproducible end-to-end on a free tier |
| **Baseline GPT-4-Turbo + RAG** | 19% pass on single-doc, 19.3% pass on multi-doc | n/a (different task shape) |
| **Cost per question** | LLM tokens × 10K questions | $0 (programmatic) |

We **don't** claim our benchmark is directly comparable to FinanceBench's published number. They tested a generative LLM stack; we test a structured-data MCP. The relevant comparison is whether structured-data lookups outperform 10-K PDF retrieval on the questions analysts actually ask. Our bet is yes by a wide margin.

## Known limitations of v1

- **No multi-doc tasks.** Multi-doc requires chaining 10-K + 10-Q + 8-K and reasoning across them. v1 keeps each task self-contained. v2 adds multi-doc.
- **No smart-money tasks.** Insider transactions + 13F deltas need Institutional tier ($499/mo). We'll publish those once the bench is mature enough to justify the run cost.
- **English only.** Tasks are all on US-listed companies filing in English. Foreign issuers (20-F / 40-F filers like ASML, Shopify) are out of scope for v1.
- **Static `as_of_date`.** We pin each task to a specific snapshot. The score doesn't measure incremental update latency.

## How to add a task

1. Open `tasks.jsonl` and append a new JSON line following the schema above.
2. Verify the `expected_value` manually against the filing on EDGAR (use the URL the runner emits during a fresh run, or look up the accession at `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<ticker>`).
3. Run `bash run-bench.sh` locally to confirm Valuein returns the value.
4. Commit the task + the run output (`results-latest.json` + `results-latest.md`).

## How to contribute a competing provider

If you sell SEC fundamentals and want a public head-to-head:
1. Fork this repo.
2. Add `<your-provider>/run-bench.sh` invoking your API the same way `finance-bench/run-bench.sh` invokes Valuein's MCP.
3. Open a PR. We'll merge it and cite your published score next to ours in the leaderboard.

The bar is the same for everyone. The methodology is published. We're not trying to win on a hidden test set — we want a public scoreboard where the institutional data providers can compete openly.
