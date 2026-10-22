"""Who owns a drift: the change under review, or the sync bot.

``sync_mcp_manifest.py --check`` compares the repo with the LIVE manifest, so
it goes stale the moment the MCP server deploys, whatever the change being
checked does. ``--check --base <ref>`` fails only on a drift the change owns:
it edits the generator, or a generated region (a GEN span, server.json's
version / tools_summary), since its merge base with ``<ref>``. Any other drift is the sync
bot's (``sync-mcp-manifest.yml``: every MCP deploy, every push to ``main``
that touches the generator or a generated file, and 03:00 UTC), so the check
reports it and passes. Refusals (exit 3 and 4) fail whatever the base.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import sync_mcp_manifest as sync
from manifest_fixtures import clean_manifest, run_main, with_tool

# ── main: --check --base ─────────────────────────────────────────────────────


def test_drift_the_change_did_not_cause_passes_with_a_base(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    monkeypatch.setattr(sync, "change_owns_drift", lambda base: False)
    assert run_main(monkeypatch, clean_manifest(), ["--check", "--base", "origin/main"]) == 0


def test_drift_after_a_generator_change_fails_with_a_base(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    monkeypatch.setattr(sync, "change_owns_drift", lambda base: True)
    assert run_main(monkeypatch, clean_manifest(), ["--check", "--base", "origin/main"]) == 1


def test_a_refusal_still_fails_when_the_change_does_not_own_the_drift(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    monkeypatch.setattr(sync, "change_owns_drift", lambda base: False)
    manifest = with_tool(clean_manifest(), "purchase_report")
    assert run_main(monkeypatch, manifest, ["--check", "--base", "origin/main"]) == 3


def test_without_a_base_every_drift_fails(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    def unexpected(base: str) -> bool:
        raise AssertionError("no base was given, so nothing may be asked of git")

    monkeypatch.setattr(sync, "change_owns_drift", unexpected)
    assert run_main(monkeypatch, clean_manifest(), ["--check"]) == 1


def test_base_without_a_ref_is_a_usage_error(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    with pytest.raises(SystemExit):
        run_main(monkeypatch, clean_manifest(), ["--check", "--base"])


# ── change_owns_drift: a real git repository ───────────────────────────


README = "# Hub\n\nprose\n\n<!-- GEN:mcp-summary -->\n2 live tools\n<!-- /GEN:mcp-summary -->\n"
SERVER = '{\n  "name": "x",\n  "description": "d",\n  "version": "1.0.0",\n  "tools_summary": {"live": 2}\n}\n'


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo whose ``main`` holds the generator and one generated file."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "sync_mcp_manifest.py").write_text("v1\n")
    (tmp_path / "README.md").write_text(README)
    (tmp_path / "server.json").write_text(SERVER)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _git(tmp_path, "checkout", "-q", "-b", "change")
    monkeypatch.setattr(sync, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sync, "GENERATOR", tmp_path / "scripts" / "sync_mcp_manifest.py")
    return tmp_path


def test_a_prose_edit_outside_the_markers_does_not_own_drift(git_repo: Path) -> None:
    (git_repo / "README.md").write_text(README.replace("prose", "better prose"))
    (git_repo / "server.json").write_text(SERVER.replace('"d"', '"a sharper description"'))
    _git(git_repo, "commit", "-qam", "docs")
    assert sync.change_owns_drift("main") is False


def test_a_hand_edit_inside_a_gen_block_owns_drift(git_repo: Path) -> None:
    (git_repo / "README.md").write_text(README.replace("2 live tools", "3 live tools"))
    _git(git_repo, "commit", "-qam", "hand edit")
    assert sync.change_owns_drift("main") is True


def test_a_hand_version_bump_in_server_json_owns_drift(git_repo: Path) -> None:
    (git_repo / "server.json").write_text(SERVER.replace("1.0.0", "1.0.1"))
    _git(git_repo, "commit", "-qam", "bump")
    assert sync.change_owns_drift("main") is True


def test_a_committed_generator_change_owns_drift(git_repo: Path) -> None:
    (git_repo / "scripts" / "sync_mcp_manifest.py").write_text("v2\n")
    _git(git_repo, "commit", "-qam", "generator")
    assert sync.change_owns_drift("main") is True


def test_a_generator_change_on_the_base_alone_is_not_the_change_s(git_repo: Path) -> None:
    # main moves on after the branch was cut: comparing with the merge base,
    # not main's tip, keeps main's own generator change off this change's bill.
    _git(git_repo, "checkout", "-q", "main")
    (git_repo / "scripts" / "sync_mcp_manifest.py").write_text("v3\n")
    _git(git_repo, "commit", "-qam", "upstream generator")
    _git(git_repo, "checkout", "-q", "change")
    assert sync.change_owns_drift("main") is False


def test_an_unknown_base_fails_closed_as_owned(git_repo: Path) -> None:
    assert sync.change_owns_drift("no-such-ref") is True
