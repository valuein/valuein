---
name: 🕵️ Data Quality Discrepancy
about: Report a specific value that differs from the SEC filing.
title: "[DQ]: <TICKER> - <METRIC> Discrepancy"
labels: ["high-priority", "data-quality"]
assignees: []
---

### 1. The Discrepancy
**Ticker:** [e.g. MSFT]
**Period:** [e.g. FY2023]
**Metric:** [e.g. Free Cash Flow]

- **Value in DB:** 14,500,000
- **Value in 10-K:** 14,850,000 (Link to filing page 45)

### 2. Impact Assessment
- [ ] Blocking a live trading model
- [ ] Affecting historical backtest
- [ ] Minor visual error

### 3. Expected Resolution
Please review the mapping logic for `Capital_Expenditures` vs `Purchase_of_Property`.
