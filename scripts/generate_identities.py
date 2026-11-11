"""Build ``docs/accuracy/identities.json`` from postgres ``scripts/QA/identities.sql``.

The SQL file is the single source of truth for the accounting identities the QA
engine grades (``accuracy/baseline.json`` ``identity_set`` is the error-severity
subset). Dormant identities (``UPDATE ... SET is_active = FALSE``) are omitted.

Usage:
    uv run python scripts/generate_identities.py [--sql PATH] [--check]

With no ``--sql`` the file is read from ``git -C ~/PycharmProjects/postgres show
origin/main:scripts/QA/identities.sql``. ``--check`` exits 1 if the JSON on disk differs.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "accuracy" / "identities.json"
POSTGRES = Path.home() / "PycharmProjects" / "postgres"
FIELDS = (
    "key",
    "name",
    "statement_type",
    "formula",
    "applies_to",
    "tolerance_mode",
    "tolerance_value",
    "severity",
    "citation",
    "description",
)


def tokenize_rows(values: str) -> list[list[Any]]:
    """Parse the SQL ``VALUES`` tuples (strings, ``::jsonb`` casts, numbers) into row lists."""
    rows: list[list[Any]] = []
    row: list[Any] | None = None
    i, n = 0, len(values)
    while i < n:
        ch = values[i]
        if ch == "-" and values.startswith("--", i):
            i = values.find("\n", i)
            i = n if i < 0 else i
        elif ch == "'":
            j, buf = i + 1, []
            while True:
                if values[j] == "'":
                    if values[j + 1 : j + 2] == "'":
                        buf.append("'")
                        j += 2
                        continue
                    break
                buf.append(values[j])
                j += 1
            if row is not None:
                row.append("".join(buf))
            i = j + 1
        elif ch == "(" and row is None:
            row = []
            i += 1
        elif ch == ")" and row is not None:
            rows.append(row)
            row = None
            i += 1
        elif row is not None and (ch.isdigit() or ch == "."):
            m = re.match(r"[0-9.]+", values[i:])
            assert m is not None
            row.append(float(m.group()))
            i += m.end()
        else:
            i += 1
    return rows


def build(sql: str) -> dict[str, Any]:
    """Return the ``identities.json`` document for the given identities.sql text."""
    start = sql.index("VALUES", sql.index("INSERT INTO accounting_identity"))
    end = sql.index("ON CONFLICT", start)
    inactive: set[str] = set()
    for block in re.findall(r"SET is_active = FALSE\s+WHERE identity_key IN \(([^)]*)\)", sql):
        inactive |= set(re.findall(r"'([^']+)'", block))
    ids = []
    for row in tokenize_rows(sql[start + len("VALUES") : end]):
        if len(row) != len(FIELDS):
            raise ValueError(f"identity row has {len(row)} fields: {row[:1]}")
        item = dict(zip(FIELDS, row, strict=True))
        if item["key"] in inactive:
            continue
        item["formula"] = json.loads(item["formula"])
        item["description"] = " ".join(str(item["description"]).split())
        ids.append(item)
    return {
        "version": "2.0.0",
        "source": "postgres scripts/QA/identities.sql (active identities)",
        "count": len(ids),
        "identities": ids,
    }


def render(doc: dict[str, Any]) -> str:
    """Serialise deterministically."""
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def read_sql(path: str | None) -> str:
    """Read identities.sql from ``path`` or the postgres checkout's origin/main."""
    if path:
        return Path(path).read_text(encoding="utf-8")
    return subprocess.run(
        ["git", "-C", str(POSTGRES), "show", "origin/main:scripts/QA/identities.sql"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sql")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = render(build(read_sql(args.sql)))
    if args.check:
        if OUT.read_text(encoding="utf-8") != text:
            print("identities.json is stale: re-run scripts/generate_identities.py")
            return 1
        return 0
    OUT.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
