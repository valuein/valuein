# Proof kit: check Valuein's claims on your own machine

Three scripts that let you verify, with no sales call, the two things that matter when a backtest
or an AI agent touches financial statements: did your data know things the market did not, and
can every number be traced to its SEC filing. Every figure carries a `fact_id` that resolves to
the filing it came from.

## 3-minute quickstart (no token, no card)

```bash
pip install "valuein-sdk>=1.1.0"
python examples/proof/look_ahead_audit.py --tickers MPWR,GE,AAPL,MSFT,INTC
python examples/proof/survivorship_check.py --start 2021-01-01 --end 2024-12-31
python examples/proof/verify_lineage.py --from-csv proof-output/look_ahead_audit.csv --limit 5
```

Each script prints a markdown report and writes `proof-output/*.csv` and `*.md`. The free sample
covers about five years of S&P 500 members, including companies that later left the index.

## What each script proves

| Script | Question it answers | How it answers |
|---|---|---|
| `look_ahead_audit.py` | How much of a backtest dataset would have been unknowable on the day? | For revenue, net income, total assets, operating cash flow and diluted EPS it orders every filed version of a number by SEC acceptance time, compares the first reported value with the latest one, and lists the ten biggest changes with both `fact_id`s and filings. `--as-of DATE` counts numbers visible on a past date that differ from today's. |
| `survivorship_check.py` | What does a universe built from today's listings leave out? | Lists companies that filed a 10-K or 10-Q in your range and are no longer listed, with the 8-K evidence (Item 1.03 bankruptcy, 2.01 completed acquisition, 3.01 delisting notice) and the share of the universe missing. `--index SP500` does the same for index members. |
| `verify_lineage.py` | Is this number really as reported? | Takes `fact_id`s (or an audit CSV) and prints the filing: form, filing date, acceptance time, accession, SEC folder URL, and every other filed version of the same number. `--check-sec` requests each URL once (set `SEC_USER_AGENT` to your contact). |

A changed number is not always a correction: spin-offs and discontinued operations recast prior
periods, and splits rescale per-share figures. The `fact_id`s let you open both filings and read
why. Valuein reports what each filing said; it does not score intent.

## Point it at your own universe

```bash
export VALUEIN_TOKEN=...          # your Stripe-issued token; the SDK uses it automatically
python examples/proof/look_ahead_audit.py --tickers AAPL,MSFT,0000320193 --periods annual
python examples/proof/survivorship_check.py --tickers AAPL,MSFT --start 2021-01-01
```

`--tickers` takes tickers or CIKs (comma-separated). A larger universe needs a token: the
no-token sample is limited to 60 requests a minute per IP. The plan sets how far back history
goes; compare plans at <https://valuein.biz/pricing>.

## Notes

- Point-in-time means filing acceptance time (`fact.accepted_at`), never period end.
- Valuein serves SEC filings data only. These scripts make no claim about stock prices.
- Licence: Valuein data is for inference and research. It must not be used to train,
  fine-tune or distil a model (Terms, section 15); the scripts only read and report.
- Index names are trademarks of their owners; Valuein is not affiliated with or endorsed by any index provider.
- Tests: `uv run --with 'pytest>=8,<10' --with pandas pytest tests/test_proof_kit.py`.
