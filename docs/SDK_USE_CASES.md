# Valuein SDK — 10 Use Cases, With Real Output

The ten things people actually do with `valuein-sdk`, ordered easiest → most
advanced. Every code block on this page was executed against the live gateway
and **every output block is the real captured stdout** — nothing here is
illustrative, rounded by hand, or reconstructed.

> **Captured 2026-07-31** against snapshot `snapshot_20260731`, SDK **v4.0.0**,
> on the free **Sample** tier with **no API key**. Re-run any of them yourself;
> if a number differs it is because the snapshot moved, not because the example
> is aspirational.

**8 of the 10 run with no token at all.** The two that show more on a paid tier
say so explicitly and still run for free.

Related:

- [`QUERY_COOKBOOK.md`](QUERY_COOKBOOK.md) — 20 DuckDB recipes and the anti-pattern table
- [`data_catalog.md`](data_catalog.md) — canonical `standard_concept` names
- [`schema.json`](schema.json) — machine-readable column types
- [`METHODOLOGY.md`](METHODOLOGY.md) — PIT architecture and restatement handling

---

## Table of Contents

| # | Use case | Tier | Runnable script |
|---|---|---|---|
| 1 | [First real data, no API key](#1-first-real-data-no-api-key) | Sample | [`getting_started.py`](../examples/python/getting_started.py) |
| 2 | [What's in here? Discovering tables and columns](#2-whats-in-here-discovering-tables-and-columns) | Sample | [`usage.py`](../examples/python/usage.py) |
| 3 | [One company's income statement](#3-one-companys-income-statement) | Sample | [`financial_analysis.py`](../examples/python/financial_analysis.py) |
| 4 | [Financial ratios over time](#4-financial-ratios-over-time) | Sample | [`financial_analysis.py`](../examples/python/financial_analysis.py) |
| 5 | [Comparing peers](#5-comparing-peers) | Sample | [`entity_screening.py`](../examples/python/entity_screening.py) |
| 6 | [Screening the universe on factors](#6-screening-the-universe-on-factors) | Sample | [`factor_screen.py`](../examples/python/factor_screen.py) |
| 7 | [Survivorship-bias-free universe](#7-survivorship-bias-free-universe) | Sample (names need Pro) | [`survivorship_bias.py`](../examples/python/survivorship_bias.py) |
| 8 | [Prices and total return](#8-prices-and-total-return) | Sample | [`price_total_return.py`](../examples/python/price_total_return.py) |
| 9 | [⭐ Point-in-time: the same query, two answers](#9--point-in-time-the-same-query-two-answers) | Sample | [`pit_as_of_restatement.py`](../examples/python/pit_as_of_restatement.py) |
| 10 | [Restatement Radar](#10-restatement-radar) | Sample | [`restatement_radar.py`](../examples/python/restatement_radar.py) |

---

## 1. First real data, no API key

**Question:** *"Can I get actual SEC data on screen before I decide whether to care?"*

```bash
pip install valuein-sdk        # or: uv pip install valuein-sdk
```

```python
import time
t0 = time.time()

from valuein_sdk import ValueinClient

client = ValueinClient(tables=["references"])

df = client.run_query("""
    SELECT symbol, name, sector
    FROM "references"
    WHERE sector = 'Information Technology'
    ORDER BY symbol
    LIMIT 5
""")
print(df.to_string(index=False))
print(f"\nElapsed: {time.time() - t0:.1f}s")
```

```
symbol               name                 sector
  AAPL         Apple Inc. Information Technology
  ABNB       Airbnb, Inc. Information Technology
   ACN      Accenture plc Information Technology
  ADBE         ADOBE INC. Information Technology
   ADI ANALOG DEVICES INC Information Technology

Elapsed: 1.8s
```

That timing is a **cold cache** (`~/.cache/valuein-sdk` deleted first), no token,
no signup. The SDK prints a one-time warning telling you it fell back to the
Sample tier — that is expected, not an error.

> **Gotcha — `references` is a reserved word in DuckDB.** Always quote it:
> `FROM "references"`. Unquoted, you get `Parser Error: syntax error at or near
> "references"`. Every recipe in this repo quotes it.

> **Gotcha — pass `tables=[...]`.** The client downloads and mounts each table
> you name. Ask only for what you need; `tables=[]` gives you an instant auth
> check with no data transfer.

---

## 2. What's in here? Discovering tables and columns

**Question:** *"What data do I actually have access to, and what are the columns called?"*

```python
from valuein_sdk import ValueinClient

client = ValueinClient(tables=[])

CORE = ["entity", "security", "references", "filing", "fact", "ratio",
        "index_membership", "stock_price_daily", "restatement_events"]

print("Snapshot :", client.manifest()["snapshot"])
print("Plan     :", client.me()["plan"])
print("Tables   :", len(client.manifest()["tables"]), "available")
print("Core     :", ", ".join(t for t in CORE if t in client.manifest()["tables"]))
print()
schema = client.get_schema("restatement_events")
for col in ("ticker", "standard_concept", "first_value", "current_value", "disclosure_class"):
    print(f"  {col:20s} {schema[col]}")
```

```
Snapshot : snapshot_20260731
Plan     : sample
Tables   : 15 available
Core     : entity, security, references, filing, fact, ratio, index_membership, stock_price_daily, restatement_events

  ticker               VARCHAR
  standard_concept     VARCHAR
  first_value          DOUBLE
  current_value        DOUBLE
  disclosure_class     VARCHAR
```

> **Gotcha — `get_schema()` returns a plain `dict`** of `{column: type}`, not a
> DataFrame. Index it directly; don't call `.columns` on it.

The schema is read from the R2 manifest at runtime, so new pipeline columns
appear without an SDK upgrade. `client.list_templates()` lists the 58 bundled
SQL templates.

---

## 3. One company's income statement

**Question:** *"What has Apple actually earned for the last five fiscal years?"*

```python
from valuein_sdk import ValueinClient

client = ValueinClient(tables=["references", "fact"])

df = client.run_query("""
    WITH latest AS (
        SELECT f.period_end, f.standard_concept, f.numeric_value,
               ROW_NUMBER() OVER (
                   PARTITION BY f.period_end, f.standard_concept
                   ORDER BY f.accepted_at DESC, f.priority ASC
               ) AS rn
        FROM fact f
        JOIN "references" r ON r.cik = f.entity_id
        WHERE r.symbol = 'AAPL'
          AND f.fiscal_period = 'FY'
          AND f.standard_concept IN
              ('TotalRevenue','GrossProfit','OperatingIncome','NetIncome')
    )
    SELECT period_end,
           MAX(CASE WHEN standard_concept='TotalRevenue'    THEN numeric_value END)/1e9 AS revenue_bn,
           MAX(CASE WHEN standard_concept='GrossProfit'     THEN numeric_value END)/1e9 AS gross_profit_bn,
           MAX(CASE WHEN standard_concept='OperatingIncome' THEN numeric_value END)/1e9 AS op_income_bn,
           MAX(CASE WHEN standard_concept='NetIncome'       THEN numeric_value END)/1e9 AS net_income_bn
    FROM latest WHERE rn = 1
    GROUP BY period_end ORDER BY period_end DESC LIMIT 5
""")
print(df.round(2).to_string(index=False))
```

```
period_end  revenue_bn  gross_profit_bn  op_income_bn  net_income_bn
2025-09-27      416.16           195.20        133.05         112.01
2024-09-28      391.04           180.68        123.22          93.74
2023-09-30      383.28           169.15        114.30          97.00
2022-09-24      394.33           170.78        119.44          99.80
2021-09-25      365.82           152.84        108.95          94.68
```

> **Gotcha — a 10-K contains prior years as comparatives.** A filing that reports
> FY2023 also restates FY2022 and FY2021 inside the same document. If you join
> `fact` to `filing` and group by the *filing's* report date, you will label a
> FY2021 comparative as a FY2023 result. **Group by `fact.period_end`**, which is
> the period the number describes — that is what the query above does.

> **Gotcha — one `standard_concept` can have several raw XBRL tags in a single
> filing.** Apple tags revenue more than one way. The
> `ROW_NUMBER() ... ORDER BY accepted_at DESC, priority ASC` picks the newest
> vintage and then the preferred tag, so you get one row per period instead of
> duplicates.

> **Gotcha — quarterly cash-flow items are year-to-date.** Q2 and Q3 10-Qs
> report cumulative figures. Use
> `COALESCE(derived_quarterly_value, numeric_value)` to isolate the single
> quarter, and always wrap CAPEX in `ABS()` — the sign varies by filer.

---

## 4. Financial ratios over time

**Question:** *"How has Microsoft's capital intensity moved as it built out AI infrastructure?"*

Ratios are precomputed — 149 distinct `ratio_name` values on this snapshot — so
you don't re-derive (and re-fumble) them.

```python
from valuein_sdk import ValueinClient

client = ValueinClient(tables=["references", "ratio"])

df = client.run_template(
    "financial_ratios_by_ticker",
    ticker="MSFT",
    fiscal_period="FY",
    start_date="2021-01-01",
    end_date="2026-07-31",
)
print(df.head(12).to_string(index=False))
```

```
symbol           name   category            ratio_name     value  unit  fiscal_year fiscal_period  is_ttm period_end                      computed_at
  MSFT MICROSOFT CORP efficiency        asset_turnover  0.498113 ratio         2025            FY   False 2025-06-30 2026-07-31 03:12:41.860297-04:00
  MSFT MICROSOFT CORP efficiency        asset_turnover  0.530487 ratio         2024            FY   False 2024-06-30 2026-07-31 03:12:41.862573-04:00
  MSFT MICROSOFT CORP efficiency        asset_turnover  0.545599 ratio         2023            FY   False 2023-06-30 2026-07-31 03:12:41.864727-04:00
  MSFT MICROSOFT CORP efficiency        asset_turnover  0.567606 ratio         2022            FY   False 2022-06-30 2026-07-31 03:12:41.866857-04:00
  MSFT MICROSOFT CORP efficiency capex_to_depreciation 10.758500 ratio         2025            FY   False 2025-06-30 2026-07-31 03:12:41.860012-04:00
  MSFT MICROSOFT CORP efficiency capex_to_depreciation  9.266042 ratio         2024            FY   False 2024-06-30 2026-07-31 03:12:41.862296-04:00
  MSFT MICROSOFT CORP efficiency capex_to_depreciation 11.242800 ratio         2023            FY   False 2023-06-30 2026-07-31 03:12:41.864465-04:00
  MSFT MICROSOFT CORP efficiency capex_to_depreciation 11.943000 ratio         2022            FY   False 2022-06-30 2026-07-31 03:12:41.866590-04:00
  MSFT MICROSOFT CORP efficiency      capex_to_revenue  0.229129 ratio         2025            FY   False 2025-06-30 2026-07-31 03:12:41.860046-04:00
  MSFT MICROSOFT CORP efficiency      capex_to_revenue  0.181448 ratio         2024            FY   False 2024-06-30 2026-07-31 03:12:41.862322-04:00
  MSFT MICROSOFT CORP efficiency      capex_to_revenue  0.132633 ratio         2023            FY   False 2023-06-30 2026-07-31 03:12:41.864491-04:00
  MSFT MICROSOFT CORP efficiency      capex_to_revenue  0.120472 ratio         2022            FY   False 2022-06-30 2026-07-31 03:12:41.866616-04:00
```

`capex_to_revenue` going 12.0% → 13.3% → 18.1% → 22.9% is the AI capex build,
straight out of the filings.

> **Gotcha — the value column is `value`, not `ratio_value`.** Getting this wrong
> raises `Binder Error: ... does not have a column named "ratio_value"`.

> **Gotcha — `ratio` is append-on-restatement and PIT-filtered.** The SDK view
> collapses each `(entity, ratio, period, fiscal_period)` to its latest
> `accepted_at` vintage automatically, so restatements never double-count.

---

## 5. Comparing peers

**Question:** *"Which of the mega-cap tech names actually converts revenue into profit best?"*

```python
from valuein_sdk import ValueinClient

client = ValueinClient(tables=["references", "ratio"])

# Anchor on period_end, NOT fiscal_year: "the fiscal year that ENDED in calendar 2024".
df = client.run_query("""
    SELECT r.symbol, ra.period_end,
           round(MAX(CASE WHEN ra.ratio_name='gross_profit_margin' THEN ra.value END)*100, 1) AS gross_margin_pct,
           round(MAX(CASE WHEN ra.ratio_name='operating_margin'    THEN ra.value END)*100, 1) AS op_margin_pct,
           round(MAX(CASE WHEN ra.ratio_name='net_margin'          THEN ra.value END)*100, 1) AS net_margin_pct
    FROM "references" r
    JOIN ratio ra ON ra.entity_id = r.cik
    WHERE r.symbol IN ('AAPL','MSFT','GOOGL','META','NVDA')
      AND ra.fiscal_period = 'FY'
      AND ra.period_end BETWEEN '2024-01-01' AND '2024-12-31'
    GROUP BY r.symbol, ra.period_end
    ORDER BY net_margin_pct DESC
""")
print(df.to_string(index=False))
```

```
symbol period_end  gross_margin_pct  op_margin_pct  net_margin_pct
  NVDA 2024-01-28              72.7           54.1            48.8
  META 2024-12-31              81.7           42.2            37.9
  MSFT 2024-06-30              69.8           44.6            36.0
 GOOGL 2024-12-31              58.2           32.1            28.6
  AAPL 2024-09-28              46.2           31.5            24.0
```

> **Gotcha — do not align peers on `fiscal_year`. Align on `period_end`.**
> This is the sharpest trap on this page. Fiscal years are not calendar years and
> the `fiscal_year` label is not reliably consistent across filers: on this
> snapshot Apple's period ending `2023-09-30` carries `fiscal_year = 2024`, while
> Microsoft's period ending `2024-06-30` carries `fiscal_year = 2024`. Joining
> five companies on `fiscal_year = 2024` silently compares Apple's FY2023 against
> everyone else's FY2024 — the individual numbers are all real, so nothing looks
> wrong. Selecting `period_end` alongside the value makes the misalignment
> visible instead of silent.

> **Gotcha — the `sector` column is unreliable for some names.** On this snapshot
> `references.sector` places Deckers Outdoor in *Materials* and Garmin in
> *Health Care*. Peer sets built by hand from tickers are trustworthy; sector
> aggregates are not yet. Verify membership before you publish a sector median.

---

## 6. Screening the universe on factors

**Question:** *"Which companies convert revenue into profit and equity into earnings better than everyone else right now?"*

Build the screen from `fact` so you control every denominator, then rank
cross-sectionally with `percent_rank()`.

```python
from valuein_sdk import ValueinClient

client = ValueinClient(tables=["references", "fact"])

df = client.run_query("""
    WITH fy AS (   -- newest fiscal year per company
        SELECT entity_id, max(period_end) AS period_end
        FROM fact WHERE fiscal_period = 'FY' AND period_end <= CURRENT_DATE
        GROUP BY entity_id
    ),
    wide AS (
        SELECT f.entity_id, f.period_end,
               -- One standard_concept can carry several raw XBRL tags in a single
               -- filing (a disaggregated component plus the true total). MAX()
               -- recovers the total; picking arbitrarily does not.
               MAX(CASE WHEN f.standard_concept='TotalRevenue'       THEN f.numeric_value END) AS revenue,
               MAX(CASE WHEN f.standard_concept='NetIncome'          THEN f.numeric_value END) AS net_income,
               MAX(CASE WHEN f.standard_concept='StockholdersEquity' THEN f.numeric_value END) AS equity
        FROM fact f
        JOIN fy ON fy.entity_id = f.entity_id AND fy.period_end = f.period_end
        WHERE f.fiscal_period = 'FY'
        GROUP BY f.entity_id, f.period_end
    ),
    scored AS (
        SELECT r.symbol, r.name, p.period_end,
               net_income / NULLIF(revenue, 0) AS net_margin,
               net_income / NULLIF(equity, 0)  AS roe
        FROM wide p JOIN "references" r ON r.cik = p.entity_id
        WHERE revenue > 0 AND equity > 0 AND net_income IS NOT NULL
        -- "references" is one row per SECURITY: Alphabet has 4 tickers and
        -- would otherwise occupy 4 slots in the top 10. Collapse to the issuer.
        QUALIFY ROW_NUMBER() OVER (PARTITION BY r.cik ORDER BY r.symbol) = 1
    )
    SELECT symbol, name, period_end,
           round(net_margin, 3) AS net_margin, round(roe, 3) AS roe,
           round((percent_rank() OVER (ORDER BY net_margin)
                + percent_rank() OVER (ORDER BY roe)) / 2, 3) AS composite
    FROM scored
    WHERE net_margin BETWEEN -1 AND 1 AND roe BETWEEN -2 AND 2
    ORDER BY composite DESC, symbol
    LIMIT 10
""")
print(df.to_string(index=False))
```

```
symbol                       name period_end  net_margin   roe  composite
   APP              AppLovin Corp 2025-12-31       0.608 1.562      0.977
    MA             Mastercard Inc 2025-12-31       0.456 1.935      0.977
  GOOG              Alphabet Inc. 2025-12-31       0.328 0.318      0.849
  NFLX                NETFLIX INC 2025-12-31       0.243 0.413      0.849
  PLTR Palantir Technologies Inc. 2025-12-31       0.363 0.220      0.791
  META       Meta Platforms, Inc. 2025-12-31       0.301 0.278      0.779
  ABNB               Airbnb, Inc. 2025-12-31       0.205 0.306      0.744
   GEV            GE Vernova Inc. 2025-12-31       0.128 0.437      0.733
   CME             CME GROUP INC. 2025-12-31       0.625 0.142      0.709
   PTC                   PTC INC. 2025-09-30       0.268 0.192      0.698
```

> **Gotcha — `"references"` is one row per SECURITY, not per company.** Alphabet
> carries four tickers (`GOOG`, `GOOGL`, `GOOGM`, `GOOGN`) and will occupy four
> of your ten slots unless you collapse to `cik`. Same lesson as the price table
> in [§8](#8-prices-and-total-return): the issuer and the listing are different
> things.

> **Gotcha — bound your ratios, and prefer computing them yourself.** The
> `WHERE net_margin BETWEEN -1 AND 1` clause is not cosmetic. On this snapshot the
> precomputed `ratio.net_margin` reports **55.8%** for Comfort Systems USA
> (`FIX`) in FY2025 — the true figure is ~11%. The company's FY2025 filing tags
> revenue twice ($9.10bn total and a $1.83bn component) and the ratio engine
> divided by the smaller one. Computing the margin from `fact` with `MAX()`, as
> above, gets it right. Always `/ NULLIF(x, 0)` and always sanity-bound the
> output before you rank on it.

Prefer not to hand-roll the ranking? The bundled alpha framework z-scores and
combines factors for you, PIT-safely:

```python
from valuein_sdk import ValueinClient
from valuein_sdk.alpha import AlphaEngine, ROE, GROSS_MARGIN, DEBT_TO_EQUITY

client = ValueinClient(tables=["references", "fact", "filing"])

engine = AlphaEngine(client).add_factor(ROE).add_factor(GROSS_MARGIN).add_factor(DEBT_TO_EQUITY)
scores = engine.compute(as_of="2024-01-01").rank().combine()
print(scores.head(5).to_string())
```

```
COO     0.862914
TXN     0.862867
EBAY    0.857016
ALGN    0.856539
NVDA    0.855735
```

`combine()` returns a `pandas.Series` of composite scores indexed by ticker,
best first.

`AlphaEngine.compute()` defaults its cutoff to `client.as_of` and **clamps a
later explicit `as_of` down** to it — the engine can never reach past the
client's PIT horizon. Worked end-to-end in
[`pit_factor_dataset.py`](../examples/python/pit_factor_dataset.py).

> **Gotcha — `SYY` shows `roe = 0.881` on a 2.3% net margin.** That is a real
> reported figure, not an error: Sysco runs a very small equity base, so ROE is
> flattered by the denominator. Always read ROE next to leverage.

---

## 7. Survivorship-bias-free universe

**Question:** *"What was the S&P 500 actually made of on a date in the past — including the companies that have since vanished?"*

Reconstructing an index from today's membership is the most common way to
manufacture a backtest that cannot lose.

```python
from valuein_sdk import ValueinClient

client = ValueinClient(tables=["index_membership"])

AS_OF = "2022-06-30"

print(client.run_query(f"""
    SELECT count(*)                                                  AS members_on_date,
           sum(CASE WHEN removal_date IS NOT NULL THEN 1 ELSE 0 END) AS departed_since
    FROM index_membership
    WHERE index_name = 'SP500'
      AND DATE '{AS_OF}' >= effective_date
      AND (DATE '{AS_OF}' < removal_date OR removal_date IS NULL)
""").to_string(index=False))

print("\nSpells that ended after this date (a survivorship-biased vendor shows none of these):")
print(client.run_query(f"""
    SELECT cik, effective_date, removal_date
    FROM index_membership
    WHERE index_name = 'SP500'
      AND DATE '{AS_OF}' >= effective_date
      AND removal_date IS NOT NULL
      AND removal_date > DATE '{AS_OF}'
    ORDER BY removal_date LIMIT 5
""").to_string(index=False))

print("\nFull SP500 history depth on this tier:")
print(client.run_query("""
    SELECT min(effective_date) AS earliest_spell,
           count(*)            AS total_spells
    FROM index_membership WHERE index_name = 'SP500'
""").to_string(index=False))
```

```
 members_on_date  departed_since
             488            64.0

Spells that ended after this date (a survivorship-biased vendor shows none of these):
       cik effective_date removal_date
0000078239     2013-02-14   2022-09-19
0000921738     2021-03-22   2022-09-19
0000877890     1999-12-01   2022-10-03
0000783280     2017-07-26   2022-10-03
0001492633     2013-07-09   2022-10-12

Full SP500 history depth on this tier:
earliest_spell  total_spells
    1996-01-02          1088
```

64 of the 488 companies in the index on 2022-06-30 have since left it. A vendor
that stores only current membership shows you 424 and calls it history.

Membership is stored as **spells** (`effective_date` → `removal_date`), back to
1996, so a company that left and rejoined has multiple rows. Join on `cik`:
`JOIN index_membership im ON r.cik = im.cik` — same column name on both sides.

> **Tier note — the CIKs above resolve to names only on Pro / Institutional.**
> The Sample tier's `entity` and `references` tables carry the **498 current**
> companies, so departed members have no name row to join to and come back
> `None`. The membership spine itself — the part that makes the backtest
> honest — is fully present for free. Full worked version:
> [`survivorship_bias.py`](../examples/python/survivorship_bias.py).

---

## 8. Prices and total return

**Question:** *"What did I actually earn holding this, dividends included?"*

```python
from valuein_sdk import ValueinClient

client = ValueinClient(tables=["references", "stock_price_daily"])

print("Issuers in this snapshot with three or more listed securities:")
print(client.run_query("""
    SELECT entity_id, count(DISTINCT security_id) AS securities,
           string_agg(DISTINCT symbol, ', ' ORDER BY symbol) AS symbols
    FROM stock_price_daily
    GROUP BY entity_id HAVING count(DISTINCT security_id) > 2
    ORDER BY securities DESC, entity_id
""").to_string(index=False))

print("\nTotal return by SECURITY (dividends + splits already inside total_return_index):")
print(client.run_query("""
    WITH bounds AS (
        SELECT security_id, symbol,
               first_value(total_return_index) OVER w AS tri_start,
               last_value(total_return_index)  OVER w AS tri_end,
               first_value(close) OVER w              AS px_start,
               last_value(close)  OVER w              AS px_end
        FROM stock_price_daily
        WHERE symbol IN ('AAPL','MSFT','KO') AND price_date >= DATE '2023-01-01'
        WINDOW w AS (PARTITION BY security_id ORDER BY price_date
                     ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
    )
    SELECT DISTINCT symbol, security_id,
           round((px_end / px_start - 1) * 100, 1)   AS price_return_pct,
           round((tri_end / tri_start - 1) * 100, 1) AS total_return_pct
    FROM bounds ORDER BY total_return_pct DESC
""").to_string(index=False))
```

```
Issuers in this snapshot with three or more listed securities:
 entity_id  securities                 symbols
0000936340           5 DTB, DTE, DTG, DTK, DTW
0000036270           3     MTB, MTB-PJ, MTB-PK
0000049196           3      HBAN, HBANL, HBANZ
0000910606           3       REG, REGCO, REGCP

Total return by SECURITY (dividends + splits already inside total_return_index):
symbol  security_id  price_return_pct  total_return_pct
  AAPL       198955             166.6             171.1
  MSFT       199271              88.3              93.6
    KO       198401              40.6              55.9
```

Coca-Cola returned 40.6% on price and **55.9% including dividends**. Drop the
dividend and you have understated the holding by 15 percentage points.

> **Gotcha — the grain of `stock_price_daily` is (security, day), NOT
> (company, day).** A CIK is an *issuer*. DTE Energy files one set of financials
> but has five listed securities (common plus four baby bonds), and this
> snapshot carries 536 securities across 498 issuers. **Partition on
> `security_id`** — not `entity_id`, not `symbol`. Partitioning on `entity_id`
> alone silently alternates between unrelated price series. Filter
> `is_primary_listing = TRUE` when you want the common stock.

> **Gotcha — do not recompound total return by hand.** `total_return_index` is
> prepopulated and dividend/split adjusted (zero nulls on this snapshot).
> Rebuilding it from `close` / `div_cash` / `split_factor` is how a dividend
> quietly goes missing.

---

## 9. ⭐ Point-in-time: the same query, two answers

**Question:** *"What did I know on the day I would have placed the trade — not what do I know now?"*

This is the differentiator. Monolithic Power Systems reported FY2024 net income
of **$1.7867bn**. A later filing restated the same fiscal year to **$1.592058bn**.
The company filed an SEC **Item 4.02 non-reliance** notice, so this is a
disclosed restatement, not a reclassification.

Most vendors overwrite the original. Ask them what MPWR earned in FY2024 and you
get $1.592bn — *including for a backtest dated mid-2025*, when nobody could have
known that. Only `as_of` changes between the two runs below; the SQL never moves.

```python
from datetime import datetime, timezone
from valuein_sdk import ValueinClient

QUESTION = """
    SELECT f.numeric_value / 1e9 AS net_income_bn, f.accession_id, f.accepted_at
    FROM fact f
    JOIN "references" r ON r.cik = f.entity_id
    WHERE r.symbol = 'MPWR'
      AND f.standard_concept = 'NetIncome'
      AND f.period_end = DATE '2024-12-31'
    QUALIFY ROW_NUMBER() OVER (ORDER BY f.accepted_at DESC) = 1
"""

for label, as_of in [
    ("What an analyst saw on 2025-06-30", datetime(2025, 6, 30, tzinfo=timezone.utc)),
    ("What the same query returns today ", datetime(2026, 7, 31, tzinfo=timezone.utc)),
]:
    client = ValueinClient(tables=["references", "fact"], as_of=as_of)
    row = client.run_query(QUESTION).iloc[0]
    print(f"{label}: ${row.net_income_bn:,.3f}bn   "
          f"(filing {row.accession_id}, accepted {row.accepted_at:%Y-%m-%d})")

orig, restated = 1.786700, 1.592058
print(f"\nThe FY2024 number fell by ${orig - restated:.3f}bn ({(restated/orig - 1)*100:.2f}%).")
print(f"Every P/E computed off the original overstated earnings by "
      f"{(orig/restated - 1)*100:.1f}% -- for ~12 months.")
```

```
What an analyst saw on 2025-06-30: $1.787bn   (filing 0001437749-25-005903, accepted 2025-03-03)
What the same query returns today : $1.592bn   (filing 0001437749-26-014084, accepted 2026-04-29)

The FY2024 number fell by $0.195bn (-10.89%).
Every P/E computed off the original overstated earnings by 12.2% -- for ~12 months.
```

Same query. Two different, *both correct*, answers — each carrying the accession
number of the filing it came from.

The distortion is exact and needs no price data: a multiple is `price ÷
denominator`, and the price on the day does not change when the company later
restates. Any P/E computed for MPWR between 2025-03-03 and 2026-02-27 was
overstating earnings by 12.2%.

> **Gotcha — `as_of` must be timezone-aware.** A naive `datetime` is rejected.
> It defaults to `datetime.now(timezone.utc)` when omitted, which is why a
> careless backtest is look-ahead-biased *by default* everywhere else — here the
> filter is applied at view-creation time across the whole session.

> **Gotcha — PIT filtering applies to the 11 tables whose rows become public at
> `accepted_at`** — including `fact`, `ratio`, `stock_price`,
> `stock_price_daily` and the smart-money tables. `entity`, `references`,
> `filing` and `valuation` are **not** PIT-filtered.

Runnable: [`pit_as_of_restatement.py`](../examples/python/pit_as_of_restatement.py).
Deeper treatment: [`pit_backtest.py`](../examples/python/pit_backtest.py).

---

## 10. Restatement Radar

**Question:** *"Which numbers changed after they were published — and did anyone announce it?"*

Everyone knows companies restate. The finding is **how** the change reaches you.

```python
from valuein_sdk import ValueinClient

client = ValueinClient(tables=["restatement_events"])

print("How revisions actually reach the public:")
print(client.run_query("""
    SELECT disclosure_class, count(*) AS revisions,
           round(100.0*count(*) / sum(count(*)) OVER (), 1) AS pct
    FROM restatement_events
    GROUP BY disclosure_class ORDER BY revisions DESC
""").to_string(index=False))

print("\nThe MPWR revision, with both filings for one-click verification:")
print(client.run_query("""
    SELECT ticker, standard_concept, fiscal_period, period_end,
           first_value/1e9 AS as_first_filed_bn, current_value/1e9 AS current_bn,
           round(delta_pct*100, 2) AS delta_pct,
           disclosure_class, first_accession, current_accession
    FROM restatement_events
    WHERE ticker = 'MPWR' AND standard_concept = 'NetIncome'
      AND period_end = DATE '2024-12-31'
""").to_string(index=False))
```

```
How revisions actually reach the public:
disclosure_class  revisions  pct
     undisclosed      44468 88.5
    non_reliance       4317  8.6
         amended       1449  2.9

The MPWR revision, with both filings for one-click verification:
ticker standard_concept fiscal_period period_end  as_first_filed_bn  current_bn  delta_pct disclosure_class      first_accession    current_accession
  MPWR        NetIncome            FY 2024-12-31             1.7867    1.592058     -10.89     non_reliance 0001437749-25-005903 0001437749-26-014084
```

The three classes mean different things:

| `disclosure_class` | What happened |
|---|---|
| `non_reliance` | The company filed an 8-K **Item 4.02** telling the SEC not to rely on previously issued financials. **Announced.** |
| `amended` | The number changed in a 10-K/A or 10-Q/A. **Flagged.** |
| `undisclosed` | The number changed inside a *routine* 10-Q or 10-K. No 4.02, no amendment. **Nothing announced it.** |

**88.5% of revisions arrived quietly.** Databases built by parsing 8-Ks can only
ever see what companies *announced*; finding the rest requires having kept every
vintage of every fact.

> **Which universe that 88.5% is measured over matters.** `restatement_events`
> is **not** sliced to your tier — the query above runs across all 5,663 CIKs in
> the feed, so 88.5% is the whole-feed figure. Elsewhere we publish **94.5%**,
> which is the same measurement restricted to the **S&P 500**. Both are correct
> and neither is the other's correction — narrowing from the whole feed to the
> S&P 500 moves the quiet share from 88.5% to 94.5%. Always state the population
> when you quote either number.

Every row carries both accession numbers, so you can check us against the source
in 30 seconds without asking us anything:

```
0001437749-25-005903 -> https://www.sec.gov/Archives/edgar/data/1280452/000143774925005903/
0001437749-26-014084 -> https://www.sec.gov/Archives/edgar/data/1280452/000143774926014084/
```

Largest *undisclosed* revisions to headline earnings — note the top row, Apple's
FY2009 net income moving from $5.704bn to $8.235bn inside a routine filing when
it retrospectively adopted new revenue-recognition rules:

```
ticker fiscal_period period_end  as_first_filed_bn  current_bn  delta_pct
  AAPL            FY 2009-09-26              5.704       8.235       44.4
   LNG            FY 2023-12-31              9.881      12.059       22.0
  MSFT          None 2017-06-30              6.513       8.069       23.9
   LNG            FY 2025-12-31              5.330       6.794       27.5
   APO            FY 2022-12-31             -3.213      -1.961       39.0
...
```

> **`undisclosed` is a claim about DISCLOSURE, never about wrongdoing.** ASC 606
> and ASC 842 adoptions restate comparatives with nobody at fault — the Apple row
> above is exactly that. The data proves *when* a number changed and *whether it
> was announced*; it does not prove intent, and no risk score is offered here on
> purpose.

> **Gotcha — `fiscal_period` is NULL for some rows** (the `None` on the MSFT
> row above is real captured output, not a formatting artifact). It is the raw
> value the filer's XBRL carried, and it is not reliable enough to key on:
> one `period_end` has been seen tagged Q1, Q2 *and* Q3. Key on `period_end`,
> and treat `fiscal_period` as a label rather than a join column.

> **Gotcha — `delta_pct` is a magnitude change, so read the sign against the
> values.** The APO row above moves from **-3.213bn to -1.961bn**: a loss that
> got *smaller*. A positive `delta_pct` does not mean the company earned more.

> **Gotcha — apply a magnitude guard before showing this to an analyst.** A
> minority of rows in this table are unit/scale artifacts rather than economic
> restatements: the same figure re-tagged at a different scale appears as a
> ~99.9% "change" (Charles Schwab's net income shows an exact ÷1000 ratio across
> five separate fiscal years). Bounding `abs(delta_pct)` below ~0.6 and pinning
> `unit = 'USD'` keeps them out. The unguarded query is what produced the
> artifact rows; the guarded one produced the table above.

> **Tier note — this table is not restricted to the Sample universe.** It spans
> 5,663 CIKs versus the 498 companies in the Sample `references` table, so you
> can hit tickers here that you cannot resolve to a name or pull fundamentals for
> without Pro / Institutional.

Runnable: [`restatement_radar.py`](../examples/python/restatement_radar.py).

---

## Tier summary

| Tier | Universe / history | What unlocks |
|---|---|---|
| **Sample** (no token) | S&P 500, ~5-year window | Everything on this page |
| **S&P 500** (free, registration) | Full S&P 500, 1993→present | Full history for index names |
| **Pro** ($49/mo) | 19,000+ companies, 15-year rolling | Delisted-company names, full universe screens |
| **Institutional** ($499/mo) | 19,000+ + foreign issuers, 1993→present | 6 smart-money tables (insider + 13F), intraday filing events, redistribution |

Smart-money workflows are shown in
[`smart_money_screen.py`](../examples/python/smart_money_screen.py) (Institutional).

---

## See also

- [`QUERY_COOKBOOK.md`](QUERY_COOKBOOK.md) — 20 recipes and the full anti-pattern table
- [`METHODOLOGY.md`](METHODOLOGY.md) — how PIT, restatements and XBRL normalization work
- [`docs/accuracy/`](accuracy/) — the measured, CI-gated accuracy baseline
- [`examples/python/`](../examples/python/) — every script referenced above
