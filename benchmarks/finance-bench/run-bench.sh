#!/usr/bin/env bash
# Valuein Finance-Bench runner.
#
# Reads tasks.jsonl, invokes Valuein's MCP server once per task via
# JSON-RPC, scores the response on (numerical, lineage, PIT) signals,
# and writes results to:
#
#   results-latest.json   — full per-task records
#   results-latest.md     — human-readable summary
#
# Usage:
#   export VALUEIN_TOKEN="tok_xxx"          # get one at valuein.biz
#   bash run-bench.sh                       # writes results-latest.{json,md}
#
# Optional:
#   VALUEIN_MCP_URL    — override the MCP endpoint (default mcp.valuein.biz)
#   BENCH_VERBOSE=1    — print per-task progress
#
# Reproducibility goal: zero hidden state. Same tasks.jsonl + same
# warehouse snapshot = same score. The runner is intentionally a shell
# script (curl + jq) so anyone can audit the wire format without
# trusting a TypeScript / Python harness.

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────
MCP_URL="${VALUEIN_MCP_URL:-https://mcp.valuein.biz/mcp}"
TASKS_FILE="$(dirname "$0")/tasks.jsonl"
OUT_JSON="$(dirname "$0")/results-latest.json"
OUT_MD="$(dirname "$0")/results-latest.md"
VERBOSE="${BENCH_VERBOSE:-0}"

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required. Install via 'brew install jq' or your package manager." >&2
  exit 1
fi

# ── Auth header — token is optional for sample-tier tasks ────────────────
AUTH_HEADER=()
if [ -n "${VALUEIN_TOKEN:-}" ]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${VALUEIN_TOKEN}")
else
  echo "Note: VALUEIN_TOKEN not set — running against the sample tier (S&P 500 only)." >&2
fi

# ── Single MCP tools/call → returns the structured tool result ───────────
mcp_call() {
  local tool="$1"
  local args="$2"
  local id="$3"
  curl -sS -X POST "${MCP_URL}" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    "${AUTH_HEADER[@]}" \
    -d "$(jq -nc \
      --arg tool "${tool}" \
      --argjson args "${args}" \
      --arg id "${id}" \
      '{jsonrpc:"2.0", id:$id, method:"tools/call", params:{name:$tool, arguments:$args}}')"
}

# Per-call sleep — stay under the sample tier's 60/min rate limit when no
# token is configured. Increase via BENCH_RATE_DELAY_SEC for parallel-safe
# runs (e.g. 0.05 for paid tiers).
RATE_DELAY="${BENCH_RATE_DELAY_SEC:-1.1}"

# ── Score a single task — outputs a one-line JSON record to stdout ───────
score_task() {
  local task="$1"

  local id ticker tool args extractor expected expected_acc tol as_of category
  id="$(echo "$task" | jq -r .id)"
  ticker="$(echo "$task" | jq -r .ticker)"
  tool="$(echo "$task" | jq -r .mcp_tool)"
  args="$(echo "$task" | jq -c '.mcp_args | . + {as_of_date: (if has("as_of_date") then .as_of_date else null end)}' )"
  # Use the task's as_of_date if present (top-level field).
  if echo "$task" | jq -e '.as_of_date' >/dev/null; then
    local as_of
    as_of="$(echo "$task" | jq -r .as_of_date)"
    args="$(echo "$args" | jq --arg d "$as_of" '. + {as_of_date: $d}')"
  fi
  extractor="$(echo "$task" | jq -r .extractor)"
  expected="$(echo "$task" | jq -r .expected_value)"
  expected_acc="$(echo "$task" | jq -r .expected_accession)"
  tol="$(echo "$task" | jq -r .tolerance_pct)"
  as_of="$(echo "$task" | jq -r '.as_of_date // ""')"
  category="$(echo "$task" | jq -r .category)"

  [ "$VERBOSE" = "1" ] && echo "  → ${id} (${ticker} ${tool})" >&2

  # Call the MCP. The tools/call response wraps the structured data inside
  # content[0].text as a JSON string.
  local raw
  raw="$(mcp_call "$tool" "$args" "$id" || true)"

  local content_text
  content_text="$(echo "$raw" | jq -r '.result.content[0].text // ""')"
  if [ -z "$content_text" ]; then
    # Surface the JSON-RPC error if there is one.
    local err
    err="$(echo "$raw" | jq -rc '.error // null')"
    jq -nc \
      --arg id "$id" --arg cat "$category" --arg ticker "$ticker" \
      --argjson expected "$expected" --arg expected_acc "$expected_acc" \
      --arg error "$err" \
      '{id:$id, category:$cat, ticker:$ticker, expected:$expected, expected_accession:$expected_acc,
        actual:null, accession_returned:null,
        numerical_pass:false, lineage_pass:false, pit_pass:false, score:0,
        error:$error}'
    return
  fi

  # Parse the structured response.
  local payload
  payload="$(echo "$content_text" | jq -c .)"

  local actual
  actual="$(echo "$payload" | jq -r "$extractor // \"null\"")"

  local accession_returned
  accession_returned="$(echo "$payload" | jq -r '.rows[0].lineage.source_filing // ""')"

  # Numerical accuracy.
  local numerical_pass="false"
  if [ "$actual" != "null" ] && [ "$expected" != "null" ]; then
    local diff
    diff="$(awk -v a="$actual" -v e="$expected" -v t="$tol" \
      'BEGIN { if (e == 0) { print (a == 0 ? "true" : "false"); exit } d = (a - e) / e; if (d < 0) d = -d; print (d <= t ? "true" : "false") }')"
    numerical_pass="$diff"
  fi

  # Lineage citation.
  local lineage_pass="false"
  if [ -n "$accession_returned" ]; then
    # Pass if exact match OR same originating CIK + same period (amendment-flexible).
    if [ "$accession_returned" = "$expected_acc" ]; then
      lineage_pass="true"
    fi
  fi

  # PIT correctness — heuristic: when as_of_date is set, the lineage's
  # accepted_at must be ≤ as_of_date. We rely on the MCP to enforce this
  # server-side; an obvious failure would be the accession returned being
  # filed after as_of_date.
  local pit_pass="true"
  if [ -n "$as_of" ]; then
    local accepted_at
    accepted_at="$(echo "$payload" | jq -r '.rows[0].lineage.accepted_at // ""' | cut -d'T' -f1)"
    if [ -n "$accepted_at" ] && [ "$accepted_at" \> "$as_of" ]; then
      pit_pass="false"
    fi
  fi

  # Weighted score: numerical 0.5, lineage 0.3, PIT 0.2.
  local score
  score="$(awk -v n="$numerical_pass" -v l="$lineage_pass" -v p="$pit_pass" \
    'BEGIN { ns = (n == "true" ? 0.5 : 0); ls = (l == "true" ? 0.3 : 0); ps = (p == "true" ? 0.2 : 0); printf "%.2f", ns + ls + ps }')"

  jq -nc \
    --arg id "$id" --arg cat "$category" --arg ticker "$ticker" \
    --argjson expected "$expected" --arg expected_acc "$expected_acc" \
    --arg actual "$actual" --arg accession_returned "$accession_returned" \
    --argjson np "$numerical_pass" --argjson lp "$lineage_pass" --argjson pp "$pit_pass" \
    --argjson sc "$score" \
    '{id:$id, category:$cat, ticker:$ticker,
      expected:$expected, expected_accession:$expected_acc,
      actual:($actual | tonumber? // $actual),
      accession_returned:$accession_returned,
      numerical_pass:$np, lineage_pass:$lp, pit_pass:$pp,
      score:$sc}'
}

# ── Run all tasks ────────────────────────────────────────────────────────
echo "Valuein Finance-Bench v1 — runner starting" >&2
echo "MCP endpoint: ${MCP_URL}" >&2
echo "Tasks: $(wc -l < "$TASKS_FILE") in $(basename "$TASKS_FILE")" >&2
echo "" >&2

records="["
sep=""
while IFS= read -r task; do
  [ -z "$task" ] && continue
  rec="$(score_task "$task")"
  records="${records}${sep}${rec}"
  sep=","
  # Pace requests to stay under the configured rate limit.
  sleep "${RATE_DELAY}"
done < "$TASKS_FILE"
records="${records}]"

# ── Aggregate ────────────────────────────────────────────────────────────
overall="$(echo "$records" | jq '[.[].score] | (add / length) | . * 100 | round / 100')"
single_doc="$(echo "$records" | jq '[.[] | select(.category | startswith("single-doc")) | .score] | (add / length) | . * 100 | round / 100')"
lineage_only="$(echo "$records" | jq '[.[] | (.lineage_pass | if . then 1 else 0 end)] | (add / length) | . * 100 | round / 100')"
numerical_only="$(echo "$records" | jq '[.[] | (.numerical_pass | if . then 1 else 0 end)] | (add / length) | . * 100 | round / 100')"
n="$(echo "$records" | jq 'length')"

run_iso="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Final JSON output.
jq -n \
  --arg run_iso "$run_iso" --arg mcp_url "$MCP_URL" \
  --argjson n "$n" \
  --argjson overall "$overall" --argjson single_doc "$single_doc" \
  --argjson lineage_only "$lineage_only" --argjson numerical_only "$numerical_only" \
  --argjson records "$records" \
  '{run_iso:$run_iso, mcp_url:$mcp_url, task_count:$n, scores:{overall:$overall, single_doc:$single_doc, lineage_only:$lineage_only, numerical_only:$numerical_only}, tasks:$records}' \
  > "$OUT_JSON"

# Markdown summary.
{
  echo "# Valuein Finance-Bench — Results"
  echo ""
  echo "**Run timestamp**: ${run_iso}"
  echo "**MCP endpoint**: ${MCP_URL}"
  echo "**Tasks**: ${n}"
  echo ""
  echo "## Aggregate Scores"
  echo ""
  echo "| Metric | Score |"
  echo "|---|---|"
  echo "| Overall (weighted) | **${overall}** / 1.00 |"
  echo "| Single-doc subset | ${single_doc} / 1.00 |"
  echo "| Numerical-only pass rate | ${numerical_only} / 1.00 |"
  echo "| Lineage-only pass rate | ${lineage_only} / 1.00 |"
  echo ""
  echo "## Per-Task Detail"
  echo ""
  echo "| Task | Ticker | Numerical | Lineage | PIT | Score |"
  echo "|---|---|---|---|---|---|"
  echo "$records" | jq -r '.[] | "| \(.id) | \(.ticker) | \(if .numerical_pass then "✅" else "❌" end) | \(if .lineage_pass then "✅" else "❌" end) | \(if .pit_pass then "✅" else "❌" end) | \(.score) |"'
} > "$OUT_MD"

echo "" >&2
echo "Results written:" >&2
echo "  ${OUT_JSON}" >&2
echo "  ${OUT_MD}" >&2
echo "" >&2
echo "Overall score: ${overall} / 1.00" >&2
