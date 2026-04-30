# Excel Setup Guide — Valuein Financial Data Essentials

This guide walks you through connecting the **Valuein FDE Excel template** to live SEC fundamental data using Microsoft Power Query.

---

## Requirements

| Requirement | Detail |
|---|---|
| **Excel version** | Microsoft 365 (build 16.0.17531 or later) — required for `Parquet.Document()` |
| **Operating system** | Windows or macOS with Microsoft 365 |
| **Internet connection** | Required on every Refresh; data is streamed live from `data.valuein.biz` |
| **API token** | Register at [valuein.biz](https://valuein.biz) to obtain a free or paid token |

> **Older Excel versions:** If you are on Excel 2019 or earlier, `Parquet.Document()` is not available. Contact [support@valuein.biz](mailto:support@valuein.biz) to request CSV exports.

---

## Step 1 — Download the Template

The Excel template ships with the SDK distribution. Get it from one of:

- The **Templates** tab on [valuein.biz/developers](https://valuein.biz/developers) (signed-in customers)
- Email [support@valuein.biz](mailto:support@valuein.biz) — we'll send the latest `valuein-fundamentals.xlsx` directly

Open the file in Excel. If prompted, click **Enable Editing** and then **Enable Content**.

---

## Step 2 — Enter Your API Token

1. Navigate to the **START HERE** sheet (the first tab).
2. Locate the purple input cell labeled **API Token** (cell C7).
3. Delete the placeholder text and paste your Valuein API token.
4. Verify the **API Base URL** in cell C9 reads `https://data.valuein.biz/v1` (the default is correct for all users).

The workbook uses two **Named Ranges** to share the token across all Power Query connections:

| Named Range | Cell | Purpose |
|---|---|---|
| `API_TOKEN` | `'START HERE'!$C$7` | Your Valuein Bearer token |
| `API_BASE_URL` | `'START HERE'!$C$9` | Gateway base URL |

To verify or recreate these named ranges: **Formulas → Name Manager**.

---

## Step 3 — Refresh All Tables

Click **Data → Refresh All** (or press **Ctrl + Alt + F5**).

Excel will query the Valuein gateway for each table simultaneously. On a first run with a cold cache, expect 30–120 seconds for the full dataset to load. Subsequent refreshes are faster because Excel caches unchanged Parquet column chunks.

**During refresh:**
- A progress spinner appears in the status bar at the bottom of Excel.
- Individual query status is visible in **Data → Queries & Connections** (right panel).

---

## Step 4 — Browse the Data

| Sheet | Description |
|---|---|
| **Income Statement** | Annual P&L metrics: Revenue, Gross Profit, Operating Income, Net Income, EPS |
| **Balance Sheet** | Annual balance sheet: Assets, Liabilities, Equity, Cash, Debt |
| **Cash Flow** | Annual cash flows: Operating CF, CapEx, Free Cash Flow, Dividends |
| **Entities** | Full entity reference: CIK, company name, sector, SIC code, status |
| **Securities** | All ticker symbols with exchange, FIGI, and active/inactive flag |
| **Filings** | SEC filing metadata: form type, `filing_date`, `report_date`, accession number |
| **Data Dictionary** | Definitions for all 150+ `standard_concept` values with unit and balance type |
| **Connectivity Guide** | Power Query M code, Python SDK examples, API endpoint reference |

---

## Adding Your Own Power Query Connections

The `excel/power-query/` directory in this repository contains ready-to-use M code for each table. To add a new connection:

1. Open **Power Query Editor** (Data → Get Data → Launch Power Query Editor).
2. **Home → New Source → Blank Query**.
3. **Home → Advanced Editor** — paste the M code from the relevant `.pq` file.
4. Name the query (e.g., `ValueinEntity`).
5. **Close & Load** — choose **Connection Only** to keep the workbook lean, or **Table** to display data in a sheet.

### Power Query file reference

| File | Query name | Description |
|---|---|---|
| `setup.pq` | `ValueinConfig` | **Load this first.** Reads `API_TOKEN` and `API_BASE_URL` named ranges. |
| `entity.pq` | `ValueinEntity` | All companies — CIK, name, sector, SIC, status |
| `security.pq` | `ValueinSecurity` | Ticker symbols with date ranges and active status |
| `filing.pq` | `ValueinFiling` | SEC filing metadata with PIT dates |
| `fact.pq` | `ValueinFact` | Standardized financial facts (annual, USD, last 10 years) |
| `taxonomy_guide.pq` | `ValueinTaxonomy` | Data dictionary for all standard concepts |

> **Load order matters:** `ValueinConfig` must be loaded before any table query, because all other queries reference it.

---

## Understanding the Data

### Point-in-Time (PIT) Accuracy

Every financial fact in the dataset carries two key dates:

| Field | Meaning |
|---|---|
| `report_date` | The fiscal period end (e.g., December 31, 2024) |
| `filing_date` | When the SEC received the filing — the market's knowledge date |

**When filtering for backtesting analysis, always use `filing_date`**, not `report_date`. Using `report_date` as a filter would include data that the market did not yet have, introducing look-ahead bias into your analysis.

**Example:** Apple's Q4 2024 earnings (period ending September 28, 2024) were filed with the SEC on November 1, 2024. If you are analyzing the market as of October 15, 2024, you should not include this fact — it was not yet public. Filter `filing_date <= '2024-10-15'` to enforce this.

### Tier Differences

| Tier | Data scope | Access |
|---|---|---|
| **Free (`sp500`)** | S&P 500 constituents only — current and historical members | Free signup at [valuein.biz/signup/free](https://valuein.biz/signup/free) |
| **Pro** | Full universe (16,000+ tickers), 10-year history | $49 / mo — [subscribe](https://valuein.biz/checkout?tier=pro&billing=monthly) |
| **Enterprise (`full`)** | Full universe, full history (1994–present), 4h priority freshness | $200 / mo — [subscribe](https://valuein.biz/checkout?tier=full&billing=monthly) |

The Power Query connections automatically detect your plan from the `/v1/me` endpoint and route to the correct R2 bucket.

---

## Troubleshooting

| Error | Cause | Resolution |
|---|---|---|
| "Invalid token" or 401 | Token is missing, wrong, or expired | Re-paste your token in cell C7 on START HERE. Regenerate at [valuein.biz/portal](https://valuein.biz/portal). |
| "Plan upgrade required" or 403 | Your token tier is below the data the query requested | Upgrade at [valuein.biz/pricing](https://valuein.biz/pricing) — Pro for full universe, Enterprise for full history. |
| "Formula.Firewall" error | Power Query privacy settings prevent cross-source queries | Go to File → Options → Trust Center → Trust Center Settings → Privacy → set to "Ignore Privacy Levels". |
| Parquet.Document not found | Excel version is too old | Upgrade to Microsoft 365 or request CSV exports from support. |
| Refresh times out | Large table on slow connection | Increase query timeout: Power Query Editor → File → Options → Query Settings. |
| Named range not found | `API_TOKEN` named range is missing | Re-create via Formulas → Name Manager → New → `API_TOKEN` → `='START HERE'!$C$7`. |

---

## Support

- **Documentation:** [valuein.biz/developers](https://valuein.biz/developers)
- **Email:** [support@valuein.biz](mailto:support@valuein.biz)
- **GitHub Issues:** [github.com/valuein/valuein/issues](https://github.com/valuein/valuein/issues)
