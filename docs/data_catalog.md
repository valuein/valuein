# Valuein Data Catalog

> **Last updated**: 2026-06-04  
> **Standardized concepts**: 291  
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

## balance_sheet

### `AccountsPayable`

**Unit:** USD  ·  **Category:** working_capital  ·  **Flow:** no

IFRS trade & other current payables.

### `AccountsPayableAndAccrued`

**Unit:** USD  ·  **Category:** working_capital  ·  **Flow:** no

Combined accounts payable and accrued liabilities.

### `AccountsReceivable`

**Unit:** USD  ·  **Category:** working_capital  ·  **Flow:** no

IFRS trade & other current receivables.

### `AccruedExpenses`

**Unit:** USD  ·  **Category:** working_capital  ·  **Flow:** no

Accrued liabilities (salaries, interest, utilities).

### `AccumulatedAmortization`

**Unit:** USD  ·  **Category:** intangibles  ·  **Flow:** no

Accumulated amortization on finite-lived intangible assets. IntangibleAssetsNet = IntangibleAssetsGross - this.

### `AccumulatedDepreciation`

**Unit:** USD  ·  **Category:** fixed_assets  ·  **Flow:** no

Total accumulated depreciation on PP&E.

### `AdditionalPaidInCapital`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** no

Excess of issue price over par value on equity issuances.

### `AllowanceForDoubtfulAccounts`

**Unit:** USD  ·  **Category:** balance_sheet_other  ·  **Flow:** no

Reserve against uncollectible receivables.

### `AOCI`

**Unit:** USD  ·  **Category:** comprehensive_income  ·  **Flow:** no

Accumulated other comprehensive income/loss balance.

### `AssetRetirementObligation`

**Unit:** USD  ·  **Category:** balance_sheet_other  ·  **Flow:** no

Asset retirement obligation liability (ASC 410) — present value of legally-required asset decommissioning, restoration, or environmental remediation costs.

### `AvailableForSaleSecurities`

**Unit:** USD  ·  **Category:** investments  ·  **Flow:** no

Securities classified as available-for-sale (AFS) under ASC 320
— neither held-to-maturity nor trading.  Carried at fair value
with unrealized gains/losses in OCI.

### `CapitalizedSoftwareCosts`

**Unit:** USD  ·  **Category:** tech_saas  ·  **Flow:** no

Capitalized internally developed software. Amortized over the
expected useful life (typically 3–5 years).

### `CashAndEquivalents`

**Unit:** USD  ·  **Category:** liquidity  ·  **Flow:** no

Cash, demand deposits, and highly liquid investments with original
maturities ≤ 90 days.  Includes restricted cash variants disclosed
by ASC 230 (US GAAP) and IAS 7 (IFRS) — both treated identically
here since restricted balances still belong on the balance sheet
and are not separable in cross-sectional analysis.

### `CommonSharesAuthorized`

**Unit:** shares  ·  **Category:** equity  ·  **Flow:** yes

Maximum shares authorized per corporate charter.

### `CommonSharesIssued`

**Unit:** shares  ·  **Category:** equity  ·  **Flow:** yes

Total common shares issued (including treasury).

### `CommonSharesOutstanding`

**Unit:** shares  ·  **Category:** equity  ·  **Flow:** no

Common shares currently outstanding (issued minus treasury).

### `CommonStockParValue`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** no

Par or stated value per common share.

### `CommonStockValue`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** no

IFRS issued share capital — analogous to GAAP CommonStockValue.

### `ContractAssets`

**Unit:** USD  ·  **Category:** tech_saas  ·  **Flow:** no

ASC 606 contract assets — earned but unbilled revenue. Common in
multi-year SaaS contracts billed annually but recognized monthly.

### `CurrentAssets`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** no

IFRS current assets.

### `CurrentLiabilities`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

IFRS current liabilities.

### `CurrentPortionLTD`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** no

Long-term debt maturing within 12 months.

### `DeferredAcquisitionCosts`

**Unit:** USD  ·  **Category:** insurance  ·  **Flow:** no

Capitalized policy acquisition costs (commissions, underwriting)
amortized over the policy life. Asset on the BS under GAAP.

### `DeferredFinanceCostsNet`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Unamortized debt-issuance costs presented as a contra-liability to
long-term debt (ASU 2015-03).  Material for issuers with frequent
debt refinancings.

### `DeferredRevenueCurrent`

**Unit:** USD  ·  **Category:** revenue  ·  **Flow:** no

Contract liabilities / deferred revenue (current).

### `DeferredRevenueNoncurrent`

**Unit:** USD  ·  **Category:** revenue  ·  **Flow:** no

Long-term deferred revenue / contract liabilities.

### `DeferredTaxAssetsGross`

**Unit:** USD  ·  **Category:** deferred  ·  **Flow:** no

Total deferred tax assets before valuation allowance.  Pair with
DeferredTaxValuationAllowance to get DeferredTaxAssetsNet.

### `DeferredTaxAssetsLiabNet`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** no

Net deferred tax position (DTA − DTL) reported as a single line.
Most filers post-ASU 2015-17 net everything to noncurrent; legacy
current vs. noncurrent split aliases are folded in here.

### `DeferredTaxAssetsNet`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** no

Net deferred tax assets.

### `DeferredTaxAssetsNOL`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** no

DTA from net operating loss carryforwards.

### `DeferredTaxAssetsOther`

**Unit:** USD  ·  **Category:** deferred  ·  **Flow:** no

Deferred tax assets from sources not separately disclosed.

### `DeferredTaxLiabilities`

**Unit:** USD  ·  **Category:** deferred  ·  **Flow:** no

Total deferred tax liabilities (gross), before netting against
deferred tax assets.  Net version is DeferredTaxLiabNoncurrent.

### `DeferredTaxLiabilitiesOther`

**Unit:** USD  ·  **Category:** deferred  ·  **Flow:** no

Deferred tax liabilities from sources not separately disclosed.

### `DeferredTaxLiabNoncurrent`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** no

Deferred tax liabilities (non-current).

### `DeferredTaxValuationAllowance`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** no

Valuation allowance against deferred tax assets.

### `Deposits`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** no

Customer deposits (checking, savings, time deposits, money market).
Largest liability on most bank balance sheets and the cheapest
funding source.

### `DerivativeAssets`

**Unit:** USD  ·  **Category:** balance_sheet_other  ·  **Flow:** no

Fair value of derivative instruments held as assets.

### `DerivativeLiabilities`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Fair value of derivative instruments held as liabilities.

### `DueToRelatedParties`

**Unit:** USD  ·  **Category:** balance_sheet_other  ·  **Flow:** no

Amounts owed to related parties.

### `EquityMethodInvestments`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** no

Equity method investees (20-50% ownership stakes).

### `FederalFundsPurchased`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** no

Overnight borrowings of reserves from other banks.

### `FederalFundsSold`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** no

Overnight loans of excess reserves to other banks.

### `FederalHomeLoanBankAdvances`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** no

Wholesale funding from FHLB system.

### `Goodwill`

**Unit:** USD  ·  **Category:** intangibles  ·  **Flow:** no

IFRS goodwill.

### `IntangibleAssetsGross`

**Unit:** USD  ·  **Category:** intangibles  ·  **Flow:** no

Intangible assets at historical cost.

### `IntangibleAssetsNet`

**Unit:** USD  ·  **Category:** intangibles  ·  **Flow:** no

Intangible assets (patents, trademarks, etc.) net of amortization.

### `InterestPayable`

**Unit:** USD  ·  **Category:** non_operating  ·  **Flow:** no

Accrued interest on debt not yet paid.

### `Inventory`

**Unit:** USD  ·  **Category:** working_capital  ·  **Flow:** no

IFRS inventories.

### `InventoryFinishedGoods`

**Unit:** USD  ·  **Category:** working_capital  ·  **Flow:** no

Finished goods inventory (ready for sale).

### `InventoryRawMaterials`

**Unit:** USD  ·  **Category:** working_capital  ·  **Flow:** no

Raw material inventory (unprocessed inputs).

### `InventoryWIP`

**Unit:** USD  ·  **Category:** working_capital  ·  **Flow:** no

Work-in-process inventory (partially completed).

### `LoanLossAllowance`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** no

Reserve held against probable / expected loan losses. CECL under
US GAAP, ECL under IFRS 9. Contra-asset against gross loans.

### `LoansReceivable`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** no

Gross loans and leases held for investment, before allowance for
credit losses. Largest asset on most bank balance sheets.

### `LongTermDebt`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Long-term debt due after 12 months, before unamortized discount or
deferred financing costs.  Excludes lease obligations (use
OperatingLeaseLiabNoncurrent) and current maturities (use
CurrentPortionLTD).

### `LongTermInvestments`

**Unit:** USD  ·  **Category:** investments  ·  **Flow:** no

Non-current investment securities.

### `MinorityInterest`

**Unit:** USD  ·  **Category:** non_operating  ·  **Flow:** no

IFRS non-controlling (minority) interests in equity.

### `NonperformingLoans`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** no

Loans 90+ days past due or on non-accrual status. NPL ratio
(NPL / total loans) is the canonical asset-quality metric.

### `NotesPayableCurrent`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Short-term notes payable (typically < 12 months).  Distinct from
accounts payable — these are formal promissory notes.

### `OperatingLeaseLiabCurrent`

**Unit:** USD  ·  **Category:** leases  ·  **Flow:** no

IFRS current lease liability (IFRS 16).

### `OperatingLeaseLiabNoncurrent`

**Unit:** USD  ·  **Category:** leases  ·  **Flow:** no

IFRS non-current lease liability (IFRS 16).

### `OperatingLeaseLiabTotal`

**Unit:** USD  ·  **Category:** leases  ·  **Flow:** no

Total operating lease liability.

### `OtherAssets`

**Unit:** USD  ·  **Category:** balance_sheet_other  ·  **Flow:** no

Single ``Other Assets`` line item — neither current nor non-current
splits.  Used by issuers that report a flat ``Other Assets`` total.
For the explicitly-current and explicitly-non-current variants use
OtherCurrentAssets / OtherNoncurrentAssets.

### `OtherCurrentAssets`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** no

Current assets not classified elsewhere.

### `OtherCurrentLiabilities`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Current liabilities not classified elsewhere.

### `OtherLiabilities`

**Unit:** USD  ·  **Category:** balance_sheet_other  ·  **Flow:** no

Single ``Other Liabilities`` line — used by issuers that don't
split current vs non-current.  See OtherCurrentLiabilities /
OtherNoncurrentLiabilities for the split variants.

### `OtherNoncurrentAssets`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** no

Non-current assets not classified elsewhere.

### `OtherNoncurrentLiabilities`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Non-current liabilities not classified elsewhere.

### `PatentsCarryingValue`

**Unit:** USD  ·  **Category:** pharma  ·  **Flow:** no

Net carrying value of acquired or licensed patents.

### `PensionLiabilities`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Defined benefit pension and postretirement obligations.

### `PensionPlanFundedStatus`

**Unit:** USD  ·  **Category:** pension  ·  **Flow:** no

Pension plan assets minus PBO (funded status).

### `PolicyLiabilities`

**Unit:** USD  ·  **Category:** insurance  ·  **Flow:** no

Total policy reserves — future obligations to policyholders for
claims, annuities, and policy benefits. Usually the largest
insurance liability.

### `PPEGross`

**Unit:** USD  ·  **Category:** fixed_assets  ·  **Flow:** no

PP&E at historical cost before accumulated depreciation.

### `PPENet`

**Unit:** USD  ·  **Category:** fixed_assets  ·  **Flow:** no

IFRS net PP&E.

### `PreferredSharesOutstanding`

**Unit:** shares  ·  **Category:** equity  ·  **Flow:** no

Preferred shares outstanding / issued / authorized.

### `PreferredStockParValue`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** no

Par or stated value per preferred share.

### `PreferredStockValue`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** no

Total value of preferred shares issued.

### `PrepaidExpenses`

**Unit:** USD  ·  **Category:** working_capital  ·  **Flow:** no

Advance payments for future expenses.

### `ProjectedBenefitObligation`

**Unit:** USD  ·  **Category:** balance_sheet_other  ·  **Flow:** no

Pension / OPEB projected benefit obligation.

### `ReinsuranceRecoverable`

**Unit:** USD  ·  **Category:** insurance  ·  **Flow:** no

Estimated amounts recoverable from reinsurers for ceded losses.
Important credit exposure to reinsurer counterparties.

### `RestructuringReserve`

**Unit:** USD  ·  **Category:** balance_sheet_other  ·  **Flow:** no

Liability for future restructuring costs (severance, lease exit,
contract termination) accrued under ASC 420 / IAS 37.  Movement
feeds the income statement RestructuringCharges line.

### `RetainedEarnings`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** no

IFRS retained earnings.

### `RightOfUseAssetFinance`

**Unit:** USD  ·  **Category:** balance_sheet_other  ·  **Flow:** no

Finance lease right-of-use asset.

### `RightOfUseAssetOperating`

**Unit:** USD  ·  **Category:** operating  ·  **Flow:** no

Operating lease right-of-use asset (ASC 842).

### `SeparateAccountAssets`

**Unit:** USD  ·  **Category:** insurance  ·  **Flow:** no

Assets held in separate accounts on behalf of variable annuity /
universal life policyholders. Off-balance-sheet for credit risk
but on-balance-sheet under GAAP/IFRS.

### `ShortTermDebt`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

IFRS short-term borrowings.

### `ShortTermInvestments`

**Unit:** USD  ·  **Category:** investments  ·  **Flow:** no

Marketable securities and short-term investment holdings.

### `StockholdersEquity`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** no

Parent-only stockholders' equity (excludes non-controlling interest).

### `StockholdersEquityIncludingNCI`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** no

Total stockholders' equity including non-controlling interest — institutional total book value.

### `TaxPayable`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** no

Current income taxes owed to tax authorities.

### `TemporaryEquity`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** no

Mezzanine/temporary equity — redeemable equity between debt and equity.

### `TotalAssets`

**Unit:** USD  ·  **Category:** balance_sheet_other  ·  **Flow:** no

IFRS total assets.

### `TotalCurrentLiabilities`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Total current liabilities.

### `TotalDebt`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Total interest-bearing debt obligations.

### `TotalLiabilities`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

IFRS total liabilities.  IFRS 16 may inflate vs GAAP ASC 842.

### `TotalLiabilitiesAndEquity`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** no

Must equal Total Assets (accounting identity).

### `TotalNoncurrentAssets`

**Unit:** USD  ·  **Category:** balance_sheet_other  ·  **Flow:** no

Sum of non-current (long-term) assets.  Reciprocal of CurrentAssets;
together they sum to TotalAssets.  Reported directly by some
issuers (us-gaap:AssetsNoncurrent) and derivable as TotalAssets −
CurrentAssets when not reported.

### `TotalNoncurrentLiabilities`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Total non-current liabilities.

### `TreasuryShares`

**Unit:** shares  ·  **Category:** equity  ·  **Flow:** yes

Number of common shares held in treasury.

### `TreasuryStock`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** no

Cost of repurchased shares held in treasury (contra-equity).

### `UnearnedPremiums`

**Unit:** USD  ·  **Category:** insurance  ·  **Flow:** no

Premiums collected for coverage not yet provided — the deferred
revenue analog for P&C insurers. Earned over the policy period.

## cash_flow

### `AccountsPayableChange`

**Unit:** USD  ·  **Category:** cash_flow_operating  ·  **Flow:** yes

Working capital: accounts payable change.

### `AccountsReceivableChange`

**Unit:** USD  ·  **Category:** cash_flow_operating  ·  **Flow:** yes

Working capital: accounts receivable change.

### `AccrualsChange`

**Unit:** USD  ·  **Category:** cash_flow_operating  ·  **Flow:** yes

Working capital: accrued liabilities change.

### `Acquisitions`

**Unit:** USD  ·  **Category:** cash_flow_investing  ·  **Flow:** yes

Cash paid for business acquisitions (M&A).

### `BadDebtProvision`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** yes

Credit loss provision (CF add-back).

### `CAPEX`

**Unit:** USD  ·  **Category:** cash_flow_other  ·  **Flow:** yes

IFRS capital expenditure — PP&E purchases.

### `CommonStockIssuance`

**Unit:** USD  ·  **Category:** cash_flow_financing  ·  **Flow:** yes

Cash proceeds from issuing common stock — IPO, follow-on offering,
private placement.  Distinct from EquityIssuance (broader,
includes non-cash issuances).

### `DebtIssuance`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** yes

IFRS debt issuance cash inflow.

### `DebtIssuanceCosts`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** yes

Fees and costs paid for issuing debt.

### `DebtRepayment`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** yes

IFRS debt repayment cash outflow.

### `DeferredRevenueChange`

**Unit:** USD  ·  **Category:** deferred  ·  **Flow:** yes

Working capital: deferred revenue change.

### `DeferredTaxNonCash`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** yes

Non-cash deferred tax provision (CF add-back).

### `Divestitures`

**Unit:** USD  ·  **Category:** cash_flow_investing  ·  **Flow:** yes

Cash received from divesting businesses or subsidiaries.  Mirror of
Acquisitions; together they bracket net M&A activity (the
``net_ma_activity`` field in get_capital_allocation_profile).

### `Dividends`

**Unit:** USD  ·  **Category:** shareholder_returns  ·  **Flow:** yes

Cash dividends paid to shareholders.

### `EffectOfExchangeRateOnCash`

**Unit:** pct  ·  **Category:** liquidity  ·  **Flow:** yes

Currency translation impact on cash position.

### `EquityIssuance`

**Unit:** USD  ·  **Category:** equity  ·  **Flow:** yes

Cash from issuing common shares (IPO, secondary, option exercises).

### `ExcessTaxBenefitFromSBC`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** yes

Tax benefit realised on SBC in excess of grant-date expense.

### `FinancingCashFlow`

**Unit:** USD  ·  **Category:** liquidity  ·  **Flow:** yes

IFRS financing cash flows.

### `FXEffectOnCash`

**Unit:** USD  ·  **Category:** liquidity  ·  **Flow:** yes

Foreign exchange rate impact on cash balances.

### `GoodwillAcquired`

**Unit:** USD  ·  **Category:** cash_flow_investing  ·  **Flow:** yes

Goodwill recognized during the period from business combinations.
A direct signal of M&A activity; complements the existing
Acquisitions cash-outflow canonical.

### `IntangiblesPurchase`

**Unit:** USD  ·  **Category:** intangibles  ·  **Flow:** yes

Cash spent on intangible assets (patents, software, licenses).

### `InterestPaidCash`

**Unit:** USD  ·  **Category:** non_operating  ·  **Flow:** yes

Cash interest paid (supplemental disclosure).

### `InterestPayableChange`

**Unit:** USD  ·  **Category:** non_operating  ·  **Flow:** yes

Working capital: interest payable change.

### `InventoryChange`

**Unit:** USD  ·  **Category:** working_capital  ·  **Flow:** yes

Working capital: inventory change.

### `InvestingCashFlow`

**Unit:** USD  ·  **Category:** liquidity  ·  **Flow:** yes

IFRS investing cash flows.

### `InvestmentsPurchase`

**Unit:** USD  ·  **Category:** investments  ·  **Flow:** yes

Cash used to purchase investment securities.

### `InvestmentsSale`

**Unit:** USD  ·  **Category:** investments  ·  **Flow:** yes

Proceeds from selling/maturing investment securities.

### `MinorityDistributions`

**Unit:** USD  ·  **Category:** cash_flow_financing  ·  **Flow:** yes

Dividends/distributions paid to non-controlling interest holders.

### `NetChangeInCash`

**Unit:** USD  ·  **Category:** liquidity  ·  **Flow:** yes

IFRS net change in cash for the period.

### `OperatingCashFlow`

**Unit:** USD  ·  **Category:** liquidity  ·  **Flow:** yes

IFRS operating cash flows.

### `OtherNonCashCharges`

**Unit:** USD  ·  **Category:** liquidity  ·  **Flow:** yes

Other non-cash adjustments to net income.

### `PPESale`

**Unit:** USD  ·  **Category:** fixed_assets  ·  **Flow:** yes

Proceeds from selling PP&E or productive assets.

### `PrepaidExpensesChange`

**Unit:** USD  ·  **Category:** working_capital  ·  **Flow:** yes

Working capital: prepaid expense change.

### `RestrictedCashChange`

**Unit:** USD  ·  **Category:** liquidity  ·  **Flow:** yes

Period change in restricted cash — reconciling item in CF statement.

### `ROUAssetForNewLeases`

**Unit:** USD  ·  **Category:** leases  ·  **Flow:** yes

Non-cash: ROU assets obtained for new operating lease liabilities.

### `SBCTaxWithholding`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** yes

Tax withholding payments related to equity award settlement.

### `ShareBuyback`

**Unit:** USD  ·  **Category:** shareholder_returns  ·  **Flow:** yes

Cash spent repurchasing company shares.

### `StockBasedCompensation`

**Unit:** USD  ·  **Category:** stock_compensation  ·  **Flow:** yes

IFRS share-based payment adjustment in the operating cash-flow reconciliation.

### `StockOptionExercise`

**Unit:** USD  ·  **Category:** cash_flow_financing  ·  **Flow:** yes

Cash received from employees exercising stock options.  Separate
from non-cash equity issuance disclosures.

### `TaxesPaidCash`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** yes

Cash income taxes paid (supplemental disclosure).

## supplemental

### `AdjustedFundsFromOperations`

**Unit:** USD  ·  **Category:** reit  ·  **Flow:** yes

AFFO = FFO − recurring CapEx − straight-line rent adjustments.
Closer to free-cash-flow-per-share than FFO.

### `CombinedRatio`

**Unit:** pct  ·  **Category:** insurance  ·  **Flow:** no

Loss ratio + expense ratio. Below 100 % = underwriting profit;
above = underwriting loss. The single most-watched P&C metric.

### `ContingentConsiderationChange`

**Category:** supplemental  ·  **Flow:** no

Fair-value re-measurement of earnout / contingent consideration.

### `DebtMaturityThereafter`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Long-term debt principal repayments due after year 5.

### `DebtMaturityY1`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Long-term debt principal repayments due within 12 months.

### `DebtMaturityY2`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Long-term debt principal repayments due in year 2.

### `DebtMaturityY3`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Long-term debt principal repayments due in year 3.

### `DebtMaturityY4`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Long-term debt principal repayments due in year 4.

### `DebtMaturityY5`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Long-term debt principal repayments due in year 5.

### `DefinedContributionCost`

**Category:** expenses  ·  **Flow:** no

401(k) and other defined contribution plan expense.

### `FundsFromOperations`

**Unit:** USD  ·  **Category:** reit  ·  **Flow:** yes

NAREIT FFO: Net income + Real estate D&A − Gains on property sales.
The standard REIT earnings proxy. AFFO subtracts recurring CapEx
to approximate distributable cash.

### `IncrementalDilutiveShares`

**Unit:** shares  ·  **Category:** supplemental  ·  **Flow:** yes

Additional shares from dilutive securities (options, RSUs, convertibles).

### `IntangibleAmortizationThereafter`

**Unit:** USD  ·  **Category:** intangibles  ·  **Flow:** yes

Expected amortization expense for finite-lived intangibles after year 5.

### `IntangibleAmortizationY1`

**Unit:** USD  ·  **Category:** intangibles  ·  **Flow:** yes

Expected amortization expense for finite-lived intangibles in the next 12 months.

### `IntangibleAmortizationY2`

**Unit:** USD  ·  **Category:** intangibles  ·  **Flow:** yes

Expected amortization expense for finite-lived intangibles in year 2.

### `IntangibleAmortizationY3`

**Unit:** USD  ·  **Category:** intangibles  ·  **Flow:** yes

Expected amortization expense for finite-lived intangibles in year 3.

### `IntangibleAmortizationY4`

**Unit:** USD  ·  **Category:** intangibles  ·  **Flow:** yes

Expected amortization expense for finite-lived intangibles in year 4.

### `IntangibleAmortizationY5`

**Unit:** USD  ·  **Category:** intangibles  ·  **Flow:** yes

Expected amortization expense for finite-lived intangibles in year 5.

### `LineOfCreditMax`

**Unit:** USD  ·  **Category:** leverage  ·  **Flow:** no

Maximum (committed) borrowing capacity under all revolving credit
facilities.  Standard credit-strength metric; the drawn portion
sits in ShortTermDebt or LongTermDebt depending on maturity.

### `LossRatio`

**Unit:** pct  ·  **Category:** insurance  ·  **Flow:** no

Claims paid / premiums earned. Sub-100 % means underwriting
profitability before expenses. Industry benchmark for P&C.

### `NetChargeOffs`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** yes

Loans written off during the period minus recoveries on previously
charged-off loans. Realized credit losses; flow-side complement to
ProvisionForLoanLosses.

### `NetOperatingIncome`

**Unit:** USD  ·  **Category:** reit  ·  **Flow:** yes

Property rental revenue − property operating expenses (excludes
D&A, interest, G&A). Same-store NOI growth is the canonical REIT
operational metric.

### `NumberOfEmployees`

**Category:** operational  ·  **Flow:** no

Total full-time equivalent employees.

### `NumberOfSegments`

**Category:** segment  ·  **Flow:** no

Number of reportable operating segments.

### `OccupancyRate`

**Unit:** pct  ·  **Category:** reit  ·  **Flow:** no

Percentage of total rentable square footage currently leased.

### `OilProduction`

**Unit:** barrels  ·  **Category:** energy  ·  **Flow:** yes

Crude oil produced during the period.

### `OperatingLeaseCashPayments`

**Category:** leases  ·  **Flow:** no

Cash paid for operating lease liabilities.

### `OperatingLeaseImputedInterest`

**Category:** non_operating  ·  **Flow:** no

Imputed interest discount on undiscounted lease payments.

### `OperatingLeasePaymentsDue`

**Category:** leases  ·  **Flow:** no

Total undiscounted future operating lease payments.

### `OperatingLeasePaymentsThereafter`

**Category:** leases  ·  **Flow:** no

Operating lease payments due after year 5.

### `OperatingLeasePaymentsY1`

**Category:** leases  ·  **Flow:** no

Operating lease payments due within 12 months.

### `OperatingLeasePaymentsY2`

**Category:** leases  ·  **Flow:** no

Operating lease payments due in year 2.

### `OperatingLeasePaymentsY3`

**Category:** leases  ·  **Flow:** no

Operating lease payments due in year 3.

### `OperatingLeasePaymentsY4`

**Category:** leases  ·  **Flow:** no

Operating lease payments due in year 4.

### `OperatingLeasePaymentsY5`

**Category:** leases  ·  **Flow:** no

Operating lease payments due in year 5.

### `OperatingLeaseWADiscountRate`

**Unit:** pct  ·  **Category:** leases  ·  **Flow:** no

Weighted average discount rate for operating leases.

### `ProvedGasReserves`

**Unit:** mcf  ·  **Category:** energy  ·  **Flow:** no

Estimated economically recoverable natural gas reserves.

### `ProvedOilReserves`

**Unit:** barrels  ·  **Category:** energy  ·  **Flow:** no

Estimated quantities of oil that can be economically recovered
under current conditions. Reserve life (reserves / annual
production) is a core upstream operator metric.

### `RemainingPerformanceObligation`

**Unit:** USD  ·  **Category:** tech_saas  ·  **Flow:** no

ASC 606 disclosure: total transaction price for unsatisfied
performance obligations. Closest GAAP-disclosed proxy for
contracted backlog / forward revenue (often bigger than ARR for
enterprise SaaS).

### `RevenueDomestic`

**Category:** revenue  ·  **Flow:** no

Revenue from the issuer's home country.

### `RevenueInternational`

**Category:** revenue  ·  **Flow:** no

Revenue from markets outside the issuer's home country.

### `SBCOptionsExercisable`

**Category:** stock_compensation  ·  **Flow:** no

Stock options currently exercisable.

### `SBCOptionsExercisableWAExercisePrice`

**Category:** stock_compensation  ·  **Flow:** no

Weighted-avg exercise price of options currently exercisable.

### `SBCOptionsExercised`

**Category:** stock_compensation  ·  **Flow:** no

Stock options exercised during the period.

### `SBCOptionsExercisesWAExercisePrice`

**Category:** stock_compensation  ·  **Flow:** no

Weighted-avg exercise price on options exercised in period.

### `SBCOptionsForfeited`

**Category:** stock_compensation  ·  **Flow:** no

Stock options forfeited during the period.

### `SBCOptionsForfeituresWAExercisePrice`

**Category:** stock_compensation  ·  **Flow:** no

Weighted-avg exercise price on options forfeited/expired.

### `SBCOptionsGranted`

**Category:** stock_compensation  ·  **Flow:** no

Stock options granted during the period.

### `SBCOptionsGrantsWAExercisePrice`

**Category:** stock_compensation  ·  **Flow:** no

Weighted-avg exercise price on options granted in period.

### `SBCOptionsGrantsWAGrantDateFairValue`

**Category:** stock_compensation  ·  **Flow:** no

Weighted-avg grant-date fair value of options granted.

### `SBCOptionsIntrinsicValue`

**Category:** stock_compensation  ·  **Flow:** no

Aggregate intrinsic value of outstanding options.

### `SBCOptionsOutstanding`

**Category:** stock_compensation  ·  **Flow:** no

Stock options currently outstanding.

### `SBCOptionsVestedAndExpectedToVestCount`

**Category:** stock_compensation  ·  **Flow:** no

Number of options vested + expected to vest (outstanding-weighted).

### `SBCOptionsVestedAndExpectedToVestIntrinsicValue`

**Category:** stock_compensation  ·  **Flow:** no

Aggregate intrinsic value of options vested + expected to vest.

### `SBCOptionsVestedAndExpectedToVestWAExercisePrice`

**Category:** stock_compensation  ·  **Flow:** no

Weighted-avg exercise price of options vested + expected to vest.

### `SBCOptionsWAPrice`

**Category:** stock_compensation  ·  **Flow:** no

Weighted average exercise price of outstanding options.

### `SBCRSUsGranted`

**Category:** stock_compensation  ·  **Flow:** no

RSUs granted during the period.

### `SBCRSUsNonvestedWAGrantDateFairValue`

**Category:** stock_compensation  ·  **Flow:** no

Weighted-avg grant-date fair value of nonvested RSUs.

### `SBCRSUsOutstanding`

**Category:** stock_compensation  ·  **Flow:** no

Restricted stock units (RSUs) currently outstanding.

### `SBCRSUsVested`

**Category:** stock_compensation  ·  **Flow:** no

RSUs vested during the period.

### `SBCTaxBenefit`

**Category:** tax  ·  **Flow:** no

Income tax benefit from equity compensation.

### `SBCUnrecognizedCost`

**Category:** stock_compensation  ·  **Flow:** no

Remaining unrecognized SBC expense for unvested awards.

### `SegmentRevenue`

**Category:** revenue  ·  **Flow:** no

Revenue / operating profit by reportable segment.

### `ShareRepurchaseAuthorized`

**Category:** shareholder_returns  ·  **Flow:** no

Board-authorized share repurchase program amount.

### `TierOneCapitalRatio`

**Unit:** pct  ·  **Category:** banking  ·  **Flow:** no

Tier 1 capital divided by risk-weighted assets. Basel III
regulatory minimum for well-capitalized banks is 8 %. Below 6 %
triggers prompt corrective action.

### `TotalRiskBasedCapitalRatio`

**Unit:** pct  ·  **Category:** banking  ·  **Flow:** no

Total regulatory capital (Tier 1 + Tier 2) divided by
risk-weighted assets. Basel III minimum is 10.5 % for
well-capitalized banks.

### `UnrecognizedTaxBenefits`

**Category:** tax  ·  **Flow:** no

Uncertain tax positions that could result in future obligations.

### `WeightedAverageCommonShares`

**Unit:** shares  ·  **Category:** equity  ·  **Flow:** yes

IFRS weighted-average shares outstanding (basic).

## income

### `AntidilutiveShares`

**Unit:** shares  ·  **Category:** income_other  ·  **Flow:** yes

Shares excluded from diluted EPS as antidilutive.

### `ClaimsAndBenefits`

**Unit:** USD  ·  **Category:** insurance  ·  **Flow:** yes

Claims paid + change in claim reserves + policyholder benefits.
The largest expense line for most insurers; drives the loss ratio.

### `ClinicalTrialCosts`

**Unit:** USD  ·  **Category:** pharma  ·  **Flow:** yes

Costs incurred running clinical trials. Not always disclosed as a
separate line — often embedded in R&D. When broken out,
reveals development-stage focus.

### `CostOfRevenue`

**Unit:** USD  ·  **Category:** revenue  ·  **Flow:** yes

IFRS cost of sales — equivalent to GAAP CostOfRevenue.

### `CurrentIncomeTaxExpense`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** yes

Aggregated current-period income tax expense (federal + state +
foreign).  Distinct from the deferred-tax component, which moves
through DeferredTaxExpense.  Companies that report only an
aggregated figure surface here; per-jurisdiction filers expose
CurrentTaxFederal / CurrentTaxState / CurrentTaxForeign.

### `CurrentTaxFederal`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** yes

Federal/national current income tax.

### `CurrentTaxForeign`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** yes

Foreign jurisdiction current income tax.

### `CurrentTaxState`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** yes

State and local current income tax.

### `DeferredTaxExpense`

**Unit:** USD  ·  **Category:** tax  ·  **Flow:** yes

Deferred income tax provision from timing differences.

### `DepletionExpense`

**Unit:** USD  ·  **Category:** energy  ·  **Flow:** yes

Period write-down of natural-resource asset basis based on units
extracted. Energy/mining specific cousin of depreciation.

### `DepreciationAndAmortization`

**Unit:** USD  ·  **Category:** fixed_assets  ·  **Flow:** yes

IFRS D&A expense.

### `DiscontinuedOpsIncome`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

Net income from discontinued business segments.

### `DividendPerShare`

**Unit:** USD/share  ·  **Category:** per_share  ·  **Flow:** yes

IFRS dividends per ordinary share.

### `EffectiveTaxRate`

**Unit:** pct  ·  **Category:** tax  ·  **Flow:** yes

Effective income tax rate.

### `EPSBasic`

**Unit:** USD/share  ·  **Category:** per_share  ·  **Flow:** yes

Basic earnings per share (US-GAAP + IFRS).

### `EPSBasicAndDiluted`

**Unit:** USD/share  ·  **Category:** per_share  ·  **Flow:** yes

Combined basic and diluted EPS (equal when no dilutive securities).

### `EPSContinuingOpsBasic`

**Unit:** USD/share  ·  **Category:** per_share  ·  **Flow:** yes

Basic EPS from continuing operations.

### `EPSContinuingOpsDiluted`

**Unit:** USD/share  ·  **Category:** per_share  ·  **Flow:** yes

Diluted EPS from continuing operations.

### `EPSDiluted`

**Unit:** USD/share  ·  **Category:** per_share  ·  **Flow:** yes

Diluted earnings per share — most conservative, standard for valuation (US-GAAP + IFRS).

### `EPSDiscontinuedOps`

**Unit:** USD/share  ·  **Category:** per_share  ·  **Flow:** yes

EPS from discontinued operations.

### `EquityMethodIncome`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

Share of income from unconsolidated affiliates (20-50% ownership).

### `ExplorationCosts`

**Unit:** USD  ·  **Category:** energy  ·  **Flow:** yes

Cost of exploring for new oil/gas/mineral reserves. Often
written off in the period (successful efforts vs full cost
accounting choice matters here).

### `ExplorationExpense`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** yes

Exploration costs for extractive industries (oil/gas, mining).

### `FederalIncomeTax`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

US Federal income tax expense/benefit (current + deferred).

### `FeesAndCommissions`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** yes

Fee income from deposit accounts, cards, advisory, custody.

### `ForeignCurrencyGainLoss`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

FX translation and transaction gains/losses.

### `ForeignIncomeTax`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

Foreign income tax expense/benefit.

### `GainLossOnAssetSale`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

Gains/losses on asset dispositions and debt extinguishments.

### `GainLossOnInvestments`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

Realized and unrealized gains/losses on investment securities.

### `GeneralAndAdmin`

**Unit:** USD  ·  **Category:** income_other  ·  **Flow:** yes

G&A — corporate overhead, management, office costs.

### `GrossProfit`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

IFRS gross profit — revenue minus cost of sales.

### `ImpairmentCharges`

**Unit:** USD  ·  **Category:** non_operating  ·  **Flow:** yes

Asset write-downs to fair value (goodwill, intangibles, PP&E).

### `IncomeContinuingOps`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

Net income from continuing operations.

### `IncomeTaxExpense`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

IFRS income tax expense.

### `InProcessRD`

**Unit:** USD  ·  **Category:** pharma  ·  **Flow:** yes

In-process research & development acquired in M&A. Charged off
at acquisition under US GAAP if abandoned; otherwise capitalized.

### `InsuranceCommissions`

**Unit:** USD  ·  **Category:** insurance  ·  **Flow:** yes

Commission income for insurance agencies and brokerages.

### `InsurancePremiums`

**Unit:** USD  ·  **Category:** insurance  ·  **Flow:** yes

Premiums earned during the period. The core revenue line for any
insurance carrier; net of premiums ceded to reinsurers.

### `InterestExpense`

**Unit:** USD  ·  **Category:** non_operating  ·  **Flow:** yes

Cost of debt financing.  Bloomberg: IS_INT_EXPENSE.

### `InterestExpenseBank`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** yes

Interest paid on deposits, borrowings, FHLB advances. Bank-specific.

### `InterestExpenseNet`

**Unit:** USD  ·  **Category:** non_operating  ·  **Flow:** yes

Net interest expense (interest expense minus interest income).

### `InterestIncome`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

Interest and dividend income from investments.

### `InterestIncomeBank`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** yes

Interest earned on loans and investment securities. Bank-specific.

### `LaborExpense`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** yes

IFRS wages & salaries — maps to LaborExpense bucket.

### `MilestonePaymentsRevenue`

**Unit:** USD  ·  **Category:** pharma  ·  **Flow:** yes

Upfront / milestone / royalty payments under licensing or
collaboration agreements (often with big-pharma partners).

### `NetIncome`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

IFRS profit/loss for the period.  Strict prevents OCI contamination.

### `NetIncomeNCI`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

IFRS profit/loss attributable to non-controlling interests.

### `NetIncomeToCommon`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

IFRS profit/loss attributable to parent-company owners.

### `NetInterestIncome`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** yes

Total interest income on loans and investments minus interest
expense on deposits and borrowings. Bank equivalent of gross
profit — the core of bank profitability.

### `NetPeriodicBenefitCost`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** yes

Pension / OPEB net periodic benefit cost (per ASC 715).

### `NonInterestExpense`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** yes

Operating expenses unrelated to interest cost (compensation,
occupancy, technology, regulatory). Drives the bank efficiency
ratio (NonInterestExpense / (NetInterestIncome + NonInterestIncome)).

### `NonInterestIncome`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** yes

Fee income, trading revenue, advisory, brokerage commissions
— bank revenue that does not derive from net interest spread.

### `OperatingExpenses`

**Unit:** USD  ·  **Category:** operating  ·  **Flow:** yes

Total operating expenses (SGA + R&D + D&A + other operating).

### `OperatingIncome`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

IFRS operating profit.  Not mandated; not all IFRS filers report this.

### `OtherIncome`

**Unit:** USD  ·  **Category:** non_operating  ·  **Flow:** yes

Single ``Other Income'' line — issuer-disclosed bucket for
non-operating income items not otherwise classified.  Use
OtherNonOperating for the netted version.

### `OtherNonOperating`

**Unit:** USD  ·  **Category:** operating  ·  **Flow:** yes

Miscellaneous non-operating income/expense.

### `OtherOperatingExpense`

**Unit:** USD  ·  **Category:** operating  ·  **Flow:** yes

Miscellaneous operating expenses not classified elsewhere.

### `OtherRevenue`

**Unit:** USD  ·  **Category:** revenue  ·  **Flow:** yes

Revenue not classified in primary categories.

### `PolicyAcquisitionCosts`

**Unit:** USD  ·  **Category:** insurance  ·  **Flow:** yes

Cost of writing new policies (commissions, underwriting). May be
capitalized as Deferred Acquisition Costs and amortized.

### `PretaxIncome`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

Earnings before income taxes (EBT).  Bloomberg: IS_INC_BEF_TAX.

### `ProfessionalFees`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** yes

Legal, audit, consulting, and professional service costs.

### `ProvisionForLoanLosses`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** yes

Charge to income for expected loan losses (CECL under US GAAP /
ECL under IFRS 9). Negative impact on earnings; movement in
LoanLossAllowance.

### `RentAndOccupancy`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** yes

Lease, rent, and occupancy expense.

### `ResearchAndDevelopment`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** yes

R&D expense — forward-looking innovation investment indicator.

### `RestructuringCharges`

**Unit:** USD  ·  **Category:** non_operating  ·  **Flow:** yes

One-time reorganization, layoff, and facility closure costs.

### `SBCDilutiveAdjustment`

**Unit:** shares  ·  **Category:** per_share  ·  **Flow:** yes

Adjustment to weighted-average diluted shares for option / RSU /
warrant dilution.  Equals WeightedAvgSharesDiluted minus
WeightedAvgSharesBasic.

### `SellingAndMarketing`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** yes

Sales, marketing, and advertising costs.

### `SellingGeneralAdmin`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** yes

SG&A — combined selling, general and administrative overhead.

### `StateAndLocalIncomeTax`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

State and local income tax expense/benefit.

### `StatutoryTaxRate`

**Unit:** pct  ·  **Category:** tax  ·  **Flow:** no

Statutory federal income tax rate from the rate-reconciliation footnote (21% post-TCJA, 35% pre-2018). Distinct from the realized EffectiveTaxRate.

### `SubscriptionRevenue`

**Unit:** USD  ·  **Category:** tech_saas  ·  **Flow:** yes

Recurring revenue from SaaS subscriptions. Not a standardized
XBRL tag — companies disclose under various extensions; mostly
reachable through the cost-of-revenue product/service split.

### `TotalCostsAndExpenses`

**Unit:** USD  ·  **Category:** expenses  ·  **Flow:** yes

Total costs and expenses before non-operating items.

### `TotalRevenue`

**Unit:** USD  ·  **Category:** revenue  ·  **Flow:** yes

IFRS top-line revenue.  IFRS 15 / ASC 606 converged.

### `TradingRevenue`

**Unit:** USD  ·  **Category:** banking  ·  **Flow:** yes

Realized + unrealized gains/losses from trading book activity.

### `WeightedAvgSharesBasic`

**Unit:** shares  ·  **Category:** income_other  ·  **Flow:** yes

Weighted average basic shares outstanding.

### `WeightedAvgSharesDiluted`

**Unit:** shares  ·  **Category:** income_other  ·  **Flow:** yes

Weighted average diluted shares outstanding.

## comprehensive_income

### `ComprehensiveIncome`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

Net income + OCI.  Total change in equity from non-owner sources.

### `ComprehensiveIncomeNCI`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

Comprehensive income attributable to non-controlling interests.

### `OCICashFlowHedges`

**Unit:** USD  ·  **Category:** liquidity  ·  **Flow:** yes

OCI — effective portion of cash flow hedge gains/losses.

### `OCIForeignCurrency`

**Unit:** USD  ·  **Category:** non_operating  ·  **Flow:** yes

OCI — foreign currency translation adjustments.

### `OCIPensions`

**Unit:** USD  ·  **Category:** pension  ·  **Flow:** yes

OCI — pension and postretirement benefit plan adjustments.

### `OCISecurities`

**Unit:** USD  ·  **Category:** comprehensive_income  ·  **Flow:** yes

OCI — unrealized gains/losses on available-for-sale securities.

### `OtherComprehensiveIncome`

**Unit:** USD  ·  **Category:** profitability  ·  **Flow:** yes

Total OCI net of tax.

### `ReclassificationFromAOCI`

**Unit:** USD  ·  **Category:** comprehensive_income  ·  **Flow:** yes

Amounts reclassified out of AOCI into net income this period.

---

## Financial Ratios

The pipeline also derives **164 financial ratios** per company into the `ratio` table (exported as `ratio.parquet`), spanning profitability, per-share, liquidity, efficiency, leverage, forensic, growth/CAGR, and sector-percentile ranks.

### Annual (FY) vs Trailing-Twelve-Month (TTM)

The `ratio` table holds BOTH annual (`fiscal_period = 'FY'`, `is_ttm = false`) and trailing-twelve-month (`fiscal_period = 'TTM'`, `is_ttm = true`) rows per company. TTM is the sum/normalization of the latest four reported quarters, dated at the entity's most recent quarter close, so it is the most-current read; FY rows are dated at fiscal-year close. TTM rows exist ONLY for the profitability, per_share, liquidity, efficiency, and leverage categories — forensic, growth (CAGR), and sector-percentile ranks are annual-only. Always filter on a single period (e.g. `WHERE is_ttm = FALSE`, or `WHERE fiscal_period = 'FY'`); a raw `read_table('ratio')` query that does NOT filter `is_ttm` / `fiscal_period` returns FY + TTM rows for the same metric and DOUBLE-COUNTS companies in a screen. The SDK SQL templates already filter by a single fiscal_period, so they are safe — this warning is for raw DuckDB queries.

Each `ratio` row carries: `entity_id`, `ratio_name`, `category`, `value`, `unit`, `period_end`, `fiscal_year`, `fiscal_period` (`'FY'` | `'TTM'`), `is_ttm` (bool), `confidence_score`, `computed_at`. Of the 164 ratios, 77 are materialized for both FY and TTM; the remaining 87 are annual-only.

### Profitability

*32 ratios · TTM available*

| Ratio | Unit | TTM | Description |
|-------|------|-----|-------------|
| `gross_profit_margin` | ratio | yes | Gross profit divided by revenue. |
| `operating_margin` | ratio | yes | Operating income divided by revenue. |
| `net_margin` | ratio | yes | Net income divided by revenue. |
| `pretax_income_margin` | ratio | yes | Pre-tax income divided by revenue. |
| `cost_of_revenue_margin` | ratio | yes | Cost of revenue divided by revenue. |
| `opex_margin` | ratio | yes | Operating expenses divided by revenue. |
| `da_margin` | ratio | yes | Depreciation & amortization divided by revenue. |
| `interest_expense_margin` | ratio | yes | Interest expense divided by revenue. |
| `net_interest_margin` | ratio | yes | Net interest income divided by revenue (financials). |
| `sga_margin` | ratio | yes | Selling, general & administrative expense divided by revenue. |
| `total_expense_margin` | ratio | yes | Total expenses divided by revenue. |
| `rd_margin` | ratio | yes | Research & development expense divided by revenue. |
| `ocf_margin` | ratio | yes | Operating cash flow divided by revenue. |
| `fcf_margin` | ratio | yes | Free cash flow divided by revenue. |
| `roic` | ratio | yes | Return on invested capital — NOPAT divided by invested capital. |
| `invested_capital` | USD | yes | Total invested capital (debt + equity, net of cash). |
| `nopat` | USD | yes | Net operating profit after tax. |
| `return_on_assets` | ratio | yes | Net income divided by average total assets. |
| `return_on_equity` | ratio | yes | Net income divided by average shareholders' equity. |
| `ebitda` | USD | yes | Earnings before interest, taxes, depreciation & amortization. |
| `ebitda_margin` | ratio | yes | EBITDA divided by revenue. |
| `roce` | ratio | yes | Return on capital employed — EBIT divided by capital employed. |
| `roce_nopat` | ratio | yes | Return on capital employed computed on NOPAT instead of EBIT. |
| `return_on_tangible_equity` | ratio | yes | Net income divided by tangible shareholders' equity. |
| `effective_tax_rate` | ratio | yes | Income-tax expense divided by pre-tax income. |
| `tax_burden` | ratio | yes | DuPont tax burden — net income divided by pre-tax income. |
| `interest_burden` | ratio | yes | DuPont interest burden — pre-tax income divided by EBIT. |
| `fcf_conversion` | ratio | yes | Free cash flow divided by net income. |
| `fcf_to_ebitda` | ratio | yes | Free cash flow divided by EBITDA. |
| `payout_ratio` | ratio | yes | Dividends paid divided by net income. |
| `retention_ratio` | ratio | yes | One minus the payout ratio (earnings retained). |
| `sustainable_growth_rate` | ratio | yes | ROE multiplied by the retention ratio — internally fundable growth. |

### Per Share

*11 ratios · TTM available*

| Ratio | Unit | TTM | Description |
|-------|------|-----|-------------|
| `book_value_per_share` | USD/share | yes | Shareholders' equity divided by diluted shares. |
| `retained_earnings_per_share` | USD/share | yes | Retained earnings divided by diluted shares. |
| `owner_earnings_per_share` | USD/share | yes | Owner earnings (Buffett definition) divided by diluted shares. |
| `fcf_per_share` | USD/share | yes | Free cash flow divided by diluted shares. |
| `dividends_per_share` | USD/share | yes | Cash dividends declared divided by diluted shares. |
| `sales_per_share` | USD/share | yes | Revenue divided by diluted shares. |
| `cash_per_share` | USD/share | yes | Cash & equivalents divided by diluted shares. |
| `ebitda_per_share` | USD/share | yes | EBITDA divided by diluted shares. |
| `tangible_book_value_per_share` | USD/share | yes | Tangible shareholders' equity divided by diluted shares. |
| `eps_basic` | USD/share | yes | Basic earnings per share. |
| `eps_diluted` | USD/share | yes | Diluted earnings per share. |

### Liquidity

*5 ratios · TTM available*

| Ratio | Unit | TTM | Description |
|-------|------|-----|-------------|
| `current_ratio` | ratio | yes | Current assets divided by current liabilities. |
| `quick_ratio` | ratio | yes | Current assets excluding inventory divided by current liabilities. |
| `cash_ratio` | ratio | yes | Cash & equivalents divided by current liabilities. |
| `working_capital` | USD | yes | Current assets minus current liabilities. |
| `net_working_capital` | USD | yes | Operating working capital, net of cash and debt. |

### Efficiency

*15 ratios · TTM available*

| Ratio | Unit | TTM | Description |
|-------|------|-----|-------------|
| `days_sales_outstanding` | days | yes | Average collection period on receivables. |
| `days_inventory_outstanding` | days | yes | Average days inventory is held before sale. |
| `days_payable_outstanding` | days | yes | Average days taken to pay suppliers. |
| `cash_conversion_cycle` | days | yes | DSO + DIO − DPO — days to convert investments into cash. |
| `cash_to_earnings` | ratio | yes | Operating cash flow divided by net income. |
| `capex_to_depreciation` | ratio | yes | Capital expenditure divided by depreciation. |
| `capex_to_revenue` | ratio | yes | Capital expenditure divided by revenue. |
| `asset_turnover` | ratio | yes | Revenue divided by average total assets. |
| `equity_multiplier` | ratio | yes | DuPont leverage — average assets divided by average equity. |
| `defensive_interval_ratio` | days | yes | Days of operating expenses covered by liquid assets. |
| `fixed_asset_turnover` | ratio | yes | Revenue divided by average net fixed assets. |
| `inventory_turnover` | ratio | yes | Cost of revenue divided by average inventory. |
| `receivables_turnover` | ratio | yes | Revenue divided by average receivables. |
| `payables_turnover` | ratio | yes | Cost of revenue divided by average payables. |
| `working_capital_turnover` | ratio | yes | Revenue divided by average working capital. |

### Leverage

*14 ratios · TTM available*

| Ratio | Unit | TTM | Description |
|-------|------|-----|-------------|
| `gross_debt` | USD | yes | Total interest-bearing debt (short + long term). |
| `net_debt` | USD | yes | Gross debt minus cash & equivalents. |
| `net_debt_to_ebitda` | ratio | yes | Net debt divided by EBITDA. |
| `liabilities_to_assets` | ratio | yes | Total liabilities divided by total assets. |
| `debt_to_assets` | ratio | yes | Gross debt divided by total assets. |
| `debt_to_equity` | ratio | yes | Gross debt divided by shareholders' equity. |
| `liabilities_to_equity` | ratio | yes | Total liabilities divided by shareholders' equity. |
| `long_term_debt_to_equity` | ratio | yes | Long-term debt divided by shareholders' equity. |
| `interest_coverage` | ratio | yes | EBIT divided by interest expense. |
| `debt_to_capital` | ratio | yes | Gross debt divided by total capital (debt + equity). |
| `long_term_debt_to_capital` | ratio | yes | Long-term debt divided by total capital. |
| `ebitda_interest_coverage` | ratio | yes | EBITDA divided by interest expense. |
| `cash_flow_to_debt` | ratio | yes | Operating cash flow divided by gross debt. |
| `dividend_coverage` | ratio | yes | Net income divided by dividends paid. |

### Forensic

*5 ratios · annual-only (no TTM)*

| Ratio | Unit | TTM | Description |
|-------|------|-----|-------------|
| `piotroski_f_score` | score | no | Piotroski F-Score (0–9) — fundamental strength. |
| `altman_z_prime` | score | no | Altman Z'-Score for private/non-listed manufacturers. |
| `altman_z_double_prime` | score | no | Altman Z''-Score for non-manufacturers / emerging markets. |
| `beneish_m_score` | score | no | Beneish M-Score — earnings-manipulation probability. |
| `sloan_accruals` | ratio | no | Sloan accrual ratio — accrual vs cash earnings quality. |

### Growth / CAGR

*60 ratios · annual-only (no TTM)*

| Ratio | Unit | TTM | Description |
|-------|------|-----|-------------|
| `revenue_cagr_1y` | ratio | no | Year-over-year growth in revenue (the 1-year CAGR variant). |
| `revenue_cagr_3y` | ratio | no | 3-year compound annual growth rate of revenue. |
| `revenue_cagr_5y` | ratio | no | 5-year compound annual growth rate of revenue. |
| `revenue_cagr_7y` | ratio | no | 7-year compound annual growth rate of revenue. |
| `revenue_cagr_10y` | ratio | no | 10-year compound annual growth rate of revenue. |
| `net_income_cagr_1y` | ratio | no | Year-over-year growth in net income (the 1-year CAGR variant). |
| `net_income_cagr_3y` | ratio | no | 3-year compound annual growth rate of net income. |
| `net_income_cagr_5y` | ratio | no | 5-year compound annual growth rate of net income. |
| `net_income_cagr_7y` | ratio | no | 7-year compound annual growth rate of net income. |
| `net_income_cagr_10y` | ratio | no | 10-year compound annual growth rate of net income. |
| `gross_profit_cagr_1y` | ratio | no | Year-over-year growth in gross profit (the 1-year CAGR variant). |
| `gross_profit_cagr_3y` | ratio | no | 3-year compound annual growth rate of gross profit. |
| `gross_profit_cagr_5y` | ratio | no | 5-year compound annual growth rate of gross profit. |
| `gross_profit_cagr_7y` | ratio | no | 7-year compound annual growth rate of gross profit. |
| `gross_profit_cagr_10y` | ratio | no | 10-year compound annual growth rate of gross profit. |
| `operating_income_cagr_1y` | ratio | no | Year-over-year growth in operating income (the 1-year CAGR variant). |
| `operating_income_cagr_3y` | ratio | no | 3-year compound annual growth rate of operating income. |
| `operating_income_cagr_5y` | ratio | no | 5-year compound annual growth rate of operating income. |
| `operating_income_cagr_7y` | ratio | no | 7-year compound annual growth rate of operating income. |
| `operating_income_cagr_10y` | ratio | no | 10-year compound annual growth rate of operating income. |
| `ebitda_cagr_1y` | ratio | no | Year-over-year growth in EBITDA (the 1-year CAGR variant). |
| `ebitda_cagr_3y` | ratio | no | 3-year compound annual growth rate of EBITDA. |
| `ebitda_cagr_5y` | ratio | no | 5-year compound annual growth rate of EBITDA. |
| `ebitda_cagr_7y` | ratio | no | 7-year compound annual growth rate of EBITDA. |
| `ebitda_cagr_10y` | ratio | no | 10-year compound annual growth rate of EBITDA. |
| `eps_cagr_1y` | ratio | no | Year-over-year growth in diluted EPS (the 1-year CAGR variant). |
| `eps_cagr_3y` | ratio | no | 3-year compound annual growth rate of diluted EPS. |
| `eps_cagr_5y` | ratio | no | 5-year compound annual growth rate of diluted EPS. |
| `eps_cagr_7y` | ratio | no | 7-year compound annual growth rate of diluted EPS. |
| `eps_cagr_10y` | ratio | no | 10-year compound annual growth rate of diluted EPS. |
| `total_assets_cagr_1y` | ratio | no | Year-over-year growth in total assets (the 1-year CAGR variant). |
| `total_assets_cagr_3y` | ratio | no | 3-year compound annual growth rate of total assets. |
| `total_assets_cagr_5y` | ratio | no | 5-year compound annual growth rate of total assets. |
| `total_assets_cagr_7y` | ratio | no | 7-year compound annual growth rate of total assets. |
| `total_assets_cagr_10y` | ratio | no | 10-year compound annual growth rate of total assets. |
| `equity_cagr_1y` | ratio | no | Year-over-year growth in shareholders' equity (the 1-year CAGR variant). |
| `equity_cagr_3y` | ratio | no | 3-year compound annual growth rate of shareholders' equity. |
| `equity_cagr_5y` | ratio | no | 5-year compound annual growth rate of shareholders' equity. |
| `equity_cagr_7y` | ratio | no | 7-year compound annual growth rate of shareholders' equity. |
| `equity_cagr_10y` | ratio | no | 10-year compound annual growth rate of shareholders' equity. |
| `bvps_cagr_1y` | ratio | no | Year-over-year growth in book value per share (the 1-year CAGR variant). |
| `bvps_cagr_3y` | ratio | no | 3-year compound annual growth rate of book value per share. |
| `bvps_cagr_5y` | ratio | no | 5-year compound annual growth rate of book value per share. |
| `bvps_cagr_7y` | ratio | no | 7-year compound annual growth rate of book value per share. |
| `bvps_cagr_10y` | ratio | no | 10-year compound annual growth rate of book value per share. |
| `owner_earnings_cagr_1y` | ratio | no | Year-over-year growth in owner earnings (the 1-year CAGR variant). |
| `owner_earnings_cagr_3y` | ratio | no | 3-year compound annual growth rate of owner earnings. |
| `owner_earnings_cagr_5y` | ratio | no | 5-year compound annual growth rate of owner earnings. |
| `owner_earnings_cagr_7y` | ratio | no | 7-year compound annual growth rate of owner earnings. |
| `owner_earnings_cagr_10y` | ratio | no | 10-year compound annual growth rate of owner earnings. |
| `fcfps_cagr_1y` | ratio | no | Year-over-year growth in free cash flow per share (the 1-year CAGR variant). |
| `fcfps_cagr_3y` | ratio | no | 3-year compound annual growth rate of free cash flow per share. |
| `fcfps_cagr_5y` | ratio | no | 5-year compound annual growth rate of free cash flow per share. |
| `fcfps_cagr_7y` | ratio | no | 7-year compound annual growth rate of free cash flow per share. |
| `fcfps_cagr_10y` | ratio | no | 10-year compound annual growth rate of free cash flow per share. |
| `dividends_cagr_1y` | ratio | no | Year-over-year growth in dividends (the 1-year CAGR variant). |
| `dividends_cagr_3y` | ratio | no | 3-year compound annual growth rate of dividends. |
| `dividends_cagr_5y` | ratio | no | 5-year compound annual growth rate of dividends. |
| `dividends_cagr_7y` | ratio | no | 7-year compound annual growth rate of dividends. |
| `dividends_cagr_10y` | ratio | no | 10-year compound annual growth rate of dividends. |

### Sector Percentile Ranks

*22 ratios · annual-only (no TTM)*

| Ratio | Unit | TTM | Description |
|-------|------|-----|-------------|
| `roic_sector_pctile` | percentile | no | Percentile rank of `roic` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `return_on_equity_sector_pctile` | percentile | no | Percentile rank of `return_on_equity` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `return_on_assets_sector_pctile` | percentile | no | Percentile rank of `return_on_assets` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `roce_sector_pctile` | percentile | no | Percentile rank of `roce` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `net_margin_sector_pctile` | percentile | no | Percentile rank of `net_margin` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `operating_margin_sector_pctile` | percentile | no | Percentile rank of `operating_margin` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `gross_profit_margin_sector_pctile` | percentile | no | Percentile rank of `gross_profit_margin` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `ebitda_margin_sector_pctile` | percentile | no | Percentile rank of `ebitda_margin` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `fcf_margin_sector_pctile` | percentile | no | Percentile rank of `fcf_margin` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `ocf_margin_sector_pctile` | percentile | no | Percentile rank of `ocf_margin` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `fcf_conversion_sector_pctile` | percentile | no | Percentile rank of `fcf_conversion` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `debt_to_equity_sector_pctile` | percentile | no | Percentile rank of `debt_to_equity` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `net_debt_to_ebitda_sector_pctile` | percentile | no | Percentile rank of `net_debt_to_ebitda` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `current_ratio_sector_pctile` | percentile | no | Percentile rank of `current_ratio` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `interest_coverage_sector_pctile` | percentile | no | Percentile rank of `interest_coverage` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `asset_turnover_sector_pctile` | percentile | no | Percentile rank of `asset_turnover` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `inventory_turnover_sector_pctile` | percentile | no | Percentile rank of `inventory_turnover` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `revenue_cagr_5y_sector_pctile` | percentile | no | Percentile rank of `revenue_cagr_5y` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `net_income_cagr_5y_sector_pctile` | percentile | no | Percentile rank of `net_income_cagr_5y` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `eps_cagr_5y_sector_pctile` | percentile | no | Percentile rank of `eps_cagr_5y` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `piotroski_f_score_sector_pctile` | percentile | no | Percentile rank of `piotroski_f_score` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |
| `altman_z_double_prime_sector_pctile` | percentile | no | Percentile rank of `altman_z_double_prime` versus same-sector peers in the same fiscal year, in [0, 1] (1 = best in sector). |

---

*This catalog is generated from the live Valuein R2 manifest (`file:///tmp/valuein_manifest.json`). The underlying matching rules are proprietary — this document describes what each concept represents, not how it is detected.*
