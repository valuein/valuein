"""identities.json is generated from postgres identities.sql and matches the graded set."""

from __future__ import annotations

import json
from pathlib import Path

import generate_identities as gen

ROOT = Path(__file__).resolve().parent.parent
SQL = """
INSERT INTO accounting_identity (identity_key) VALUES
-- comment, with (parens) 'quote'
('a_01_x', 'It''s A = B', 'balance_sheet',
 '{"lhs":[{"concept":"A","weight":1}],"rhs":[{"concept":"B","weight":1}]}'::jsonb,
 'all', 'percent', 0.005, 'error', 'cite', 'desc  one'),
('a_02_y', 'dormant', 'cross_statement', '{"operator":"q"}'::jsonb,
 'FY', 'absolute', 0.0, 'warning', 'c', 'd')
ON CONFLICT (identity_key) DO UPDATE SET x = 1;
UPDATE accounting_identity SET is_active = FALSE
WHERE identity_key IN ('a_02_y');
"""


def test_build_parses_rows_and_drops_dormant() -> None:
    """Quotes, comments and casts parse; inactive identities are omitted."""
    doc = gen.build(SQL)
    assert doc["count"] == 1
    item = doc["identities"][0]
    assert item["key"] == "a_01_x" and item["name"] == "It's A = B"
    assert item["tolerance_value"] == 0.005 and item["description"] == "desc one"
    assert item["formula"]["lhs"][0]["concept"] == "A"


def test_published_identities_match_baseline_identity_set() -> None:
    """Every error identity in identities.json is exactly the set baseline.json graded."""
    pub = json.loads((ROOT / "docs/accuracy/identities.json").read_text(encoding="utf-8"))
    assert pub["count"] == len(pub["identities"])
    base = json.loads((ROOT / "docs/accuracy/baseline.json").read_text(encoding="utf-8"))
    graded = {
        i["identity_key"]: (i["tolerance_mode"], i["tolerance_value"])
        for i in base["identity_set"]["identities"]
    }
    errors = {
        i["key"]: (i["tolerance_mode"], i["tolerance_value"])
        for i in pub["identities"]
        if i["severity"] == "error"
    }
    assert errors == graded
