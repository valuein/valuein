"""Pytest configuration for the ``scripts/sync_mcp_manifest.py`` tests.

Puts ``scripts/`` on ``sys.path`` (the repo has no package to install) and
provides the ``repo`` fixture shared by every test module.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import sync_mcp_manifest as sync
from manifest_fixtures import (
    AGENTS_TEXT,
    MCP_TOOLS_TEXT,
    README_TEXT,
    SERVER_JSON_TEXT,
)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Point the script at throwaway copies of every file it writes."""
    server_json = tmp_path / "server.json"
    readme = tmp_path / "README.md"
    mcp_tools = tmp_path / "MCP_TOOLS.md"
    agents = tmp_path / "AGENTS.md"
    server_json.write_text(SERVER_JSON_TEXT)
    readme.write_text(README_TEXT)
    mcp_tools.write_text(MCP_TOOLS_TEXT)
    agents.write_text(AGENTS_TEXT)
    monkeypatch.setattr(sync, "SERVER_JSON", server_json)
    monkeypatch.setattr(sync, "README", readme)
    monkeypatch.setattr(sync, "MCP_TOOLS_DOC", mcp_tools)
    monkeypatch.setattr(sync, "AGENTS_DOC", agents)
    return {"server_json": server_json, "readme": readme, "mcp_tools": mcp_tools, "agents": agents}
