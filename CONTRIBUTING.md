# Contributing to Valuein SDK

Valuein is a commercial SDK but we welcome contributions to examples, research scripts, documentation, and bug fixes.

## Getting Started

```bash
# 1. Fork and clone the repo
git clone https://github.com/valuein/quants.git
cd quants

# 2. Install dependencies
uv sync --group dev

# 3. Create .env with your API key
echo "VALUEIN_API_KEY=your_key_here" > .env

# 4. Verify setup (no API key needed for unit tests)
uv run pytest -k "not integration"
```

## What You Can Contribute

| Type | Where | Notes |
|---|---|---|
| Bug reports | GitHub Issues | Include reproduction steps and SDK version |
| New examples | `examples/python/` | Follow naming convention, see rules below |
| New research | `research/` | Appropriate subdirectory, proves something specific |
| Documentation | `docs/` | Fix typos, improve clarity, add missing content |
| SDK improvements | Open an issue first | Discuss approach before implementing |

## Examples Contribution Rules

- **Filename**: `snake_case.py`, no numeric prefix
- **Docstring**: Required. State what the script does, who it's for, tables loaded.
- **Import**: `from valuein_sdk import ValueinClient` at top
- **Tables**: Use `tables=` param — only load what you need
- **Standalone**: Must run with `VALUEIN_API_KEY=xxx python examples/filename.py`
- **Length**: Keep under 150 lines. One concept per file.
- **No secrets**: No hardcoded API keys, bucket names, or internal URLs

## Research Contribution Rules

- Place in the correct subdirectory: `fundamental/`, `quantitative/`, `data_engineering/`, `quality_proof/`
- Docstring must state: what it proves, who it's for, which tables it loads
- Must use the SDK correctly — no direct HTTP calls or DuckDB hacks
- `quality_proof/` scripts must have a clear pass/fail output

## Code Standards

```bash
# Format and lint (required before PR)
uv run ruff check . --fix
uv run ruff format .

# Type checking (required for SDK code in valuein_sdk/)
uv run mypy --strict valuein_sdk/

# Tests
uv run pytest -k "not integration"           # No API key needed
VALUEIN_API_KEY=xxx uv run pytest -m integration  # Full suite with live API
```

- Python 3.10+
- Line length: 100
- Docstrings: Google style
- Type hints: required on all public functions in `valuein_sdk/`
- `print()` is fine in `examples/` and `research/`. Use `logging` in `valuein_sdk/`.
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`

## Pull Request Process

1. Branch from `main`
2. One logical change per PR
3. CI must pass: `uv run ruff check` → `uv run ruff format --check` → `uv run pytest -k "not integration"`
4. For examples: include sample output in the PR description
5. For research: state what the script proves and show a snippet of results

## Verify Before Submitting

```bash
# Syntax check
python -c "import ast; ast.parse(open('your_file.py').read())"

# No old package name
grep -r "valuein_sec_sdk" examples/ research/ && echo "FAIL: old package name found"

# No old env var
grep -r "VALUEIN_API_TOKEN" examples/ research/ && echo "FAIL: old env var found"

# Lint passes
uv run ruff check examples/ research/ --fix
uv run ruff format examples/ research/
```

## Code of Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/) Code of Conduct.

## License

By contributing, you agree your contributions are licensed under [Apache 2.0](LICENSE).
