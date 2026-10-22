"""The workflows wire the self-healing sync the way the script assumes.

A merge to ``main`` that changes the generator or a generated file must start
``sync-mcp-manifest.yml`` (the bot regenerates on that push), runs of it must
queue rather than race on the push to ``main``, and ``doc-integrity.yml`` must
hand the change's base to ``--check`` (and leave ``main`` pushes to the sync).
Plain-text assertions: the repo ships no YAML parser, and these lines are the
contract.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
SYNC = (WORKFLOWS / "sync-mcp-manifest.yml").read_text()
INTEGRITY = (WORKFLOWS / "doc-integrity.yml").read_text()

OWNED = (
    "scripts/sync_mcp_manifest.py",
    "server.json",
    "README.md",
    "docs/MCP_TOOLS.md",
    "AGENTS.md",
)


def _push_block(text: str) -> str:
    match = re.search(r"^  push:\n((?:    .*\n|\s*\n)+)", text, re.MULTILINE)
    assert match, "no `push:` trigger"
    return match.group(1)


def test_a_push_to_main_touching_the_generator_or_its_output_runs_the_sync() -> None:
    block = _push_block(SYNC)
    assert re.search(r"branches:\s*\[\s*main\s*\]", block)
    for path in OWNED:
        assert f"'{path}'" in block or f'"{path}"' in block or f"- {path}" in block, path


def test_sync_runs_queue_instead_of_racing() -> None:
    assert re.search(
        r"^concurrency:\n\s+group: sync-mcp-manifest\n\s+cancel-in-progress: false",
        SYNC,
        re.MULTILINE,
    )


def test_the_sync_regenerates_on_a_rejected_push_instead_of_failing() -> None:
    assert "git reset --hard origin/main" in SYNC


def test_doc_integrity_checks_against_the_change_s_base() -> None:
    assert "sync_mcp_manifest.py --check --base" in INTEGRITY
    assert "fetch-depth: 0" in INTEGRITY


def test_doc_integrity_leaves_main_pushes_to_the_sync() -> None:
    assert "github.ref != 'refs/heads/main'" in INTEGRITY
