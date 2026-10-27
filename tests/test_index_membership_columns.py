"""index_membership has no announcement-date columns (dropped 2026-10-27, founder decision)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GONE = ("announcement_date", "removal_announcement_date")


def test_public_schema_has_no_announcement_columns() -> None:
    """The public schema lists the effective/removal dates and no announcement column."""
    schema = json.loads((ROOT / "docs" / "schema.json").read_text(encoding="utf-8"))
    cols = schema["tables"]["index_membership"]["columns"]
    assert {"effective_date", "removal_date"} <= set(cols)
    for name in GONE:
        assert name not in cols


def test_cookbook_does_not_advertise_announcement_dates() -> None:
    """The query cookbook no longer points readers at the dropped columns."""
    text = (ROOT / "docs" / "QUERY_COOKBOOK.md").read_text(encoding="utf-8")
    for name in GONE:
        assert name not in text
