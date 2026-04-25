# Contributing to Valuein

Valuein is a commercial data platform with an open community layer. **This repository** holds the public docs, examples, notebooks, and the MCP registry manifest that points AI agents at our service. The SDK, MCP server, data pipeline, and infrastructure live in dedicated repositories — this is the front door.

We love contributions to:

- **Examples** — new Python scripts in [`examples/python/`](examples/python/) that exercise the SDK on a specific use case
- **Notebooks** — corresponding Jupyter notebooks in [`examples/notebooks/`](examples/notebooks/)
- **Query recipes** — additions to [`docs/QUERY_COOKBOOK.md`](docs/QUERY_COOKBOOK.md)
- **Documentation** — clarity, typos, accuracy fixes anywhere in [`docs/`](docs/)
- **Issue triage** — confirming reproductions, adding context, suggesting fixes

If you want to change the SDK itself or the MCP server, those repos have their own `CONTRIBUTING.md` — open an issue here first and we'll route it.

---

## Quick start

```bash
git clone https://github.com/valuein/valuein.git
cd valuein

# We use uv for everything (https://github.com/astral-sh/uv)
# Examples are standalone scripts that depend only on the published SDK.

# Run any example on the Sample tier (no token, no signup):
uv run python examples/python/getting_started.py

# Or with a paid tier:
VALUEIN_API_KEY=xxx uv run python examples/python/factor_screen.py
```

There is no `pyproject.toml`, no test suite, and no build step in this repo. The example scripts are themselves the smoke test — if `getting_started.py` runs cleanly on the Sample tier, the published SDK is healthy.

---

## What you can contribute

| Type | Where | Notes |
|---|---|---|
| Bug report | [Issue templates](.github/ISSUE_TEMPLATE/) | Pick the right one — data, feature, outage, or question |
| New example script | [`examples/python/`](examples/python/) | One concept per file, < 150 lines, follow the rules below |
| New Jupyter notebook | [`examples/notebooks/`](examples/notebooks/) | Mirror an existing Python script — same name, same content |
| New query recipe | [`docs/QUERY_COOKBOOK.md`](docs/QUERY_COOKBOOK.md) | Add to the right section, include `Use when:` and `Why:` |
| Doc fix / clarification | [`docs/`](docs/) | Just open a PR |
| New MCP-tool walkthrough | [`docs/MCP_TOOLS.md`](docs/MCP_TOOLS.md) | Show input → output for one real tool |
| Catalog change | [`scripts/generate_catalog.py`](scripts/generate_catalog.py) | Update `CONCEPTS`, run the generator, commit the regenerated md/json/xlsx |

---

## Examples — contribution rules

These are stricter than typical OSS examples because the scripts are **the way users learn the product**. Inconsistency here costs every reader.

- **Filename:** `snake_case.py`, no numeric prefix
- **One concept per file**, kept under 150 lines — split if needed
- **Import:** `from valuein_sdk import ValueinClient` (the published PyPI package)
- **Context manager:** `with ValueinClient() as client:` — never bare construction
- **Tables:** `tables=[...]` to load only what's needed (faster startup)
- **Standalone:** `uv run python examples/python/your_file.py` must succeed on the Sample tier without a token, or document the minimum required tier in the docstring
- **Module docstring:** required — state what the script does, who it's for, the SDK methods used, and the tables loaded
- **No secrets:** no hardcoded tokens, internal URLs, or bucket names
- **`print()` is fine** in examples and `scripts/` (unlike the SDK, which uses `logging`)
- **Use canonical concept names** (`'TotalRevenue'`, `'NetIncome'`) — never raw XBRL tags (`'Revenues'`, `'NetIncomeLoss'`)
- **PIT discipline:** if the example is a backtest, filter by `filing_date <= trade_date`. Use `report_date` only for fiscal calendar alignment.
- **CAPEX:** always `ABS(capex)` — sign varies by filer
- **Quarterly cash flows:** use `COALESCE(derived_quarterly_value, numeric_value)`
- **Cross-company queries:** start from the `references` table (zero joins)

If you add a Python script, **add the matching notebook** in the same PR. The notebook should produce the same output as the script.

---

## Code style

```bash
# Format and lint before opening a PR
uv run ruff check examples/ scripts/ --fix
uv run ruff format examples/ scripts/
```

- Python 3.10+
- Line length: 100
- Docstrings: Google style
- Type hints: encouraged, not required for examples
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`

---

## Pull request process

1. Fork the repo and branch from `main`. Branch names: `feat/short-description`, `fix/short-description`, `docs/short-description`.
2. **One logical change per PR.** A new example + its notebook = one PR. A doc fix unrelated to that example = a separate PR.
3. Run `ruff check` and `ruff format` locally.
4. For new examples: paste a 5–10 line snippet of the script's output in the PR description. We need to see it ran.
5. For doc changes: explain *what was wrong* and *what's right now*. Drift between this repo and the SDK is a real failure mode — call out the source of truth.
6. Open the PR and fill in the [PR template](.github/PULL_REQUEST_TEMPLATE.md).
7. CI will run lint and (where relevant) try to import the example script. Address any failures before requesting review.

---

## What goes here vs. upstream

If your change is conceptually about…

| Concern | Lives in | What this repo does |
|---|---|---|
| SDK internals (`ValueinClient`, transport, alpha factors, SQL templates) | The SDK repo (private) | Mirrors the public surface in examples and docs |
| MCP worker code (tool implementations, auth, R2 access) | The MCP repo (private) | Hosts `server.json` (registry manifest) and `docs/MCP_TOOLS.md` |
| `fact.standard_concept` definitions | The data-pipeline repo (private) | Mirrors the canonical concept list in `scripts/generate_catalog.py` |
| Cloudflare workers (gateway, Stripe webhook) | The infra repo (private) | None — config changes are invisible from the outside |
| Frontend / dashboard | [`frontend`](https://github.com/valuein/frontend) | None |

If you find drift between any of these — for example, the README says one Pro price and the website says another — please open a [Q&A issue](.github/ISSUE_TEMPLATE/04_general_question.yml). Drift is a bug.

---

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you agree to its terms.

---

## License

By contributing, you agree your contributions are licensed under [Apache 2.0](LICENSE).
