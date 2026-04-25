# Support

The fastest way to get help depends on what you need. Pick the closest match below.

## I have a question about the data, the SDK, or the MCP server

Start with the docs — they cover the common cases:

- [`README.md`](README.md) — quickstart, channels, plans, recipes by role
- [`docs/QUERY_COOKBOOK.md`](docs/QUERY_COOKBOOK.md) — 20 DuckDB recipes with the right patterns
- [`docs/MCP_TOOLS.md`](docs/MCP_TOOLS.md) — every MCP tool, its parameters, and a worked example
- [`docs/data_catalog.md`](docs/data_catalog.md) — canonical `standard_concept` names
- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) — sourcing, PIT, restatements, valuation models
- [`docs/excel-guide.md`](docs/excel-guide.md) — full Power Query setup walkthrough
- [valuein.biz](https://valuein.biz) — pricing, dashboard, signup

If the answer isn't there, open a [Q&A issue](.github/ISSUE_TEMPLATE/04_general_question.yml). Q&A issues are public — that means everyone benefits from the answer.

## I think I found a data error

Open a [Data Quality Report](.github/ISSUE_TEMPLATE/01_data_quality_report.yml). Please include the ticker, fiscal period, the standardized concept, the value we report, the value in the SEC filing, and a link to the filing page. We treat these as high-priority and respond within one business day.

## I want a new metric, concept, or dataset

Open a [Feature Request](.github/ISSUE_TEMPLATE/02_feature_request.yml). The faster path to a yes is a clean GAAP definition (or formula) and a concrete use case.

## Something is broken — I can't connect, queries fail, or the API is down

Open a [Service Outage](.github/ISSUE_TEMPLATE/03_service_outage.yml). Include the timestamp, the channel (SDK / MCP / API / Excel), the exact error, and your tier. For confirmed outages we acknowledge within 2 hours, 24/7.

## I need a private channel for billing, contracts, or compliance

Email the right inbox — public issues are not appropriate for these:

| Topic | Email |
|---|---|
| Billing, refunds, invoicing | billing@valuein.biz |
| DPAs, security questionnaires, vendor due diligence | compliance@valuein.biz |
| Enterprise contracts, custom plans, redistribution licensing | sales@valuein.biz |
| Security vulnerabilities (see [`SECURITY.md`](SECURITY.md)) | security@valuein.biz |
| Code-of-conduct concerns (see [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)) | conduct@valuein.biz |
| Anything else | support@valuein.biz |

## I want to contribute

See [`CONTRIBUTING.md`](CONTRIBUTING.md). We welcome examples, notebooks, query recipes, and doc fixes.

## I want to follow along

- ⭐ Star this repo to get notified of new examples and docs
- Watch the repo for releases (Watch → Custom → Releases)
- Follow [@valuein](https://valuein.biz) on the channels linked from the website

## Service-level agreements

[`docs/SLA.md`](docs/SLA.md) covers uptime, data freshness, support response times by severity, and SLA credits for paid tiers.
