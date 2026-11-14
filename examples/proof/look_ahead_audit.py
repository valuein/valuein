"""Look-ahead audit: how many reported numbers changed after the day the market first saw them.

What it does: for each company and metric (revenue, net income, total assets, operating cash flow,
diluted EPS) it keeps every version of a number as each filing reported it, compares the FIRST
reported value with the LATEST one, and counts what a backtest on latest-restated data would have
"known" before the market did. Every version carries a ``fact_id`` that resolves to its filing
(``verify_lineage.py``).
Who it is for: quants and systematic funds auditing a backtest dataset.
Plan: none. Runs on the free sample; set VALUEIN_TOKEN for your own universe.
Method: key = company, concept, period, unit. Versions are ordered by filing ACCEPTANCE time
(``fact.accepted_at``), never by period end. A value "changed" when the latest differs from the
first by more than ``--min-change`` (relative, default 0.1%). Per-share figures can change because
of a stock split rather than a correction; the report keeps them, flagged by concept.
Behaviour is mirrored in the marketing audit module; change both together.

Run:
    pip install "valuein-sdk>=1.1.0"
    python examples/proof/look_ahead_audit.py --tickers MPWR,AAPL,MSFT
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    DEFAULT_TICKERS,
    LICENCE_NOTE,
    fmt_value,
    md_table,
    open_client,
    resolve_universe,
    sec_folder_url,
    sql_list,
    write_outputs,
)

METRICS = ["TotalRevenue", "NetIncome", "TotalAssets", "OperatingCashFlow", "EPSDiluted"]
KEY = ["cik", "standard_concept", "period_start", "period_end", "unit"]
BINS = [0.001, 0.01, 0.05, 0.10, 0.50, float("inf")]
BIN_LABELS = ["0.1-1%", "1-5%", "5-10%", "10-50%", ">50%"]


def load_versions(client, ciks: list[str], periods: str = "all") -> pd.DataFrame:
    """Every filed version of the key metrics for ``ciks`` (one row per fact per filing).

    Args:
        client: An open ``ValueinClient``.
        ciks: Ten-digit CIKs.
        periods: ``annual``, ``quarterly`` or ``all``. Flow concepts are kept at 3-month and
            12-month spans only (10-Q cash flow is year-to-date, so it appears in Q1 only);
            balance-sheet concepts are point-in-time.

    Returns:
        Columns ``fact_id, cik, accession_id, standard_concept, numeric_value, unit,
        period_start, period_end, accepted_at``.
    """
    spans = {
        "annual": "period_span_days BETWEEN 350 AND 380",
        "quarterly": "period_span_days BETWEEN 80 AND 100",
        "all": "(period_span_days BETWEEN 80 AND 100 OR period_span_days BETWEEN 350 AND 380)",
    }
    span_sql = f"AND (period_span_days IS NULL OR {spans[periods]})"
    return client.run_query(
        "SELECT fact_id, entity_id AS cik, accession_id, standard_concept, numeric_value, unit, "
        "period_start, period_end, accepted_at FROM fact "
        f"WHERE priority = 1 AND numeric_value IS NOT NULL AND entity_id IN ({sql_list(ciks)}) "
        f"AND standard_concept IN ({sql_list(METRICS)}) {span_sql}"
    )


def point_in_time(versions: pd.DataFrame, as_of: str | pd.Timestamp) -> pd.DataFrame:
    """The version of each number a user could see on ``as_of``: latest filing accepted by then."""
    cutoff = pd.Timestamp(as_of, tz="UTC")
    known = versions[pd.to_datetime(versions["accepted_at"], utc=True) <= cutoff]
    known = known.sort_values("accepted_at")
    return known.groupby(KEY, dropna=False, sort=False).tail(1).reset_index(drop=True)


def as_of_drift(versions: pd.DataFrame, as_of: str, min_change: float = 0.001) -> str:
    """One sentence: how many numbers visible on ``as_of`` differ from today's latest value."""
    pit = point_in_time(versions, as_of)
    latest = (
        versions.sort_values("accepted_at")
        .groupby(KEY, dropna=False, sort=False)
        .tail(1)[[*KEY, "numeric_value"]]
        .rename(columns={"numeric_value": "latest_value"})
    )
    merged = pit.merge(latest, on=KEY, how="left")
    gap = (merged["numeric_value"] - merged["latest_value"]).abs()
    differ = int((gap > merged["numeric_value"].abs() * min_change).sum())
    return (
        f"{differ} of {len(merged):,} numbers visible on {as_of} differ from the value in the "
        "latest filing for the same period."
    )


def audit(versions: pd.DataFrame, min_change: float = 0.001) -> pd.DataFrame:
    """One row per company-period: first reported value, latest value and when it changed.

    Args:
        versions: Output of :func:`load_versions`.
        min_change: Relative change below which a difference is treated as rounding.

    Returns:
        Columns ``cik, standard_concept, period_end, unit, n_versions, first_value, first_fact_id,
        first_accession, first_accepted_at, latest_value, latest_fact_id, latest_accession,
        latest_accepted_at, changed_at, rel_change, changed, window_days``. ``changed_at`` is the
        first filing whose value differs from the first by more than ``min_change``;
        ``window_days`` is how long the market only knew the first value.
    """
    if versions.empty:
        return pd.DataFrame()
    v = versions.copy()
    v["accepted_at"] = pd.to_datetime(v["accepted_at"], utc=True)
    v = v.sort_values(["accepted_at", "accession_id"])
    rows = []
    for _, g in v.groupby(KEY, dropna=False, sort=False):
        first, last = g.iloc[0], g.iloc[-1]
        denom = abs(first["numeric_value"])
        diff = abs(last["numeric_value"] - first["numeric_value"])
        rel = (diff / denom) if denom else (0.0 if diff == 0 else float("inf"))
        changed = rel > min_change
        changed_at = pd.NaT
        if changed:
            for _, r in g.iterrows():
                d = abs(r["numeric_value"] - first["numeric_value"])
                if (d / denom if denom else float(d != 0)) > min_change:
                    changed_at = r["accepted_at"]
                    break
        rows.append(
            {
                "cik": first["cik"],
                "standard_concept": first["standard_concept"],
                "period_end": first["period_end"],
                "unit": first["unit"],
                "n_versions": len(g),
                "first_value": first["numeric_value"],
                "first_fact_id": first["fact_id"],
                "first_accession": first["accession_id"],
                "first_accepted_at": first["accepted_at"],
                "latest_value": last["numeric_value"],
                "latest_fact_id": last["fact_id"],
                "latest_accession": last["accession_id"],
                "latest_accepted_at": last["accepted_at"],
                "changed_at": changed_at,
                "rel_change": rel,
                "changed": changed,
                "window_days": (changed_at - first["accepted_at"]).days if changed else 0,
            }
        )
    return pd.DataFrame(rows)


def magnitude_distribution(result: pd.DataFrame) -> pd.DataFrame:
    """Count of changed company-periods per relative-change bucket."""
    changed = result[result["changed"]]
    cut = pd.cut(changed["rel_change"], bins=BINS, labels=BIN_LABELS, right=False)
    counts = cut.value_counts().reindex(BIN_LABELS, fill_value=0)
    return pd.DataFrame({"change_size": counts.index, "company_periods": counts.values})


def biggest(result: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """The ``n`` largest changes by relative size, excluding per-share (split-prone) concepts."""
    pool = result[result["changed"] & (result["standard_concept"] != "EPSDiluted")]
    return pool.sort_values("rel_change", ascending=False).head(n).reset_index(drop=True)


def render_markdown(
    result: pd.DataFrame, names: dict[str, str], universe_n: int, args, drift: str = ""
) -> str:
    """Render the audit report as markdown (counts, distribution, top changes, gap narrative)."""
    total, changed = len(result), int(result["changed"].sum())
    reread = int((result["n_versions"] > 1).sum())
    top = biggest(result)
    lines = [
        "# Look-ahead audit",
        "",
        f"Universe: {universe_n} companies. Company-periods checked: {total:,}; filed more than "
        f"once: {reread:,}; value changed by more than {args.min_change:.1%}: {changed:,}"
        f" ({changed / total:.1%} of all, {changed / max(reread, 1):.1%} of re-filed).",
        "",
        "Ordered by filing acceptance time. First = the value the market saw first; latest = the "
        "value in the most recent filing that reports the same period.",
        "",
        "## Size of the changes",
        "",
        md_table(magnitude_distribution(result)),
        "",
        "## By metric",
        "",
        md_table(
            result.groupby("standard_concept")
            .agg(company_periods=("changed", "size"), changed=("changed", "sum"))
            .reset_index()
        ),
        "",
        "## The 10 biggest (excluding per-share figures)",
        "",
    ]
    rows = []
    for r in top.itertuples():
        rows.append(
            {
                "company": names.get(r.cik, r.cik),
                "metric": r.standard_concept,
                "period_end": str(r.period_end)[:10],
                "first": fmt_value(r.first_value, r.unit),
                "first_fact_id": r.first_fact_id,
                "latest": fmt_value(r.latest_value, r.unit),
                "latest_fact_id": r.latest_fact_id,
                "change": f"{(r.latest_value - r.first_value) / abs(r.first_value):+.1%}"
                if r.first_value
                else "n/a",
            }
        )
    lines += [md_table(pd.DataFrame(rows)), "", "## What a latest-restated backtest saw early", ""]
    for r in top.itertuples():
        lines.append(
            f"- {names.get(r.cik, r.cik)} {r.standard_concept}, period ending "
            f"{str(r.period_end)[:10]}: from {r.first_accepted_at:%Y-%m-%d} to "
            f"{r.changed_at:%Y-%m-%d} the market knew {fmt_value(r.first_value, r.unit)} "
            f"([filing]({sec_folder_url(r.cik, r.first_accession)}), fact_id `{r.first_fact_id}`); "
            f"data holding only the latest value shows {fmt_value(r.latest_value, r.unit)} "
            f"([filing]({sec_folder_url(r.cik, r.latest_accession)}), fact_id `{r.latest_fact_id}`)"
            f" for those {r.window_days} days."
        )
    if args.as_of:
        lines += ["", f"## Point-in-time check as of {args.as_of}", "", drift]
    lines += [
        "",
        "A change is not always a correction: spin-offs and discontinued operations recast prior "
        "periods, and splits rescale per-share figures. Each fact_id opens the filing so you can "
        "read why.",
    ]
    lines += [
        "",
        "Resolve any fact_id to its SEC filing: `python verify_lineage.py <fact_id>`.",
        "",
    ]
    lines += [f"_{LICENCE_NOTE}_", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns a process exit code."""
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--tickers", help="comma list of tickers or CIKs (default: a sample universe)")
    p.add_argument("--periods", choices=["annual", "quarterly", "all"], default="all")
    p.add_argument("--min-change", type=float, default=0.001, help="relative, default 0.001")
    p.add_argument("--as-of", help="also count values that differ between this date and today")
    p.add_argument("--out-dir", default="proof-output")
    args = p.parse_args(argv)

    items = (
        [t.strip() for t in args.tickers.split(",") if t.strip()]
        if args.tickers
        else DEFAULT_TICKERS
    )
    with open_client() as client:
        universe = resolve_universe(client, items)
        if universe.empty:
            print("No companies matched; check the tickers or CIKs.", file=sys.stderr)
            return 2
        if universe.attrs.get("missing"):
            print(f"Not found in this tier: {universe.attrs['missing']}", file=sys.stderr)
        versions = load_versions(client, universe["cik"].tolist(), args.periods)
    result = audit(versions, args.min_change)
    if result.empty:
        print("No metric facts found for this universe.", file=sys.stderr)
        return 2
    names = dict(zip(universe["cik"], universe["ticker"].fillna(universe["name"]), strict=False))
    drift = as_of_drift(versions, args.as_of, args.min_change) if args.as_of else ""
    md = render_markdown(result, names, len(universe), args, drift)
    out = result.assign(company=result["cik"].map(names))
    paths = write_outputs(Path(args.out_dir), "look_ahead_audit", out, md)
    print(md)
    print("Wrote:", *paths, sep="\n  ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
