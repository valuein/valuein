# Security policy

## Reporting a vulnerability

If you believe you have found a security vulnerability in any part of the Valuein platform — the SDK, the MCP server at `mcp.valuein.biz`, the bulk-data API at `data.valuein.biz`, the website at `valuein.biz`, or anything in this repository — please report it privately. **Do not open a public GitHub issue.**

Email **security@valuein.biz** with:

- A clear description of the issue and its potential impact
- Steps to reproduce or a minimal proof-of-concept
- The affected component (e.g. SDK version, MCP tool name, API endpoint)
- Your name or handle so we can credit you (optional)

We will acknowledge receipt within **24 hours** and aim to provide an initial assessment within **3 business days**. For confirmed high-severity issues we target a fix and disclosure timeline of **30 days** or less.

GitHub's [private vulnerability reporting](https://github.com/valuein/valuein/security/advisories/new) is also enabled — use it if you prefer.

## What's in scope

- The Python SDK (`valuein-sdk` on PyPI) and any of its public methods or templates
- The MCP server endpoints (`mcp.valuein.biz/mcp` and discovery routes)
- The bulk-data API (`data.valuein.biz/v1/*`)
- Token / auth flows that could let one customer access another's data or higher-tier data without paying
- Any integrity issue affecting the published Parquet snapshots (data corruption, restatement integrity, PIT violations)
- The MCP registry manifest in [`server.json`](server.json) and the publish workflow in [`.github/workflows/publish-mcp.yml`](.github/workflows/publish-mcp.yml)
- The example scripts and notebooks if they could leak credentials or execute attacker-controlled code

## What's out of scope

- Anything in third-party services we depend on (Cloudflare, Stripe, GitHub, PyPI) — report directly to them
- Vulnerabilities in unpublished sample data or the Sample tier rate limits
- Issues that require physical access to a user's machine
- Best-practice recommendations without a demonstrable security impact

## Disclosure

We follow coordinated disclosure. We will:

- Confirm the issue privately and keep you updated on progress
- Credit you in the release notes and the published advisory unless you prefer to remain anonymous
- Publish a CVE / GitHub Security Advisory once a fix is available
- Avoid public discussion of unfixed issues — please give us a reasonable window before disclosing externally

Thank you for helping keep Valuein and its users safe.
