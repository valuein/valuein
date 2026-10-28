#!/usr/bin/env python3
"""
sync_mcp_manifest.py — sync server.json + the MCP docs from the MCP server's manifest.

The MCP server (`https://mcp.valuein.biz/manifest.json`) emits an authoritative `manifest.json`
listing every live tool, SOP prompt, and resource, plus the agent contract
(how a tool error and a paged result read). This script updates this repo's
public-facing surfaces to match:

- `server.json`: tools_summary {live, stubs, prompts, resources} + version
- `README.md`: the prose block between
  `<!-- GEN:mcp-summary -->` and `<!-- /GEN:mcp-summary -->`
- `docs/MCP_TOOLS.md`: four generated blocks —
  `GEN:agent-contract` (the manifest's `agent_contract.markdown`, verbatim),
  `GEN:mcp-tool-reference` (every tool: title, min plan, effect, summary,
  an inputs table, output fields, paging form), `GEN:mcp-prompts` and
  `GEN:mcp-resources`
- `AGENTS.md`: the `GEN:agent-contract` block (same verbatim Markdown)

Hand-editing those values is a silent lie to PyPI/Smithery/Show HN visitors
and to every agent that reads the docs; this script keeps them honest. A block
is only ever replaced between its markers: a file that lacks a marker pair is
an error, never a guess.

Publish guard (both modes, before anything is written): the run is refused with
exit code 3 if the manifest lists any tool in HIDDEN_TOOLS (whatever its status),
if the manifest cannot be judged (no usable `tools` list, a tool without a string
`name`, or `counts.tools` / `tools_live` / `tools_stub` disagreeing with the tools
listed), if `server.json` already names a hidden tool, or if a rendered docs block
would name a hidden tool or a withheld internal dataset name. Nothing is written
when it refuses.

Agent-contract fields (both modes): the run is refused with exit code 4 when the
manifest lacks `agent_contract.markdown` or any tool lacks `inputs`,
`output_fields` or `paging` (MCP server 3.7.2 and later carry them). The docs are
never rendered from a partial manifest, so an older server fails LOUDLY instead
of silently leaving the reference stale.

Public redaction (documented, deliberate): `doc-integrity.yml` forbids a few
internal dataset and column names in every tracked file (`IP_DENYLIST` below).
Some live tool descriptions and enum values mention them. In the generated tool
reference, prompts and resources, each identifier carrying one of those names is
replaced by `[withheld]` (descriptions, enum values, defaults, output fields);
the live `tools/list` keeps them. A tool or input NAME carrying one, or an agent
contract that does, refuses the run (exit 3) rather than publish a broken page.

Source resolution order:
1. `MCP_MANIFEST_PATH` env var — an explicit local manifest file (highest)
2. Override via `MCP_MANIFEST_URL` env var
3. Default: https://mcp.valuein.biz/manifest.json (served by the deployed Worker;
   the `valuein/mcp` GitHub repo is private, so the raw.githubusercontent URL
   would 404 in CI)
There is deliberately no sibling-checkout fallback: a stale local mcp checkout
would silently regenerate the docs from an old manifest.

Usage:
  uv run python scripts/sync_mcp_manifest.py            # write changes
  uv run python scripts/sync_mcp_manifest.py --check    # exit 1 stale, 3 guard refused,
                                                        # 4 agent-contract fields missing
  uv run python scripts/sync_mcp_manifest.py --check --base origin/main
      # a PR or branch: drift fails only when this change edits the generator;
      # drift from an MCP deploy is reported and left to sync-mcp-manifest.yml
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent
# This script. A change that edits it owns the drift its new output shows (see
# `change_owns_drift`); any other drift is the sync bot's to commit.
GENERATOR = Path(__file__).resolve()
SERVER_JSON = REPO_ROOT / "server.json"
README = REPO_ROOT / "README.md"
MCP_TOOLS_DOC = REPO_ROOT / "docs" / "MCP_TOOLS.md"
AGENTS_DOC = REPO_ROOT / "AGENTS.md"

DEFAULT_MANIFEST_URL = "https://mcp.valuein.biz/manifest.json"

# Tools that are deliberately hidden until the paid report marketplace launches.
# The publish guard refuses any manifest that lists one of these, whatever its
# status, so a hidden tool can never reach server.json or the public registry by
# way of the automatic sync. Remove a name from this set when that tool is
# released (and only then).
HIDDEN_TOOLS = frozenset({"purchase_report", "list_my_purchases", "connect_stripe_account"})

# Exit code when the guard refuses. Distinct from 1, which means "stale" in --check.
EXIT_GUARD_REFUSED = 3

# Exit code when the manifest predates the agent contract (no `agent_contract`,
# or a tool without `inputs` / `output_fields` / `paging`).
EXIT_CONTRACT_MISSING = 4

# The doc-integrity IP-leak denylist, as the exact alternation that workflow greps
# for. Keep this line byte-identical to the gate's pattern: the gate exempts lines
# that quote the whole alternation, and this is the one place the generator names it.
IP_DENYLIST_ALTERNATION = "factor_scores|earnings_signals|composite_rank|eps_trend_est"
# Same lookbehind as the gate: a published tool name prefixed `get_` is not a leak.
IP_LEAK_RE = re.compile(r"(?<!get_)(" + IP_DENYLIST_ALTERNATION + r")")
WITHHELD = "[withheld]"
WITHHELD_NOTE = (
    f"Identifiers shown as `{WITHHELD}` name internal datasets and are left out of "
    "this public page; the live `tools/list` response carries them."
)


def load_manifest() -> dict:
    """Resolve and load the MCP manifest.

    Returns:
        Parsed manifest dict.

    Raises:
        FileNotFoundError: If `MCP_MANIFEST_PATH` names a file that does not exist.
        URLError: If the manifest URL is unreachable.
    """
    explicit = os.environ.get("MCP_MANIFEST_PATH", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"MCP_MANIFEST_PATH={explicit} is not a file")
        print(f"  source: {path}")
        return json.loads(path.read_text())
    url = os.environ.get("MCP_MANIFEST_URL", DEFAULT_MANIFEST_URL)
    print(f"  source: {url}")
    req = Request(url, headers={"User-Agent": "valuein-sync-mcp-manifest/1.0"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _guard_manifest_problems(manifest: object) -> list[str]:
    """Return why the manifest is unsafe or unjudgeable to publish (empty if fine)."""
    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]
    tools = manifest.get("tools")
    if not isinstance(tools, list) or not tools:
        return ["manifest `tools` is missing, not a list, or empty"]

    problems: list[str] = []
    found: set[str] = set()
    live = 0
    stub = 0
    for index, tool in enumerate(tools):
        name = tool.get("name") if isinstance(tool, dict) else None
        if not isinstance(name, str) or not name.strip():
            problems.append(f"manifest tools[{index}] has no string `name`")
            continue
        if name.strip().lower() in HIDDEN_TOOLS:
            found.add(name.strip().lower())
        if tool.get("status") == "live":
            live += 1
        elif tool.get("status") == "stub":
            stub += 1
    if found:
        problems.append(
            "manifest exposes hidden tool(s): " + ", ".join(sorted(found)) + " (status is ignored)"
        )

    # Every count the README and server.json are written from must agree with
    # the tools actually listed, so a tool cannot be counted without being named.
    counts = manifest.get("counts")
    expected = {"tools": len(tools), "tools_live": live, "tools_stub": stub}
    for key, actual in expected.items():
        declared = counts.get(key) if isinstance(counts, dict) else None
        if not isinstance(declared, int) or isinstance(declared, bool) or declared < 0:
            problems.append(f"manifest `counts.{key}` is missing or not a non-negative integer")
        elif declared != actual:
            problems.append(
                f"manifest `counts.{key}` is {declared} but the tools list gives {actual}"
            )
    return problems


def _names_in_text(text: str) -> list[str]:
    """Return the hidden tool names that appear in `text` as whole identifiers."""
    lowered = text.lower()
    return sorted(
        name
        for name in HIDDEN_TOOLS
        if re.search(rf"(?<![a-z0-9_]){re.escape(name)}(?![a-z0-9_])", lowered)
    )


def guard_problems(manifest: object, server_json_text: str) -> list[str]:
    """Run the publish guard and return every reason to refuse (empty means safe).

    Checks the manifest (hidden tools, malformed shape, live-count invariant) and
    the text of `server.json`, which is the file actually published.

    Args:
        manifest: The parsed MCP manifest, as loaded (may be malformed).
        server_json_text: Current contents of `server.json`.

    Returns:
        Human-readable problems; an empty list when it is safe to proceed.
    """
    problems = _guard_manifest_problems(manifest)
    in_server_json = _names_in_text(server_json_text)
    if in_server_json:
        problems.append("server.json names hidden tool(s): " + ", ".join(in_server_json))
    return problems


def update_server_json(manifest: dict) -> tuple[str, str]:
    """Return (current_text, target_text) for server.json.

    Surgical string replacement of the four `tools_summary` integer fields AND
    the top-level `version` — never a JSON round-trip, which would reformat
    unrelated short arrays.

    On `version`: this reads the LIVE Worker manifest (mcp.valuein.biz), and this
    sync is fired by the MCP's deploy workflow AFTER a successful prod deploy — so
    at the moment it runs, the Worker is ALREADY live at this version. Writing it
    into server.json is therefore documenting what is already shipped, which is
    exactly when the public repo is supposed to move. (It previously left version
    alone and only WARNED — and the registry drifted five versions behind the live
    Worker as a result. A warning nobody reads is not a sync.)

    The republish-to-registry that a version bump triggers reflects reality, not a
    speculative claim, precisely because the deploy already happened upstream.
    """
    current_text = SERVER_JSON.read_text()
    counts = manifest["counts"]
    targets = {
        "live": counts["tools_live"],
        "stubs": counts["tools_stub"],
        "prompts": counts["prompts"],
        "resources": counts["resources"],
    }
    target_text = current_text
    for field, value in targets.items():
        # Match `"field": <integer>` with any whitespace, replace integer only.
        # Quoted to avoid colliding with other fields that happen to share a name.
        pattern = re.compile(rf'("{field}"\s*:\s*)(\d+)')
        if not pattern.search(target_text):
            raise RuntimeError(f'server.json: could not find tools_summary field "{field}"')
        target_text = pattern.sub(rf"\g<1>{value}", target_text, count=1)

    # Top-level version → the live Worker's. Anchored to the FIRST `"version"`
    # (server.json's own), not a nested one inside packages[]/remotes[].
    deployed_version = manifest["version"]
    version_pattern = re.compile(r'("version"\s*:\s*")([^"]+)(")')
    if not version_pattern.search(target_text):
        raise RuntimeError('server.json: could not find a top-level "version" field')
    target_text = version_pattern.sub(rf"\g<1>{deployed_version}\g<3>", target_text, count=1)

    return current_text, target_text


README_SUMMARY_TEMPLATE = (
    "The server exposes **{live} live tools{stub_clause}**, "
    "plus **{prompts} agentic SOP prompts** "
    "(two flagship cross-persona briefs — `equity_research_brief` and "
    "`screen_and_shortlist` — plus specialised chains for analyst, PM, "
    "quant, ratio, smart-money, and workflow personas) and **{resources} "
    "data resources** (`schema://{{table}}`, `reference://sp500`, "
    "`pricing://current`). Tier gating happens at the data layer — the "
    "free Sample (no token, from 2020) and Benchmark (the large-cap US "
    "benchmark universe, current constituents, from 1993) tiers see their "
    "slices; Pro sees the full universe of 28,000+ active and delisted "
    "companies with a 15-year point-in-time window (2011 → present); "
    "Institutional unlocks the smart-money tools (insider transactions "
    "on Forms 3 / 4 / 5 / 144 + institutional ownership on Forms 13F / "
    "13D / 13G), Form ADV, unlimited history back to 1993 and "
    "filing-event webhooks, for internal use. Redistribution, display and "
    "white-label are Enterprise-only, under a Commercial licence."
)

MARKER_RE = re.compile(
    r"<!-- GEN:mcp-summary -->.*?<!-- /GEN:mcp-summary -->",
    re.DOTALL,
)
STALE_PARAGRAPH_RE = re.compile(
    r"The server exposes \d+ tools.*?commercial redistribution license\.",
    re.DOTALL,
)


def render_summary(manifest: dict) -> str:
    """Render the README summary block with marker fence.

    The stub clause is suppressed entirely when the manifest reports zero
    stub tools — "72 live tools" reads cleanly, while "72 live tools + 0 stub"
    would be a confusing artifact for public visitors.
    """
    counts = manifest["counts"]
    stubs = counts["tools_stub"]
    if stubs:
        noun = "stub" if stubs == 1 else "stubs"
        stub_clause = f" + {stubs} {noun} ({counts['tools']} total)"
    else:
        stub_clause = ""
    body = README_SUMMARY_TEMPLATE.format(
        live=counts["tools_live"],
        stub_clause=stub_clause,
        prompts=counts["prompts"],
        resources=counts["resources"],
    )
    return f"<!-- GEN:mcp-summary -->\n{body}\n<!-- /GEN:mcp-summary -->"


def update_readme(manifest: dict) -> tuple[str, str]:
    """Return (current_text, target_text) for README.md."""
    current = README.read_text()
    rendered = render_summary(manifest)
    if MARKER_RE.search(current):
        target = MARKER_RE.sub(rendered, current)
    elif STALE_PARAGRAPH_RE.search(current):
        target = STALE_PARAGRAPH_RE.sub(rendered, current, count=1)
    else:
        # No anchor — refuse to guess. Surface the error rather than silently
        # leaving stale prose in place.
        raise RuntimeError(
            "Could not locate the MCP summary in README.md. "
            "Add markers manually: <!-- GEN:mcp-summary --> ... <!-- /GEN:mcp-summary -->"
        )
    return current, target


# ── agent contract + generated docs ──────────────────────────────────────────

PAGING_FORMS = (None, "offset", "cursor")
CONTRACT_BLOCK = "agent-contract"
TOOL_REFERENCE_BLOCK = "mcp-tool-reference"
PROMPTS_BLOCK = "mcp-prompts"
RESOURCES_BLOCK = "mcp-resources"

# Which generated blocks each docs file carries. A file missing one of its
# marker pairs is an error (refuse to guess), exactly like the README block.
DOC_BLOCKS: dict[str, tuple[str, ...]] = {
    "MCP_TOOLS_DOC": (CONTRACT_BLOCK, TOOL_REFERENCE_BLOCK, PROMPTS_BLOCK, RESOURCES_BLOCK),
    "AGENTS_DOC": (CONTRACT_BLOCK,),
}

_CODE_SPAN_RE = re.compile(r"(`[^`\n]*`)")
# One identifier: a back-ticked span, or a dotted word (`table.column`), so the
# redaction removes the whole name, never half of it.
_IDENTIFIER_RE = re.compile(r"`[^`\n]+`|[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*")


def _summarise_missing(missing: dict[str, list[str]]) -> list[str]:
    """Collapse per-tool contract gaps into one line per missing field."""
    lines = []
    for what, names in missing.items():
        shown = ", ".join(names[:5]) + (f", … (+{len(names) - 5} more)" if len(names) > 5 else "")
        lines.append(f"{len(names)} tool(s) lack {what}: {shown}")
    return lines


def contract_problems(manifest: dict) -> list[str]:
    """Return why the manifest cannot drive the generated docs (empty if it can).

    The tool reference and the agent-contract blocks are rendered only from a
    manifest that carries every field they need; a missing field is a refusal,
    never a silently skipped section.

    Args:
        manifest: A manifest that already passed `guard_problems`.

    Returns:
        Human-readable problems; an empty list when the docs can be rendered.
    """
    problems: list[str] = []
    contract = manifest.get("agent_contract")
    if not isinstance(contract, dict):
        problems.append("manifest has no `agent_contract` object")
    else:
        markdown = contract.get("markdown")
        if not isinstance(markdown, str) or not markdown.strip():
            problems.append("manifest `agent_contract.markdown` is missing or empty")

    missing: dict[str, list[str]] = {}

    def lack(what: str, name: str) -> None:
        missing.setdefault(what, []).append(name)

    for tool in manifest["tools"]:
        name = tool["name"]
        if not isinstance(tool.get("description"), str):
            lack("a string `description`", name)
        if not isinstance(tool.get("min_plan"), str):
            lack("a string `min_plan`", name)
        inputs = tool.get("inputs")
        if not isinstance(inputs, list):
            lack("an `inputs` list", name)
        else:
            for item in inputs:
                ok = (
                    isinstance(item, dict)
                    and isinstance(item.get("name"), str)
                    and item["name"].strip()
                    and isinstance(item.get("type"), str)
                    and isinstance(item.get("required"), bool)
                    and isinstance(item.get("enum", []), list)
                    and isinstance(item.get("description", ""), (str, type(None)))
                )
                if not ok:
                    lack("well-formed `inputs` entries (name, type, required)", name)
                    break
        fields = tool.get("output_fields")
        if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
            lack("an `output_fields` list of strings", name)
        if "paging" not in tool:
            lack("a `paging` key", name)
        elif tool["paging"] not in PAGING_FORMS:
            lack('a `paging` of "offset", "cursor" or null', name)
    problems.extend(_summarise_missing(missing))

    for section in ("prompts", "resources"):
        entries = manifest.get(section)
        if not isinstance(entries, list) or not all(
            isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"].strip()
            for e in entries
        ):
            problems.append(f"manifest `{section}` is missing or has an entry without a `name`")
    return problems


def redact(text: str, where: str, withheld: list[str]) -> str:
    """Replace every identifier carrying an IP-denylisted name with `[withheld]`.

    Args:
        text: Manifest text bound for the public docs.
        where: Location label for the log (e.g. `screen_universe.description`).
        withheld: Collector; one entry is appended per replaced identifier.

    Returns:
        The text with each offending identifier (back-ticked span or dotted
        word) replaced by `WITHHELD`; unchanged when nothing matches.
    """

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        if IP_LEAK_RE.search(token):
            withheld.append(where)
            return WITHHELD
        return token

    return _IDENTIFIER_RE.sub(replace, text)


def _md_text(text: str, *, in_table: bool) -> str:
    """Make manifest prose safe to embed in Markdown without changing its words.

    Outside code spans, `<` becomes `&lt;` (so `<id>` is not swallowed as HTML);
    in a table cell, `|` is escaped and a newline becomes `<br>`.
    """
    parts = _CODE_SPAN_RE.split(text)
    out: list[str] = []
    for index, part in enumerate(parts):
        if index % 2 == 1:
            out.append(part.replace("|", "\\|") if in_table else part)
            continue
        segment = part.replace("<", "&lt;")
        if in_table:
            segment = segment.replace("|", "\\|")
        out.append(segment)
    joined = "".join(out)
    if in_table:
        joined = joined.replace("\r\n", "\n").replace("\n", "<br>")
    return joined


def _code(value: str) -> str:
    """Render `value` as an inline code span (double fence if it holds a backtick)."""
    return f"`` {value} ``" if "`" in value else f"`{value}`"


def _literal(value: Any, where: str, withheld: list[str]) -> str:
    """Render an enum value or a default as code, redacting a denylisted name."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if IP_LEAK_RE.search(text):
        withheld.append(where)
        return WITHHELD
    return _code(text).replace("|", "\\|")


def _effect(tool: dict) -> str:
    """Describe a tool's declared risk from its MCP annotations."""
    annotations = tool.get("annotations") if isinstance(tool.get("annotations"), dict) else {}
    if annotations.get("readOnlyHint") is True:
        return "read-only"
    if annotations.get("destructiveHint") is True:
        return "destructive"
    if annotations.get("readOnlyHint") is False:
        return "writes"
    return "not declared"


def _paging(tool: dict) -> str:
    """Describe a tool's paging form."""
    return {"offset": "offset", "cursor": "cursor"}.get(tool["paging"], "none")


def _plan_legend(manifest: dict) -> str:
    """Render the plan-key legend from the manifest's own `tier_matrix`."""
    tiers = manifest.get("tier_matrix")
    if not isinstance(tiers, dict) or not tiers:
        return ""
    names = []
    for key, tier in tiers.items():
        display = tier.get("display_name") if isinstance(tier, dict) else None
        names.append(f"`{key}` = {display}" if isinstance(display, str) else f"`{key}`")
    return "Plan keys: " + " · ".join(names) + "."


def _inputs_table(tool: dict, withheld: list[str]) -> list[str]:
    """Render one tool's inputs as a Markdown table (or a one-line note)."""
    inputs = tool["inputs"]
    if not inputs:
        return ["_No inputs._"]
    rows = [
        "| Input | Type | Required | Values | Description |",
        "|---|---|---|---|---|",
    ]
    for item in inputs:
        where = f"{tool['name']}.{item['name']}"
        values: list[str] = []
        enum = item.get("enum") or []
        if enum:
            kept = [v for v in enum if not IP_LEAK_RE.search(str(v))]
            dropped = len(enum) - len(kept)
            withheld.extend([f"{where}.enum"] * dropped)
            shown = ", ".join(_literal(v, f"{where}.enum", withheld) for v in kept)
            if dropped:
                shown = f"{shown} + {dropped} {WITHHELD}" if shown else f"{dropped} {WITHHELD}"
            values.append(f"one of {shown}")
        if "default" in item:
            values.append(f"default {_literal(item['default'], f'{where}.default', withheld)}")
        description = item.get("description")
        if isinstance(description, str) and description.strip():
            cell = _md_text(redact(description, f"{where}.description", withheld), in_table=True)
        else:
            cell = "—"
        rows.append(
            f"| `{item['name']}` | {_md_text(item['type'], in_table=True)} | "
            f"{'yes' if item['required'] else 'no'} | {'; '.join(values) or '—'} | {cell} |"
        )
    return rows


def render_agent_contract(manifest: dict) -> str:
    """Render the agent-contract block: the manifest's Markdown, byte for byte."""
    markdown = manifest["agent_contract"]["markdown"]
    tail = "" if markdown.endswith("\n") else "\n"
    return f"<!-- GEN:{CONTRACT_BLOCK} -->\n{markdown}{tail}<!-- /GEN:{CONTRACT_BLOCK} -->"


def render_tool_reference(manifest: dict, withheld: list[str]) -> str:
    """Render every tool: an index table, then one section per tool in manifest order.

    Args:
        manifest: A manifest that passed `guard_problems` and `contract_problems`.
        withheld: Collector for redaction locations (see `redact`).

    Returns:
        The full marker-fenced block.
    """
    tools = manifest["tools"]
    sections: list[str] = []
    index = ["| Tool | Title | Min plan | Effect | Paging |", "|---|---|---|---|---|"]
    for tool in tools:
        name = tool["name"]
        title = tool.get("title") if isinstance(tool.get("title"), str) else name
        title_md = _md_text(redact(title, f"{name}.title", withheld), in_table=True)
        index.append(
            f"| [`{name}`](#{name}) | {title_md} | `{tool['min_plan']}` | "
            f"{_effect(tool)} | {_paging(tool)} |"
        )
        summary = _md_text(
            redact(tool["description"], f"{name}.description", withheld), in_table=False
        )
        fields = [WITHHELD if IP_LEAK_RE.search(f) else f"`{f}`" for f in tool["output_fields"]]
        withheld.extend(
            f"{name}.output_fields" for f in tool["output_fields"] if IP_LEAK_RE.search(f)
        )
        section = [
            f"### `{name}`",
            "",
            (
                f"**{_md_text(redact(title, f'{name}.title', []), in_table=False)}** · "
                f"min plan `{tool['min_plan']}` · {_effect(tool)} · paging: {_paging(tool)}"
            ),
            "",
            summary,
            "",
            *_inputs_table(tool, withheld),
            "",
            "**Output fields:** " + (", ".join(fields) if fields else "_none declared_"),
        ]
        sections.append("\n".join(section))

    header = [
        f"<!-- GEN:{TOOL_REFERENCE_BLOCK} -->",
        (
            f"_Generated from the MCP server manifest (v{manifest['version']}) by "
            "`scripts/sync_mcp_manifest.py`. Do not edit by hand: the next sync overwrites it._"
        ),
        "",
        (
            f"**{len(tools)} tools**, in the server's registration order. Effect comes from "
            "each tool's MCP annotations (`readOnlyHint`, `destructiveHint`); paging is "
            "explained in the agent contract above. Descriptions are the manifest's summaries: "
            "the live `tools/list` response carries each tool's full description and JSON Schema."
        ),
    ]
    legend = _plan_legend(manifest)
    if legend:
        header += ["", legend]
    if withheld:
        header += ["", WITHHELD_NOTE]
    body = "\n".join(header) + "\n\n" + "\n".join(index) + "\n\n" + "\n\n".join(sections)
    return f"{body}\n<!-- /GEN:{TOOL_REFERENCE_BLOCK} -->"


def _catalog_block(
    block: str, label: str, manifest: dict, entries: list[dict], withheld: list[str]
) -> str:
    """Render a prompts or resources table (name, title, min plan, summary)."""
    before = len(withheld)
    rows = [f"| {label} | Title | Min plan | Summary |", "|---|---|---|---|"]
    for entry in entries:
        name = entry["name"]
        title = entry.get("title") if isinstance(entry.get("title"), str) else name
        plan = entry.get("min_plan")
        description = entry.get("description")
        summary = (
            redact(description, f"{name}.description", withheld)
            if isinstance(description, str)
            else ""
        )
        title_md = _md_text(redact(title, f"{name}.title", withheld), in_table=True)
        plan_md = _code(plan) if isinstance(plan, str) else "—"
        rows.append(
            f"| `{name}` | {title_md} | {plan_md} | {_md_text(summary, in_table=True) or '—'} |"
        )
    plural = "" if len(entries) == 1 else "s"
    lines = [
        f"<!-- GEN:{block} -->",
        (
            f"_Generated from the MCP server manifest (v{manifest['version']}); "
            f"{len(entries)} {label.lower()}{plural}._"
        ),
    ]
    if len(withheld) > before:
        lines += ["", WITHHELD_NOTE]
    return "\n".join(lines) + "\n\n" + "\n".join(rows) + f"\n<!-- /GEN:{block} -->"


def render_doc_blocks(manifest: dict) -> tuple[dict[str, str], list[str]]:
    """Render every generated docs block.

    Returns:
        (blocks by name, redaction locations).
    """
    withheld: list[str] = []
    blocks = {
        CONTRACT_BLOCK: render_agent_contract(manifest),
        TOOL_REFERENCE_BLOCK: render_tool_reference(manifest, withheld),
        PROMPTS_BLOCK: _catalog_block(
            PROMPTS_BLOCK, "Prompt", manifest, manifest["prompts"], withheld
        ),
        RESOURCES_BLOCK: _catalog_block(
            RESOURCES_BLOCK, "Resource", manifest, manifest["resources"], withheld
        ),
    }
    return blocks, withheld


def rendered_problems(manifest: dict, blocks: dict[str, str]) -> list[str]:
    """Return why the rendered docs must not be written (empty when safe).

    Second line of defence behind `guard_problems`: no block may name a hidden
    tool or carry an IP-denylisted name, the verbatim agent contract may not hold
    a marker of its own, and a tool or input NAME may not be denylisted (a name
    cannot be withheld without breaking the reference).
    """
    problems: list[str] = []
    for name, text in blocks.items():
        hidden = _names_in_text(text)
        if hidden:
            problems.append(f"generated `{name}` block names hidden tool(s): {', '.join(hidden)}")
        if IP_LEAK_RE.search(text):
            problems.append(f"generated `{name}` block carries an IP-denylisted name")
    markdown = manifest["agent_contract"]["markdown"]
    if "<!-- GEN:" in markdown or "<!-- /GEN:" in markdown:
        problems.append("`agent_contract.markdown` contains a GEN marker")
    for tool in manifest["tools"]:
        names = [tool["name"]] + [i["name"] for i in tool["inputs"]]
        if any(IP_LEAK_RE.search(n) for n in names):
            problems.append(f"tool `{tool['name']}` has an IP-denylisted tool or input name")
    return problems


def replace_block(text: str, block: str, rendered: str, label: str) -> str:
    """Replace the one `<!-- GEN:block -->` … `<!-- /GEN:block -->` span in `text`.

    Raises:
        RuntimeError: When the marker pair is absent or appears more than once.
    """
    pattern = re.compile(
        rf"<!-- GEN:{re.escape(block)} -->.*?<!-- /GEN:{re.escape(block)} -->", re.DOTALL
    )
    found = len(pattern.findall(text))
    if found != 1:
        raise RuntimeError(
            f"{label}: expected exactly one <!-- GEN:{block} --> … <!-- /GEN:{block} --> "
            f"block, found {found}. Add the markers by hand once."
        )
    return pattern.sub(lambda _match: rendered, text, count=1)


def update_docs(blocks: dict[str, str]) -> list[tuple[Path, str, str]]:
    """Return (path, current_text, target_text) for every generated docs file."""
    out = []
    for attr, names in DOC_BLOCKS.items():
        path: Path = globals()[attr]
        current = path.read_text()
        target = current
        for name in names:
            target = replace_block(target, name, blocks[name], path.name)
        out.append((path, current, target))
    return out


def _refuse(problems: list[str], code: int, headline: str) -> int:
    """Print a refusal and return its exit code."""
    print(f"\n✗ {headline} — nothing written:", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    return code


# Every file this script writes, repo-relative; `change_owns_drift` compares
# their generated regions (`_generated_regions`) with the change's base.
GENERATED_FILES = ("server.json", "README.md", "docs/MCP_TOOLS.md", "AGENTS.md")
_GEN_SPAN = re.compile(r"<!-- GEN:([\w-]+) -->.*?<!-- /GEN:\1 -->", re.DOTALL)


def _generated_regions(rel_path: str, text: str | None) -> list[str]:
    """The parts of a written file this script owns: GEN spans, or server.json's synced fields.

    Args:
        rel_path: Repo-relative path of one of `GENERATED_FILES`.
        text: The file's content, or None when it does not exist at that commit.

    Returns:
        The owned regions in file order (`["<absent>"]` for a missing file).
    """
    if text is None:
        return ["<absent>"]
    if rel_path == "server.json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return [text]
        return [json.dumps([data.get("version"), data.get("tools_summary")], sort_keys=True)]
    return [match.group(0) for match in _GEN_SPAN.finditer(text)]


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    """Run git in the repo root, capturing output (never raises on a non-zero exit)."""
    return subprocess.run(
        ["git", *args], check=False, cwd=REPO_ROOT, capture_output=True, text=True
    )


def change_owns_drift(base: str) -> bool:
    """Whether the change since its merge base with `base` caused the drift `--check` sees.

    It does when it edits the generator (it must ship what the new generator
    renders, so a reviewer sees the public output) or hand-edits a generated
    region (the next sync would silently revert it). A deploy of the MCP server
    is neither: that drift is the sync bot's. Prose outside the GEN markers and
    server.json fields the sync does not write are free. The merge base, not
    `base`'s tip, so a change that landed on `base` after the branch was cut is
    not the branch's. Fails closed: when git cannot answer (unknown ref, shallow
    clone) the change is treated as owning the drift.

    Args:
        base: The ref the change will merge into, e.g. `origin/main`.

    Returns:
        True when the change owns the drift (or git could not tell), else False.
    """
    try:
        merge_base = _git("merge-base", base, "HEAD")
        if merge_base.returncode != 0:
            print(
                f"  ⚠ no merge base with {base} ({merge_base.stderr.strip()}); treating the drift as this change's"
            )
            return True
        sha = merge_base.stdout.strip()
        generator = str(GENERATOR.relative_to(REPO_ROOT))
        diff = _git("diff", "--quiet", sha, "HEAD", "--", generator)
        if diff.returncode not in (0, 1):
            print(
                f"  ⚠ git diff against {base} failed ({diff.stderr.strip()}); treating the drift as this change's"
            )
            return True
        if diff.returncode == 1:
            print(f"  this change edits {generator}: it must carry the output it renders")
            return True
        for rel_path in GENERATED_FILES:
            before, after = (_git("show", f"{ref}:{rel_path}") for ref in (sha, "HEAD"))
            if _generated_regions(rel_path, before.stdout if before.returncode == 0 else None) != (
                _generated_regions(rel_path, after.stdout if after.returncode == 0 else None)
            ):
                print(
                    f"  this change edits a generated region of {rel_path}: the sync would revert it"
                )
                return True
    except (OSError, ValueError) as exc:
        print(f"  ⚠ cannot compare with {base} ({exc}); treating the drift as this change's")
        return True
    return False


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the command line (`--check`, `--base REF`)."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--check", action="store_true", help="verify only; exit 1 when stale")
    parser.add_argument(
        "--base",
        metavar="REF",
        help=(
            "with --check: fail only on drift this change owns (it edits the generator or a "
            "generated region since its merge base with REF); report any other drift and pass"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Sync (or with `--check`, verify) server.json, the README summary and the MCP docs.

    Args:
        argv: Command-line arguments; defaults to `sys.argv[1:]`.

    Returns:
        0 on success (or, under `--check --base`, on drift the change does not
        own), 1 when `--check` finds drift, 3 when the publish guard refuses, 4
        when the manifest lacks the agent-contract fields.
    """
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    check_mode = args.check
    print("Sync MCP manifest → public hub:")
    manifest = load_manifest()

    # Publish guard: runs in both modes, before anything is read further or written.
    problems = guard_problems(manifest, SERVER_JSON.read_text())
    if problems:
        return _refuse(problems, EXIT_GUARD_REFUSED, "publish guard refused")

    print(
        f"  loaded v{manifest['version']} — "
        f"{manifest['counts']['tools_live']} live + "
        f"{manifest['counts']['tools_stub']} stub tools, "
        f"{manifest['counts']['prompts']} prompts, "
        f"{manifest['counts']['resources']} resources"
    )

    # Agent contract: the docs are rendered from these fields or not at all.
    missing = contract_problems(manifest)
    if missing:
        return _refuse(
            missing,
            EXIT_CONTRACT_MISSING,
            f"manifest v{manifest.get('version')} lacks the agent-contract fields "
            "(MCP server 3.7.2+ publishes them)",
        )

    blocks, withheld = render_doc_blocks(manifest)
    problems = rendered_problems(manifest, blocks)
    if problems:
        return _refuse(problems, EXIT_GUARD_REFUSED, "publish guard refused the generated docs")
    if withheld:
        print(
            f"  withheld {len(withheld)} IP-denylisted identifier(s) in: "
            + ", ".join(sorted(set(withheld)))
        )

    server_current, server_target = update_server_json(manifest)
    readme_current, readme_target = update_readme(manifest)
    docs = update_docs(blocks)
    for path, _current, target in docs:
        if path == MCP_TOOLS_DOC and _names_in_text(target):
            return _refuse(
                [f"{path.name} names hidden tool(s): " + ", ".join(_names_in_text(target))],
                EXIT_GUARD_REFUSED,
                "publish guard refused the generated docs",
            )

    # ── Version now AUTO-SYNCS, and drift is still a FAILURE in --check ───────
    #
    # History: this used to leave `version` alone and print "⚠ version drift",
    # then carry on. The nightly job printed that line into a log nobody reads —
    # every night — while the public registry advertised v2.48.0 and the live
    # Worker ran v2.53.0. Five versions. The check saw it nightly and stopped
    # nothing.
    #
    # `server.json` is what registry.modelcontextprotocol.io serves to every agent
    # deciding whether to connect. A registry describing a server we are not
    # running is a false claim about our own product — the trust we tell
    # institutions never to extend to a vendor.
    #
    # Two changes fixed it, and they compose:
    #   1. `update_server_json` now rewrites `version` too. This sync is FIRED BY
    #      the MCP's deploy workflow after a successful PROD deploy, so the Worker
    #      is already live at this version — writing it is documenting what shipped,
    #      not a speculative bump. In sync mode it is written + committed like any
    #      other field, and the version bump republishes to the registry (which now
    #      matches reality).
    #   2. `--check` (the nightly + CI backstop) still returns non-zero on ANY
    #      drift, so if the auto-sync ever fails to fire — a missing secret, a
    #      dropped dispatch — a human is told LOUDLY instead of the warning being
    #      buried again.
    deployed_version = manifest["version"]
    registry_version = json.loads(server_current).get("version")
    version_behind = registry_version != deployed_version

    targets: list[tuple[Path, str, str]] = [
        (SERVER_JSON, server_current, server_target),
        (README, readme_current, readme_target),
        *docs,
    ]
    stale = [(path, target) for path, current, target in targets if current != target]
    drift = [_display_name(path) for path, _target in stale]

    if check_mode:
        if drift and args.base is not None and not change_owns_drift(args.base):
            print(
                f"\nℹ stale against live v{deployed_version}: {', '.join(drift)} — not this change's "
                "doing (no generator or generated-region edit). sync-mcp-manifest.yml commits it to main on the "
                "next MCP deploy, push to main or 03:00 UTC run; no action needed here."
            )
            return 0
        if drift:
            if version_behind:
                print(
                    f"\n✗ VERSION DRIFT — server.json={registry_version}, "
                    f"live Worker={deployed_version}."
                )
            print(f"\n✗ stale: {', '.join(drift)}")
            print("  run: uv run python scripts/sync_mcp_manifest.py")
            return 1
        print("\n✓ in sync")
        return 0

    if drift:
        for path, target in stale:
            path.write_text(target)
        note = f" (version {registry_version}→{deployed_version})" if version_behind else ""
        print(f"\n✓ updated: {', '.join(drift)}{note}")
        return 0

    print("\n✓ already in sync — no changes")
    return 0


def _display_name(path: Path) -> str:
    """Return `path` relative to the repo root when it lies inside it."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return path.name


if __name__ == "__main__":
    sys.exit(main())
