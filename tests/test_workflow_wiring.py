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


PUBLISH = (WORKFLOWS / "publish-mcp.yml").read_text()
SERVER_JSON = Path(__file__).resolve().parent.parent / "server.json"


def test_the_registry_name_is_the_valuein_biz_domain_namespace() -> None:
    """``biz.valuein/*`` is granted only to whoever proves valuein.biz (DNS TXT).

    ``io.github.valuein/*`` is the retired GitHub namespace: publishing a new
    version under it would revive the deprecated listing.
    """
    import json

    name = json.loads(SERVER_JSON.read_text())["name"]
    assert name == "biz.valuein/mcp"
    meta_keys = json.loads(SERVER_JSON.read_text())["_meta"].keys()
    assert all(key.startswith("biz.valuein/") for key in meta_keys), sorted(meta_keys)


def test_publish_logs_in_with_the_dns_key_before_publishing() -> None:
    login = PUBLISH.index("mcp-publisher login dns")
    publish = PUBLISH.index("mcp-publisher publish")
    assert login < publish
    assert "secrets.MCP_REGISTRY_PRIVATE_KEY" in PUBLISH
    # The GitHub login exists only to deprecate the retired name, after the
    # new one is published and verified.
    assert PUBLISH.index("mcp-publisher login github-oidc") > PUBLISH.index("check_registry_sync.py")


def test_the_retired_name_is_deprecated_never_deleted() -> None:
    assert "--status deprecated --all-versions --yes" in PUBLISH
    assert "--status deleted" not in PUBLISH
    assert "OLD=io.github.valuein/mcp-sec-edgar" in PUBLISH


def test_the_sync_hands_its_secrets_to_the_reusable_publish() -> None:
    block = SYNC[SYNC.index("uses: ./.github/workflows/publish-mcp.yml") :]
    assert re.match(r"uses: \./\.github/workflows/publish-mcp\.yml\n\s+secrets: inherit\n", block)
