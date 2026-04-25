# Valuein Query Cookbook

A collection of copy-pasteable **DuckDB** recipes for the Valuein SEC EDGAR
fundamentals dataset. Every query in this document runs against the tables
exposed by the SDK (`references`, `entity`, `security`, `filing`, `fact`,
`valuation`, `taxonomy_guide`, `index_membership`).

> All examples here work on the **Sample tier** (no token required) unless
> noted otherwise. Upgrade to **S&P 500** or **Pro** for full history and the
> full universe.

Related:

- [`data_catalog.md`](data_catalog.md) — canonical `standard_concept` names
- [`schema.json`](schema.json) — machine-readable column types
- [`examples/python/`](../examples/python/) — runnable end-to-end scripts

---

## Table of Contents

**Foundations**
- [1. Always start from `references`](#1-always-start-from-references)
- [2. Latest filing per company (`LATERAL`)](#2-latest-filing-per-company-lateral)
- [3. Pivot multiple concepts in one `fact` scan](#3-pivot-multiple-concepts-in-one-fact-scan)
- [4. The NULLIF + ABS safety pattern for ratios](#4-the-nullif--abs-safety-pattern-for-ratios)
- [5. Cash flow: `COALESCE` for YTD → quarterly](#5-cash-flow-coalesce-for-ytd--quarterly)
- [6. `QUALIFY` for latest-row filtering](#6-qualify-for-latest-row-filtering)

**Point-in-time discipline**
- [7. PIT-correct query (filing_date filter)](#7-pit-correct-query-filing_date-filter)
- [8. Millisecond PIT with `accepted_at`](#8-millisecond-pit-with-accepted_at)
- [9. Anti-pattern: filtering by `report_date`](#9-anti-pattern-filtering-by-report_date)

**Universe construction**
- [10. Survivorship-bias-free universe](#10-survivorship-bias-free-universe)
- [11. Current S&P 500 members](#11-current-sp-500-members)
- [12. Historical S&P 500 (entries and exits)](#12-historical-sp-500-entries-and-exits)

**End-to-end recipes**
- [13. Factor screen (Quality + Growth + Efficiency)](#13-factor-screen-quality--growth--efficiency)
- [14. Two-stage DCF inputs](#14-two-stage-dcf-inputs)
- [15. Earnings momentum (YoY acceleration)](#15-earnings-momentum-yoy-acceleration)
- [16. 5-year revenue history for one ticker](#16-5-year-revenue-history-for-one-ticker)
- [17. Balance sheet snapshot](#17-balance-sheet-snapshot)
- [18. Gross margin trend](#18-gross-margin-trend)

**Reference**
- [19. Concept normalization: many XBRL tags → one name](#19-concept-normalization-many-xbrl-tags--one-name)
- [20. Common anti-patterns to avoid](#20-common-anti-patterns-to-avoid)

---

## Foundations

### 1. Always start from `references`

**Use when:** any cross-company query. `references` is the denormalized flat
join of `entity` + `security` + `index_membership` with one row per security
and a boolean `is_sp500` flag. It replaces the 3-table join you would
otherwise write.

```sql
SELECT symbol, name, sector, is_sp500, is_active
FROM   "references"
WHERE  sector    ILIKE '%technology%'
  AND  is_active = TRUE
ORDER  BY name
LIMIT  20
```

> Why: every cross-company query that filters on sector/index/active status
> is 10× faster and simpler starting here.

---

### 2. Latest filing per company (`LATERAL`)

**Use when:** you need "the most recent 10-K (or 10-Q) per company."

```sql
SELECT r.symbol, r.name, f.filing_date, f.accession_id
FROM   "references" r
JOIN   LATERAL (
    SELECT accession_id, filing_date
    FROM   filing
    WHERE  entity_id = r.cik
      AND  form_type = '10-K'
    ORDER  BY filing_date DESC
    LIMIT  1
) f ON TRUE
WHERE r.is_sp500  = TRUE
  AND r.is_active = TRUE
```

> Why: `LATERAL` reads one row per outer row. Compared to a window function
> over all filings and then a `WHERE rn = 1`, this is much cheaper because
> DuckDB pushes the `LIMIT 1` down per company.

---

### 3. Pivot multiple concepts in one `fact` scan

**Use when:** you need several standardized concepts (revenue, net income,
equity, etc.) for the same filing. One scan, not N joins.

```sql
SELECT
    fa.accession_id,
    MAX(CASE WHEN fa.standard_concept = 'TotalRevenue'       THEN fa.numeric_value END) AS revenue,
    MAX(CASE WHEN fa.standard_concept = 'NetIncome'          THEN fa.numeric_value END) AS net_income,
    MAX(CASE WHEN fa.standard_concept = 'StockholdersEquity' THEN fa.numeric_value END) AS equity,
    MAX(CASE WHEN fa.standard_concept = 'TotalAssets'        THEN fa.numeric_value END) AS total_assets
FROM fact fa
WHERE fa.standard_concept IN
      ('TotalRevenue','NetIncome','StockholdersEquity','TotalAssets')
  AND fa.fiscal_period = 'FY'
GROUP BY fa.accession_id
```

> Why: a self-join per concept scales as O(N×concepts). `MAX(CASE WHEN ...)`
> reads `fact` once and pivots in a single aggregation.

---

### 4. The NULLIF + ABS safety pattern for ratios

**Use when:** any ratio. Zero denominators raise, and CAPEX sign varies by
filer — wrap every divisor in `NULLIF(x, 0)` and CAPEX in `ABS()`.

```sql
SELECT
    symbol,
    name,
    round(100.0 * net_income / NULLIF(revenue, 0),       1) AS net_margin_pct,
    round(ocf - ABS(capex),                              2) AS free_cash_flow
FROM   /* pivoted fact cte */ p
```

> Why: dividing by zero crashes the query; `NULLIF` makes it `NULL` so the
> row survives. `ABS(capex)` normalizes the sign across filers (some report
> CAPEX as a negative cash outflow, others as a positive magnitude).

---

### 5. Cash flow: `COALESCE` for YTD → quarterly

**Use when:** you want *quarterly* cash-flow numbers. Q2 and Q3 10-Qs report
year-to-date cash flows, not the quarter in isolation.

```sql
SELECT
    accession_id,
    fiscal_year,
    fiscal_period,
    COALESCE(derived_quarterly_value, numeric_value) AS q_ocf
FROM   fact
WHERE  standard_concept = 'OperatingCashFlow'
```

> Why: the pipeline pre-computes the isolated quarter in
> `derived_quarterly_value` when it can. Fall back to `numeric_value` (the
> raw value from the filing) when the derivation is unavailable.

---

### 6. `QUALIFY` for latest-row filtering

**Use when:** "give me the latest row per group." Cleaner than a correlated
subquery, faster than `SELECT ... WHERE (pk, dt) IN (SELECT ...)`.

```sql
SELECT *
FROM   fact
WHERE  standard_concept = 'TotalRevenue'
  AND  fiscal_period    = 'FY'
QUALIFY row_number() OVER (
    PARTITION BY entity_id, fiscal_year ORDER BY period_end DESC
) = 1
```

> Why: `QUALIFY` is DuckDB's post-window filter. It runs after the window
> function and before `SELECT`, so there is no subquery nesting.

---

## Point-in-time discipline

### 7. PIT-correct query (filing_date filter)

**Use when:** any backtest. You must filter facts by *when they became
public*, not by *when the fiscal period ended*.

```sql
SELECT
    fa.standard_concept,
    fa.fiscal_year,
    f.filing_date,
    fa.numeric_value
FROM   fact    fa
JOIN   filing  f ON fa.accession_id = f.accession_id
WHERE  f.entity_id       = :cik
  AND  f.form_type       = '10-K'
  AND  f.filing_date    <= :trade_date         -- ← the PIT filter
  AND  fa.standard_concept IN ('TotalRevenue', 'NetIncome')
ORDER  BY f.filing_date DESC
```

> Why: `filing_date` is when the SEC received the filing — i.e. when the
> market could have known. Filtering by anything else leaks future data.

---

### 8. Millisecond PIT with `accepted_at`

**Use when:** intraday research where the intra-day filing timestamp matters.
The `fact` table carries `accepted_at` as a `TIMESTAMPTZ`.

```sql
SELECT fa.*, fa.accepted_at
FROM   fact fa
WHERE  fa.entity_id       = :cik
  AND  fa.accepted_at    <= :trade_timestamp
ORDER  BY fa.accepted_at DESC
LIMIT  1
```

> Why: `filing_date` is daily resolution. `accepted_at` is millisecond
> resolution — critical for same-day signals (earnings release → trade).

---

### 9. Anti-pattern: filtering by `report_date`

**DO NOT DO THIS.** `report_date` is the fiscal period end, not when the
market learned about it.

```sql
-- WRONG — leaks look-ahead bias
WHERE fa.period_end <= :trade_date
```

> Why this is wrong: Apple's Q4 2023 period ends 2023-09-30 but the 10-K is
> filed ~2023-11-03. Filtering by `period_end <= '2023-10-15'` returns
> facts that nobody could have seen on that date.

---

## Universe construction

### 10. Survivorship-bias-free universe

**Use when:** backtesting. Include delisted, bankrupt, and acquired companies.

```sql
SELECT cik, name, status, sector, fiscal_year_end
FROM   entity
WHERE  status != 'ACTIVE'           -- include everything non-active
```

> Why: most providers silently delete these rows. A backtest on
> "survivors only" makes every strategy look better than it is.

---

### 11. Current S&P 500 members

**Use when:** you want today's index constituents. Fast path via `references`.

```sql
SELECT symbol, name, sector, exchange
FROM   "references"
WHERE  is_sp500  = TRUE
  AND  is_active = TRUE
ORDER  BY name
```

> Why: `references.is_sp500` is a pre-computed flag. No join to
> `index_membership` needed.

---

### 12. Historical S&P 500 (entries and exits)

**Use when:** "which companies *left* the S&P 500?" — membership timeline.

```sql
SELECT
    e.name,
    e.status,
    s.symbol,
    im.start_date AS joined_index,
    im.end_date   AS left_index
FROM   index_membership im
JOIN   security s ON s.id      = im.security_id
JOIN   entity   e ON e.cik     = s.entity_id
WHERE  im.index_name = 'S&P 500'
  AND  im.end_date IS NOT NULL        -- they left the index
ORDER  BY im.end_date DESC
```

> Why: `references.is_sp500` is current-only. Historical entry/exit dates
> live in `index_membership`.

---

## End-to-end recipes

### 13. Factor screen (Quality + Growth + Efficiency)

**Use when:** you want a multi-factor fundamental ranking. Full script:
[`examples/python/factor_screen.py`](../examples/python/factor_screen.py).

```sql
WITH latest AS (
    SELECT r.cik, r.symbol, r.name, r.sector,
           f.accession_id, f.filing_date
    FROM "references" r
    JOIN LATERAL (
        SELECT accession_id, filing_date
        FROM   filing
        WHERE  entity_id = r.cik AND form_type = '10-K'
        ORDER  BY filing_date DESC
        LIMIT  1
    ) f ON TRUE
    WHERE r.is_sp500 = TRUE AND r.is_active = TRUE
),
prior AS (
    SELECT l.cik, f.accession_id AS prior_accession_id
    FROM latest l
    JOIN LATERAL (
        SELECT accession_id
        FROM   filing
        WHERE  entity_id = l.cik
          AND  form_type = '10-K'
          AND  filing_date < l.filing_date
        ORDER  BY filing_date DESC
        LIMIT  1
    ) f ON TRUE
),
latest_facts AS (
    SELECT fa.accession_id,
        MAX(CASE WHEN fa.standard_concept = 'TotalRevenue'       THEN fa.numeric_value END) AS revenue,
        MAX(CASE WHEN fa.standard_concept = 'NetIncome'          THEN fa.numeric_value END) AS net_income,
        MAX(CASE WHEN fa.standard_concept = 'StockholdersEquity' THEN fa.numeric_value END) AS equity,
        MAX(CASE WHEN fa.standard_concept = 'TotalAssets'        THEN fa.numeric_value END) AS total_assets
    FROM fact fa
    WHERE fa.standard_concept IN
          ('TotalRevenue','NetIncome','StockholdersEquity','TotalAssets')
      AND fa.fiscal_period = 'FY'
    GROUP BY fa.accession_id
),
prior_facts AS (
    SELECT fa.accession_id,
        MAX(CASE WHEN fa.standard_concept = 'TotalRevenue' THEN fa.numeric_value END) AS revenue
    FROM fact fa
    WHERE fa.standard_concept = 'TotalRevenue' AND fa.fiscal_period = 'FY'
    GROUP BY fa.accession_id
)
SELECT
    l.symbol, l.name, l.sector,
    round(100.0 * lf.net_income / NULLIF(lf.equity, 0),       2) AS roe_pct,
    round(100.0 * (lf.revenue - pf.revenue)
                / NULLIF(pf.revenue, 0),                      1) AS rev_yoy_pct,
    round(       lf.revenue / NULLIF(lf.total_assets, 0),     3) AS asset_turnover
FROM latest l
JOIN latest_facts lf ON lf.accession_id = l.accession_id
LEFT JOIN prior p    ON p.cik           = l.cik
LEFT JOIN prior_facts pf ON pf.accession_id = p.prior_accession_id
```

Then z-score and composite-rank in pandas — see the script.

---

### 14. Two-stage DCF inputs

**Use when:** you want raw inputs for your own DCF. Full script:
[`examples/python/dcf_inputs.py`](../examples/python/dcf_inputs.py).

```sql
WITH fy_10k AS (
    SELECT
        fa.fiscal_year, fa.period_end,
        MAX(CASE WHEN fa.standard_concept = 'OperatingCashFlow' THEN fa.numeric_value END) AS ocf,
        MAX(CASE WHEN fa.standard_concept = 'CAPEX'             THEN fa.numeric_value END) AS capex
    FROM fact fa
    JOIN filing  f  ON fa.accession_id = f.accession_id
    JOIN "references" r ON f.entity_id   = r.cik
    WHERE r.symbol         = 'MSFT'
      AND f.form_type      = '10-K'
      AND fa.fiscal_period = 'FY'
      AND fa.standard_concept IN ('OperatingCashFlow', 'CAPEX')
    GROUP BY fa.accession_id, fa.fiscal_year, fa.period_end
    QUALIFY ROW_NUMBER() OVER (PARTITION BY fa.fiscal_year ORDER BY fa.period_end DESC) = 1
)
SELECT fiscal_year, period_end,
       ocf, ABS(capex) AS capex_abs,
       ocf - ABS(capex) AS fcf
FROM   fy_10k
WHERE  ocf IS NOT NULL AND capex IS NOT NULL
ORDER  BY fiscal_year DESC
LIMIT  5
```

Cross-check against Valuein's pre-computed DCF:

```sql
SELECT period_end, dcf_value_per_share, wacc, terminal_growth_rate,
       stage1_growth_rate, stage1_years, fcf_base
FROM   valuation v
JOIN   "references" r ON v.entity_id = r.cik
WHERE  r.symbol = 'MSFT'
ORDER  BY v.period_end DESC
LIMIT  3
```

---

### 15. Earnings momentum (YoY acceleration)

**Use when:** classic momentum factor — rank by YoY growth of revenue and
earnings. Full script:
[`examples/python/earnings_momentum.py`](../examples/python/earnings_momentum.py).

```sql
-- See recipe 13 for the `latest` / `prior` CTEs (same skeleton).
SELECT
    l.symbol, l.name, l.sector,
    round(100.0 * (lp.revenue    - pp.revenue)    / NULLIF(pp.revenue, 0),    1) AS rev_yoy_pct,
    round(100.0 * (lp.net_income - pp.net_income) / NULLIF(ABS(pp.net_income), 0), 1) AS ni_yoy_pct
FROM latest l
JOIN latest_pivot lp ON lp.accession_id = l.accession_id
JOIN prior        p  ON p.cik           = l.cik
JOIN prior_pivot  pp ON pp.accession_id = p.prior_accession_id
WHERE lp.revenue IS NOT NULL AND pp.revenue IS NOT NULL
ORDER BY rev_yoy_pct DESC
LIMIT 20
```

> Why `ABS` on the denominator: a company that swung from net loss to net
> profit would otherwise produce a nonsensically negative growth rate.

---

### 16. 5-year revenue history for one ticker

**Use when:** you want a clean 5-year time series from annual 10-Ks.

```sql
SELECT
    fa.fiscal_year,
    fa.period_end,
    round(fa.numeric_value / 1e9, 2) AS revenue_bn_usd
FROM   fact    fa
JOIN   filing  f  ON fa.accession_id = f.accession_id
JOIN   "references" r ON f.entity_id  = r.cik
WHERE  r.symbol           = 'NVDA'
  AND  r.is_active        = TRUE
  AND  f.form_type        = '10-K'
  AND  fa.standard_concept = 'TotalRevenue'
  AND  fa.fiscal_period    = 'FY'
QUALIFY row_number() OVER (
    PARTITION BY fa.fiscal_year ORDER BY fa.period_end DESC
) = 1
ORDER  BY fa.fiscal_year DESC
LIMIT  5
```

> Why `QUALIFY` here: each 10-K contains comparative periods. Without the
> row-number filter you would see duplicates — current year + two comparative
> prior years in every filing.

---

### 17. Balance sheet snapshot

**Use when:** you want all balance sheet line items from the latest 10-K in
one shot.

```sql
WITH latest AS (
    SELECT f.accession_id
    FROM   filing    f
    JOIN   "references" r ON f.entity_id = r.cik
    WHERE  r.symbol    = 'AAPL'
      AND  f.form_type = '10-K'
    ORDER  BY f.filing_date DESC
    LIMIT  1
)
SELECT
    fa.standard_concept,
    fa.period_end,
    round(fa.numeric_value / 1e9, 3) AS value_bn
FROM fact fa
JOIN latest l ON fa.accession_id = l.accession_id
WHERE fa.standard_concept IN (
    'CashAndEquivalents',
    'CurrentAssets',
    'TotalAssets',
    'TotalLiabilities',
    'StockholdersEquity'
)
QUALIFY row_number() OVER (
    PARTITION BY fa.standard_concept ORDER BY fa.period_end DESC
) = 1
ORDER BY fa.standard_concept
```

---

### 18. Gross margin trend

**Use when:** margin analysis. Pivot revenue and gross profit on the same
filing, then compute the ratio.

```sql
SELECT
    fa.fiscal_year,
    round(100.0 * gp / NULLIF(rev, 0), 1) AS gross_margin_pct,
    round(rev / 1e9, 2) AS revenue_bn,
    round(gp  / 1e9, 2) AS gross_profit_bn
FROM (
    SELECT
        fa.fiscal_year,
        MAX(CASE WHEN fa.standard_concept = 'TotalRevenue' THEN fa.numeric_value END) AS rev,
        MAX(CASE WHEN fa.standard_concept = 'GrossProfit'  THEN fa.numeric_value END) AS gp
    FROM fact    fa
    JOIN filing  f  ON fa.accession_id = f.accession_id
    JOIN "references" r ON f.entity_id   = r.cik
    WHERE r.symbol         = 'AAPL'
      AND f.form_type      = '10-K'
      AND fa.fiscal_period = 'FY'
      AND fa.standard_concept IN ('TotalRevenue', 'GrossProfit')
    GROUP BY fa.fiscal_year, fa.accession_id
    QUALIFY row_number() OVER (PARTITION BY fa.fiscal_year ORDER BY MAX(fa.period_end) DESC) = 1
) fa
ORDER BY fiscal_year DESC
LIMIT 5
```

---

## Reference

### 19. Concept normalization: many XBRL tags → one name

**Use when:** you want to see how standardization works. No private mapping
table needed — both the raw and canonical names are on the `fact` row.

```sql
SELECT DISTINCT
    fa.concept          AS raw_xbrl_tag,
    fa.standard_concept AS canonical_name
FROM   fact fa
WHERE  fa.standard_concept = 'TotalRevenue'
ORDER  BY fa.concept
LIMIT  20
```

> Why: `fact.concept` = raw SEC XBRL tag, `fact.standard_concept` =
> canonical label. Query canonical names for cross-company work; inspect
> raw names only for debugging.

---

### 20. Common anti-patterns to avoid

| Anti-pattern | Fix |
|---|---|
| Filtering by `fa.period_end <= trade_date` in backtests | Use `f.filing_date <= trade_date` |
| `WHERE status = 'ACTIVE'` (survivorship bias) | Drop the filter for universe construction |
| Dividing without `NULLIF(denominator, 0)` | Always wrap divisors |
| Using raw XBRL tags (`'Revenues'`, `'NetIncomeLoss'`) | Use canonical `standard_concept` names (`'TotalRevenue'`, `'NetIncome'`) |
| Joining `entity` + `security` + `index_membership` by hand | Start from `references` |
| Self-join per concept for multi-concept pivots | One `fact` scan with `MAX(CASE WHEN ...)` |
| Correlated subquery for latest-per-group | `QUALIFY row_number() OVER (...) = 1` |
| Raw `numeric_value` for quarterly cash flows | `COALESCE(derived_quarterly_value, numeric_value)` |
| Subtracting CAPEX as-is from OCF | Wrap CAPEX in `ABS()` — sign varies by filer |

---

## See also

- [`examples/python/getting_started.py`](../examples/python/getting_started.py) — first run
- [`examples/python/financial_analysis.py`](../examples/python/financial_analysis.py) — intermediate patterns
- [`examples/python/pit_backtest.py`](../examples/python/pit_backtest.py) — PIT discipline in depth
- [`examples/python/factor_screen.py`](../examples/python/factor_screen.py) — full factor screen
- [`examples/python/dcf_inputs.py`](../examples/python/dcf_inputs.py) — DCF assembly
- [`examples/python/earnings_momentum.py`](../examples/python/earnings_momentum.py) — momentum screen
