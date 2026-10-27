"""Third-party index trademark notice guard (see CLAUDE.md "Third-party index trademarks")."""

from __future__ import annotations

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
]


def test_readme_has_full_notice() -> None:
    """The README carries the full trademark notice."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Trademarks" in text
    assert FULL in text


@pytest.mark.parametrize("path", ["AGENTS.md", "docs/MCP_TOOLS.md"])
def test_agent_docs_have_full_notice(path: str) -> None:
    """AGENTS.md and MCP_TOOLS.md carry the full notice."""
    assert FULL in (ROOT / path).read_text(encoding="utf-8")


@pytest.mark.parametrize("path", DOCS)
def test_guides_have_short_notice(path: str) -> None:
    """Guides that describe index membership or tiers carry the short form."""
    assert SHORT in (ROOT / path).read_text(encoding="utf-8")
