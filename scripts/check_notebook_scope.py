#!/usr/bin/env python3
"""Scope, hygiene and refresh helper for the playbook notebooks.

``examples/playbooks/*.ipynb`` are committed with outputs. Each one declares who it is for in
``metadata.valuein.plan`` (``benchmark`` = a free Benchmark reader can reproduce every cell,
``institutional`` = it needs the Institutional plan) and when its outputs were produced in
``metadata.valuein.executed_at``. This script is the gate that keeps those promises:

(a) every notebook has a valid ``plan`` and an ``executed_at`` timestamp;
(b) a ``benchmark`` notebook's code cells never name Institutional/Pro-only data (tables, SDK
    methods, MCP tools, filing families such as 13F or Form ADV);
(c) every ticker / CIK literal a ``benchmark`` notebook passes to a lookup is a current or former
    S&P 500 member, judged with ``index_membership`` on the FREE sample (no key is ever used);
(d) no output carries a local path, an API key assignment or a bearer token.

Modes (combine freely)::

    check_notebook_scope.py [PATH ...]            # check, exit 0 clean / 1 findings
    check_notebook_scope.py --scrub [PATH ...]    # redact paths and keys in outputs, in place
    check_notebook_scope.py --stamp [PATH ...]    # set metadata.valuein.executed_at to now (UTC)

With no PATH it reads ``examples/playbooks/*.ipynb``. ``--scrub`` and ``--stamp`` run before the
check. Only the standard library is imported at module load; ``valuein_sdk`` is imported lazily
for check (c) and is never given a key.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PLAYBOOK_GLOB = "examples/playbooks/*.ipynb"
PLANS = frozenset({"benchmark", "institutional"})

# Tables a free Benchmark reader cannot read. Source: ``docs/schema.json`` in this repo: every
# table whose description says "Institutional (full) tier only" or "FULL bucket only" (insider
# Forms 3/4/5/144, SC 13D/13G, 13F, Form ADV), plus the daily price table (named ``price_daily``
# in ``docs/schema.json``, ``stock_price_daily`` in the warehouse), which is Pro and above.
# ``tests/test_check_notebook_scope.py`` fails when the schema grows a full-tier table that is
# missing here.
RESTRICTED_TABLES: tuple[str, ...] = (
    "insider_party",
    "insider_filing",
    "insider_transaction",
    "insider_ownership",
    "insider_footnote",
    "insider_ownership_purpose",
    "institutional_filing",
    "institutional_holding",
    "institutional_other_manager",
    "investment_adviser",
    "investment_adviser_private_fund",
    "price_daily",
    "stock_price_daily",
)

# Institutional/Pro-only SDK methods (``valuein_sdk.ValueinClient``) and MCP tools (tier column
# in ``docs/MCP_TOOLS.md``; ``get_price_history`` is a price tool and is kept out of free-reader
# notebooks too, see CLAUDE.md "Data primer"). The test checks each MCP name appears in that file.
RESTRICTED_METHODS: tuple[str, ...] = (
    "insider_transactions",
    "institutional_holdings",
    "advisers",
    "adviser_private_funds",
    "get_insider_transactions",
    "get_insider_sentiment",
    "get_institutional_holdings",
    "get_manager_portfolio",
    "get_smart_money_flow",
    "get_ownership_pack",
    "get_blockholders",
    "get_price_history",
)

# Filing families that live only in the restricted tables.
RESTRICTED_TERMS: tuple[str, ...] = (r"13F(?:-HR|-NT)?", r"13D", r"13G", r"Form\s+ADV", r"Form\s+4")

_RESTRICTED_RE = re.compile(
    r"(?<![A-Za-z0-9_])("
    + "|".join(
        [re.escape(t) for t in (*RESTRICTED_TABLES, *RESTRICTED_METHODS)] + list(RESTRICTED_TERMS)
    )
    + r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

# Calls whose first positional argument is a ticker or CIK, and keyword names that carry one.
IDENTIFIER_METHODS = frozenset(
    {"resolve", "search", "financials", "filing_links", "dcf", "price_multiples", "restatements"}
)
IDENTIFIER_KWARGS = frozenset({"ticker", "tickers", "cik", "ciks", "symbol"})

_PATH_RE = re.compile(r"(?:/home|/mnt|/Users)/[^\s\"'\\)\]>,;]*")
_KEY_ASSIGN_RE = re.compile(r"VALUEIN_API_KEY\s*=\s*[^\s\"'\\]*")
_BEARER_RE = re.compile(r"Bearer\s+(?!YOUR_|<)[A-Za-z0-9._~+/=\-]{16,}")
_KEY_LIKE_RE = re.compile(r"\b(?:vi|sk|pk)_[A-Za-z0-9]{20,}\b")
_FORBIDDEN_OUTPUT: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("local path", re.compile(r"/home/|/mnt/|/Users/")),
    ("API key assignment", re.compile(r"VALUEIN_API_KEY=(?!<redacted>)")),
    ("bearer token", _BEARER_RE),
    ("API key", _KEY_LIKE_RE),
)

MembershipFn = Callable[[str], bool]


@dataclass(frozen=True)
class Finding:
    """One problem in one notebook, with the cell it was found in (``None`` = notebook level)."""

    notebook: str
    cell: int | None
    message: str

    def __str__(self) -> str:
        """Render as ``notebook[cell N]: message``."""
        where = self.notebook if self.cell is None else f"{self.notebook} cell {self.cell}"
        return f"{where}: {self.message}"


def cell_source(cell: dict[str, Any]) -> str:
    """Return a cell's source as one string (nbformat stores a string or a list of lines)."""
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else str(source)


def _code_for_ast(source: str) -> str:
    """Blank IPython magics and shell escapes so the cell parses as plain Python."""
    return "\n".join(
        "" if line.lstrip().startswith(("%", "!")) else line for line in source.splitlines()
    )


def _literal_strings(node: ast.AST, names: dict[str, list[str]]) -> list[str]:
    """Strings an argument expression evaluates to: literals, lists of them, or a known name."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, int)) and not isinstance(node.value, bool):
            return [str(node.value)]
        return []
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [s for element in node.elts for s in _literal_strings(element, names)]
    if isinstance(node, ast.Name):
        return list(names.get(node.id, []))
    return []


def _module_constants(trees: Iterable[ast.AST]) -> dict[str, list[str]]:
    """Collect ``NAME = "literal"`` assignments (``TICKER = "KO"``) across a notebook."""
    names: dict[str, list[str]] = {}
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    values = _literal_strings(node.value, {})
                    if values:
                        names[target.id] = values
    return names


def identifier_literals(notebook: dict[str, Any]) -> list[tuple[int, str]]:
    """Return ``(cell index, identifier)`` for every ticker/CIK literal passed to a lookup.

    Covers the first argument of ``resolve``/``search``/``financials``/... , the keyword
    arguments ``ticker=``/``tickers=``/``cik=``, and ``"ticker"``/``"cik"`` keys of dict
    literals (MCP tool arguments). A name bound to a literal (``TICKER = "KO"``) is followed.
    """
    parsed: list[tuple[int, ast.AST]] = []
    for index, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        try:
            parsed.append((index, ast.parse(_code_for_ast(cell_source(cell)))))
        except SyntaxError:
            continue
    names = _module_constants(tree for _, tree in parsed)
    found: list[tuple[int, str]] = []
    for index, tree in parsed:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                method = (
                    node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else getattr(node.func, "id", "")
                )
                if method in IDENTIFIER_METHODS and node.args:
                    found += [(index, s) for s in _literal_strings(node.args[0], names)]
                for keyword in node.keywords:
                    if keyword.arg in IDENTIFIER_KWARGS:
                        found += [(index, s) for s in _literal_strings(keyword.value, names)]
            elif isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if (
                        isinstance(key, ast.Constant)
                        and key.value in IDENTIFIER_KWARGS
                        and value is not None
                    ):
                        found += [(index, s) for s in _literal_strings(value, names)]
    return found


def _normalise(identifier: str) -> str:
    """Zero-pad a bare CIK to 10 digits; leave a ticker alone (upper-cased)."""
    text = identifier.strip()
    return text.zfill(10) if text.isdigit() else text.upper()


def sample_sp500_membership() -> MembershipFn:
    """Build a membership test from the free sample (never reads ``VALUEIN_API_KEY``).

    Returns a function ``identifier -> bool``: ``True`` when the ticker or CIK resolves on the
    sample and its CIK has any ``index_membership`` row for ``SP500`` (current or former
    member), ``False`` when it is unknown or never a member.
    """
    from valuein_sdk import ValueinClient  # lazy: tests inject their own function

    client = ValueinClient(api_key="")
    table = client.read_table("index_membership", columns=["cik", "index_name"])
    members = set(table.loc[table["index_name"] == "SP500", "cik"].astype(str))

    def is_member(identifier: str) -> bool:
        """Resolve on the sample, then look the CIK up in the SP500 member set."""
        try:
            resolved = client.resolve([identifier])
        except Exception:  # noqa: BLE001  unknown or outside the sample: not provably a member
            return False
        return str(resolved.iloc[0]["cik"]) in members

    return is_member


_MEMBERSHIP_CACHE: list[MembershipFn] = []


def _lazy_membership() -> MembershipFn:
    """Return a membership test that loads the sample once, on first use, for the whole run."""

    def is_member(identifier: str) -> bool:
        """Build the sample-backed test on first call and reuse it."""
        if not _MEMBERSHIP_CACHE:
            _MEMBERSHIP_CACHE.append(sample_sp500_membership())
        return _MEMBERSHIP_CACHE[0](identifier)

    return is_member


def _strings(value: Any, key: str = "") -> Iterator[str]:
    """Yield every string leaf of an output structure, skipping binary image payloads."""
    if isinstance(value, str):
        if not key.startswith("image/"):
            yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item, key)
    elif isinstance(value, dict):
        for child_key, child in value.items():
            yield from _strings(child, str(child_key))


def check_notebook(
    path: Path, membership: MembershipFn | None = None, secret: str = ""
) -> list[Finding]:
    """Run checks (a) to (d) on one notebook and return its findings.

    Args:
        path: the ``.ipynb`` file.
        membership: ``identifier -> bool`` for check (c); ``None`` loads the free sample lazily,
            and only when the notebook has identifier literals to judge.
        secret: the real API key value, if any; it must not appear in any output.
    """
    name = path.name
    findings: list[Finding] = []
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
        cells = notebook["cells"]
    except (OSError, ValueError, KeyError) as exc:
        return [Finding(name, None, f"not a readable notebook ({exc.__class__.__name__}: {exc})")]
    meta = (notebook.get("metadata") or {}).get("valuein") or {}
    plan = meta.get("plan")
    if plan not in PLANS:
        findings.append(
            Finding(
                name, None, f"metadata.valuein.plan must be one of {sorted(PLANS)}, got {plan!r}"
            )
        )
    if not meta.get("executed_at"):
        findings.append(Finding(name, None, "metadata.valuein.executed_at is missing"))

    if plan == "benchmark":
        for index, cell in enumerate(cells):
            if cell.get("cell_type") != "code":
                continue
            hits = sorted({m.group(1).lower() for m in _RESTRICTED_RE.finditer(cell_source(cell))})
            for hit in hits:
                findings.append(
                    Finding(
                        name,
                        index,
                        f"plan=benchmark but the code uses Institutional/Pro-only {hit!r}",
                    )
                )
        literals = identifier_literals(notebook)
        if literals:
            is_member = membership or _lazy_membership()
            for index, identifier in literals:
                try:
                    member = is_member(_normalise(identifier))
                except Exception as exc:  # noqa: BLE001  cannot judge: fail closed, never skip
                    findings.append(Finding(name, None, f"cannot load sample membership: {exc}"))
                    break
                if not member:
                    findings.append(
                        Finding(
                            name,
                            index,
                            f"{identifier!r} is not a current or former S&P 500 member "
                            "(or does not resolve on the free sample)",
                        )
                    )

    for index, cell in enumerate(cells):
        if cell.get("cell_type") != "code":
            continue
        for text in _strings(cell.get("outputs", [])):
            for label, pattern in _FORBIDDEN_OUTPUT:
                if pattern.search(text):
                    findings.append(Finding(name, index, f"output contains a {label}"))
            if secret and secret in text:
                findings.append(Finding(name, index, "output contains the API key value"))
    return findings


def scrub_text(text: str, secret: str = "") -> str:
    """Redact local paths, key assignments, bearer tokens and the real key from one string."""
    if secret:
        text = text.replace(secret, "<redacted>")
    text = _PATH_RE.sub("<path>", text)
    text = _KEY_ASSIGN_RE.sub("VALUEIN_API_KEY=<redacted>", text)
    text = _BEARER_RE.sub("Bearer <redacted>", text)
    return _KEY_LIKE_RE.sub("<redacted>", text)


def _scrub_value(value: Any, secret: str, key: str = "") -> Any:
    """Return ``value`` with every non-image string leaf scrubbed."""
    if isinstance(value, str):
        return value if key.startswith("image/") else scrub_text(value, secret)
    if isinstance(value, list):
        return [_scrub_value(item, secret, key) for item in value]
    if isinstance(value, dict):
        return {k: _scrub_value(v, secret, str(k)) for k, v in value.items()}
    return value


def _write(path: Path, notebook: dict[str, Any]) -> None:
    """Write a notebook the way nbformat does (indent 1, ASCII-escaped, trailing newline)."""
    path.write_text(json.dumps(notebook, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


def scrub_notebook(path: Path, secret: str = "") -> bool:
    """Scrub every code cell's outputs in place; return whether the file changed."""
    notebook = json.loads(path.read_text(encoding="utf-8"))
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = _scrub_value(cell.get("outputs", []), secret)
    before = path.read_text(encoding="utf-8")
    _write(path, notebook)
    return path.read_text(encoding="utf-8") != before


def stamp_notebook(path: Path, now: datetime | None = None) -> None:
    """Set ``metadata.valuein.executed_at`` to ``now`` (UTC, second precision)."""
    stamp = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    notebook = json.loads(path.read_text(encoding="utf-8"))
    notebook.setdefault("metadata", {}).setdefault("valuein", {})["executed_at"] = stamp
    _write(path, notebook)


def notebook_paths(args: Sequence[str]) -> list[Path]:
    """Expand explicit paths, or the default playbook glob under the repo root."""
    if args:
        return [Path(a) for a in args]
    return sorted(ROOT.glob(PLAYBOOK_GLOB))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; returns the process exit code (0 clean, 1 findings or no notebooks)."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("paths", nargs="*", help="notebooks (default: examples/playbooks/*.ipynb)")
    parser.add_argument("--scrub", action="store_true", help="redact paths/keys in outputs first")
    parser.add_argument("--stamp", action="store_true", help="set executed_at to now (UTC) first")
    options = parser.parse_args(argv)

    paths = notebook_paths(options.paths)
    if not paths:
        print("no notebooks found", file=sys.stderr)
        return 1
    secret = os.environ.get("VALUEIN_API_KEY", "")
    for path in paths:
        if options.stamp:
            stamp_notebook(path)
        if options.scrub and scrub_notebook(path, secret):
            print(f"scrubbed {path.name}")

    findings: list[Finding] = []
    for path in paths:
        findings += check_notebook(path, _lazy_membership(), secret)
    for finding in findings:
        print(f"FAIL {finding}")
    print(f"{len(paths)} notebook(s) checked, {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
