"""Survivorship check: which companies a today's-listings dataset would have silently dropped.

What it does: lists every company that filed a 10-K or 10-Q in your date range and is no longer
listed today (delisted, merged, bankrupt, deregistered), with the SEC filing evidence Valuein
holds for why (8-K Item 1.03 bankruptcy, Item 2.01 completed acquisition, Item 3.01 delisting
notice, or none found), and the share of the range's universe a survivorship-biased source would
lack. With ``--index`` it does the same for an index's members over the range.
Who it is for: quants checking a backtest universe.
Plan: none. Runs on the free sample (about five years of history); a token extends the range.
Method: "listed today" is ``entity.status = 'ACTIVE'`` (the registrant has a ticker in the SEC
ticker file when the data was built). Evidence is read from ``filing.items``; nothing is inferred
from price or name. Mirrored in the marketing audit module; change both together.

Run:
    pip install "valuein-sdk>=1.1.0"
    python examples/proof/survivorship_check.py --start 2021-01-01 --end 2024-12-31
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    INDEX_NOTICE,
    LICENCE_NOTE,
    md_table,
    open_client,
    resolve_universe,
    sec_folder_url,
    sql_list,
    write_outputs,
)

INDEX_LABELS = {"SP500": "S&P 500", "RUSSELL1000": "Russell 1000", "RUSSELL2000": "Russell 2000"}
EVIDENCE_ITEMS = {
    "1.03": "bankruptcy (8-K Item 1.03)",
    "2.01": "acquisition completed (8-K Item 2.01)",
    "3.01": "delisting notice (8-K Item 3.01)",
}


def load_companies(client, start: str, end: str, ciks: list[str] | None) -> pd.DataFrame:
    """Companies with a 10-K/10-Q filed in ``[start, end]``, with status and last periodic filing."""
    scope = f"AND e.cik IN ({sql_list(ciks)})" if ciks else ""
    return client.run_query(
        "SELECT e.cik, e.name, e.status, e.succeeded_by_cik, "
        "max(f.filing_date) AS last_periodic_filing, count(*) AS periodic_filings "
        "FROM entity e JOIN filing f ON f.entity_id = e.cik "
        "AND f.form_type IN ('10-K', '10-Q') "
        f"AND f.filing_date BETWEEN DATE '{_date(start)}' AND DATE '{_date(end)}' "
        f"WHERE 1 = 1 {scope} GROUP BY ALL"
    )


def _date(value: str) -> str:
    """Validate an ISO date string (guards the SQL built from CLI input)."""
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def load_evidence(client, ciks: list[str]) -> pd.DataFrame:
    """The latest 8-K per company carrying Item 1.03, 2.01 or 3.01 (cik, item, date, accession)."""
    if not ciks:
        return pd.DataFrame(columns=["cik", "item", "filing_date", "accession_id"])
    items = ", ".join(f"'{i}'" for i in EVIDENCE_ITEMS)
    return client.run_query(
        "SELECT cik, item, filing_date, accession_id FROM ("
        "SELECT f.entity_id AS cik, i.item, f.filing_date, f.accession_id, "
        "row_number() OVER (PARTITION BY f.entity_id, i.item ORDER BY f.filing_date DESC) AS rn "
        "FROM filing f, UNNEST(f.items) AS i(item) "
        f"WHERE f.form_type = '8-K' AND f.entity_id IN ({sql_list(ciks)}) "
        f"AND i.item IN ({items})) WHERE rn = 1"
    )


def classify(companies: pd.DataFrame, evidence: pd.DataFrame) -> pd.DataFrame:
    """Add ``reason`` and its filing to every company no longer listed today.

    Evidence counts only when the 8-K was filed within a year before the company's last
    periodic filing or after it (the company's final stretch), most specific item first.
    """
    gone = companies[companies["status"] != "ACTIVE"].copy()
    gone["last_periodic_filing"] = pd.to_datetime(gone["last_periodic_filing"])
    priority = {"1.03": 0, "2.01": 1, "3.01": 2}
    ev = evidence.copy()
    ev["filing_date"] = pd.to_datetime(ev["filing_date"])
    ev["rank"] = ev["item"].map(priority)
    ev = ev.merge(gone[["cik", "last_periodic_filing"]], on="cik")
    ev = ev[ev["filing_date"] >= ev["last_periodic_filing"] - pd.Timedelta(days=365)]
    ev = ev.sort_values(["cik", "rank"]).drop_duplicates("cik")
    gone = gone.merge(ev[["cik", "item", "filing_date", "accession_id"]], on="cik", how="left")
    gone = gone.rename(columns={"filing_date": "evidence_filed"})
    gone["reason"] = gone["item"].map(EVIDENCE_ITEMS).fillna("no 8-K evidence found")
    gone["evidence_url"] = [
        sec_folder_url(c, a) if isinstance(a, str) else ""
        for c, a in zip(gone["cik"], gone["accession_id"], strict=True)
    ]
    return gone.drop(columns=["item"]).sort_values("last_periodic_filing").reset_index(drop=True)


def index_view(client, index: str, start: str, end: str) -> pd.DataFrame:
    """Index members at any time in ``[start, end]`` (half-open spells) and whether they remain."""
    if index not in INDEX_LABELS:
        raise ValueError(f"--index must be one of {sorted(INDEX_LABELS)}")
    return client.run_query(
        "SELECT m.cik, any_value(e.name) AS name, min(m.effective_date) AS first_effective, "
        "max(m.removal_date) AS last_removal, bool_or(m.removal_date IS NULL) AS member_today "
        "FROM index_membership m LEFT JOIN entity e ON e.cik = m.cik "
        f"WHERE m.index_name = '{index}' AND m.effective_date <= DATE '{_date(end)}' "
        f"AND (m.removal_date IS NULL OR m.removal_date > DATE '{_date(start)}') GROUP BY m.cik"
    )


def render(
    gone: pd.DataFrame,
    companies: pd.DataFrame,
    start: str,
    end: str,
    idx: pd.DataFrame | None,
    label: str,
) -> str:
    """Render the report as markdown."""
    total, dropped = len(companies), len(gone)
    lines = [
        "# Survivorship check",
        "",
        f"Range: {start} to {end}. Companies that filed a 10-K or 10-Q in the range: {total:,}. "
        f"No longer listed today: {dropped:,} ({dropped / max(total, 1):.1%}). A dataset built "
        "from today's listings would not contain them.",
        "",
        "## By the filing evidence Valuein holds",
        "",
        md_table(gone["reason"].value_counts().rename_axis("reason").reset_index(name="companies")),
        "",
        "## Companies a survivorship-biased source drops (first 25 by last filing)",
        "",
        md_table(
            gone.head(25)[["cik", "name", "last_periodic_filing", "reason", "evidence_url"]].assign(
                last_periodic_filing=lambda d: d["last_periodic_filing"].dt.strftime("%Y-%m-%d")
            )
        ),
    ]
    if idx is not None:
        left = idx[~idx["member_today"]]
        lines += [
            "",
            f"## {label} members over the range",
            "",
            f"{len(idx):,} companies were members at some point; {len(left):,} "
            f"({len(left) / max(len(idx), 1):.1%}) are not members today, so a list of today's "
            "members would omit them.",
            "",
            md_table(
                left.sort_values("last_removal")
                .head(25)
                .drop(columns=["member_today"])
                .assign(
                    first_effective=lambda d: d["first_effective"].astype(str).str[:10],
                    last_removal=lambda d: d["last_removal"].astype(str).str[:10],
                )
            ),
            "",
            f"_{INDEX_NOTICE}_",
        ]
    lines += ["", f"_{LICENCE_NOTE}_", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns a process exit code."""
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--start", default="2021-01-01")
    p.add_argument("--end", default=pd.Timestamp.today().strftime("%Y-%m-%d"))
    p.add_argument("--tickers", help="comma list of tickers or CIKs (default: the whole tier)")
    p.add_argument("--index", choices=sorted(INDEX_LABELS), help="also report this index's members")
    p.add_argument("--out-dir", default="proof-output")
    args = p.parse_args(argv)
    with open_client() as client:
        ciks = None
        if args.tickers:
            items = [t.strip() for t in args.tickers.split(",") if t.strip()]
            ciks = resolve_universe(client, items)["cik"].tolist()
            if not ciks:
                print("No companies matched.", file=sys.stderr)
                return 2
        companies = load_companies(client, args.start, args.end, ciks)
        if companies.empty:
            print("No filings in that range for this tier.", file=sys.stderr)
            return 2
        gone = classify(
            companies,
            load_evidence(client, companies.loc[companies["status"] != "ACTIVE", "cik"].tolist()),
        )
        idx = index_view(client, args.index, args.start, args.end) if args.index else None
    md = render(gone, companies, args.start, args.end, idx, INDEX_LABELS.get(args.index or "", ""))
    paths = write_outputs(Path(args.out_dir), "survivorship_check", gone, md)
    print(md)
    print("Wrote:", *paths, sep="\n  ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
