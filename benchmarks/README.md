# Valuein Benchmarks

Reproducible benchmarks measuring whether Valuein's MCP server returns **correct, lineage-traceable, point-in-time** answers to the questions analysts and AI agents actually ask. The intent is to publish a score on the same scoreboard that the institutional data providers (FactSet, S&P CIQ, Bloomberg) compete on — and to show that free + low-cost SEC data, properly standardised, can match or exceed those baselines on the questions that matter.

## Why this exists

[FinanceBench](https://arxiv.org/abs/2311.11944) (Islam et al., 2023) established the modern bar: 10,231 question-answer pairs over 10-K / 10-Q / 8-K filings, and the published result that GPT-4-Turbo with RAG **fails 81%** of single-doc questions and **80.7%** of multi-doc questions. That number is the wedge for everyone shipping a finance-grounded LLM stack today — the open question is what fixes it.

Valuein's hypothesis: the right MCP tool surface (standardised facts + lineage + point-in-time integrity) beats raw RAG on 10-Ks by a wide margin. This directory ships the scaffolding to test that hypothesis publicly.

## Benchmarks shipped here

| Benchmark | What it measures | Source |
|---|---|---|
| [`finance-bench/`](./finance-bench/) | Single-doc + multi-doc fundamental-retrieval accuracy on US-listed 10-Ks, modelled on the FinanceBench task shape. | Custom task set (this repo) inspired by Islam et al. (2023). |

## Methodology principles

1. **Reproducible from this repo.** Every benchmark task is a JSON line; the runner script is checked in; a future contributor can `bash run-bench.sh` and reproduce our published number.
2. **Lineage-graded.** A correct answer is not enough — the response must cite the originating SEC accession via the `lineage` envelope. Answers without lineage score 0.
3. **Point-in-time honest.** Each task carries an `as_of_date`. The MCP response is graded against the warehouse state at that date, not "today". Tasks that require restatements / amendments are tagged so the grader credits the right snapshot.
4. **No cherry-picking.** Task selection is documented; the question set is published before the run; we don't drop tasks that score poorly between runs.

## Running the benchmarks yourself

The runner is a shell script + curl + jq. No LLM in the loop — the harness exercises Valuein's MCP tools directly and compares structured responses to expected JSON. This makes the score reproducible without API spend.

```bash
# Get a free token at valuein.biz (S&P 500 tier, no credit card needed for the bench questions covered)
export VALUEIN_TOKEN="tok_xxx"

# Run the FinanceBench-flavour task set
cd finance-bench
bash run-bench.sh
```

The script writes per-task results to `results-latest.json` and aggregate stats to `results-latest.md`. Both are checked into the repo on every official run.

## How we score

For each task the harness computes three signals:

| Signal | Weight | Pass criterion |
|---|---|---|
| **Numerical accuracy** | 0.5 | Returned value within `tolerance_pct` of expected (default 0.5% — SEC rounding band). |
| **Lineage citation** | 0.3 | Response carries a `lineage.source_filing` matching the expected accession (or any later amendment of it). |
| **PIT correctness** | 0.2 | If `as_of_date` is set on the task, the answer must reflect the warehouse state at that date (no look-ahead). |

Per-task score = weighted sum. A task scores 1.0 only when all three pass.

## Inviting external audits

If you maintain a competing data provider and want to publish a comparable score against the same task set: open a PR adding `your-provider/run-bench.sh` to your repo, link it back to this benchmark spec, and we'll cite your number alongside ours. Comparable methodology, comparable bar.

## Roadmap

- **v1 (this PR)** — methodology + 20 single-doc tasks anchored to S&P 500 10-Ks from 2020-2024. Scoreable today via the sample tier.
- **v2** — multi-doc tasks (chain 10-K + 10-Q for the same fiscal period; amendment-aware grading).
- **v3** — smart-money tasks (insider clusters, 13F deltas, 13D→13G conversion detection). Requires Institutional tier; published score will be paired with the cost-per-correct-answer comparison vs the FactSet / S&P CIQ baseline.
- **v4** — public leaderboard at `valuein.biz/benchmarks` that pulls the JSON results on every push to main.

## Citation

If you reference Valuein's benchmark results in a paper, blog post, or competitive analysis, please cite this repository + commit hash. Methodology details live in [`finance-bench/methodology.md`](./finance-bench/methodology.md).
