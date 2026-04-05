# Service Level Agreement (SLA)

**Effective Date:** February 1, 2026

This Service Level Agreement ("SLA") outlines the performance commitments for the Valuein Financial Data Essentials (FDE) feed.

---

## 1. System Availability

Valuein guarantees that the Data API and database access will be available **99.9%** of the time during any monthly billing cycle.

| Status | Definition |
|---|---|
| **Operational** | API responds with 200 OK; database accepts connections |
| **Degraded** | API latency > 2 seconds; connection pool utilization > 90% |
| **Outage** | Total inability to access data endpoints |

Downtime is measured from the time a verified incident is opened to the time service is fully restored.

---

## 2. Data Freshness & Latency

The following "time-to-database" commitments apply from the moment a filing is accepted by the SEC EDGAR system:

| Filing Type | Processing Target | SLA Guarantee |
|---|---|---|
| **8-K (Current Events)** | < 5 minutes | < 24 hours |
| **10-Q (Quarterly Report)** | < 5 minutes | < 24 hours |
| **10-K (Annual Report)** | < 5 minutes | < 24 hours |
| **10-K/A, 10-Q/A (Amendments)** | < 5 minutes | < 24 hours |

A new snapshot is published daily by **06:00 UTC**. The snapshot ID and `last_updated` timestamp are accessible via `client.manifest()`.

---

## 3. Support Response Times

Tickets submitted via the [Support Portal](../.github/ISSUE_TEMPLATE) are prioritized as follows:

| Severity | Definition | Response Time |
|---|---|---|
| **Critical** | Complete service outage; production blocker | < 2 hours (24/7) |
| **High** | Significant data error (e.g., incorrect ticker mapping, missing filing) | < 1 business day |
| **Normal** | Methodology question; feature request; integration help | < 3 business days |

---

## 4. Maintenance Windows

- **Scheduled maintenance:** Sundays between 04:00 UTC and 06:00 UTC.
- **Emergency maintenance:** Critical security patches may be applied immediately. Email notification is sent within 30 minutes of any unscheduled maintenance window.

---

## 5. SLA Credits

If monthly uptime falls below the 99.9% commitment, affected clients are eligible for service credits:

| Monthly Uptime | Credit |
|---|---|
| 99.0% – 99.9% | 10% of monthly fee |
| 95.0% – 99.0% | 25% of monthly fee |
| < 95.0% | 50% of monthly fee |

To request a credit, contact **billing@valuein.biz** with your incident ticket number within 30 days of the affected billing period.
