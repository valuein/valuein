"""Tests for the publish guard in ``scripts/sync_mcp_manifest.py``.

The guard refuses to sync or publish a manifest that exposes a tool which is
deliberately hidden until its launch, and fails closed on a manifest it cannot
judge. Everything here is offline: manifests are passed in directly and the
script's file paths are redirected into a temporary directory (the ``repo``
fixture in ``conftest.py``). The generated-docs rendering is covered in
``test_mcp_docs_render.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import sync_mcp_manifest as sync
from manifest_fixtures import (
    HIDDEN,
    SERVER_JSON_TEXT,
    assert_untouched,
    clean_manifest,
    run_main,
    with_tool,
)

# ── the constant ─────────────────────────────────────────────────────────────


def test_hidden_tools_constant_names_exactly_the_three_tools() -> None:
    assert set(sync.HIDDEN_TOOLS) == set(HIDDEN)


def test_guard_exit_code_is_the_documented_3() -> None:
    assert sync.EXIT_GUARD_REFUSED == 3


# ── manifest guard: pure function ────────────────────────────────────────────


def test_clean_manifest_has_no_problems() -> None:
    assert sync.guard_problems(clean_manifest(), SERVER_JSON_TEXT) == []


@pytest.mark.parametrize("name", HIDDEN)
def test_each_hidden_tool_alone_fails_and_is_named(name: str) -> None:
    problems = sync.guard_problems(with_tool(clean_manifest(), name), SERVER_JSON_TEXT)
    assert problems
    assert name in "\n".join(problems)


def test_all_three_hidden_tools_fail_and_all_are_named() -> None:
    manifest = clean_manifest()
    for name in HIDDEN:
        manifest = with_tool(manifest, name)
    text = "\n".join(sync.guard_problems(manifest, SERVER_JSON_TEXT))
    for name in HIDDEN:
        assert name in text


@pytest.mark.parametrize("status", ["stub", "hidden", "disabled", "beta", ""])
@pytest.mark.parametrize("name", HIDDEN)
def test_hidden_tool_with_non_live_status_still_fails(name: str, status: str) -> None:
    problems = sync.guard_problems(with_tool(clean_manifest(), name, status), SERVER_JSON_TEXT)
    assert name in "\n".join(problems)


def test_hidden_name_match_ignores_case_and_whitespace() -> None:
    manifest = with_tool(clean_manifest(), " Purchase_Report ")
    assert sync.guard_problems(manifest, SERVER_JSON_TEXT)


def test_a_similarly_named_tool_is_not_a_false_positive() -> None:
    manifest = with_tool(clean_manifest(), "list_my_reports")
    assert sync.guard_problems(manifest, SERVER_JSON_TEXT) == []


# ── manifest guard: fail closed on what it cannot judge ──────────────────────


def _drop_tools(m: dict[str, Any]) -> None:
    del m["tools"]


@pytest.mark.parametrize(
    "mutate",
    [
        _drop_tools,
        lambda m: m.update(tools=None),
        lambda m: m.update(tools={"search_companies": {}}),
        lambda m: m.update(tools="search_companies"),
        lambda m: m.update(tools=[]),
        lambda m: m["tools"].append({"status": "live"}),
        lambda m: m["tools"].append({"name": 7, "status": "live"}),
        lambda m: m["tools"].append({"name": "", "status": "live"}),
        lambda m: m["tools"].append("search_companies"),
        lambda m: m["tools"].append(None),
    ],
    ids=[
        "tools-missing",
        "tools-null",
        "tools-dict",
        "tools-string",
        "tools-empty",
        "entry-without-name",
        "entry-non-string-name",
        "entry-empty-name",
        "entry-not-an-object",
        "entry-null",
    ],
)
def test_malformed_tools_fail_closed(mutate: Any) -> None:
    manifest = clean_manifest()
    mutate(manifest)
    assert sync.guard_problems(manifest, SERVER_JSON_TEXT)


@pytest.mark.parametrize("manifest", [None, [], "manifest", 3, {}])
def test_non_object_or_empty_manifest_fails_closed(manifest: Any) -> None:
    assert sync.guard_problems(manifest, SERVER_JSON_TEXT)


def test_tools_live_lower_than_live_tools_fails() -> None:
    manifest = clean_manifest()
    manifest["counts"]["tools_live"] = 1
    assert sync.guard_problems(manifest, SERVER_JSON_TEXT)


def test_tools_live_higher_than_live_tools_fails() -> None:
    manifest = clean_manifest()
    manifest["counts"]["tools_live"] = 3
    assert sync.guard_problems(manifest, SERVER_JSON_TEXT)


def test_non_live_tools_are_not_counted_as_live() -> None:
    manifest = with_tool(clean_manifest(), "some_stub_tool", "stub")
    assert sync.guard_problems(manifest, SERVER_JSON_TEXT) == []
    manifest["counts"]["tools_live"] = 3
    assert sync.guard_problems(manifest, SERVER_JSON_TEXT)


@pytest.mark.parametrize("key", ["tools", "tools_live", "tools_stub"])
@pytest.mark.parametrize("bad", [None, "2", 2.0, True, -1])
def test_unusable_count_fails_closed(key: str, bad: Any) -> None:
    manifest = clean_manifest()
    manifest["counts"][key] = bad
    assert sync.guard_problems(manifest, SERVER_JSON_TEXT)


def test_a_tool_counted_as_a_stub_but_not_listed_fails() -> None:
    manifest = clean_manifest()
    manifest["counts"]["tools_stub"] = 3
    assert "tools_stub" in "\n".join(sync.guard_problems(manifest, SERVER_JSON_TEXT))


def test_total_count_that_disagrees_with_the_tools_list_fails() -> None:
    manifest = clean_manifest()
    manifest["counts"]["tools"] = 5
    assert "counts.tools`" in "\n".join(sync.guard_problems(manifest, SERVER_JSON_TEXT))


@pytest.mark.parametrize("counts", [None, [], "x", {}])
def test_unusable_counts_fails_closed(counts: Any) -> None:
    manifest = clean_manifest()
    manifest["counts"] = counts
    assert sync.guard_problems(manifest, SERVER_JSON_TEXT)


def test_counts_missing_fails_closed() -> None:
    manifest = clean_manifest()
    del manifest["counts"]
    assert sync.guard_problems(manifest, SERVER_JSON_TEXT)


# ── server.json guard ────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", HIDDEN)
def test_server_json_containing_a_hidden_name_fails(name: str) -> None:
    text = SERVER_JSON_TEXT.replace('"version"', f'"note": "{name}",\n  "version"')
    problems = sync.guard_problems(clean_manifest(), text)
    assert name in "\n".join(problems)


def test_server_json_hidden_name_is_found_anywhere_in_the_text() -> None:
    text = SERVER_JSON_TEXT + "\n// mentions connect_stripe_account in a trailing comment\n"
    assert sync.guard_problems(clean_manifest(), text)


def test_server_json_longer_identifier_is_not_a_false_positive() -> None:
    text = SERVER_JSON_TEXT.replace('"version"', '"note": "list_my_purchases_v2",\n  "version"')
    assert sync.guard_problems(clean_manifest(), text) == []


# ── main(): both modes, exit codes, and nothing is written on failure ────────


@pytest.mark.parametrize("argv", [[], ["--check"]])
@pytest.mark.parametrize("name", HIDDEN)
def test_main_refuses_a_hidden_tool_in_both_modes(
    monkeypatch: pytest.MonkeyPatch,
    repo: dict[str, Path],
    capsys: pytest.CaptureFixture[str],
    name: str,
    argv: list[str],
) -> None:
    code = run_main(monkeypatch, with_tool(clean_manifest(), name), argv)
    assert code == sync.EXIT_GUARD_REFUSED
    assert name in capsys.readouterr().err
    assert repo["server_json"].read_text() == SERVER_JSON_TEXT
    assert_untouched(repo)


@pytest.mark.parametrize("argv", [[], ["--check"]])
def test_main_fails_closed_on_a_malformed_manifest_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path], argv: list[str]
) -> None:
    manifest = clean_manifest()
    manifest["tools"] = []
    assert run_main(monkeypatch, manifest, argv) == sync.EXIT_GUARD_REFUSED
    assert repo["server_json"].read_text() == SERVER_JSON_TEXT
    assert_untouched(repo)


@pytest.mark.parametrize("argv", [[], ["--check"]])
def test_main_refuses_when_server_json_contains_a_hidden_name(
    monkeypatch: pytest.MonkeyPatch,
    repo: dict[str, Path],
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
) -> None:
    dirty = SERVER_JSON_TEXT.replace('"version"', '"note": "purchase_report",\n  "version"')
    repo["server_json"].write_text(dirty)
    assert run_main(monkeypatch, clean_manifest(), argv) == sync.EXIT_GUARD_REFUSED
    assert "purchase_report" in capsys.readouterr().err
    assert repo["server_json"].read_text() == dirty
    assert_untouched(repo)


def test_main_write_mode_still_syncs_a_clean_manifest(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    assert run_main(monkeypatch, clean_manifest(), []) == 0
    written = json.loads(repo["server_json"].read_text())
    assert written["version"] == "2.0.0"
    assert written["tools_summary"] == {"live": 2, "stubs": 0, "prompts": 3, "resources": 3}
    assert "**2 live tools**" in repo["readme"].read_text()


def test_main_check_mode_reports_stale_as_exit_1_for_a_clean_manifest(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    assert run_main(monkeypatch, clean_manifest(), ["--check"]) == 1


def test_main_check_mode_passes_once_in_sync(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    assert run_main(monkeypatch, clean_manifest(), []) == 0
    assert run_main(monkeypatch, clean_manifest(), ["--check"]) == 0
