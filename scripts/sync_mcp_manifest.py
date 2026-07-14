#!/usr/bin/env python3
"""
sync_mcp_manifest.py — sync server.json + README from the MCP server's manifest.

The MCP repo (`~/WebstormProjects/mcp`) emits an authoritative `manifest.json`
listing every live tool, SOP prompt, and resource. This script updates this
repo's public-facing surfaces to match:

- `server.json`: tools_summary {live, stubs, prompts, resources} + version
- `README.md`: the prose block between
  `<!-- GEN:mcp-summary -->` and `<!-- /GEN:mcp-summary -->`

Hand-editing those values is a silent lie to PyPI/Smithery/Show HN visitors;
this script keeps them honest.

Source resolution order:
1. Sibling local checkout (`~/WebstormProjects/mcp/manifest.json`) — for dev
2. Override via `MCP_MANIFEST_URL` env var
3. Default: https://mcp.valuein.biz/manifest.json (served by the deployed Worker;
   the `valuein/mcp` GitHub repo is private, so the raw.githubusercontent URL
   would 404 in CI)

Usage:
  uv run python scripts/sync_mcp_manifest.py            # write changes
  uv run python scripts/sync_mcp_manifest.py --check    # exit 1 if stale
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Tuple
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_JSON = REPO_ROOT / "server.json"
README = REPO_ROOT / "README.md"

DEFAULT_MANIFEST_URL = "https://mcp.valuein.biz/manifest.json"
LOCAL_MCP = REPO_ROOT.parent.parent / "WebstormProjects" / "mcp" / "manifest.json"


def load_manifest() -> dict:
    """Resolve and load the MCP manifest.

    Returns:
        Parsed manifest dict.

    Raises:
        RuntimeError: If neither the local sibling nor the URL is reachable.
    """
    if LOCAL_MCP.exists():
        print(f"  source: {LOCAL_MCP}")
        return json.loads(LOCAL_MCP.read_text())
    url = os.environ.get("MCP_MANIFEST_URL", DEFAULT_MANIFEST_URL)
    print(f"  source: {url}")
    req = Request(url, headers={"User-Agent": "valuein-sync-mcp-manifest/1.0"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def update_server_json(manifest: dict) -> Tuple[str, str]:
    """Return (current_text, target_text) for server.json.

    Surgical replacement of the four `tools_summary` integer fields only —
    JSON round-tripping would reformat unrelated short arrays. Does NOT
    auto-modify `version`; version bumps are a deliberate human decision
    (they trigger registry republish). Drift is surfaced as a warning.
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
            raise RuntimeError(
                f'server.json: could not find tools_summary field "{field}"'
            )
        target_text = pattern.sub(rf"\g<1>{value}", target_text, count=1)
    return current_text, target_text


README_SUMMARY_TEMPLATE = (
    "The server exposes **{live} live tools{stub_clause}**, "
    "plus **{prompts} agentic SOP prompts** "
    "(two flagship cross-persona briefs — `equity_research_brief` and "
    "`screen_and_shortlist` — plus specialised chains for analyst, PM, "
    "quant, ratio, smart-money, and workflow personas) and **{resources} "
    "data resources** (`schema://{{table}}`, `reference://sp500`, "
    "`pricing://current`). Tier gating happens at the data layer — Sample "
    "/ Free tokens see Sample / S&P 500 data; Pro sees the full 19,000+-"
    "entity universe with a 15-year point-in-time window (2011 → present); "
    "Institutional unlocks the smart-money tools (insider transactions "
    "on Forms 3 / 4 / 5 / 144 + institutional ownership on Forms 13F / "
    "13D / 13G), unlimited history back to 1993, filing-event webhooks, "
    "and the commercial redistribution license."
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


def update_readme(manifest: dict) -> Tuple[str, str]:
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


def main() -> int:
    check_mode = "--check" in sys.argv
    print("Sync MCP manifest → public hub:")
    manifest = load_manifest()
    print(
        f"  loaded v{manifest['version']} — "
        f"{manifest['counts']['tools_live']} live + "
        f"{manifest['counts']['tools_stub']} stub tools, "
        f"{manifest['counts']['prompts']} prompts, "
        f"{manifest['counts']['resources']} resources"
    )

    server_current, server_target = update_server_json(manifest)
    readme_current, readme_target = update_readme(manifest)

    # ── Version drift is a FAILURE, not a warning ────────────────────────────
    #
    # This used to print "⚠ version drift" and carry on. The nightly job then
    # printed that line into a log nobody reads — every night — while the public
    # registry advertised **v2.48.0 and the live Worker ran v2.53.0**. Five
    # versions. The check saw it every single night and never once stopped
    # anything.
    #
    # A warning is not a gate. And this is not a cosmetic mismatch: `server.json`
    # is what registry.modelcontextprotocol.io serves to every agent deciding
    # whether to connect to us. A registry that describes a server we are not
    # running is a claim about our own product that is false — which is exactly
    # the trust we tell institutions never to extend to a data vendor.
    #
    # Version is still NOT auto-modified: bumping it triggers a republish to a
    # public registry, and an outward-facing publish stays a human decision. But
    # the drift now turns the build RED, so the human is asked instead of the
    # warning being buried.
    deployed_version = manifest["version"]
    registry_version = json.loads(server_current).get("version")
    version_drift = registry_version != deployed_version
    if version_drift:
        print(
            f"\n✗ VERSION DRIFT — the public registry is lying about what is running.\n"
            f"    server.json (published to the registry) : {registry_version}\n"
            f"    live Worker (mcp.valuein.biz)           : {deployed_version}\n"
            f"\n"
            f"  Fix whichever is behind:\n"
            f"    • Worker behind  → deploy the MCP.\n"
            f"    • server.json behind → set version to {deployed_version} and push;\n"
            f"      publish-mcp.yml republishes to the registry.\n"
            f"    Do the deploy FIRST — the public repo documents what is ALREADY\n"
            f"    shipped, and updating it early is a silent lie to the public."
        )

    drift: list[str] = []
    if server_current != server_target:
        drift.append("server.json")
    if readme_current != readme_target:
        drift.append("README.md")

    if check_mode:
        if drift:
            print(f"\n✗ stale: {', '.join(drift)}")
            print("  run: uv run python scripts/sync_mcp_manifest.py")
            return 1
        # A version mismatch is stale-ness too, even when every count agrees.
        if version_drift:
            return 1
        print("\n✓ in sync")
        return 0

    if drift:
        SERVER_JSON.write_text(server_target)
        README.write_text(readme_target)
        print(f"\n✓ updated: {', '.join(drift)}")
    else:
        print("\n✓ counts already in sync — no changes")

    # Counts can be perfectly in sync while the version is five releases behind —
    # that is exactly how this drifted unnoticed. Fail AFTER writing the count
    # fixes (they are correct and worth keeping) so the job is red until a human
    # resolves the version, rather than green with a buried warning.
    if version_drift:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
