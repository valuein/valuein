<!-- Thanks for contributing to Valuein!  Pick the type, fill in what applies, drop the rest. -->

## What and why

<!-- One paragraph: what does this PR change, and what user problem does it solve? -->

## Type

- [ ] New example script (`examples/python/*.py`)
- [ ] New notebook (`examples/notebooks/*.ipynb`)
- [ ] Update to an existing example or notebook
- [ ] New query recipe (`docs/QUERY_COOKBOOK.md`)
- [ ] Documentation fix or improvement (`docs/`, `README.md`, …)
- [ ] Catalog regeneration (`scripts/generate_catalog.py` + outputs)
- [ ] MCP registry manifest bump (`server.json`)
- [ ] Other (describe below)

## Checklist

<!-- Tick everything that applies; remove rows that don't. -->

- [ ] Ran `uv run ruff check examples/ scripts/ --fix && uv run ruff format examples/ scripts/`
- [ ] Ran the script / notebook end-to-end on the **Sample tier** (no token needed) and pasted output below
- [ ] Used canonical `standard_concept` names (`'TotalRevenue'`, `'NetIncome'`, …) — not raw XBRL tags
- [ ] Started cross-company queries from the `references` table
- [ ] Filtered backtests by `filing_date <= trade_date` (not `report_date`)
- [ ] Wrapped CAPEX in `ABS()` and ratio denominators in `NULLIF(..., 0)`
- [ ] If touching `fact` quarterly cash flows: used `COALESCE(derived_quarterly_value, numeric_value)`
- [ ] Updated the matching notebook if a Python script changed (and vice versa)
- [ ] No hardcoded tokens, internal URLs, or bucket names
- [ ] If catalog changed: re-ran `scripts/generate_catalog.py` and committed regenerated `data_catalog.{md,json}` + `DATA_CATALOG.xlsx`

## Output / screenshots

<!-- For new or modified examples / notebooks: paste 5–10 lines of the actual output. -->

```text
$ uv run python examples/python/your_file.py
...
```

## Cross-repo notes

<!-- Does this depend on a change in the SDK, MCP, pipeline, or frontend? Link the upstream PR/issue. -->

## Closes / refs

<!-- Closes #123, refs #456 -->
