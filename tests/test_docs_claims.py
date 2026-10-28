"""Public prose must agree with the machine-readable sources it quotes."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    """Return the text of a repo file."""
    return (ROOT / rel).read_text(encoding="utf-8")


def test_methodology_table_matches_baseline() -> None:
    """The methodology headline table quotes baseline.json's figures exactly."""
    base = json.loads(_read("docs/accuracy/baseline.json"))["standardized_facts"]
    text = _read("docs/accuracy/methodology.md")
    modern = base["by_era"]["modern_2010_onward"]
    for expected in (
        f"{base['overall']['accuracy_pct']:.2f} %",
        f"{modern['accuracy_pct']:.2f} %",
        f"{base['overall']['filings']:,}",
        f"{modern['filings']:,}",
    ):
        assert expected in text, expected


def test_accuracy_pages_do_not_claim_perfect_accuracy() -> None:
    """No accuracy page may state a 100 % headline while the baseline is below it."""
    base = json.loads(_read("docs/accuracy/baseline.json"))["standardized_facts"]
    assert base["overall"]["accuracy_pct"] < 100
    for rel in ("docs/accuracy/README.md", "docs/accuracy/methodology.md", "README.md"):
        assert "**100 %**" not in _read(rel), rel
        assert "0 identity failures" not in _read(rel), rel


def test_readme_data_model_names_every_public_table() -> None:
    """Every table in the public schema appears in the README data model."""
    tables = json.loads(_read("docs/schema.json"))["tables"]
    readme = _read("README.md")
    missing = [name for name in tables if f"`{name}`" not in readme]
    assert not missing, missing


def test_sourcing_claims_admit_licensed_prices() -> None:
    """DDQ and methodology must not say all data comes from EDGAR: prices are licensed."""
    for rel in ("docs/COMPLIANCE_AND_DDQ.md", "docs/METHODOLOGY.md"):
        text = _read(rel)
        assert "100% of the data originates" not in text, rel
        assert "licensed price archive" in text, rel


def test_institutional_tier_is_not_sold_with_redistribution_rights() -> None:
    """plans.ts sets redistribution=false on every tier: redistribution is a Commercial licence."""
    for rel in ("README.md", "SUPPORT.md", "AGENTS.md"):
        text = re.sub(r"<!-- GEN:.*?<!-- /GEN:[^>]*-->", "", _read(rel), flags=re.DOTALL | re.IGNORECASE)
        assert "commercial redistribution" not in text.lower(), rel
        assert "redistribution license +" not in text, rel
