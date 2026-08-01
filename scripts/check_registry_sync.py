#!/usr/bin/env python3
"""
check_registry_sync.py — compare the PUBLISHED registry against the LIVE Worker.

Every other guard in this pipeline compares a *file in a repo* against the
Worker: `sync_mcp_manifest.py --check` diffs `server.json` against
`manifest.json`, and `check-version-sync.mjs` (mcp repo) diffs `version.ts` /
`package.json` / `manifest.json` against each other. All of them can be green
while the thing customers actually read — https://registry.modelcontextprotocol.io
— advertises a version we stopped serving weeks ago.

That is not hypothetical. The registry sat at 2.54.0 while prod served 2.61.0,
and it was invisible because `server.json` in the repo was correct the whole
time. Reading the repo gave a false all-clear.

The specific failure mode this closes
-------------------------------------
`sync-mcp-manifest.yml` gated its publish job on a REPO DIFF
(``needs.sync.outputs.changed == 'true'``). That gate is only correct if every
publish succeeds:

  1. sync rewrites server.json 2.67.0 -> 2.68.0, commits, pushes  (changed=true)
  2. publish runs and FAILS (registry 5xx, OIDC hiccup, network)
  3. next night: server.json already says 2.68.0, so nothing diffs
     -> changed=false -> the publish job is SKIPPED
  4. ...forever. Every subsequent run reports "already in sync" and is green.

The repo was self-consistent, so the automation concluded there was nothing to
do — while the registry stayed stale until a human noticed and hand-ran a
`workflow_dispatch`. Gating on the registry instead of on a repo diff makes the
nightly run self-healing: it re-checks reality, not a proxy for reality.

Source of truth for each side
-----------------------------
- LIVE WORKER: `https://mcp.valuein.biz/manifest.json`, always over the wire.
  Never a local checkout — see the note on MANIFEST_URL below.
- PUBLISHED: the registry's own API, filtered to the `name` in `server.json`.

Neither side is a file in this repo. That is the whole point: this is the only
check in the pipeline that can catch a repo which is perfectly self-consistent
and still describing a server nobody is running.

Usage:
  uv run python scripts/check_registry_sync.py                  # report only
  uv run python scripts/check_registry_sync.py --check          # exit 1 on drift
  uv run python scripts/check_registry_sync.py --github-output  # emit CI outputs
  uv run python scripts/check_registry_sync.py --wait-for 180   # post-publish verify

Exit codes (with --check):
  0  registry matches the live Worker
  1  DRIFT — the registry advertises a version we are not serving
  2  INDETERMINATE — could not reach the registry or the Worker

2 is deliberately distinct from 1. A registry outage must never be mistaken for
drift: the CI gate falls back to the old repo-diff behaviour on 2 rather than
firing a publish it cannot justify.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_JSON = REPO_ROOT / "server.json"

DEFAULT_REGISTRY_URL = "https://registry.modelcontextprotocol.io"
REGISTRY_URL = os.environ.get("MCP_REGISTRY_URL", DEFAULT_REGISTRY_URL)

# Deliberately NOT `sync_mcp_manifest.load_manifest`, whose resolution order
# prefers a local `~/WebstormProjects/mcp/manifest.json` sibling checkout when
# one exists. That precedence is right for the SYNC (a developer wants to sync
# against the tree they are editing) and wrong here: comparing the published
# registry against a file on someone's laptop answers a different question than
# the one this script exists to ask. "Live" has to mean the deployed Worker, so
# this always goes over the wire — in CI and locally alike.
DEFAULT_MANIFEST_URL = "https://mcp.valuein.biz/manifest.json"
MANIFEST_URL = os.environ.get("MCP_MANIFEST_URL", DEFAULT_MANIFEST_URL)

# Exit codes — named so callers read intent, not integers.
EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_INDETERMINATE = 2

_OFFICIAL_META = "io.modelcontextprotocol.registry/official"


class RegistryUnavailable(RuntimeError):
    """The registry could not be reached or returned something unparseable.

    Distinct from "the server is not published", which is a definitive answer
    that we ARE drifted, not an inability to tell.
    """


def parse_semver(version: str) -> tuple[int, ...]:
    """Parse a semver string into a comparable tuple.

    Pre-release suffixes are dropped: ordering between `2.68.0-rc.1` and
    `2.68.0` is not something this check needs to adjudicate, and treating them
    as equal is the conservative choice (it will not claim drift on a suffix
    difference alone).

    Args:
        version: A version string such as ``"2.68.0"``.

    Returns:
        Tuple of integers, e.g. ``(2, 68, 0)``. Unparseable segments become 0.
    """
    core = version.split("+", 1)[0].split("-", 1)[0]
    parts = []
    for segment in core.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def read_server_name() -> str:
    """Read the registry server name from server.json.

    Returns:
        The ``name`` field, e.g. ``"io.github.valuein/mcp-sec-edgar"``.

    Raises:
        RuntimeError: If server.json is missing or has no ``name``.
    """
    if not SERVER_JSON.exists():
        raise RuntimeError(f"server.json not found at {SERVER_JSON}")
    data = json.loads(SERVER_JSON.read_text())
    name = data.get("name")
    if not name:
        raise RuntimeError("server.json has no 'name' field")
    return name


def fetch_published_version(name: str, timeout: int = 30) -> str | None:
    """Fetch the latest version published to the MCP registry.

    Selection is deliberately defensive rather than trusting one field: the
    search endpoint returns EVERY published version (30+ rows for us), so we
    filter to exact-name matches, prefer the row the registry flags
    ``isLatest``, and fall back to the highest semver if that flag is ever
    absent. A substring search match on some other publisher's server must
    never be read as ours.

    Args:
        name: Exact registry server name from server.json.
        timeout: Per-request timeout in seconds.

    Returns:
        The published version string, or ``None`` if the server has never been
        published (a definitive answer, not a failure).

    Raises:
        RegistryUnavailable: The registry was unreachable or returned a body
            that could not be parsed.
    """
    url = f"{REGISTRY_URL}/v0/servers?search={quote(name)}&version=latest"
    req = Request(url, headers={"User-Agent": "valuein-check-registry-sync/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        raise RegistryUnavailable(f"could not reach {url}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryUnavailable(f"registry returned non-JSON from {url}: {exc}") from exc

    rows = payload.get("servers")
    if rows is None:
        raise RegistryUnavailable(f"registry response from {url} has no 'servers' key")

    ours = [r for r in rows if (r.get("server") or {}).get("name") == name]
    if not ours:
        # Reached the registry fine; it simply has no record of this server.
        return None

    flagged = [r for r in ours if (r.get("_meta") or {}).get(_OFFICIAL_META, {}).get("isLatest")]
    candidates = flagged or ours
    best = max(candidates, key=lambda r: parse_semver(r["server"].get("version", "0")))
    return best["server"].get("version")


def fetch_worker_version(timeout: int = 30) -> str:
    """Fetch the version the deployed Worker is currently serving.

    Args:
        timeout: Request timeout in seconds.

    Returns:
        The ``version`` field of the live manifest.

    Raises:
        RegistryUnavailable: The Worker manifest was unreachable or malformed.
            Reused for symmetry — either side being unreachable yields the same
            INDETERMINATE verdict, because in both cases we genuinely cannot
            tell whether we are drifted.
    """
    req = Request(MANIFEST_URL, headers={"User-Agent": "valuein-check-registry-sync/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            manifest = json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        raise RegistryUnavailable(f"could not reach {MANIFEST_URL}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryUnavailable(f"non-JSON manifest from {MANIFEST_URL}: {exc}") from exc

    version = manifest.get("version")
    if not version:
        raise RegistryUnavailable(f"manifest at {MANIFEST_URL} has no 'version' field")
    return version


def emit_github_output(**pairs: str) -> None:
    """Append key=value pairs to $GITHUB_OUTPUT when running under Actions.

    A no-op outside CI, so the script stays runnable locally.

    Args:
        **pairs: Output names mapped to their string values.
    """
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.writelines(f"{key}={value}\n" for key, value in pairs.items())


def compare(wait_for: int = 0, expect: str | None = None) -> tuple[int, str | None, str | None]:
    """Compare the published registry version against a target version.

    Args:
        wait_for: Seconds to keep re-polling the registry while it disagrees.
            Used after a publish, where the registry may take a moment to
            reflect the new version; a mismatch during that window is
            propagation lag, not a failed publish. 0 disables polling.
        expect: Target version to require. ``None`` (the default) targets the
            LIVE WORKER — the drift question, and what the nightly gate asks.
            Passing an explicit version instead asks the narrower post-publish
            question "did the thing I just published actually land?", which is
            deliberately NOT phrased against the Worker: if a newer version
            deploys while a publish is in flight, registry != worker is briefly
            true and correct, and failing the publish job for it would be a red
            build reporting someone else's race. The next sync run closes that
            gap on its own.

    Returns:
        Tuple of ``(exit_code, registry_version, target_version)``. Either
        version may be ``None`` when it could not be determined.
    """
    if expect:
        target = expect
        print(f"  expecting:        {target} (just published)")
    else:
        try:
            target = fetch_worker_version()
        except RegistryUnavailable as exc:
            print(f"  ⚠ {exc}")
            return EXIT_INDETERMINATE, None, None
        print(f"  live Worker:      {target}")

    name = read_server_name()
    deadline = time.monotonic() + max(0, wait_for)
    attempt = 0
    published: str | None = None

    while True:
        attempt += 1
        try:
            published = fetch_published_version(name)
        except RegistryUnavailable as exc:
            # Transient registry trouble during a wait window is worth retrying;
            # with no wait window it is immediately indeterminate.
            if time.monotonic() < deadline:
                print(f"  … registry unreachable (attempt {attempt}), retrying: {exc}")
                time.sleep(10)
                continue
            print(f"  ⚠ {exc}")
            return EXIT_INDETERMINATE, None, target

        if published == target:
            print(f"  registry:         {published}")
            print(f"✓ registry advertises {target}")
            return EXIT_OK, published, target

        if time.monotonic() < deadline:
            shown = published or "(not published)"
            print(f"  … registry at {shown}, waiting for {target} (attempt {attempt})")
            time.sleep(10)
            continue

        break

    shown = published or "(not published)"
    print(f"  registry:         {shown}")
    print(f"✗ DRIFT — registry advertises {shown}, expected {target}")
    return EXIT_DRIFT, published, target


def main() -> int:
    """CLI entry point.

    Returns:
        Process exit code. Always 0 unless ``--check`` is passed, so the
        informational mode can be dropped into a workflow without gating it.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 on drift, 2 if it could not be determined",
    )
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="append registry_stale/registry_version/worker_version to $GITHUB_OUTPUT",
    )
    parser.add_argument(
        "--wait-for",
        type=int,
        default=0,
        metavar="SECONDS",
        help="poll the registry for up to N seconds (post-publish propagation)",
    )
    parser.add_argument(
        "--expect",
        metavar="VERSION",
        help=(
            "require this exact version instead of whatever the live Worker "
            "serves; use 'server.json' to read it from the file being published"
        ),
    )
    args = parser.parse_args()

    expect = args.expect
    if expect == "server.json":
        # The post-publish caller wants "did MY publish land?", and the honest
        # source for that is the file mcp-publisher was just handed — not the
        # Worker, which may already have moved on.
        expect = json.loads(SERVER_JSON.read_text()).get("version")
        if not expect:
            print("✗ server.json has no 'version' field")
            return EXIT_INDETERMINATE

    if expect:
        print(f"Checking the published registry reached {expect}…")
    else:
        print("Checking published registry against the live Worker…")
    code, registry_version, worker_version = compare(wait_for=args.wait_for, expect=expect)

    if args.github_output:
        # 'unknown' is a first-class value, NOT folded into 'false'. The publish
        # gate treats it as "fall back to the repo-diff signal" — a registry
        # outage must not silently look like "everything is in sync".
        stale = {EXIT_OK: "false", EXIT_DRIFT: "true"}.get(code, "unknown")
        emit_github_output(
            registry_stale=stale,
            registry_version=registry_version or "",
            worker_version=worker_version or "",
        )

    if args.check:
        return code
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
