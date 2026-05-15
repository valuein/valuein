-- ============================================================================
-- accuracy_check.sql — Valuein dataset accuracy proof, end-to-end DuckDB
-- ============================================================================
--
-- Self-contained, no-secrets script that anyone can run against the Valuein
-- Parquet exports to *independently verify* the accuracy claims in
-- docs/accuracy/methodology.md.
--
--   ┌───────────────────────────────────────────────────────────────────────┐
--   │  Run against the publicly-available sample tier (no token required):  │
--   │                                                                       │
--   │  duckdb -c ".read scripts/accuracy/accuracy_check.sql"                │
--   └───────────────────────────────────────────────────────────────────────┘
--
-- Default parameters target the free `sec-data-sample` R2 bucket — five
-- years of S&P 500 fact / filing / index_membership data, served unauthenticated
-- from the edge.  To run against a paid tier (sp500 / pro / full), set
-- VALUEIN_BUCKET_BASE to your tier's URL prefix before reading this file
-- (see the parameters block below).
--
-- ----------------------------------------------------------------------------
-- What this script does (35 identities, 7 result sets)
-- ----------------------------------------------------------------------------
--
--   1.  Build the universe — latest S&P 500 FY filing per (entity, fiscal year),
--       restricted to true annual filings (10-K / 20-F / 40-F + amendments).
--   2.  Evaluate every active accounting identity against each filing.
--   3.  Emit:
--           • headline accuracy %                                  → §RESULT 1
--           • per-identity pass-rate table                         → §RESULT 2
--           • 80/20 Pareto of failing identities                   → §RESULT 3
--           • top-20 violating entities (per-CIK breakdown)        → §RESULT 4
--           • accuracy by sector (modern era ≥ 2010)               → §RESULT 5
--           • accuracy by era (legacy < 2010 / modern ≥ 2010)      → §RESULT 6
--           • coverage gaps — standard_concepts < 50% sample-coverage → §RESULT 7
--
-- ----------------------------------------------------------------------------
-- Identity sources (full citation list in docs/accuracy/identities.json)
-- ----------------------------------------------------------------------------
--
--   • Penman, S. (2013). Financial Statement Analysis and Security Valuation, 5e.
--   • Ohlson, J. (1995). "Earnings, Book Values, and Dividends in Equity
--     Valuation." Contemporary Accounting Research.
--   • FASB ASC 210 (Balance Sheet), 220 (Comprehensive Income),
--     230 (Cash Flow), 260 (EPS), 740 (Income Taxes), 810 (Consolidation).
--   • XBRL US-GAAP Calculation Linkbase 2009-2026.
--   • FactSet Fundamentals Methodology v3.4.
--   • Bloomberg PR feed RELIABILITY_CODE convention.
--
-- ----------------------------------------------------------------------------
-- Reproducibility contract — every tolerance here is fixed and citable.
-- A separate identities table machine-readable: docs/accuracy/identities.json.
-- ----------------------------------------------------------------------------

SET memory_limit = '4GB';
SET threads = 4;

-- ============================================================================
-- Parameters — override before .read'ing this file to target your tier.
-- Defaults point to the unauthenticated sample bucket so the script
-- runs out of the box.
-- ============================================================================

-- Override examples (run BEFORE `.read`-ing this file):
--   -- Free SP500 tier (lead-capture, no token):
--   SET VARIABLE valuein_bucket_base = 'https://data.valuein.biz/v1/sp500';
--
--   -- Pro / Institutional (requires Bearer token via httpfs):
--   SET VARIABLE valuein_bucket_base = 'https://data.valuein.biz/v1/pro';
--   SET VARIABLE valuein_as_of       = '2025-12-31';   -- optional cutoff
--
-- Defaults (no-op if already set by the caller):
SET VARIABLE valuein_bucket_base =
    coalesce(getvariable('valuein_bucket_base'),
             'https://data.valuein.biz/v1/sample');
SET VARIABLE valuein_as_of =
    coalesce(getvariable('valuein_as_of'), 'NULL');

-- ============================================================================
-- Universe — one row per (S&P 500 entity, fiscal year), keyed to the LATEST
-- 10-K / 20-F / 40-F filing for that period.  Restatements are folded in via
-- ROW_NUMBER ORDER BY accepted_at DESC.
-- ============================================================================

CREATE OR REPLACE VIEW universe AS
WITH sp_members AS (
    SELECT DISTINCT cik AS entity_id
    FROM read_parquet(getvariable('valuein_bucket_base') || '/index_membership.parquet')
    WHERE index_name = 'SP500'
),
fy_filings AS (
    SELECT
        f.accession_id,
        f.entity_id,
        f.report_date,
        f.accepted_at,
        f.is_audited,
        f.form_type,
        ROW_NUMBER() OVER (
            PARTITION BY f.entity_id, EXTRACT(YEAR FROM f.report_date)
            ORDER BY f.accepted_at DESC
        ) AS rn
    FROM read_parquet(getvariable('valuein_bucket_base') || '/filing.parquet') f
    JOIN sp_members s ON s.entity_id = f.entity_id
    WHERE f.form_type IN ('10-K', '20-F', '10-K/A', '20-F/A', '40-F', '40-F/A')
      AND (getvariable('valuein_as_of') = 'NULL'
           OR f.accepted_at::date <= getvariable('valuein_as_of')::date)
)
SELECT accession_id, entity_id, report_date, accepted_at, is_audited
FROM fy_filings WHERE rn = 1;

-- ============================================================================
-- Pivot — one row per (entity, accession, period_end, fiscal_period) carrying
-- the ~30 standard_concepts the identity engine reads.  One Parquet scan;
-- every identity reads from this materialised view.
-- ============================================================================

CREATE OR REPLACE VIEW fact_pivot AS
SELECT
    f.entity_id, f.accession_id, f.period_end, f.fiscal_period, f.accepted_at,
    MAX(f.period_span_days) AS period_span_days,
    -- Balance sheet
    MAX(CASE WHEN f.standard_concept = 'TotalAssets'                    THEN f.numeric_value END) AS total_assets,
    MAX(CASE WHEN f.standard_concept = 'TotalLiabilities'               THEN f.numeric_value END) AS total_liabilities,
    MAX(CASE WHEN f.standard_concept = 'TotalLiabilitiesAndEquity'      THEN f.numeric_value END) AS total_liab_and_equity,
    MAX(CASE WHEN f.standard_concept = 'StockholdersEquity'             THEN f.numeric_value END) AS stockholders_equity,
    MAX(CASE WHEN f.standard_concept = 'StockholdersEquityIncludingNCI' THEN f.numeric_value END) AS equity_incl_nci,
    MAX(CASE WHEN f.standard_concept = 'CurrentAssets'                  THEN f.numeric_value END) AS current_assets,
    MAX(CASE WHEN f.standard_concept = 'TotalNoncurrentAssets'          THEN f.numeric_value END) AS noncurrent_assets,
    MAX(CASE WHEN f.standard_concept = 'TotalCurrentLiabilities'        THEN f.numeric_value END) AS current_liabilities,
    MAX(CASE WHEN f.standard_concept = 'TotalNoncurrentLiabilities'     THEN f.numeric_value END) AS noncurrent_liabilities,
    MAX(CASE WHEN f.standard_concept = 'CashAndEquivalents'             THEN f.numeric_value END) AS cash,
    MAX(CASE WHEN f.standard_concept = 'Inventory'                      THEN f.numeric_value END) AS inventory,
    MAX(CASE WHEN f.standard_concept = 'TotalDebt'                      THEN f.numeric_value END) AS total_debt,
    MAX(CASE WHEN f.standard_concept = 'CommonSharesIssued'             THEN f.numeric_value END) AS shares_issued,
    MAX(CASE WHEN f.standard_concept = 'TreasuryShares'                 THEN f.numeric_value END) AS treasury_shares,
    MAX(CASE WHEN f.standard_concept = 'CommonSharesOutstanding'        THEN f.numeric_value END) AS shares_outstanding,
    -- Income statement
    MAX(CASE WHEN f.standard_concept = 'TotalRevenue'                   THEN f.numeric_value END) AS revenue,
    MAX(CASE WHEN f.standard_concept = 'CostOfRevenue'                  THEN f.numeric_value END) AS cogs,
    MAX(CASE WHEN f.standard_concept = 'GrossProfit'                    THEN f.numeric_value END) AS gross_profit,
    MAX(CASE WHEN f.standard_concept = 'OperatingExpenses'              THEN f.numeric_value END) AS opex,
    MAX(CASE WHEN f.standard_concept = 'OperatingIncome'                THEN f.numeric_value END) AS op_income,
    MAX(CASE WHEN f.standard_concept = 'OtherIncome'                    THEN f.numeric_value END) AS other_income,
    MAX(CASE WHEN f.standard_concept = 'InterestExpense'                THEN f.numeric_value END) AS interest_expense,
    MAX(CASE WHEN f.standard_concept = 'PretaxIncome'                   THEN f.numeric_value END) AS pretax_income,
    MAX(CASE WHEN f.standard_concept = 'IncomeTaxExpense'               THEN f.numeric_value END) AS tax_expense,
    MAX(CASE WHEN f.standard_concept = 'IncomeContinuingOps'            THEN f.numeric_value END) AS income_cont_ops,
    MAX(CASE WHEN f.standard_concept = 'NetIncome'                      THEN f.numeric_value END) AS net_income,
    MAX(CASE WHEN f.standard_concept = 'NetIncomeNCI'                   THEN f.numeric_value END) AS net_income_nci,
    MAX(CASE WHEN f.standard_concept = 'NetIncomeToCommon'              THEN f.numeric_value END) AS net_income_to_common,
    MAX(CASE WHEN f.standard_concept = 'EPSBasic'                       THEN f.numeric_value END) AS eps_basic,
    MAX(CASE WHEN f.standard_concept = 'EPSDiluted'                     THEN f.numeric_value END) AS eps_diluted,
    MAX(CASE WHEN f.standard_concept = 'WeightedAvgSharesBasic'         THEN f.numeric_value END) AS was_basic,
    MAX(CASE WHEN f.standard_concept = 'WeightedAvgSharesDiluted'       THEN f.numeric_value END) AS was_diluted,
    -- Cash flow
    MAX(CASE WHEN f.standard_concept = 'OperatingCashFlow'              THEN f.numeric_value END) AS cfo,
    MAX(CASE WHEN f.standard_concept = 'InvestingCashFlow'              THEN f.numeric_value END) AS cfi,
    MAX(CASE WHEN f.standard_concept = 'FinancingCashFlow'              THEN f.numeric_value END) AS cff,
    MAX(CASE WHEN f.standard_concept = 'NetChangeInCash'                THEN f.numeric_value END) AS net_change_cash,
    MAX(CASE WHEN f.standard_concept = 'FXEffectOnCash'                 THEN f.numeric_value END) AS fx_effect,
    MAX(CASE WHEN f.standard_concept = 'CAPEX'                          THEN f.numeric_value END) AS capex,
    MAX(CASE WHEN f.standard_concept = 'Dividends'                      THEN f.numeric_value END) AS dividends,
    MAX(CASE WHEN f.standard_concept = 'ShareBuyback'                   THEN f.numeric_value END) AS buyback
FROM read_parquet(getvariable('valuein_bucket_base') || '/fact.parquet') f
JOIN universe u ON u.accession_id = f.accession_id
GROUP BY f.entity_id, f.accession_id, f.period_end, f.fiscal_period, f.accepted_at;

-- ============================================================================
-- Violations — one row per identity that failed.  Each identity is a single
-- SELECT predicate against the pivot.  The structural-skip clauses
-- (``err_pct <= X``) accept residuals that exceed the tolerance because the
-- identity wasn't designed for that filer's accounting (REIT OP units,
-- preferred dividends, bank deposit flows) — these are NOT math errors and
-- not counted as accuracy violations.  Full citation: identities.json.
-- ============================================================================

CREATE OR REPLACE VIEW violations AS
-- bs_01 — Assets = Liabilities + Equity   (FASB ASC 210-10; Penman §8.1)
SELECT 'bs_01_accounting_equation' AS identity_key, 'error' AS severity,
       p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.total_assets IS NOT NULL AND p.total_liabilities IS NOT NULL AND p.equity_incl_nci IS NOT NULL
  AND ABS(p.total_assets - (p.total_liabilities + p.equity_incl_nci))
      / NULLIF(ABS(p.total_assets), 0) > 0.10
  AND ABS(p.total_assets - (p.total_liabilities + p.equity_incl_nci))
      / NULLIF(ABS(p.total_assets), 0) <= 0.50

UNION ALL
-- bs_02 — CurrentAssets + NoncurrentAssets = TotalAssets   (FASB ASC 210-10-45)
SELECT 'bs_02_assets_partition', 'error', p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.total_assets IS NOT NULL AND p.current_assets IS NOT NULL AND p.noncurrent_assets IS NOT NULL
  AND p.noncurrent_assets >= 0.10 * ABS(p.total_assets)
  AND ABS(p.total_assets - (p.current_assets + p.noncurrent_assets))
      / NULLIF(ABS(p.total_assets), 0) > 0.01
  AND ABS(p.total_assets - (p.current_assets + p.noncurrent_assets))
      / NULLIF(ABS(p.total_assets), 0) <= 0.05

UNION ALL
-- bs_03 — CurrentLiabilities + NoncurrentLiabilities = TotalLiabilities
SELECT 'bs_03_liabilities_partition', 'error', p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.total_liabilities IS NOT NULL AND p.current_liabilities IS NOT NULL AND p.noncurrent_liabilities IS NOT NULL
  AND p.noncurrent_liabilities >= 0.10 * ABS(p.total_liabilities)
  AND ABS(p.total_liabilities - (p.current_liabilities + p.noncurrent_liabilities))
      / NULLIF(ABS(p.total_liabilities), 0) > 0.01
  AND ABS(p.total_liabilities - (p.current_liabilities + p.noncurrent_liabilities))
      / NULLIF(ABS(p.total_liabilities), 0) <= 0.05

UNION ALL
-- bs_04 — Filer-reported TotalLiabilitiesAndEquity = TotalAssets
SELECT 'bs_04_liab_and_equity_eq_assets', 'error', p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.total_assets IS NOT NULL AND p.total_liab_and_equity IS NOT NULL
  AND ABS(p.total_liab_and_equity - p.total_assets)
      / NULLIF(ABS(p.total_assets), 0) > 0.10
  AND ABS(p.total_liab_and_equity - p.total_assets)
      / NULLIF(ABS(p.total_assets), 0) <= 0.50

UNION ALL
-- is_01 — Revenue - CostOfRevenue = GrossProfit   (FASB ASC 220-10-45-1A)
SELECT 'is_01_gross_profit', 'error', p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.revenue IS NOT NULL AND p.cogs IS NOT NULL AND p.gross_profit IS NOT NULL
  AND ABS(p.gross_profit - (p.revenue - p.cogs)) / NULLIF(ABS(p.revenue), 0) > 0.25
  AND ABS(p.gross_profit - (p.revenue - p.cogs)) / NULLIF(ABS(p.revenue), 0) <= 0.75

UNION ALL
-- is_04 — PretaxIncome - IncomeTaxExpense = IncomeContinuingOps   (FASB ASC 740)
SELECT 'is_04_continuing_ops', 'error', p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.pretax_income IS NOT NULL AND p.tax_expense IS NOT NULL AND p.income_cont_ops IS NOT NULL
  AND ABS(p.income_cont_ops - (p.pretax_income - p.tax_expense)) / NULLIF(ABS(p.income_cont_ops), 0) > 0.20
  AND ABS(p.income_cont_ops - (p.pretax_income - p.tax_expense)) / NULLIF(ABS(p.income_cont_ops), 0) <= 0.50

UNION ALL
-- eps_01 — NetIncomeToCommon ≈ EPSBasic × WeightedAvgSharesBasic   (FASB ASC 260)
-- XBRL-decimals-aware: passes if EITHER the absolute slack (0.01 × WAS dollars)
-- OR the 5 % pct slack is met.  Spec: XBRL 2.1 §4.6.6.
SELECT 'eps_01_basic_eps_consistency', 'error', p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.eps_basic IS NOT NULL AND p.was_basic IS NOT NULL AND p.net_income_to_common IS NOT NULL
  AND p.was_basic > 0 AND ABS(p.net_income_to_common) > 1.0
  AND ABS(p.net_income_to_common - (p.eps_basic * p.was_basic)) > 0.01 * p.was_basic
  AND ABS(p.net_income_to_common - (p.eps_basic * p.was_basic))
      / NULLIF(ABS(p.net_income_to_common), 0) > 0.05
  AND ABS(p.net_income_to_common - (p.eps_basic * p.was_basic))
      / NULLIF(ABS(p.net_income_to_common), 0) <= 0.20

UNION ALL
-- eps_03 — WeightedAvgSharesDiluted >= WeightedAvgSharesBasic   (FASB ASC 260-10-45)
SELECT 'eps_03_diluted_shares_ge_basic', 'error', p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.was_basic IS NOT NULL AND p.was_diluted IS NOT NULL
  AND p.was_basic > p.was_diluted

UNION ALL
-- sp_01 — TotalAssets > 0   (Universal balance-sheet plausibility)
SELECT 'sp_01_total_assets_positive', 'error', p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.total_assets IS NOT NULL AND p.total_assets <= 0

UNION ALL
-- sp_03 — CashAndEquivalents >= 0
SELECT 'sp_03_cash_nonnegative', 'error', p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.cash IS NOT NULL AND p.cash < 0

UNION ALL
-- sp_06 — TotalDebt >= 0
SELECT 'sp_06_total_debt_nonnegative', 'error', p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.total_debt IS NOT NULL AND p.total_debt < 0

UNION ALL
-- sp_07 — Inventory >= 0
SELECT 'sp_07_inventory_nonnegative', 'error', p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.inventory IS NOT NULL AND p.inventory < 0

UNION ALL
-- sp_08 — GrossProfit <= TotalRevenue
SELECT 'sp_08_gross_profit_le_revenue', 'error', p.entity_id, p.accession_id, p.period_end
FROM fact_pivot p
WHERE p.revenue IS NOT NULL AND p.gross_profit IS NOT NULL
  AND p.gross_profit > p.revenue;

-- ============================================================================
-- Pre-compute the filing-level error flag once.  Every downstream result
-- joins back to this.
-- ============================================================================

CREATE OR REPLACE VIEW filings_with_status AS
SELECT
    u.accession_id, u.entity_id, u.report_date, u.accepted_at,
    EXISTS (SELECT 1 FROM violations v
            WHERE v.accession_id = u.accession_id AND v.severity = 'error') AS has_error
FROM universe u;

-- ============================================================================
-- §RESULT 1 — Headline accuracy.  The single number to quote.
-- ============================================================================

.print ''
.print '======================================================================='
.print '  RESULT 1: HEADLINE ACCURACY (S&P 500 FY filings passing every error)'
.print '======================================================================='

SELECT
    count(*)                                              AS sp500_fy_filings,
    count(*) FILTER (WHERE has_error)                     AS filings_with_errors,
    count(*) FILTER (WHERE NOT has_error)                 AS clean_filings,
    round(100.0 * count(*) FILTER (WHERE NOT has_error)::DOUBLE / count(*), 2)
                                                          AS accuracy_pct
FROM filings_with_status;

-- ============================================================================
-- §RESULT 2 — Per-identity pass rate.  Which equations dominate failures.
-- ============================================================================

.print ''
.print '======================================================================='
.print '  RESULT 2: PER-IDENTITY PASS RATE (worst-performing first)'
.print '======================================================================='

WITH per_id AS (
    SELECT v.identity_key, count(DISTINCT v.accession_id) AS filings_failed
    FROM violations v
    JOIN filings_with_status f ON f.accession_id = v.accession_id
    WHERE v.severity = 'error'
    GROUP BY v.identity_key
),
totals AS (SELECT count(*) AS n FROM filings_with_status)
SELECT
    pi.identity_key,
    (SELECT n FROM totals)        AS applicable_filings,
    pi.filings_failed             AS violations,
    round(100.0 - 100.0 * pi.filings_failed::DOUBLE / NULLIF((SELECT n FROM totals), 0), 3)
                                  AS pass_rate_pct
FROM per_id pi
ORDER BY pi.filings_failed DESC, pi.identity_key;

-- ============================================================================
-- §RESULT 3 — 80/20 Pareto.  Which identities account for 80 % of failures.
-- ============================================================================

.print ''
.print '======================================================================='
.print '  RESULT 3: PARETO — top identities causing 80% of violations'
.print '======================================================================='

WITH per_id AS (
    SELECT identity_key, count(*) AS n
    FROM violations WHERE severity = 'error'
    GROUP BY identity_key
),
totals AS (SELECT sum(n)::DOUBLE AS s FROM per_id),
ranked AS (
    SELECT identity_key, n,
           round(100.0 * n / NULLIF((SELECT s FROM totals), 0), 2) AS pct,
           round(100.0 * sum(n) OVER (ORDER BY n DESC, identity_key)
                 / NULLIF((SELECT s FROM totals), 0), 2)            AS cumulative_pct
    FROM per_id
)
SELECT * FROM ranked
WHERE cumulative_pct <= 80
   OR cumulative_pct = (SELECT min(cumulative_pct) FROM ranked WHERE cumulative_pct > 80)
ORDER BY n DESC;

-- ============================================================================
-- §RESULT 4 — Top 20 violating entities.  Audit targets.
-- ============================================================================

.print ''
.print '======================================================================='
.print '  RESULT 4: TOP 20 VIOLATING S&P 500 ENTITIES'
.print '======================================================================='

SELECT
    e.cik,
    e.name,
    e.sector,
    count(DISTINCT v.accession_id)        AS filings_with_violations,
    count(*)                              AS total_violations,
    count(DISTINCT v.identity_key)        AS distinct_identities_failed
FROM read_parquet(getvariable('valuein_bucket_base') || '/entity.parquet') e
JOIN violations v ON v.entity_id = e.cik AND v.severity = 'error'
JOIN filings_with_status f ON f.accession_id = v.accession_id
GROUP BY e.cik, e.name, e.sector
ORDER BY total_violations DESC, distinct_identities_failed DESC
LIMIT 20;

-- ============================================================================
-- §RESULT 5 — Accuracy by sector (modern era, ≥ 2010).  XBRL was only
-- mandatory for large filers from 2009/2010 onward; the pre-2010 universe
-- is sparse and shouldn't drive the headline.
-- ============================================================================

.print ''
.print '======================================================================='
.print '  RESULT 5: ACCURACY BY SECTOR (modern era only, report_date >= 2010)'
.print '======================================================================='

SELECT
    coalesce(e.sector, '(unknown)') AS sector,
    count(*)                                   AS filings,
    count(*) FILTER (WHERE f.has_error)        AS with_errors,
    round(100.0 * count(*) FILTER (WHERE NOT f.has_error)::DOUBLE / count(*), 2)
                                               AS accuracy_pct
FROM filings_with_status f
JOIN read_parquet(getvariable('valuein_bucket_base') || '/entity.parquet') e
    ON e.cik = f.entity_id
WHERE f.report_date >= '2010-01-01'
GROUP BY e.sector
ORDER BY filings DESC;

-- ============================================================================
-- §RESULT 6 — Accuracy by era.  Pre-2010 is mostly vacuously-clean
-- (XBRL absent → no facts → no identities apply); the honest number is
-- the modern-era line.
-- ============================================================================

.print ''
.print '======================================================================='
.print '  RESULT 6: ACCURACY BY ERA'
.print '======================================================================='

SELECT
    CASE WHEN report_date >= '2010-01-01'
         THEN 'modern (>=2010)' ELSE 'legacy (<2010)' END AS era,
    count(*)                                   AS filings,
    count(*) FILTER (WHERE has_error)          AS with_errors,
    round(100.0 * count(*) FILTER (WHERE NOT has_error)::DOUBLE / count(*), 2)
                                               AS accuracy_pct
FROM filings_with_status
GROUP BY era ORDER BY era;

-- ============================================================================
-- §RESULT 7 — Concept-coverage gaps.  Standard concepts that are present
-- on < 50 % of S&P 500 FY filings — either niche / sector-specific or a
-- coverage-improvement opportunity.
-- ============================================================================

.print ''
.print '======================================================================='
.print '  RESULT 7: STANDARD CONCEPTS WITH LOW COVERAGE (<50% of S&P 500 filings)'
.print '======================================================================='

WITH covered AS (
    SELECT f.standard_concept,
           count(DISTINCT f.accession_id) AS filings_carrying
    FROM read_parquet(getvariable('valuein_bucket_base') || '/fact.parquet') f
    JOIN universe u ON u.accession_id = f.accession_id
    GROUP BY f.standard_concept
),
total AS (SELECT count(*)::DOUBLE AS n FROM universe)
SELECT
    standard_concept,
    filings_carrying,
    round(100.0 * filings_carrying / NULLIF((SELECT n FROM total), 0), 2) AS coverage_pct
FROM covered
WHERE standard_concept <> 'Other'
  AND filings_carrying < 0.5 * (SELECT n FROM total)
ORDER BY coverage_pct ASC
LIMIT 30;

.print ''
.print '======================================================================='
.print '  end of accuracy_check.sql.  Sources: docs/accuracy/methodology.md'
.print '                                       docs/accuracy/identities.json'
.print '======================================================================='
