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
            raise RuntimeError(
                f'server.json: could not find tools_summary field "{field}"'
            )
        target_text = pattern.sub(rf"\g<1>{value}", target_text, count=1)

    # Top-level version → the live Worker's. Anchored to the FIRST `"version"`
    # (server.json's own), not a nested one inside packages[]/remotes[].
    deployed_version = manifest["version"]
    version_pattern = re.compile(r'("version"\s*:\s*")([^"]+)(")')
    if not version_pattern.search(target_text):
        raise RuntimeError('server.json: could not find a top-level "version" field')
    target_text = version_pattern.sub(
        rf"\g<1>{deployed_version}\g<3>", target_text, count=1
    )

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

    drift: list[str] = []
    if server_current != server_target:
        drift.append("server.json")
    if readme_current != readme_target:
        drift.append("README.md")

    if check_mode:
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
        SERVER_JSON.write_text(server_target)
        README.write_text(readme_target)
        note = f" (version {registry_version}→{deployed_version})" if version_behind else ""
        print(f"\n✓ updated: {', '.join(drift)}{note}")
        return 0

    print("\n✓ already in sync — no changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
