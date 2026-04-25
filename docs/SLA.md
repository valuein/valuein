# Service Level Agreement

**Effective date:** February 1, 2026

This Service Level Agreement ("SLA") covers the production performance commitments for Valuein's distribution channels — the Python SDK, the MCP server (`mcp.valuein.biz`), the bulk-data API (`data.valuein.biz`), and the Excel template — for paid plans (Pro, Enterprise, Custom). The Sample and Free tiers are best-effort and not covered.

The pricing and tier scope referenced below mirrors [valuein.biz/pricing](https://valuein.biz/pricing). When the website and this document disagree, the website is the source of truth.

---

## 1. System availability

Valuein guarantees **99.9% monthly uptime** for the SDK gateway, the MCP endpoint, and the bulk-data API on paid tiers.

| Status | Definition |
|---|---|
| **Operational** | Gateway / MCP endpoint responds with HTTP 200; R2 streams complete |
| **Degraded** | p95 latency > 2s, or connection-pool utilization > 90% |
| **Outage** | Total inability to authenticate or stream data for ≥ 5 minutes |

Downtime is measured from the time a verified incident is opened to the time service is fully restored. Maintenance windows announced ≥ 24 hours in advance do not count toward downtime.

---

## 2. Data freshness

The "time-to-database" commitment runs from SEC EDGAR acceptance to the data being queryable through any Valuein channel.

| Filing type | Free / Pro target | Enterprise target | SLA guarantee |
|---|---|---|---|
| 8-K (current events) | < 5 minutes | < 5 minutes | < 24h (Pro) · < 4h (Enterprise) |
| 10-Q (quarterly) | < 5 minutes | < 5 minutes | < 24h (Pro) · < 4h (Enterprise) |
| 10-K (annual) | < 5 minutes | < 5 minutes | < 24h (Pro) · < 4h (Enterprise) |
| 10-K/A, 10-Q/A (amendments) | < 5 minutes | < 5 minutes | < 24h (Pro) · < 4h (Enterprise) |
| 20-F (foreign private issuers) | < 5 minutes | < 5 minutes | < 24h (Pro) · < 4h (Enterprise) |

The Free and Sample tiers receive a daily snapshot. The Custom tier supports real-time 8-K push delivery via webhook.

A new authoritative snapshot is published daily by **06:00 UTC**. Snapshot ID and `last_updated` timestamp are accessible via `client.manifest()` (SDK) or the `manifest` resource (MCP).

---

## 3. Support response times

GitHub Issues is the public support channel. Email is reserved for private matters (billing, contracts, security). Triage SLAs are tier-aware.

| Severity | Definition | Free | Pro | Enterprise / Custom |
|---|---|---|---|---|
| **Critical** | Total outage; production blocker | Best-effort | < 4h, business hours | < 2h, 24/7 |
| **High** | Significant data error (incorrect value, missing filing) | Best-effort | < 1 business day | < 4 business hours |
| **Normal** | Methodology question; feature request; integration help | < 5 business days | < 3 business days | < 1 business day |

Open tickets at [github.com/valuein/valuein/issues](https://github.com/valuein/valuein/issues) using the right template. For private channels see [`SUPPORT.md`](../SUPPORT.md#i-need-a-private-channel-for-billing-contracts-or-compliance).

---

## 4. Maintenance windows

- **Scheduled maintenance:** Sundays 04:00 – 06:00 UTC. Notice given ≥ 24 hours in advance via the [release notes](https://github.com/valuein/valuein/releases) and the website status page.
- **Emergency maintenance:** Critical security patches may be applied immediately. Email notice to active customers within 30 minutes of any unscheduled maintenance window.

---

## 5. Rate limits

Per-tier rate limits are canonical at [`https://data.valuein.biz/v1/plans`](https://data.valuein.biz/v1/plans). Current values:

| Plan | Per minute | Per hour |
|---|---:|---:|
| Sample (anonymous) | 15 | 150 |
| Free | 60 | 1,000 |
| Pro | 100 | 3,000 |
| Enterprise | 300 | 10,000 |

Rate-limit responses include a `Retry-After` header and a typed `ValueinRateLimitError.retry_after` in the SDK. Bursting above the per-minute limit briefly is allowed up to a 2× factor; sustained bursts trigger a backoff window.

---

## 6. SLA credits

If monthly uptime falls below the 99.9% commitment for paid tiers, affected accounts are eligible for service credits:

| Monthly uptime | Credit |
|---|---|
| 99.0% – 99.9% | 10% of monthly fee |
| 95.0% – 99.0% | 25% of monthly fee |
| < 95.0% | 50% of monthly fee |

To claim, email **billing@valuein.biz** with your incident ticket number(s) within 30 days of the affected billing period.

---

## 7. What is not covered

- The Sample tier (anonymous) and the Free tier — both are best-effort and have no uptime, freshness, or response-time commitments.
- Outages caused by force majeure, customer-side network issues, or third-party services we depend on (Cloudflare, Stripe, GitHub, PyPI).
- Beta or experimental features explicitly labelled as such (currently `search_filing_text` on MCP — Vectorize backfill in progress).
- Use beyond the documented rate limits.

---

## 8. Status

Live status, snapshot freshness, and incident history are published on the website's status page (linked from [valuein.biz](https://valuein.biz)) and in the GitHub release feed. Subscribers to the customer mailing list receive incident notifications by email.
