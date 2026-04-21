"""
generate_catalog.py
===================
Generates the public-facing data catalog from the canonical concept definitions.

Outputs:
  docs/data_catalog.md       — Human-readable Markdown for analysts and integration partners.
  docs/data_catalog.json     — Machine-readable JSON for SDK metadata and docs sites.
  docs/DATA_CATALOG.xlsx     — Excel workbook for financial analysts (updates sheet
                               "5. Standardized Concepts" and refreshes the generated date
                               on the Overview sheet; all other sheets are preserved).

Run from the repo root:
    uv run python scripts/generate_catalog.py

Re-run whenever STANDARD_DEFINITIONS in data-pipeline/services/accounting/definitions.py
changes.  The canonical concept names in this script must stay in sync with what the
pipeline writes to fact.standard_concept.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Canonical concept definitions
# Source: data-pipeline/services/accounting/definitions.py (STANDARD_DEFINITIONS)
# These names are what SDK users query against fact.standard_concept.
# ---------------------------------------------------------------------------

CONCEPTS: list[dict] = [
    # Income Statement — Revenue
    {
        "name": "TotalRevenue",
        "statement": "Income Statement",
        "unit": "USD",
        "description": (
            "Total top-line revenue recognized during the period. Represents the aggregate "
            "net sales of goods and services before any deductions for costs or expenses. "
            "Segment sub-totals, deferred revenue balances, and revenue-adjacent items are "
            "excluded to prevent double-counting."
        ),
    },
    {
        "name": "CostOfRevenue",
        "statement": "Income Statement",
        "unit": "USD",
        "description": (
            "Direct costs attributable to the production of goods sold or services delivered. "
            "Includes raw materials, direct labor, and manufacturing overhead. Excludes "
            "operating expenses such as SG&A and R&D."
        ),
    },
    {
        "name": "GrossProfit",
        "statement": "Income Statement",
        "unit": "USD",
        "description": (
            "Revenue minus Cost of Revenue. Represents the profit a company earns after "
            "subtracting the direct costs of producing its products or delivering its services, "
            "before operating expenses, interest, and taxes."
        ),
    },
    # Income Statement — Expenses
    {
        "name": "OperatingExpenses",
        "statement": "Income Statement",
        "unit": "USD",
        "description": (
            "Total operating expenses incurred in the ordinary course of business, including "
            "SG&A, R&D, and other recurring operational costs. Excludes non-operating items "
            "such as interest expense and income tax."
        ),
    },
    {
        "name": "ResearchAndDevelopment",
        "statement": "Income Statement",
        "unit": "USD",
        "description": (
            "Costs incurred in the research and development of new products, technologies, or "
            "processes. A forward-looking investment indicator — high R&D as a percentage of "
            "revenue often signals innovation-driven growth strategies."
        ),
    },
    {
        "name": "SellingGeneralAdmin",
        "statement": "Income Statement",
        "unit": "USD",
        "description": (
            "Selling, General and Administrative expenses — the overhead costs of running the "
            "business not directly tied to production. Includes marketing, executive "
            "compensation, rent, legal, and other administrative costs."
        ),
    },
    # Income Statement — Bottom line
    {
        "name": "OperatingIncome",
        "statement": "Income Statement",
        "unit": "USD",
        "description": (
            "Earnings from core business operations before interest income/expense and income "
            "taxes (EBIT proxy). Calculated as Gross Profit minus Operating Expenses. A key "
            "measure of operational efficiency independent of capital structure."
        ),
    },
    {
        "name": "NetIncome",
        "statement": "Income Statement",
        "unit": "USD",
        "description": (
            "The bottom-line profit attributable to the consolidated entity after all expenses, "
            "taxes, interest, and non-controlling interest deductions. Comprehensive income "
            "adjustments and per-share variants are excluded."
        ),
    },
    {
        "name": "EPS_Basic",
        "statement": "Income Statement",
        "unit": "USD/share",
        "description": (
            "Basic Earnings Per Share — net income divided by the weighted-average number of "
            "common shares outstanding during the period, excluding dilutive securities such as "
            "stock options and convertible instruments."
        ),
    },
    {
        "name": "EPS_Diluted",
        "statement": "Income Statement",
        "unit": "USD/share",
        "description": (
            "Diluted Earnings Per Share — net income divided by the weighted-average diluted "
            "share count, which includes all potentially dilutive securities (options, warrants, "
            "convertible bonds). The most conservative EPS measure and the standard for "
            "valuation multiples."
        ),
    },
    # Balance Sheet — Assets
    {
        "name": "CashAndEquivalents",
        "statement": "Balance Sheet",
        "unit": "USD",
        "description": (
            "Cash and short-term liquid instruments with original maturities of three months or "
            "less, including bank deposits and money market funds. Includes restricted cash "
            "where the SEC-mandated combined presentation is reported."
        ),
    },
    {
        "name": "TotalAssets",
        "statement": "Balance Sheet",
        "unit": "USD",
        "description": (
            "The aggregate of all assets owned or controlled by the entity — current assets, "
            "property and equipment, intangible assets, and other long-term holdings. Equals "
            "total liabilities plus stockholders' equity (the fundamental accounting identity). "
            "Asset sub-categories and segment breakdowns are excluded."
        ),
    },
    {
        "name": "CurrentAssets",
        "statement": "Balance Sheet",
        "unit": "USD",
        "description": (
            "Assets expected to be converted to cash or consumed within one operating cycle "
            "(typically 12 months). Includes cash, accounts receivable, inventory, and "
            "short-term investments. A key component of liquidity analysis."
        ),
    },
    # Balance Sheet — Liabilities & Equity
    {
        "name": "TotalLiabilities",
        "statement": "Balance Sheet",
        "unit": "USD",
        "description": (
            "The total of all financial obligations owed by the entity — both current (due "
            "within 12 months) and long-term. Includes debt, accounts payable, deferred "
            "revenue, and other commitments."
        ),
    },
    {
        "name": "TotalLiabilitiesAndEquity",
        "statement": "Balance Sheet",
        "unit": "USD",
        "description": (
            "The sum of total liabilities and stockholders' equity — the right-hand side of the "
            "balance sheet. Must equal Total Assets by the fundamental accounting identity "
            "(Assets = Liabilities + Equity). Used as a cross-check for balance sheet integrity."
        ),
    },
    {
        "name": "StockholdersEquity",
        "statement": "Balance Sheet",
        "unit": "USD",
        "description": (
            "The residual interest in the entity's assets after deducting all liabilities — the "
            "book value owned by shareholders. Includes paid-in capital, retained earnings, "
            "accumulated other comprehensive income, and non-controlling interests where "
            "reported on a consolidated basis."
        ),
    },
    # Cash Flow Statement
    {
        "name": "OperatingCashFlow",
        "statement": "Cash Flow Statement",
        "unit": "USD",
        "description": (
            "Net cash generated or consumed by the company's core operating activities during "
            "the period. Often considered more reliable than net income as a measure of "
            "underlying business profitability because it is harder to manipulate with "
            "non-cash accounting choices."
        ),
    },
    {
        "name": "InvestingCashFlow",
        "statement": "Cash Flow Statement",
        "unit": "USD",
        "description": (
            "Net cash used in or generated by investing activities — primarily capital "
            "expenditures (outflow), acquisitions, and proceeds from asset sales or investment "
            "maturities (inflows). A consistently negative value typically indicates a "
            "capital-intensive growth strategy."
        ),
    },
    {
        "name": "FinancingCashFlow",
        "statement": "Cash Flow Statement",
        "unit": "USD",
        "description": (
            "Net cash from financing activities — debt issuance and repayments, equity raises, "
            "share buybacks, and dividend payments. Reflects how the company funds its "
            "operations and returns capital to shareholders."
        ),
    },
    {
        "name": "CAPEX",
        "statement": "Cash Flow Statement",
        "unit": "USD",
        "description": (
            "Capital Expenditures — cash paid to acquire, maintain, or upgrade physical assets "
            "such as property, plant, and equipment. Key input for Free Cash Flow "
            "calculations: FCF = OperatingCashFlow − CAPEX."
        ),
    },
]

_DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")


def generate() -> tuple[str, str, str]:
    """Generate all three catalog outputs. Returns (md_path, json_path, xlsx_path)."""
    os.makedirs(_DOCS_DIR, exist_ok=True)
    md_path = os.path.normpath(os.path.join(_DOCS_DIR, "data_catalog.md"))
    json_path = os.path.normpath(os.path.join(_DOCS_DIR, "data_catalog.json"))
    xlsx_path = os.path.normpath(os.path.join(_DOCS_DIR, "DATA_CATALOG.xlsx"))
    _write_markdown(md_path)
    _write_json(json_path)
    _update_xlsx(xlsx_path)
    print(f"Generated {md_path}")
    print(f"Generated {json_path}")
    print(f"Updated   {xlsx_path}")
    return md_path, json_path, xlsx_path


def _write_markdown(path: str) -> None:
    today = date.today().isoformat()
    by_statement: dict[str, list[dict]] = {}
    for c in CONCEPTS:
        by_statement.setdefault(c["statement"], []).append(c)

    statement_order = ["Income Statement", "Balance Sheet", "Cash Flow Statement"]

    lines: list[str] = [
        "# Valuein Data Catalog",
        "",
        f"> **Last updated**: {today}  ",
        f"> **Standardized concepts**: {len(CONCEPTS)}  ",
        "> **Historical coverage**: 1990 – present  ",
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

    for stmt in statement_order:
        concepts = by_statement.get(stmt, [])
        if not concepts:
            continue
        lines += [f"## {stmt}", ""]
        for c in concepts:
            lines += [
                f"### `{c['name']}`",
                "",
                f"**Unit:** {c['unit']}",
                "",
                c["description"],
                "",
            ]

    lines += [
        "---",
        "",
        "*This catalog is generated from the Valuein standardization pipeline. "
        "The underlying matching rules are proprietary — this document describes "
        "what each concept represents, not how it is detected.*",
        "",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_json(path: str) -> None:
    payload = {
        "generated": date.today().isoformat(),
        "concept_count": len(CONCEPTS),
        "coverage_target": ">=95%",
        "accuracy_score_guide": {
            "1.00": "human_verified",
            "0.70-0.85": "taxonomy_rule",
            "0.45-0.65": "pattern_match",
            "0.30-0.44": "keyword_heuristic",
            "0.00": "unmapped",
        },
        "concepts": CONCEPTS,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _update_xlsx(path: str) -> None:
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
        ("Financial Statement", 24, "statement"),
        ("Unit", 14, "unit"),
        ("Description", 80, "description"),
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
    for row_idx, concept in enumerate(CONCEPTS, start=2):
        is_alt = row_idx % 2 == 0
        fill = alt_fill if is_alt else PatternFill(fill_type=None)

        for col_idx, (_, _, attr) in enumerate(columns, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=concept[attr])
            cell.font = body_font
            cell.fill = fill
            # Description column wraps; others stay single-line
            cell.alignment = wrap_align if attr == "description" else top_align

        ws.row_dimensions[row_idx].height = 60  # tall enough for wrapped descriptions

    # Add a footer note below the data
    footer_row = len(CONCEPTS) + 3
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
