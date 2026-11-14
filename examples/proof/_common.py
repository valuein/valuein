"""Shared helpers for the proof kit: client, universe resolution, SEC links, report output.

Nothing here is a scoring model. Every function reads Valuein tables (or formats what they
returned) so each number in a proof report keeps the ``fact_id`` that resolves to its filing.
"""

from __future__ import annotations

import os
import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from valuein_sdk import ValueinClient

INDEX_NOTICE = (
    "Index names are trademarks of their owners; Valuein is not affiliated with or "
    "endorsed by any index provider."
)
LICENCE_NOTE = (
    "Valuein data is licensed for inference and research only: never for training, "
    "fine-tuning or distilling a model (Terms, section 15)."
)
# Large, long-lived sample-tier names that include well-known later revisions.
DEFAULT_TICKERS = [
    "MPWR",
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "JPM",
    "XOM",
    "PFE",
    "KO",
    "INTC",
    "BA",
    "GE",
    "F",
    "GM",
    "T",
    "VZ",
    "CSCO",
    "ORCL",
    "IBM",
    "CAT",
    "MMM",
    "DIS",
    "NKE",
    "WMT",
    "HD",
    "UNH",
    "CVS",
    "TGT",
    "LOW",
    "MRK",
]


def open_client() -> ValueinClient:
    """Open a client: ``VALUEIN_TOKEN`` (or ``VALUEIN_API_KEY``) if set, else the free sample.

    Returns:
        A ``ValueinClient``; the empty key forces the no-token sample tier.
    """
    from valuein_sdk import ValueinClient  # lazy: the pure helpers import without the SDK

    token = os.environ.get("VALUEIN_TOKEN") or os.environ.get("VALUEIN_API_KEY") or ""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ValueinClient(api_key=token)


def sql_list(values: list[str]) -> str:
    """Render a list of strings as a SQL ``IN`` body, rejecting anything but safe characters."""
    for v in values:
        if not re.fullmatch(r"[A-Za-z0-9.\-]+", v):
            raise ValueError(f"unsafe identifier: {v!r}")
    return ", ".join(f"'{v}'" for v in values)


def resolve_universe(client: ValueinClient, items: list[str]) -> pd.DataFrame:
    """Resolve tickers and/or CIKs to one row per company (``cik``, ``ticker``, ``name``, ``status``).

    Args:
        client: An open client.
        items: Tickers (``AAPL``) or CIKs (``320193`` or ``0000320193``); unknown ones are
            reported on stderr by the caller via the returned frame's ``attrs['missing']``.

    Returns:
        The matched companies; ``attrs['missing']`` lists the items that matched nothing.
    """
    ciks = [i.zfill(10) for i in items if i.isdigit()]
    tickers = [i.upper() for i in items if not i.isdigit()]
    clauses = []
    if tickers:
        clauses.append(f"symbol IN ({sql_list(tickers)})")
    if ciks:
        clauses.append(f"cik IN ({sql_list(ciks)})")
    if not clauses:
        return pd.DataFrame(columns=["cik", "ticker", "name", "status"])
    df = client.run_query(
        'SELECT cik, symbol AS ticker, name, status, is_primary_ticker FROM "references" '
        f"WHERE {' OR '.join(clauses)}"
    )
    df = df.sort_values("is_primary_ticker", ascending=False, na_position="last")
    df = df.drop_duplicates("cik")[["cik", "ticker", "name", "status"]].reset_index(drop=True)
    found = set(df["cik"]) | set(df["ticker"].dropna())
    df.attrs["missing"] = [i for i in items if i.upper() not in found and i.zfill(10) not in found]
    return df


def sec_folder_url(cik: str, accession: str) -> str:
    """EDGAR folder holding every document of one filing (``cik`` may carry leading zeros)."""
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"


def md_table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub-flavoured markdown table (no extra dependency)."""
    if df.empty:
        return "_none_"
    cols = list(df.columns)
    rows = [
        "| " + " | ".join(str(v).replace("|", "/") for v in rec) + " |"
        for rec in df.itertuples(index=False)
    ]
    return "\n".join(
        ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|", *rows]
    )


def fmt_value(value: float, unit: str | None) -> str:
    """Human-readable value; the raw number stays in the CSV."""
    if unit and "shares" in unit:
        return f"{value:,.2f}"
    return f"{value:,.0f}"


def write_outputs(out_dir: Path, stem: str, csv_df: pd.DataFrame, markdown: str) -> list[Path]:
    """Write ``<stem>.csv`` and ``<stem>.md`` into ``out_dir`` and return the paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path, md_path = out_dir / f"{stem}.csv", out_dir / f"{stem}.md"
    csv_df.to_csv(csv_path, index=False)
    md_path.write_text(markdown, encoding="utf-8")
    return [csv_path, md_path]
