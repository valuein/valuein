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


def test_sourcing_claims_are_scoped_to_sec_filings() -> None:
    """DDQ and methodology scope the SEC-sourcing claim to statements, ownership and insiders.

    Prices are a licensed series, so a blanket "all data from EDGAR" claim is false.
    """
    for rel in ("docs/COMPLIANCE_AND_DDQ.md", "docs/METHODOLOGY.md"):
        text = _read(rel)
        assert "100% of the data originates" not in text, rel
        assert "All financial statements, ownership and insider data come from SEC filings" in text, rel
        assert "separately licensed series" in text, rel


def test_institutional_tier_is_not_sold_with_redistribution_rights() -> None:
    """plans.ts sets redistribution=false on every tier: redistribution is a Commercial licence."""
    for rel in ("README.md", "SUPPORT.md", "AGENTS.md", "docs/MCP_TOOLS.md", "docs/WORKSPACE_GUIDE.md"):
        text = re.sub(r"<!-- GEN:.*?<!-- /GEN:[^>]*-->", "", _read(rel), flags=re.DOTALL | re.IGNORECASE)
        assert "commercial redistribution" not in text.lower(), rel
        assert "redistribution license" not in text.lower(), rel
        assert "expanded redistribution" not in text.lower(), rel


def test_generated_mcp_summary_matches_plans() -> None:
    """The README's generated MCP summary sells no redistribution and names no stale universe count.

    plans.ts sets redistribution=false on every tier, and the old "19,000+" universe figure
    predates the full-universe build. Rendering the template (not the README) catches the
    generator itself, so the next manifest sync cannot bring either claim back.
    """
    import sync_mcp_manifest as sync

    rendered = sync.render_summary(
        {"counts": {"tools_live": 1, "tools_stub": 0, "tools": 1, "prompts": 1, "resources": 1}}
    )
    assert "redistribution license" not in rendered
    assert "Enterprise-only, under a Commercial licence" in rendered
    assert "19,000" not in rendered
    assert "S&P 500" not in rendered


def test_no_stale_universe_count_or_form_scope() -> None:
    """Public docs carry neither the stale 19,000+ universe count nor the pre-2026-09-22 6-K exclusion."""
    for rel in (
        "docs/METHODOLOGY.md",
        "docs/COMPLIANCE_AND_DDQ.md",
        "docs/accuracy/README.md",
        "docs/accuracy/methodology.md",
    ):
        assert "19,000" not in _read(rel), rel
    assert "6-K (FPI interims) is not currently in the ingest scope" not in _read("docs/METHODOLOGY.md")


def test_raw_tag_count_agrees_across_docs() -> None:
    """The catalog generator and the methodology quote the same raw-tag count (taxonomy_guide: 11,966)."""
    assert "15,000+" not in _read("scripts/generate_catalog.py")
    assert "15,000+" not in _read("docs/data_catalog.md")
    assert "11,966 unique raw XBRL tags" in _read("docs/METHODOLOGY.md")
