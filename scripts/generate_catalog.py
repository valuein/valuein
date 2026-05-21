"""
generate_catalog.py
===================
Generates the public-facing data catalog from the canonical standardized-concept
list published in the R2 ``manifest.json``.

Single source of truth
----------------------
The list of canonical ``fact.standard_concept`` values is no longer hardcoded in
this script.  It is sourced directly from the live, publicly readable R2 manifest
(no API token required):

    https://data.valuein.biz/v1/sample/manifest

The manifest carries a top-level ``standard_concepts`` key produced by the
pipeline (``data-pipeline/run_exports.py`` from
``services/accounting/definitions.py``).  Two shapes are supported so the catalog
keeps working across the pipeline contract migration:

  * **Rich shape (current contract)** — ``list[dict]``, each entry carrying::

        standard_concept, level, statement_type, category, definition,
        unit_default, is_flow, bloomberg_equivalent, factset_equivalent,
        gaap_ifrs_comparable

  * **Legacy shape** — ``list[str]`` of concept names only.  Name-only entries
    are surfaced with empty definition/category/statement_type so the catalog
    still lists them; re-run after the next pipeline export to backfill the rich
    fields.

Outputs:
  docs/data_catalog.md       — Human-readable Markdown for analysts and integration partners.
  docs/data_catalog.json     — Machine-readable JSON for SDK metadata and docs sites.
  docs/DATA_CATALOG.xlsx     — Excel workbook for financial analysts (updates sheet
                               "5. Standardized Concepts" and refreshes the generated date
                               on the Overview sheet; all other sheets are preserved).

Run from the repo root:
    uv run python scripts/generate_catalog.py

Override the manifest source for testing:
    VALUEIN_MANIFEST_URL=https://example/manifest uv run python scripts/generate_catalog.py

Re-run whenever STANDARD_DEFINITIONS in data-pipeline/services/accounting/definitions.py
changes AND a fresh pipeline export has been published — this script reflects
exactly what the live manifest exposes, not a local copy.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Manifest source — the canonical standardized-concept list lives here.
# Publicly readable, no API token required.
# ---------------------------------------------------------------------------

DEFAULT_MANIFEST_URL = "https://data.valuein.biz/v1/sample/manifest"
_MANIFEST_TIMEOUT_SECONDS = 30

_DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")

# Canonical statement-type ordering for the Markdown sections. Any
# statement_type returned by the manifest that is not listed here is appended
# afterwards in first-seen order; name-only/legacy concepts fall into the
# "Uncategorized" bucket which always sorts last.
_UNCATEGORIZED = "Uncategorized"
_STATEMENT_ORDER = [
    "Income Statement",
    "Balance Sheet",
    "Cash Flow Statement",
]


class CatalogError(RuntimeError):
    """Raised when the catalog cannot be generated (e.g. manifest unavailable
    or has not yet published any standardized concepts)."""


# ---------------------------------------------------------------------------
# Manifest fetch + normalisation
# ---------------------------------------------------------------------------


def _manifest_url() -> str:
    """Return the manifest URL, honouring the VALUEIN_MANIFEST_URL override."""
    return (
        os.environ.get("VALUEIN_MANIFEST_URL", DEFAULT_MANIFEST_URL).strip() or DEFAULT_MANIFEST_URL
    )


def fetch_manifest(url: str | None = None) -> dict:
    """Fetch and parse the R2 manifest JSON.

    Args:
        url: Manifest URL. Defaults to ``VALUEIN_MANIFEST_URL`` or
            ``DEFAULT_MANIFEST_URL``.

    Returns:
        The parsed manifest as a dict.

    Raises:
        CatalogError: If the request fails or the body is not a JSON object.
    """
    target = url or _manifest_url()
    req = urllib.request.Request(target, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_MANIFEST_TIMEOUT_SECONDS) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
        raise CatalogError(
            f"Manifest request failed with HTTP {exc.code} for {target}: {exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:  # pragma: no cover - network dependent
        raise CatalogError(f"Could not reach the manifest at {target}: {exc.reason}") from exc

    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CatalogError(f"Manifest at {target} returned invalid JSON: {exc}") from exc

    if not isinstance(manifest, dict):
        raise CatalogError(
            f"Manifest at {target} is not a JSON object (got {type(manifest).__name__})."
        )
    return manifest


def normalise_concepts(raw: object) -> list[dict]:
    """Normalise the manifest ``standard_concepts`` value into catalog rows.

    Handles BOTH manifest shapes:

      * ``dict`` entries (rich contract) — full fields are carried through.
      * ``str`` entries (legacy contract) — treated as name-only; definition,
        statement_type and category are left empty.

    Each returned row has a stable set of keys regardless of input shape::

        name, statement, category, unit, level, is_flow, definition,
        bloomberg_equivalent, factset_equivalent, gaap_ifrs_comparable

    Rows are sorted by concept name (case-insensitive).

    Args:
        raw: The raw ``manifest["standard_concepts"]`` value.

    Returns:
        A sorted list of normalised concept rows.

    Raises:
        CatalogError: If ``raw`` is missing/null/empty, or any entry is an
            unsupported type.
    """
    if raw is None:
        raise CatalogError(
            "Manifest field 'standard_concepts' is null. The manifest has not "
            "published the concept list yet — run a data-pipeline export "
            "(run_exports.py) first, then re-run this script."
        )
    if not isinstance(raw, list):
        raise CatalogError(
            f"Manifest field 'standard_concepts' must be a list (got {type(raw).__name__})."
        )
    if not raw:
        raise CatalogError(
            "Manifest field 'standard_concepts' is empty. The manifest has not "
            "published the concept list yet — run a data-pipeline export "
            "(run_exports.py) first, then re-run this script."
        )

    rows: list[dict] = []
    for entry in raw:
        if isinstance(entry, str):
            name = entry.strip()
            if not name:
                continue
            rows.append(_blank_row(name))
        elif isinstance(entry, dict):
            name = str(entry.get("standard_concept", "")).strip()
            if not name:
                # Skip malformed rich entries that carry no name.
                continue
            rows.append(
                {
                    "name": name,
                    "statement": _clean(entry.get("statement_type")),
                    "category": _clean(entry.get("category")),
                    "unit": _clean(entry.get("unit_default")),
                    "level": _clean(entry.get("level")),
                    "is_flow": entry.get("is_flow"),
                    "definition": _clean(entry.get("definition")),
                    "bloomberg_equivalent": _clean(entry.get("bloomberg_equivalent")),
                    "factset_equivalent": _clean(entry.get("factset_equivalent")),
                    "gaap_ifrs_comparable": _clean(entry.get("gaap_ifrs_comparable")),
                }
            )
        else:
            raise CatalogError(
                "Unsupported entry in 'standard_concepts': expected str or dict, "
                f"got {type(entry).__name__}."
            )

    if not rows:
        raise CatalogError(
            "Manifest 'standard_concepts' contained no usable concept names. "
            "Run a data-pipeline export first, then re-run this script."
        )

    rows.sort(key=lambda r: r["name"].lower())
    return rows


def _blank_row(name: str) -> dict:
    """Build a name-only catalog row for a legacy ``list[str]`` entry."""
    return {
        "name": name,
        "statement": "",
        "category": "",
        "unit": "",
        "level": "",
        "is_flow": None,
        "definition": "",
        "bloomberg_equivalent": "",
        "factset_equivalent": "",
        "gaap_ifrs_comparable": "",
    }


def _clean(value: object) -> str:
    """Coerce a manifest value to a trimmed string ('' for None)."""
    if value is None:
        return ""
    return str(value).strip()


def _statement_order(concepts: list[dict]) -> list[str]:
    """Build the section order: canonical statements first, then any others
    seen in the manifest, with the catch-all bucket always last."""
    seen: list[str] = []
    for c in concepts:
        stmt = c["statement"] or _UNCATEGORIZED
        if stmt not in seen:
            seen.append(stmt)
    ordered = [s for s in _STATEMENT_ORDER if s in seen]
    ordered += [s for s in seen if s not in _STATEMENT_ORDER and s != _UNCATEGORIZED]
    if _UNCATEGORIZED in seen:
        ordered.append(_UNCATEGORIZED)
    return ordered


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def generate(url: str | None = None) -> tuple[str, str, str]:
    """Generate all three catalog outputs from the live manifest.

    Args:
        url: Optional manifest URL override (defaults to env / built-in).

    Returns:
        ``(md_path, json_path, xlsx_path)``.

    Raises:
        CatalogError: If the manifest is unreachable or has not published the
            standardized-concept list.
    """
    source = url or _manifest_url()
    manifest = fetch_manifest(source)
    concepts = normalise_concepts(manifest.get("standard_concepts"))
    print(f"Sourced {len(concepts)} standardized concepts from {source}")

    os.makedirs(_DOCS_DIR, exist_ok=True)
    md_path = os.path.normpath(os.path.join(_DOCS_DIR, "data_catalog.md"))
    json_path = os.path.normpath(os.path.join(_DOCS_DIR, "data_catalog.json"))
    xlsx_path = os.path.normpath(os.path.join(_DOCS_DIR, "DATA_CATALOG.xlsx"))
    _write_markdown(md_path, concepts, source)
    _write_json(json_path, concepts, source)
    _update_xlsx(xlsx_path, concepts)
    print(f"Generated {md_path}")
    print(f"Generated {json_path}")
    print(f"Updated   {xlsx_path}")
    return md_path, json_path, xlsx_path


def _write_markdown(path: str, concepts: list[dict], source: str) -> None:
    today = date.today().isoformat()
    by_statement: dict[str, list[dict]] = {}
    for c in concepts:
        by_statement.setdefault(c["statement"] or _UNCATEGORIZED, []).append(c)

    lines: list[str] = [
        "# Valuein Data Catalog",
        "",
        f"> **Last updated**: {today}  ",
        f"> **Standardized concepts**: {len(concepts)}  ",
        "> **Historical coverage**: 1994 – present  ",
        "> **Coverage target**: ≥ 95% of all SEC EDGAR financial facts",
        "",
        "---",
        "",
        "## Overview",
        "",
        "The Valuein pipeline normalizes 15,000+ raw SEC EDGAR XBRL tags into a set of "
        "canonical financial concepts listed below.  Every fact in the dataset carries:",
        "",
        "- `standard_concept` — the canonical name from this catalog (or `'Other'` if unmapped)",
        "- `accuracy_score` — standardization confidence (0.0–1.0)",
        "",
        "### Accuracy Score Guide",
        "",
        "| Score | Meaning | Recommended use |",
        "|-------|---------|----------------|",
        "| 1.00 | Human-verified exact match | Any query |",
        "| 0.70–0.85 | US GAAP taxonomy rule | Any query |",
        "| 0.45–0.65 | Automated pattern match | Use with review |",
        "| 0.30–0.44 | Keyword heuristic | Research / exploratory only |",
        "| 0.00 | Unmapped (`standard_concept = 'Other'`) | Exclude from analytics |",
        "",
        "**Recommended filter for production queries:** `accuracy_score >= 0.70`",
        "",
        "---",
        "",
    ]

    for stmt in _statement_order(concepts):
        stmt_concepts = by_statement.get(stmt, [])
        if not stmt_concepts:
            continue
        lines += [f"## {stmt}", ""]
        for c in stmt_concepts:
            lines += [f"### `{c['name']}`", ""]
            meta: list[str] = []
            if c["unit"]:
                meta.append(f"**Unit:** {c['unit']}")
            if c["category"]:
                meta.append(f"**Category:** {c['category']}")
            if c["is_flow"] is not None:
                meta.append(f"**Flow:** {'yes' if c['is_flow'] else 'no'}")
            if meta:
                lines += ["  ·  ".join(meta), ""]
            if c["definition"]:
                lines += [c["definition"], ""]

    lines += [
        "---",
        "",
        "*This catalog is generated from the live Valuein R2 manifest "
        f"(`{source}`). The underlying matching rules are proprietary — this "
        "document describes what each concept represents, not how it is detected.*",
        "",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_json(path: str, concepts: list[dict], source: str) -> None:
    payload = {
        "generated": date.today().isoformat(),
        "source": source,
        "concept_count": len(concepts),
        "coverage_target": ">=95%",
        "accuracy_score_guide": {
            "1.00": "human_verified",
            "0.70-0.85": "taxonomy_rule",
            "0.45-0.65": "pattern_match",
            "0.30-0.44": "keyword_heuristic",
            "0.00": "unmapped",
        },
        "concepts": concepts,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _update_xlsx(path: str, concepts: list[dict]) -> None:
    """Add/replace the 'Standardized Concepts' sheet and refresh the Overview date."""
    wb = openpyxl.load_workbook(path)

    # --- Refresh generated date on the Overview sheet -------------------------
    overview = wb["1. Overview"]
    for row in overview.iter_rows():
        for cell in row:
            if cell.value == "Generated:" or (
                isinstance(cell.value, str) and cell.value.startswith("Generated:")
            ):
                # Value is in the next column
                next_cell = overview.cell(row=cell.row, column=cell.column + 1)
                next_cell.value = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                break

    # --- Build (or replace) sheet "5. Standardized Concepts" -----------------
    sheet_name = "5. Standardized Concepts"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)

    # Styles matching the existing workbook
    header_fill = PatternFill("solid", fgColor="4A148C")  # deep purple
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="left", vertical="center", wrap_text=False)

    alt_fill = PatternFill("solid", fgColor="F3E5F5")  # very light purple for alternating rows
    body_font = Font(name="Calibri", size=11)
    wrap_align = Alignment(horizontal="left", vertical="top", wrap_text=True)
    top_align = Alignment(horizontal="left", vertical="top", wrap_text=False)

    # Column definitions: (header, width, attr)
    columns = [
        ("standard_concept", 28, "name"),
        ("Financial Statement", 22, "statement"),
        ("Category", 22, "category"),
        ("Unit", 14, "unit"),
        ("Definition", 80, "definition"),
    ]

    # Header row
    for col_idx, (header, width, _) in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws.row_dimensions[1].height = 20
    ws.freeze_panes = "A2"

    # Data rows
    for row_idx, concept in enumerate(concepts, start=2):
        is_alt = row_idx % 2 == 0
        fill = alt_fill if is_alt else PatternFill(fill_type=None)

        for col_idx, (_, _, attr) in enumerate(columns, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=concept[attr])
            cell.font = body_font
            cell.fill = fill
            # Definition column wraps; others stay single-line
            cell.alignment = wrap_align if attr == "definition" else top_align

        ws.row_dimensions[row_idx].height = 60  # tall enough for wrapped definitions

    # Add a footer note below the data
    footer_row = len(concepts) + 3
    footer_cell = ws.cell(
        row=footer_row,
        column=1,
        value="Filter accuracy_score >= 0.70 for high-confidence analytics. "
        "standard_concept = 'Other' means the tag was not mapped.",
    )
    footer_cell.font = Font(name="Calibri", size=10, italic=True, color="757575")
    footer_cell.alignment = Alignment(horizontal="left")

    wb.save(path)


if __name__ == "__main__":
    generate()
