"""Shared manifests, fixture texts and helpers for the ``sync_mcp_manifest`` tests.

Imported by both test modules; the ``repo`` fixture that redirects the script's
files lives in ``conftest.py``. Nothing here touches the network.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import sync_mcp_manifest as sync

HIDDEN = ("purchase_report", "list_my_purchases", "connect_stripe_account")

SERVER_JSON_TEXT = """{
  "name": "io.github.valuein/mcp-sec-edgar",
  "version": "1.0.0",
  "tools_summary": {
    "live": 1,
    "stubs": 0,
    "prompts": 1,
    "resources": 1
  }
}
"""

README_TEXT = "# Hub\n\n<!-- GEN:mcp-summary -->\nstale\n<!-- /GEN:mcp-summary -->\n"

MCP_TOOLS_TEXT = (
    "# Tools\n\n<!-- GEN:agent-contract -->\n<!-- /GEN:agent-contract -->\n\n"
    "<!-- GEN:mcp-tool-reference -->\n<!-- /GEN:mcp-tool-reference -->\n\n"
    "<!-- GEN:mcp-prompts -->\n<!-- /GEN:mcp-prompts -->\n\n"
    "<!-- GEN:mcp-resources -->\n<!-- /GEN:mcp-resources -->\n"
)

AGENTS_TEXT = "# Agents\n\n<!-- GEN:agent-contract -->\n<!-- /GEN:agent-contract -->\n"

CONTRACT_MARKDOWN = (
    "## Reading tool results: errors and paging\n\n"
    "A tool error is a result with `isError: true`. It carries **no `structuredContent`**.\n"
)


def contract_tool(name: str, status: str = "live", min_plan: str = "sample") -> dict[str, Any]:
    """Return a tool entry carrying every agent-contract field the docs need."""
    return {
        "name": name,
        "title": name.replace("_", " ").title(),
        "description": f"Summary of {name}.",
        "status": status,
        "min_plan": min_plan,
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
        "inputs": [
            {"name": "ticker", "type": "string", "required": True, "description": "A ticker."}
        ],
        "output_fields": ["ticker", "data"],
        "paging": None,
    }


def clean_manifest() -> dict[str, Any]:
    """Return a small, valid manifest with no hidden tools."""
    return {
        "version": "2.0.0",
        "counts": {"tools": 2, "tools_live": 2, "tools_stub": 0, "prompts": 3, "resources": 3},
        "agent_contract": {"version": 1, "markdown": CONTRACT_MARKDOWN},
        "tools": [
            contract_tool("search_companies"),
            contract_tool("get_company_fundamentals"),
        ],
        "prompts": [
            {
                "name": "equity_research_brief",
                "title": "Brief",
                "description": "A brief.",
                "min_plan": "sample",
            }
        ],
        "resources": [
            {"name": "schema", "title": "Schema", "description": "Columns.", "min_plan": "sample"}
        ],
    }


def with_tool(manifest: dict[str, Any], name: str, status: str = "live") -> dict[str, Any]:
    """Return a copy of ``manifest`` with one more tool, keeping counts consistent if live."""
    out = copy.deepcopy(manifest)
    out["tools"].append(contract_tool(name, status, "pro"))
    out["counts"]["tools"] += 1
    if status == "live":
        out["counts"]["tools_live"] += 1
    elif status == "stub":
        out["counts"]["tools_stub"] += 1
    return out


def assert_untouched(repo: dict[str, Path]) -> None:
    """Assert the docs files still hold their fixture text (nothing was written)."""
    assert repo["readme"].read_text() == README_TEXT
    assert repo["mcp_tools"].read_text() == MCP_TOOLS_TEXT
    assert repo["agents"].read_text() == AGENTS_TEXT


def run_main(monkeypatch: pytest.MonkeyPatch, manifest: Any, argv: list[str]) -> int:
    """Run ``main`` against an in-memory manifest instead of the network."""
    monkeypatch.setattr(sync, "load_manifest", lambda: manifest)
    return sync.main(argv)
