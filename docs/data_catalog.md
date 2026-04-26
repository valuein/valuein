# Valuein Data Catalog

> **Last updated**: 2026-04-25  
> **Standardized concepts**: 20  
> **Historical coverage**: 1994 – present  
> **Coverage target**: ≥ 95% of all SEC EDGAR financial facts

---

## Overview

The Valuein pipeline normalizes 15,000+ raw SEC EDGAR XBRL tags into a set of canonical financial concepts listed below.  Every fact in the dataset carries:

- `standard_concept` — the canonical name from this catalog (or `'Other'` if unmapped)
- `accuracy_score` — standardization confidence (0.0–1.0)

### Accuracy Score Guide

| Score | Meaning | Recommended use |
|-------|---------|----------------|
| 1.00 | Human-verified exact match | Any query |
| 0.70–0.85 | US GAAP taxonomy rule | Any query |
| 0.45–0.65 | Automated pattern match | Use with review |
| 0.30–0.44 | Keyword heuristic | Research / exploratory only |
| 0.00 | Unmapped (`standard_concept = 'Other'`) | Exclude from analytics |

**Recommended filter for production queries:** `accuracy_score >= 0.70`

---

## Income Statement

### `TotalRevenue`

**Unit:** USD

Total top-line revenue recognized during the period. Represents the aggregate net sales of goods and services before any deductions for costs or expenses. Segment sub-totals, deferred revenue balances, and revenue-adjacent items are excluded to prevent double-counting.

### `CostOfRevenue`

**Unit:** USD

Direct costs attributable to the production of goods sold or services delivered. Includes raw materials, direct labor, and manufacturing overhead. Excludes operating expenses such as SG&A and R&D.

### `GrossProfit`

**Unit:** USD

Revenue minus Cost of Revenue. Represents the profit a company earns after subtracting the direct costs of producing its products or delivering its services, before operating expenses, interest, and taxes.

### `OperatingExpenses`

**Unit:** USD

Total operating expenses incurred in the ordinary course of business, including SG&A, R&D, and other recurring operational costs. Excludes non-operating items such as interest expense and income tax.

### `ResearchAndDevelopment`

**Unit:** USD

Costs incurred in the research and development of new products, technologies, or processes. A forward-looking investment indicator — high R&D as a percentage of revenue often signals innovation-driven growth strategies.

### `SellingGeneralAdmin`

**Unit:** USD

Selling, General and Administrative expenses — the overhead costs of running the business not directly tied to production. Includes marketing, executive compensation, rent, legal, and other administrative costs.

### `OperatingIncome`

**Unit:** USD

Earnings from core business operations before interest income/expense and income taxes (EBIT proxy). Calculated as Gross Profit minus Operating Expenses. A key measure of operational efficiency independent of capital structure.

### `NetIncome`

**Unit:** USD

The bottom-line profit attributable to the consolidated entity after all expenses, taxes, interest, and non-controlling interest deductions. Comprehensive income adjustments and per-share variants are excluded.

### `EPS_Basic`

**Unit:** USD/share

Basic Earnings Per Share — net income divided by the weighted-average number of common shares outstanding during the period, excluding dilutive securities such as stock options and convertible instruments.

### `EPS_Diluted`

**Unit:** USD/share

Diluted Earnings Per Share — net income divided by the weighted-average diluted share count, which includes all potentially dilutive securities (options, warrants, convertible bonds). The most conservative EPS measure and the standard for valuation multiples.

## Balance Sheet

### `CashAndEquivalents`

**Unit:** USD

Cash and short-term liquid instruments with original maturities of three months or less, including bank deposits and money market funds. Includes restricted cash where the SEC-mandated combined presentation is reported.

### `TotalAssets`

**Unit:** USD

The aggregate of all assets owned or controlled by the entity — current assets, property and equipment, intangible assets, and other long-term holdings. Equals total liabilities plus stockholders' equity (the fundamental accounting identity). Asset sub-categories and segment breakdowns are excluded.

### `CurrentAssets`

**Unit:** USD

Assets expected to be converted to cash or consumed within one operating cycle (typically 12 months). Includes cash, accounts receivable, inventory, and short-term investments. A key component of liquidity analysis.

### `TotalLiabilities`

**Unit:** USD

The total of all financial obligations owed by the entity — both current (due within 12 months) and long-term. Includes debt, accounts payable, deferred revenue, and other commitments.

### `TotalLiabilitiesAndEquity`

**Unit:** USD

The sum of total liabilities and stockholders' equity — the right-hand side of the balance sheet. Must equal Total Assets by the fundamental accounting identity (Assets = Liabilities + Equity). Used as a cross-check for balance sheet integrity.

### `StockholdersEquity`

**Unit:** USD

The residual interest in the entity's assets after deducting all liabilities — the book value owned by shareholders. Includes paid-in capital, retained earnings, accumulated other comprehensive income, and non-controlling interests where reported on a consolidated basis.

## Cash Flow Statement

### `OperatingCashFlow`

**Unit:** USD

Net cash generated or consumed by the company's core operating activities during the period. Often considered more reliable than net income as a measure of underlying business profitability because it is harder to manipulate with non-cash accounting choices.

### `InvestingCashFlow`

**Unit:** USD

Net cash used in or generated by investing activities — primarily capital expenditures (outflow), acquisitions, and proceeds from asset sales or investment maturities (inflows). A consistently negative value typically indicates a capital-intensive growth strategy.

### `FinancingCashFlow`

**Unit:** USD

Net cash from financing activities — debt issuance and repayments, equity raises, share buybacks, and dividend payments. Reflects how the company funds its operations and returns capital to shareholders.

### `CAPEX`

**Unit:** USD

Capital Expenditures — cash paid to acquire, maintain, or upgrade physical assets such as property, plant, and equipment. Key input for Free Cash Flow calculations: FCF = OperatingCashFlow − CAPEX.

---

*This catalog is generated from the Valuein standardization pipeline. The underlying matching rules are proprietary — this document describes what each concept represents, not how it is detected.*
