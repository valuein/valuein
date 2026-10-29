"""Public prose must agree with the machine-readable sources it quotes."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

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


#: How each doc says prices are not SEC data (the DDQ names no licence, only the provider type).
PRICE_SCOPE = {
    "docs/COMPLIANCE_AND_DDQ.md": "prices come from a commercial end-of-day market-data provider",
    "docs/METHODOLOGY.md": "separately licensed series",
}


def test_sourcing_claims_are_scoped_to_sec_filings() -> None:
    """DDQ and methodology scope the SEC-sourcing claim to statements, ownership and insiders.

    Prices come from a market-data provider, so a blanket "all data from EDGAR" claim is false.
    """
    for rel, price_scope in PRICE_SCOPE.items():
        text = _read(rel)
        assert "100% of the data originates" not in text, rel
        assert "All financial statements, ownership and insider data come from SEC filings" in text, rel
        assert price_scope in text, rel


#: DDQ sentences the code and the Terms contradict (2026-10-29 accuracy review).
DDQ_RETIRED_CLAIMS = (
    "No web scraping",  # membership reads publicly available constituent lists and fund sponsors' holdings files
    "| **PII** | Not present",  # accounts hold emails and names; filings name insiders
    "99.9%",  # plans.ts: self-serve plans carry no SLA or uptime commitment
    "24/7",  # Institutional support is a 4-hour business-hours target, not an SLA
    "zero-retention tier",  # no zero-data-retention arrangement with any provider
    "Read-only Bearer tokens",  # the same token also writes Workspace state through the MCP
    "millisecond-resolution",  # EDGAR's acceptance time is to the second at best
    "Historical snapshots are never overwritten",  # patch/incremental exports rewrite the live snapshot
    "SLA.md",  # the SLA was retired; service levels live only in an Enterprise Agreement
)


def test_ddq_carries_no_retired_claims() -> None:
    """The DDQ repeats none of the claims the 2026-10-29 review found false."""
    text = _read("docs/COMPLIANCE_AND_DDQ.md")
    found = [claim for claim in DDQ_RETIRED_CLAIMS if claim in text]
    assert not found, found


def test_ddq_membership_answer_is_scoped() -> None:
    """The membership answer names categories of public information, never a website, and never calls membership
    exact, SEC-only or 1993-deep (founder, 2026-10-29)."""
    text = _read("docs/COMPLIANCE_AND_DDQ.md")
    section = text.split("- **Index membership:**", 1)[1].split("- **Transformations:**", 1)[0]
    assert "publicly available constituent lists, public reports of index changes" in section
    assert "does not fetch data from any index provider's website" in section
    for banned in ("exact", "SEC-only", "1993", "scrape-free"):
        assert banned not in section, banned
    assert not re.search(r"https?://|www\.|\b[\w-]+\.(org|com|net|io)\b", section), "the answer names a website"


@pytest.mark.parametrize("rel", ["README.md", "docs/schema.json"])
def test_the_russell_grading_is_not_published(rel: str) -> None:
    """How the Russell rows are graded against an index provider's own lists stays internal (founder, 2026-10-29)."""
    assert "reconstitution list" not in _read(rel).lower()


LICENCE_DOCS = (
    "README.md",
    "SUPPORT.md",
    "AGENTS.md",
    "docs/MCP_TOOLS.md",
    "docs/WORKSPACE_GUIDE.md",
    ".github/ISSUE_TEMPLATE/config.yml",
)
RETIRED_LICENCE_NAMES = re.compile(
    r"commercial licen[cs]e|commercial agreement|enterprise-only", re.IGNORECASE
)


def test_institutional_tier_is_not_sold_with_redistribution_rights() -> None:
    """plans.ts sets redistribution=false on every plan: redistribution is a Redistribution Licence.

    Founder decision 2026-10-28: no plan includes redistribution, resale or white-label,
    Enterprise included; data vendors sign a separate Redistribution Licence.
    """
    for rel in LICENCE_DOCS:
        text = re.sub(
            r"<!-- GEN:.*?<!-- /GEN:[^>]*-->", "", _read(rel), flags=re.DOTALL | re.IGNORECASE
        )
        assert "commercial redistribution" not in text.lower(), rel
        assert "redistribution license" not in text.lower(), rel
        assert "expanded redistribution" not in text.lower(), rel
        assert "commercial licen" not in text.lower(), rel


def test_retired_licence_names_are_gone() -> None:
    """The retired names ("Commercial licence", "Enterprise-only") are gone, GEN blocks included.

    Founder decision 2026-10-28.
    """
    for rel in LICENCE_DOCS:
        match = RETIRED_LICENCE_NAMES.search(_read(rel))
        assert match is None, f"{rel}: {match.group(0) if match else ''}"


def test_enterprise_rows_name_the_redistribution_licence_as_separate() -> None:
    """Enterprise is the team tier; redistribution is a separate licence no plan includes."""
    readme = _read("README.md")
    enterprise = next(ln for ln in readme.splitlines() if ln.startswith("| **Enterprise** |"))
    assert "Enterprise Agreement" in enterprise
    assert "redistribution" not in enterprise.lower()
    assert "separate **Redistribution Licence**" in readme
    tools = _read("docs/MCP_TOOLS.md")
    row = next(ln for ln in tools.splitlines() if ln.startswith("| Enterprise |"))
    assert "redistribution, resale and white-label: separate Redistribution Licence" in row
    guide = _read("docs/WORKSPACE_GUIDE.md")
    label = "| **Redistribution · resale · white-label** |"
    row = next(ln for ln in guide.splitlines() if ln.startswith(label))
    assert row.rstrip(" |").endswith("— (separate Redistribution Licence)")


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
    assert RETIRED_LICENCE_NAMES.search(rendered) is None
    assert "single-seat internal use" in rendered
    assert "separate Redistribution Licence, which no plan includes" in rendered
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


def test_sql_blocks_do_not_name_a_cte_with_a_duckdb_keyword() -> None:
    """`asof` is a DuckDB join keyword: `FROM asof JOIN ...` is a parser error for readers."""
    pattern = re.compile(r"\b(?:WITH|FROM|JOIN)\s+asof\b", re.IGNORECASE)
    for rel in ("README.md", "AGENTS.md", "docs/QUERY_COOKBOOK.md", "docs/METHODOLOGY.md", "docs/SDK_USE_CASES.md"):
        assert not pattern.search(_read(rel)), rel


def test_duckdb_dot_commands_are_separate_c_arguments() -> None:
    """The DuckDB CLI rejects `.read` after a `;` inside one -c string (parser error)."""
    bad = re.compile(r";\s*\.read\b")
    for rel in ("README.md", "docs/accuracy/README.md", "docs/accuracy/methodology.md", "scripts/accuracy/accuracy_check.sql"):
        assert not bad.search(_read(rel)), rel
    assert "sample/$t.parquet" not in _read("docs/accuracy/methodology.md")


#: Membership claims the measured history contradicts (fewer members before ~2007, under half high confidence).
MEMBERSHIP_RETIRED_CLAIMS = {
    "README.md": "SP500 is survivorship-free back to 1996",
    "docs/WORKSPACE_GUIDE.md": "exact index/sector membership",
    "examples/notebooks/03_survivorship_free_screening.ipynb": "exactly as it stood",
}


@pytest.mark.parametrize(("rel", "claim"), sorted(MEMBERSHIP_RETIRED_CLAIMS.items()))
def test_membership_copy_is_not_exact(rel: str, claim: str) -> None:
    """No public doc calls the reconstructed membership history exact or wholly high confidence."""
    assert claim not in _read(rel), rel
