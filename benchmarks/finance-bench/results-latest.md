# Valuein Finance-Bench — Results

**Status**: ⏳ Pending first official run.

Run `bash run-bench.sh` with a valid `VALUEIN_TOKEN` (free `sp500`-tier token from [valuein.biz](https://valuein.biz)) to populate this file. The runner writes both `results-latest.json` (full per-task records) and this Markdown summary on every invocation.

## Why this is empty

The benchmark scaffolding ships with no committed scores deliberately. We're not going to publish a number we haven't run end-to-end with the right configuration — that's how benchmarks lose credibility. The first official run will land as a commit named `bench: first official run — overall X.XX` so the score is permanently linked to a specific commit hash.

If you want to reproduce a score before then, the runner is checked in and self-contained — you don't need to wait for our first run.

## Reproduction recipe (the runner already does this for you)

```bash
# Get a free token at valuein.biz (S&P 500 tier, no credit card)
export VALUEIN_TOKEN="tok_xxx"

# Run all 20 tasks (~30 seconds with the default 1.1s rate-limit pacing)
cd benchmarks/finance-bench
bash run-bench.sh

# Read the score
cat results-latest.md
```

The runner auto-paces requests at 1.1s/task to stay under the free-tier 60/min rate limit. With a Pro tier token set `BENCH_RATE_DELAY_SEC=0.05` for ~1s total runtime.

## What gets published here on each run

- Run timestamp + MCP endpoint
- Aggregate scores: overall, single-doc subset, numerical-only, lineage-only
- Per-task breakdown table

Historical runs accumulate in `results-history.md` (created on the second run).

## Wire-protocol note (for the curious)

The MCP server speaks the Streamable HTTP transport from the official MCP spec (2025-11-25). Each task is a single JSON-RPC `tools/call`. The runner uses curl + jq — no SDK dependency — so any future contributor can audit the wire format without trusting a TypeScript or Python harness. The request shape is:

```
POST https://mcp.valuein.biz/mcp
Content-Type: application/json
Accept: application/json, text/event-stream
Authorization: Bearer tok_xxx (optional for sample-tier tasks)

{
  "jsonrpc": "2.0",
  "id": "fbb-001",
  "method": "tools/call",
  "params": {
    "name": "get_company_fundamentals",
    "arguments": { "ticker": "AAPL", "fiscal_year": 2023, "period": "annual" }
  }
}
```

Response wraps the structured payload inside `result.content[0].text` as a JSON string — the runner parses it with jq, applies the per-task `extractor` JSONPath, and scores numerical / lineage / PIT signals.
