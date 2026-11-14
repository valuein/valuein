"""Verify lineage: resolve any fact_id to the SEC filing it came from.

What it does: for each ``fact_id`` (given directly or read from a CSV that ``look_ahead_audit.py``
wrote) prints the company, concept, period, the value AS REPORTED in that filing, the filing's
form, filing date, acceptance time, accession number and SEC folder URL, and every other filed
version of the same number. Open the URL, find the line item, compare.
Who it is for: compliance, auditors, anyone who must trust a number before using it.
Plan: none for sample-tier facts; a fact outside your tier is reported as not found.
Optional ``--check-sec`` requests each folder URL once (SEC asks for a contact in the User-Agent:
set ``SEC_USER_AGENT="Your Name you@example.com"``).

Run:
    pip install "valuein-sdk>=1.1.0"
    python examples/proof/verify_lineage.py <fact_id> [<fact_id> ...]
    python examples/proof/verify_lineage.py --from-csv proof-output/look_ahead_audit.csv
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import LICENCE_NOTE, md_table, open_client, sec_folder_url, sql_list

FACT_ID = re.compile(r"^[0-9a-f]{64}$")


def ids_from_csv(path: Path) -> list[str]:
    """Collect every 64-hex fact_id from columns whose name ends in ``fact_id``."""
    df = pd.read_csv(path, dtype=str)
    found: list[str] = []
    for col in (c for c in df.columns if c.endswith("fact_id")):
        found += [v for v in df[col].dropna() if FACT_ID.match(v)]
    return list(dict.fromkeys(found))


def resolve(client, fact_ids: list[str]) -> pd.DataFrame:
    """One row per fact_id with its filing; unknown ids are absent from the result."""
    return client.run_query(
        "SELECT x.fact_id, x.entity_id AS cik, e.name AS company, x.standard_concept, x.concept AS "
        "xbrl_tag, x.period_start, x.period_end, x.numeric_value AS value_as_reported, x.unit, "
        "x.accession_id, f.form_type, f.filing_date, x.accepted_at, f.filing_url "
        "FROM fact x LEFT JOIN filing f ON f.accession_id = x.accession_id "
        f"LEFT JOIN entity e ON e.cik = x.entity_id WHERE x.fact_id IN ({sql_list(fact_ids)})"
    )


def other_versions(client, resolved: pd.DataFrame) -> pd.DataFrame:
    """Every filed version of the same number (same company, concept, period, unit)."""
    frames = []
    for r in resolved.itertuples():
        period = f"period_end = DATE '{pd.Timestamp(r.period_end):%Y-%m-%d}'"
        start = (
            f"period_start = DATE '{pd.Timestamp(r.period_start):%Y-%m-%d}'"
            if pd.notna(r.period_start)
            else "period_start IS NULL"
        )
        frames.append(
            client.run_query(
                "SELECT fact_id AS version_fact_id, accession_id, numeric_value, accepted_at "
                f"FROM fact WHERE entity_id = '{r.cik}' AND standard_concept = '{r.standard_concept}' "
                f"AND unit = '{r.unit}' AND priority = 1 AND {period} AND {start} "
                "ORDER BY accepted_at"
            ).assign(origin_fact_id=r.fact_id)
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def check_sec(url: str) -> str:
    """HEAD-style check that the SEC folder answers; returns ``ok`` or the error text."""
    agent = os.environ.get("SEC_USER_AGENT", "valuein-proof-kit contact-not-set")
    req = urllib.request.Request(url, headers={"User-Agent": agent})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return "ok" if resp.status == 200 else f"http {resp.status}"
    except OSError as exc:
        return f"error: {exc}"


def render(resolved: pd.DataFrame, versions: pd.DataFrame, missing: list[str]) -> str:
    """Markdown lineage report."""
    out = ["# Lineage", ""]
    for r in resolved.itertuples():
        url = (
            r.filing_url
            if isinstance(r.filing_url, str) and r.filing_url
            else sec_folder_url(r.cik, r.accession_id)
        )
        out += [
            f"## {r.company}: {r.standard_concept}, period ending {pd.Timestamp(r.period_end):%Y-%m-%d}",
            "",
            f"- fact_id `{r.fact_id}`",
            f"- value as reported in this filing: {r.value_as_reported:,.2f} {r.unit}",
            f"- filing: {r.form_type} filed {pd.Timestamp(r.filing_date):%Y-%m-%d}, accepted "
            f"{pd.Timestamp(r.accepted_at):%Y-%m-%d %H:%M} UTC, accession {r.accession_id}",
            f"- SEC folder: {url} (XBRL tag `{r.xbrl_tag}`)",
        ]
        v = versions[versions["origin_fact_id"] == r.fact_id] if not versions.empty else versions
        if len(v) > 1:
            out += ["- every filed version of this number:", ""]
            out += [
                md_table(v[["version_fact_id", "accession_id", "numeric_value", "accepted_at"]]),
                "",
            ]
        out.append("")
    if missing:
        out += ["## Not found in this tier", "", *[f"- `{m}`" for m in missing], ""]
    out += [f"_{LICENCE_NOTE}_", ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns a process exit code."""
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("fact_ids", nargs="*")
    p.add_argument("--from-csv", type=Path, help="CSV with *fact_id columns (audit output)")
    p.add_argument("--limit", type=int, default=50, help="max fact_ids to resolve (default 50)")
    p.add_argument("--check-sec", action="store_true", help="request each SEC folder once")
    p.add_argument("--out-dir", default="proof-output")
    args = p.parse_args(argv)
    ids = list(args.fact_ids)
    if args.from_csv:
        ids += ids_from_csv(args.from_csv)
    bad = [i for i in ids if not FACT_ID.match(i)]
    if bad:
        print(f"Not a fact_id (64 hex characters): {bad[:3]}", file=sys.stderr)
        return 2
    ids = list(dict.fromkeys(ids))[: args.limit]
    if not ids:
        p.print_usage(sys.stderr)
        return 2
    with open_client() as client:
        resolved = resolve(client, ids)
        versions = other_versions(client, resolved) if not resolved.empty else pd.DataFrame()
    missing = [i for i in ids if i not in set(resolved["fact_id"])]
    md = render(resolved, versions, missing)
    if args.check_sec:
        for r in resolved.itertuples():
            print(f"{r.fact_id[:12]}  {check_sec(sec_folder_url(r.cik, r.accession_id))}")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "lineage.md").write_text(md, encoding="utf-8")
    resolved.to_csv(out_dir / "lineage.csv", index=False)
    print(md)
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
