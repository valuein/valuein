# Playbooks

Six job-shaped notebooks. Each one is a short path to an outcome, written as numbered steps
("Step n · title"), each step with runnable code and a "Check it worked" line. Open any in Colab
with the badge at its top. Every notebook is committed **with its output**, executed on the free
sample tier with no API key.

| Playbook | For | You get | Plan |
|---|---|---|---|
| [Backtest without bias](backtest-without-bias.ipynb) | quants | members as of each rebalance date, ratios as known that day, your own prices joined on CIK, a receipt per number | none (one 2008 cell wants a free Benchmark key and prints a skip without it) |
| [Smart money, point in time](smart-money-point-in-time.ipynb) | PMs, analysts | insider trades, 13F holders, a manager's portfolio, gated on `accepted_at` | Institutional (every data cell prints a skip on other plans) |
| [Connect your AI agent](connect-your-agent.ipynb) | AI builders | MCP setup for Claude, ChatGPT and Cursor, a first call from Python, a figure traced to its filing | none |
| [Cover a company](cover-a-company.ipynb) | analysts, investors | three statements, receipts, restatement check, a sourced CSV, then the Workspace clicks | none |
| [Answer the AI question in a DDQ](ddq-ai-question.ipynb) | compliance, operations | an evidence pack: figure, fact_id, independent check, filing link | none |
| [Free S&P 500 statements](free-sp500-statements.ipynb) | students, builders | income, balance and cash flow for an S&P 500 company, a chart, a sourced CSV | none, no key |

Conventions: Valuein serves SEC filings, not market prices, so backtests bring their own prices
joined on CIK. Restatement classes are `non_reliance`, `amended` and `undisclosed`. Nothing here
is investment advice. Steps that need a key never print it, and a missing key or plan prints a one-line
`Skipped:` message while the notebook still runs to the end.

_Index names are trademarks of their owners; Valuein is not affiliated with or endorsed by any index provider._
