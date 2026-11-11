"""Third-party index trademark notice guard (see CLAUDE.md "Third-party index trademarks")."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FULL = "not affiliated with, sponsored, endorsed or licensed by any index provider"
SHORT = "not affiliated with or endorsed by any index provider"
DOCS = [
    "docs/WORKSPACE_GUIDE.md",
    "docs/QUERY_COOKBOOK.md",
    "docs/METHODOLOGY.md",
    "docs/SDK_USE_CASES.md",
    "docs/COMPLIANCE_AND_DDQ.md",
    "docs/accuracy/README.md",
    "docs/accuracy/methodology.md",
    "examples/README.md",
]


@pytest.mark.parametrize("path", ["README.md", "AGENTS.md", "docs/MCP_TOOLS.md"])
def test_top_level_docs_have_the_canonical_notice(path: str) -> None:
    """README, AGENTS.md and MCP_TOOLS.md carry the canonical notice, not the retired long form (founder 2026-11-09)."""
    text = (ROOT / path).read_text(encoding="utf-8")
    assert SHORT in text
    assert FULL not in text
    assert "registered trademark" not in text


def test_readme_keeps_its_trademarks_heading() -> None:
    """The README keeps a Trademarks section for the notice."""
    assert "## Trademarks" in (ROOT / "README.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("path", DOCS)
def test_guides_have_short_notice(path: str) -> None:
    """Guides that describe index membership or tiers carry the short form."""
    assert SHORT in (ROOT / path).read_text(encoding="utf-8")


PAGES = ["README.md", "AGENTS.md", "docs/MCP_TOOLS.md", *DOCS]
INDEX_NAME = re.compile(r"S&P 500|Russell|Nasdaq-100")


@pytest.mark.parametrize("path", PAGES)
def test_notice_appears_at_most_once_per_page(path: str) -> None:
    """A page carries the non-affiliation notice once, never repeated (founder 2026-11-02)."""
    text = (ROOT / path).read_text(encoding="utf-8")
    assert len(re.findall(r"not affiliated with", text)) == 1


def test_server_listing_title_names_no_index() -> None:
    """The registry listing title and description-level name carry no index name."""
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    assert not INDEX_NAME.search(server["title"])
    assert not INDEX_NAME.search(server["name"])


@pytest.mark.parametrize("path", ["README.md", "AGENTS.md", "docs/MCP_TOOLS.md", "docs/WORKSPACE_GUIDE.md"])
def test_plan_names_carry_no_index_name(path: str) -> None:
    """Plan and tier names are never branded with an index name: the free tier is Benchmark."""
    text = (ROOT / path).read_text(encoding="utf-8")
    assert not re.search(r"\*\*(S&P 500|Russell|Nasdaq-100)[^*]*\*\*\s*\|", text)
    assert not re.search(r"(S&P 500|Russell|Nasdaq-100)\s+(tier|plan)\b", text, re.IGNORECASE)


def test_sources_name_no_list_website_or_provider_comparison() -> None:
    """Sources stay generic for lists and never describe a check against a provider's own lists."""
    for path in PAGES:
        text = (ROOT / path).read_text(encoding="utf-8").lower()
        assert "sponsors publish" not in text, path
        assert "against the index provider" not in text, path
