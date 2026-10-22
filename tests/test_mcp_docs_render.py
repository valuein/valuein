"""Tests for the generated MCP docs in ``scripts/sync_mcp_manifest.py``.

Covers the tool reference (inputs table, enum/default rendering, missing
descriptions, effect and paging), the verbatim agent-contract embedding,
``--check`` drift detection on the generated blocks, the loud refusal when a
manifest predates the agent contract, the hidden-tool guard on the rendered
docs, the IP-denylist redaction, and the ``MCP_MANIFEST_PATH`` override.

Everything is offline: manifests are built in memory and every file the script
writes is redirected into a temporary directory by the ``repo`` fixture (``conftest.py``).
No denylisted name is written literally in this file (the doc-integrity gate
scans it); they are taken from ``sync.IP_DENYLIST_ALTERNATION``.
"""

from __future__ import annotations

import copy
import io
import json
from pathlib import Path
from typing import Any

import pytest
import sync_mcp_manifest as sync
from manifest_fixtures import (
    CONTRACT_MARKDOWN,
    HIDDEN,
    MCP_TOOLS_TEXT,
    assert_untouched,
    clean_manifest,
    contract_tool,
    run_main,
)

DENYLISTED = tuple(sync.IP_DENYLIST_ALTERNATION.split("|"))


def render_reference(manifest: dict[str, Any]) -> tuple[str, list[str]]:
    """Render the tool-reference block and return it with the redaction log."""
    withheld: list[str] = []
    return sync.render_tool_reference(manifest, withheld), withheld


def rich_tool() -> dict[str, Any]:
    """Return a tool whose inputs exercise every column of the inputs table."""
    tool = contract_tool("get_pit_universe")
    tool["paging"] = "offset"
    tool["inputs"] = [
        {"name": "as_of_date", "type": "string", "required": True, "description": "PIT date."},
        {
            "name": "index",
            "type": "enum",
            "required": False,
            "description": "Index filter.",
            "enum": ["sp500", "russell1000"],
            "default": "sp500",
        },
        {"name": "limit", "type": "integer", "required": False, "default": 100},
        {"name": "offset", "type": "integer", "required": False, "description": None},
        {
            "name": "tags",
            "type": "array",
            "required": False,
            "default": ["a", "b"],
            "description": "Uses a|b and <id> placeholders.",
        },
    ]
    tool["output_fields"] = ["universe_size", "truncation", "companies"]
    return tool


# ── inputs table ─────────────────────────────────────────────────────────────


def test_inputs_table_renders_required_enum_default_and_descriptions() -> None:
    rows = sync._inputs_table(rich_tool(), [])
    assert rows[0] == "| Input | Type | Required | Values | Description |"
    assert "| `as_of_date` | string | yes | — | PIT date. |" in rows
    assert (
        "| `index` | enum | no | one of `sp500`, `russell1000`; default `sp500` | Index filter. |"
        in rows
    )


@pytest.mark.parametrize("name", ["limit", "offset"])
def test_missing_or_null_input_description_renders_a_dash(name: str) -> None:
    rows = sync._inputs_table(rich_tool(), [])
    row = next(r for r in rows if r.startswith(f"| `{name}` |"))
    assert row.endswith("| — |")


def test_non_string_default_is_json_and_cell_text_is_markdown_safe() -> None:
    rows = sync._inputs_table(rich_tool(), [])
    row = next(r for r in rows if r.startswith("| `tags` |"))
    assert 'default `["a", "b"]`' in row
    assert "a\\|b" in row
    assert "&lt;id>" in row


def test_integer_default_renders_as_code() -> None:
    rows = sync._inputs_table(rich_tool(), [])
    assert "| `limit` | integer | no | default `100` | — |" in rows


def test_tool_with_no_inputs_says_so() -> None:
    tool = contract_tool("get_morning_brief")
    tool["inputs"] = []
    assert sync._inputs_table(tool, []) == ["_No inputs._"]


# ── tool sections, index, effect, paging ─────────────────────────────────────


def test_reference_lists_every_tool_in_manifest_order_with_its_fields() -> None:
    manifest = clean_manifest()
    manifest["tools"].append(rich_tool())
    block, _ = render_reference(manifest)
    assert block.startswith("<!-- GEN:mcp-tool-reference -->")
    assert block.endswith("<!-- /GEN:mcp-tool-reference -->")
    order = [block.index(f"### `{t['name']}`") for t in manifest["tools"]]
    assert order == sorted(order)
    assert "min plan `sample` · read-only · paging: offset" in block
    assert "**Output fields:** `universe_size`, `truncation`, `companies`" in block
    assert "(v2.0.0)" in block


@pytest.mark.parametrize(
    ("annotations", "effect"),
    [
        ({"readOnlyHint": True, "destructiveHint": False}, "read-only"),
        ({"readOnlyHint": False, "destructiveHint": True}, "destructive"),
        ({"readOnlyHint": False, "destructiveHint": False}, "writes"),
        ({}, "not declared"),
    ],
)
def test_effect_comes_from_annotations(annotations: dict[str, bool], effect: str) -> None:
    tool = contract_tool("delete_thesis")
    tool["annotations"] = annotations
    assert sync._effect(tool) == effect


@pytest.mark.parametrize(
    ("paging", "shown"), [(None, "none"), ("offset", "offset"), ("cursor", "cursor")]
)
def test_paging_form_is_rendered(paging: str | None, shown: str) -> None:
    tool = contract_tool("list_theses")
    tool["paging"] = paging
    assert sync._paging(tool) == shown


def test_plan_legend_comes_from_the_tier_matrix() -> None:
    manifest = clean_manifest()
    manifest["tier_matrix"] = {"sample": {"display_name": "Sample"}, "full": {}}
    assert sync._plan_legend(manifest) == "Plan keys: `sample` = Sample · `full`."
    del manifest["tier_matrix"]
    assert sync._plan_legend(manifest) == ""


def test_rendering_is_deterministic() -> None:
    manifest = clean_manifest()
    manifest["tools"].append(rich_tool())
    assert sync.render_doc_blocks(manifest) == sync.render_doc_blocks(copy.deepcopy(manifest))


def test_prompts_and_resources_blocks_list_every_entry() -> None:
    blocks, _ = sync.render_doc_blocks(clean_manifest())
    assert "| `equity_research_brief` | Brief | `sample` | A brief. |" in blocks["mcp-prompts"]
    assert "| `schema` | Schema | `sample` | Columns. |" in blocks["mcp-resources"]
    assert "; 1 prompt._" in blocks["mcp-prompts"]


# ── agent contract: verbatim ─────────────────────────────────────────────────


@pytest.mark.parametrize("markdown", [CONTRACT_MARKDOWN, CONTRACT_MARKDOWN.rstrip("\n")])
def test_agent_contract_block_embeds_the_markdown_byte_for_byte(markdown: str) -> None:
    manifest = clean_manifest()
    manifest["agent_contract"]["markdown"] = markdown
    block = sync.render_agent_contract(manifest)
    inner = block.removeprefix("<!-- GEN:agent-contract -->\n").removesuffix(
        "<!-- /GEN:agent-contract -->"
    )
    assert inner.rstrip("\n") == markdown.rstrip("\n")
    assert markdown in block


def test_main_writes_the_contract_verbatim_into_both_docs(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    assert run_main(monkeypatch, clean_manifest(), []) == 0
    for key in ("mcp_tools", "agents"):
        text = repo[key].read_text()
        assert CONTRACT_MARKDOWN in text
        assert text.count("<!-- GEN:agent-contract -->") == 1
    tools_doc = repo["mcp_tools"].read_text()
    assert "### `search_companies`" in tools_doc
    assert "### `get_company_fundamentals`" in tools_doc


def test_contract_markdown_carrying_a_marker_is_refused(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    manifest = clean_manifest()
    manifest["agent_contract"]["markdown"] += "<!-- /GEN:agent-contract -->\n"
    assert run_main(monkeypatch, manifest, []) == sync.EXIT_GUARD_REFUSED
    assert_untouched(repo)


# ── --check: drift detection on the generated blocks ─────────────────────────


def test_check_passes_once_synced_then_fails_when_a_tool_changes(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = clean_manifest()
    assert run_main(monkeypatch, manifest, []) == 0
    assert run_main(monkeypatch, manifest, ["--check"]) == 0
    changed = copy.deepcopy(manifest)
    changed["tools"][0]["inputs"][0]["description"] = "A ticker or a CIK."
    capsys.readouterr()
    assert run_main(monkeypatch, changed, ["--check"]) == 1
    out = capsys.readouterr().out
    assert repo["mcp_tools"].name in out
    assert repo["agents"].name not in out


def test_check_fails_when_only_the_agent_contract_changes(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    manifest = clean_manifest()
    assert run_main(monkeypatch, manifest, []) == 0
    manifest["agent_contract"]["markdown"] += "\nA new rule.\n"
    assert run_main(monkeypatch, manifest, ["--check"]) == 1


def test_check_fails_on_a_hand_edit_inside_a_block_but_not_outside(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    manifest = clean_manifest()
    assert run_main(monkeypatch, manifest, []) == 0
    synced = repo["mcp_tools"].read_text()
    repo["mcp_tools"].write_text("Hand-written prose stays.\n\n" + synced)
    assert run_main(monkeypatch, manifest, ["--check"]) == 0
    repo["mcp_tools"].write_text(synced.replace("A ticker.", "A ticker (edited)."))
    assert run_main(monkeypatch, manifest, ["--check"]) == 1


def test_check_mode_never_writes(monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]) -> None:
    assert run_main(monkeypatch, clean_manifest(), ["--check"]) == 1
    assert repo["mcp_tools"].read_text() == MCP_TOOLS_TEXT


@pytest.mark.parametrize("text", ["# no markers\n", MCP_TOOLS_TEXT + MCP_TOOLS_TEXT])
def test_a_missing_or_duplicated_marker_pair_is_an_error(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path], text: str
) -> None:
    repo["mcp_tools"].write_text(text)
    with pytest.raises(RuntimeError, match="GEN:"):
        run_main(monkeypatch, clean_manifest(), [])
    assert repo["mcp_tools"].read_text() == text


# ── a manifest without the agent contract fails loudly ───────────────────────


def _drop(key: str) -> Any:
    return lambda m: m.pop(key)


def _drop_tool_key(key: str) -> Any:
    return lambda m: m["tools"][0].pop(key)


@pytest.mark.parametrize(
    "mutate",
    [
        _drop("agent_contract"),
        lambda m: m["agent_contract"].pop("markdown"),
        lambda m: m["agent_contract"].update(markdown="  "),
        _drop_tool_key("inputs"),
        _drop_tool_key("output_fields"),
        _drop_tool_key("paging"),
        _drop_tool_key("description"),
        lambda m: m["tools"][0].update(paging="page"),
        lambda m: m["tools"][0].update(output_fields="ticker"),
        lambda m: m["tools"][0]["inputs"][0].pop("type"),
        lambda m: m["tools"][0]["inputs"][0].update(required="yes"),
        lambda m: m["tools"][0]["inputs"][0].update(enum="sp500"),
        _drop("prompts"),
        _drop("resources"),
    ],
    ids=[
        "no-agent-contract",
        "no-markdown",
        "blank-markdown",
        "tool-without-inputs",
        "tool-without-output-fields",
        "tool-without-paging-key",
        "tool-without-description",
        "unknown-paging-form",
        "output-fields-not-a-list",
        "input-without-type",
        "input-required-not-bool",
        "input-enum-not-a-list",
        "no-prompts",
        "no-resources",
    ],
)
@pytest.mark.parametrize("argv", [[], ["--check"]])
def test_missing_contract_field_refuses_loudly_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch,
    repo: dict[str, Path],
    capsys: pytest.CaptureFixture[str],
    mutate: Any,
    argv: list[str],
) -> None:
    manifest = clean_manifest()
    mutate(manifest)
    assert run_main(monkeypatch, manifest, argv) == sync.EXIT_CONTRACT_MISSING
    assert "agent-contract" in capsys.readouterr().err
    assert repo["server_json"].read_text().count('"version": "1.0.0"') == 1
    assert_untouched(repo)


def test_contract_problems_collapse_per_field_and_name_the_tools() -> None:
    manifest = clean_manifest()
    for tool in manifest["tools"]:
        del tool["inputs"]
    problems = sync.contract_problems(manifest)
    assert problems == [
        "2 tool(s) lack an `inputs` list: search_companies, get_company_fundamentals"
    ]


def test_contract_exit_code_is_distinct() -> None:
    assert sync.EXIT_CONTRACT_MISSING == 4
    assert sync.EXIT_CONTRACT_MISSING not in (0, 1, sync.EXIT_GUARD_REFUSED)


# ── hidden tools never reach the generated reference ─────────────────────────


@pytest.mark.parametrize("name", HIDDEN)
def test_a_hidden_tool_never_reaches_the_reference(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path], name: str
) -> None:
    manifest = clean_manifest()
    manifest["tools"].append(contract_tool(name))
    manifest["counts"]["tools"] += 1
    manifest["counts"]["tools_live"] += 1
    assert run_main(monkeypatch, manifest, []) == sync.EXIT_GUARD_REFUSED
    assert name not in repo["mcp_tools"].read_text()
    assert_untouched(repo)


@pytest.mark.parametrize("name", HIDDEN)
@pytest.mark.parametrize("where", ["tool-description", "input-description", "prompt", "contract"])
def test_a_hidden_name_mentioned_anywhere_in_rendered_docs_is_refused(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path], name: str, where: str
) -> None:
    manifest = clean_manifest()
    mention = f" See {name}."
    if where == "tool-description":
        manifest["tools"][0]["description"] += mention
    elif where == "input-description":
        manifest["tools"][0]["inputs"][0]["description"] += mention
    elif where == "prompt":
        manifest["prompts"][0]["description"] += mention
    else:
        manifest["agent_contract"]["markdown"] += mention
    assert run_main(monkeypatch, manifest, []) == sync.EXIT_GUARD_REFUSED
    assert_untouched(repo)


def test_hidden_names_in_hand_prose_of_the_tools_doc_are_refused(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    repo["mcp_tools"].write_text(f"Coming soon: {HIDDEN[0]}.\n\n" + MCP_TOOLS_TEXT)
    assert run_main(monkeypatch, clean_manifest(), []) == sync.EXIT_GUARD_REFUSED


# ── IP-denylist redaction ────────────────────────────────────────────────────


def test_the_alternation_matches_the_doc_integrity_gate() -> None:
    workflow = Path(__file__).resolve().parent.parent / ".github/workflows/doc-integrity.yml"
    if not workflow.exists():
        pytest.skip("doc-integrity.yml not present in this checkout")
    assert f"PATTERN='(?<!get_)({sync.IP_DENYLIST_ALTERNATION})'" in workflow.read_text()


@pytest.mark.parametrize("term", DENYLISTED)
def test_denylisted_identifiers_are_withheld_everywhere_they_render(term: str) -> None:
    manifest = clean_manifest()
    tool = manifest["tools"][0]
    tool["description"] = f"Ranks rows from {term}.parquet by score."
    tool["output_fields"] = ["data", term]
    tool["inputs"] = [
        {
            "name": "sort_by",
            "type": "enum",
            "required": False,
            "description": f"Defaults to `{term}`. Via {term}.accepted_at only.",
            "enum": ["roe_rank", term],
            "default": term,
        }
    ]
    blocks, withheld = sync.render_doc_blocks(manifest)
    text = "\n".join(blocks.values())
    assert not sync.IP_LEAK_RE.search(text)
    assert term not in text
    reference = blocks["mcp-tool-reference"]
    assert "Ranks rows from [withheld] by score." in reference
    assert "Defaults to [withheld]. Via [withheld] only." in reference
    assert "one of `roe_rank` + 1 [withheld]; default [withheld]" in reference
    assert "**Output fields:** `data`, [withheld]" in reference
    assert "left out of this public page" in reference
    assert len(withheld) == 6
    assert sync.rendered_problems(manifest, blocks) == []


def test_a_get_prefixed_tool_name_is_not_withheld() -> None:
    published = "get_" + DENYLISTED[1]
    manifest = clean_manifest()
    manifest["tools"][0]["description"] = f"Pairs with `{published}`."
    blocks, withheld = sync.render_doc_blocks(manifest)
    assert f"Pairs with `{published}`." in blocks["mcp-tool-reference"]
    assert withheld == []
    assert "left out of this public page" not in blocks["mcp-tool-reference"]


@pytest.mark.parametrize("where", ["tool", "input"])
def test_a_denylisted_tool_or_input_name_refuses_the_run(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path], where: str
) -> None:
    manifest = clean_manifest()
    if where == "tool":
        manifest["tools"][0]["name"] = "list_" + DENYLISTED[0]
    else:
        manifest["tools"][0]["inputs"][0]["name"] = DENYLISTED[2]
    assert run_main(monkeypatch, manifest, []) == sync.EXIT_GUARD_REFUSED
    assert_untouched(repo)


def test_a_denylisted_name_in_the_agent_contract_refuses_rather_than_redacts(
    monkeypatch: pytest.MonkeyPatch, repo: dict[str, Path]
) -> None:
    manifest = clean_manifest()
    manifest["agent_contract"]["markdown"] += f"\nSee {DENYLISTED[3]}.\n"
    assert run_main(monkeypatch, manifest, []) == sync.EXIT_GUARD_REFUSED
    assert_untouched(repo)


# ── manifest source: MCP_MANIFEST_PATH wins ──────────────────────────────────


def test_manifest_path_env_beats_the_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    explicit = tmp_path / "explicit.json"
    explicit.write_text(json.dumps({"version": "9.9.9"}))
    monkeypatch.setenv("MCP_MANIFEST_PATH", str(explicit))
    monkeypatch.setenv("MCP_MANIFEST_URL", "http://127.0.0.1:9/never-fetched")
    assert sync.load_manifest() == {"version": "9.9.9"}


def test_manifest_path_env_naming_a_missing_file_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_MANIFEST_PATH", str(tmp_path / "absent.json"))
    with pytest.raises(FileNotFoundError):
        sync.load_manifest()


def test_without_the_env_the_deployed_url_is_used_never_a_local_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale sibling mcp checkout must never win over the deployed manifest."""
    assert not hasattr(sync, "LOCAL_MCP")
    seen: list[str] = []

    def fake_urlopen(req: object, timeout: float) -> io.BytesIO:
        seen.append(req.full_url)  # type: ignore[attr-defined]
        return io.BytesIO(json.dumps({"version": "3.7.4"}).encode())

    monkeypatch.delenv("MCP_MANIFEST_PATH", raising=False)
    monkeypatch.delenv("MCP_MANIFEST_URL", raising=False)
    monkeypatch.setattr(sync, "urlopen", fake_urlopen)
    assert sync.load_manifest() == {"version": "3.7.4"}
    assert seen == [sync.DEFAULT_MANIFEST_URL]
