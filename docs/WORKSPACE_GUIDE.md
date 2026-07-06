<div align="center">

<a href="https://valuein.biz">
  <img src="https://valuein.biz/valuein/colored_full_logo.png" alt="Valuein" width="140" />
</a>

# Workspace Welcome Guide

**Your SEC research desk, run by an AI analyst.**

111M+ point-in-time financial facts · 19,000+ US companies · 1993→present · zero survivorship bias

[![Open the Workspace](https://img.shields.io/badge/Open-valuein.biz%2Fworkspace-2563EB?style=flat)](https://valuein.biz/workspace)
[![Read online](https://img.shields.io/badge/Read_online-valuein.biz%2Fworkspace--guide-7C3AED?style=flat)](https://valuein.biz/workspace-guide)
[![MCP](https://img.shields.io/badge/MCP-mcp.valuein.biz-1E293B?style=flat)](https://mcp.valuein.biz/mcp)
[![Pricing](https://img.shields.io/badge/Pricing-Free_%E2%86%92_%2449_%E2%86%92_%24499-16A34A?style=flat)](https://valuein.biz/pricing)

<br/>

<img src="https://valuein.biz/valuein/LinkedIn_Cover.png" alt="Valuein — SEC EDGAR fundamentals for analysts, quants, and AI agents" width="820" />

</div>

---

> **111M+ point-in-time financial facts across 19,000+ US companies (1993→present, zero survivorship bias) — wired into a chat-first workspace with 95 data tools and 28 ready-to-run analyst playbooks.**

This is a simple, cadence-based setup so the Workspace earns its keep in your *daily, weekly, and monthly* routine within the first week.

Read the **15-minute setup** first. Then jump to the **one persona that matches you** (Analyst, PM, Quant, or Creator). Everything else is reference.

> 📖 **Prefer it interactive?** This guide is live at **[valuein.biz/workspace-guide](https://valuein.biz/workspace-guide)** with a role selector.

---

## 1. What the Workspace actually is

The Workspace is the authenticated product at **[valuein.biz/workspace](https://valuein.biz/workspace)**. It is *chat-first* — you talk to your own LLM (Claude or GPT, your key, zero retention) and it has Valuein's entire data layer wired in behind it.

Five things live here, and they reinforce each other:

| Building block | What it is | The job it does for you |
|---|---|---|
| **Chat** | BYO-LLM assistant with 95 SEC data tools + 28 SOPs | Ask anything about any US public company; get cited, point-in-time answers |
| **Watchlists** | Named ticker lists (≤500 tickers + a criteria note) | The universe everything else points at — coverage, portfolio, pipeline |
| **Theses** | Time-stamped bull/bear/neutral calls (conviction 1–5, horizon) | Record what you thought *and when*; auto-graded against fundamentals |
| **Alerts → Inbox** | Rules on filings, ratios, or watchlist changes | Passive monitoring so you never miss an 8-K or a covenant trip |
| **Reports** | Editable research artifacts → shareable at `/r/[slug]` | Your deliverable + your public, SEO-indexed credibility |

Plus four data channels behind **one Bearer token**: the in-app chat, the **MCP server** (Claude Desktop / Cursor / Codex), the **Python SDK**, and the **Bulk Data API**. Connect once, use everywhere.

> **Mental model:** Watchlists define *what* you watch. Theses record *what you believe*. Alerts tell you *when something changed*. Chat + SOPs do *the analysis*. Reports are *what you ship*. Publishing reports builds *reputation*.

---

## 2. The 15-minute setup (do this first)

A checklist that takes you from zero to first real value. Tick these in order.

- [ ] **1. Sign in & pick a handle** (`/onboarding`). This is your public identity (`valuein.biz/@yourhandle`). One-time, required before you can publish.
- [ ] **2. Paste your LLM key into chat** (`/workspace`). Claude (`sk-ant-…`), OpenAI (`sk-…`), or OpenRouter (`sk-or-…`). It's sealed in an encrypted, httpOnly cookie — **never stored on our servers**, never sent to anyone but your provider. Disconnect wipes it.
- [ ] **3. Run your first query.** Paste this into chat:
  > *"Give me a quick equity research brief on NVDA — fundamentals, valuation, and the one thing a skeptic would flag."*
  This invokes the `equity_research_brief` SOP at `quick` depth. You'll see cited, point-in-time data come back in ~30s.
- [ ] **4. Create your first watchlist** (`/workspace/watchlists/new`). Paste 5–20 tickers you actually care about. Add a one-line criteria note (e.g. *"core coverage — quality compounders"*). This becomes the spine of your daily routine.
- [ ] **5. Set one alert** (`/workspace/alerts/new`). Pick **Watchlist change** → your new watchlist → **Dashboard** channel. Now any 8-K/10-Q/10-K from those names lands in your Inbox. Hit **Test alert** to confirm it fires.
- [ ] **6. Record one thesis** (`/workspace/theses/new`). Take your highest-conviction name, set bull/bear/neutral, conviction, and horizon. This is the seed of your track record.
- [ ] **7. Connect your desktop AI** (`/workspace/connect`). Copy the Claude Desktop / Cursor / Codex config (your token is pre-filled), paste it, restart the app, hit **Test connection**. Now Valuein is in the tool you already use all day.

**You're live.** Steps 1–3 are the "aha" (cited data in your chat). Steps 4–6 turn it into a *system* that works while you sleep. Step 7 meets you where you already work.

---

## 3. Pick your playbook

Find the persona closest to you and follow its **Setup → Daily → Weekly → Monthly**. Each routine names the exact SOP or tool to use and gives a copy-paste prompt. Run SOPs either in the in-app chat ("run the X SOP on TICKER") or from Claude Desktop/Cursor once connected.

---

### 3A. Equity Analyst

*(sell-side/buy-side analyst, RIA, research-led investor — your job is coverage, earnings, and memos.)*

**One-time setup**
- Watchlist **"Coverage"** — every name you cover (criteria: *"active coverage list"*).
- Watchlist **"Earnings — this quarter"** — names reporting in the next ~6 weeks.
- Alert: **Filing event** on Coverage tickers, form types `8-K, 10-Q, 10-K` → **Dashboard** (and **Email** for your top 5 names).
- A **thesis** for each covered name so your view is on record and self-grades.

**Daily (5–10 min)**
- Check the **Inbox** — new filings on your coverage.
- For anything that moved: *"Summarize the 8-K [TICKER] just filed and tell me if it changes the thesis."*
- Quick fundamental pulls in chat as questions come up — every answer is cited to the filing.

**Weekly (30–60 min)**
- Run **`equity_research_brief`** (`full` depth) on the 1–2 names most in focus → save as a Report.
- Before any earnings: **`earnings_pulse`** → *"Run earnings_pulse on [TICKER] — last 8 quarters, trend, and management credibility."*
- **`peer_benchmarking_memo`** on a contested name to pressure-test relative value.
- **Publish one report** publicly (see §4) — your weekly credibility deposit.

**Monthly (deep work)**
- **`margin_and_moat_teardown`** — 5-year operating-efficiency + moat read on a core holding.
- **`capital_allocation_review`** — is management actually creating value with retained earnings?
- **`restatement_radar`** across Coverage (`since` = last month) — catch quiet 10-K/A and 10-Q/A amendments.
- Re-score theses: *"Score all my theses past their horizon and tell me which broke."* (`score_due_theses`).

**Upgrade path:** **Pro** unlocks the full 19,000+ universe (cover anything, not just S&P 500) and your public analyst profile + reputation. **Institutional** adds DCF, forensic audit, and one-click **DOCX/XLSX export** of briefs and models for client/IC deliverables.

---

### 3B. Portfolio Manager

*(your job is idea generation, position monitoring, and risk-sized conviction.)*

**One-time setup**
- Watchlist **"Portfolio"** — current positions (criteria: *"live book"*).
- Watchlist **"Pipeline"** — researched candidates not yet sized.
- Alerts: **Watchlist change** on Portfolio → Dashboard; plus **Ratio threshold** alerts on your levered names (e.g. `net_debt_to_ebitda > 4`, `interest_coverage < 2`) → Email.
- A **thesis per position** with conviction + horizon — this *is* your book's memory.

**Daily (5 min)**
- **`morning_briefing`** → *"Run morning_briefing on my Portfolio watchlist since yesterday — rank by likely impact."* Material filings, ranked, before the open.
- Clear the **Inbox**.

**Weekly (45 min)**
- **`screen_and_shortlist`** for fresh ideas → *"Screen the S&P 500 industrials for quality, give me a top-10 shortlist, QC the top 3."* Best candidates flow straight into a research brief.
- **`quality_and_risk_audit`** on any new position before sizing — capital-structure safety + dividend sustainability scorecard.
- *(Institutional)* **`smart_money_pulse`** on Portfolio → who's accumulating, insider clusters, activist filings.

**Monthly**
- **`portfolio_health_check`** → which theses are on track vs broken, top-3 issues.
- **`capital_allocation_review`** on the names you're adding to.
- Trim/rotate the **Pipeline** watchlist and refresh convictions.

**Upgrade path:** **Institutional** unlocks the full **smart-money layer** — insider transactions (Forms 3/4/5/144), 13F manager portfolios + QoQ deltas, 13D/13G blockholders with going-active flags, and a composite smart-money flow score. Plus filing-event **webhooks** and priority data freshness.

---

### 3C. Quant Researcher

*(your job is factors, backtests, and signals — and you want bulk data, not a UI.)*

**One-time setup**
- Connect the **MCP** (`/workspace/connect`) and grab your Bearer token from `/account/settings/api` for the **Python SDK** (`pip install valuein-sdk`).
- One watchlist per factor sleeve if you want to monitor live screens.

**Working loop (continuous)**
- **`survivorship_free_backtest`** → *"Set up a survivorship-free backtest from 2010-01-01 to 2024-12-31."* Returns the historical universe definition + Parquet URLs, ready for DuckDB.
- **`pit_factor_constructor`** → build Quality / Value / Momentum factor scores cross-sectionally, point-in-time correct.
- **`get_pit_universe`** → exact index/sector membership on any historical date (no lookahead).
- **`get_compute_ready_stream`** → presigned Parquet URLs for `fact`, `ratio`, `valuation`, `index_membership`, etc. → stream into the SDK's out-of-core DuckDB.
- **`screen_to_thesis`** → screen → forensic audit → auto-save theses on the top names (closes the loop from signal to tracked call).

**Why it matters here:** every PIT-tabled value is filtered at `as_of` — no survivorship bias, no restatement leakage. That's the difference between a backtest you can trust and one you can't.

**Upgrade path:** **Pro** unlocks the full universe; **Institutional** adds the smart-money tables for ownership-based factors.

---

### 3D. Creator / Financial Influencer

*(your job is to publish credible research, grow an audience, and build a reputation that compounds.)*

This is the highest-leverage path — your published work becomes an SEO/AEO-indexed landing page that funnels *your* audience back to your profile.

**One-time setup**
- Complete your **public profile** (`/account/settings/profile`): display name, bio, avatar, cover image, and flip **Make profile public** ON. Your page is `valuein.biz/@yourhandle`.
- Decide your beat (a sector, a style, a theme) and build a watchlist for it.

**The publishing flywheel (weekly rhythm)**
1. **Form a view** → record a **public thesis** (bull/bear/neutral + conviction + horizon). Set visibility = **Public** so it counts toward your reputation.
2. **Build the case** → run `equity_research_brief` in chat → save as a **Report**.
3. **Polish** → edit in the report editor (`/workspace/reports/[id]`), autosave on.
4. **Publish** → **Share** → visibility **Public** → set your byline display name → you get `valuein.biz/r/[slug]` with Article JSON-LD + clickable SEC EDGAR citations baked in.
5. **Distribute** → drop the link on LinkedIn/X/Substack. Every citation is verifiable, which is the whole pitch.
6. **Compound** → as your public theses get auto-graded, your **reputation score** (`correct / (correct+wrong)`, shown once you have ≥5 graded) becomes your credibility moat.

**Why creators win here:** the reputation is *earned and provable* (graded against real fundamentals, not vibes), and every report is a citation-rich page that AI search engines (Perplexity, SearchGPT, Claude) can cite. Your distribution becomes your top-of-funnel, and Valuein's data becomes your credibility.

**Upgrade path:** **Pro** unlocks the public profile + reputation scoring and the full universe to cover anything your audience asks about.

---

## 4. The publishing flywheel in detail (everyone should do this)

Publishing isn't just for creators — it's how *any* user turns work into reputation, and it's the engine of the whole platform. The flow:

```
Form a view → save thesis (public) → research it (SOP → Report)
   → edit → Share (public) → valuein.biz/r/[slug]  ──┐
                                                       │ SEO / AEO indexed
   reputation builds as theses auto-grade  ◄───────────┘ citation-rich article
                                                       │
   readers discover it via /research + your profile ◄──┘
```

**Share visibility — pick deliberately:**

| Visibility | Who can see it | Indexed by search/AI? | Use it for |
|---|---|---|---|
| **Private** | Only you | No | Drafts, internal work |
| **Unlisted** | Anyone with the link | No (noindex) | Sharing with a client/colleague |
| **Public** | Everyone, on your profile + the public research catalog | **Yes** | Building audience + reputation |

Slugs are stable; if you rotate one, the old link 410s gracefully for 30 days. View counts and a per-view audit log are tracked. Owners can purge the edge cache on demand.

---

## 5. Tier guide — what each tier *removes* (not "more data")

Each tier is designed to remove a *different* buyer objection, not slide a "more data" lever.

| | **Sample** | **S&P 500** (free) | **Pro** | **Institutional** | **Enterprise** |
|---|---|---|---|---|---|
| **Price** | $0, no signup | $0, register | **$49/mo · $490/yr** | **$499/mo · $4,790/yr** | Custom |
| **Universe** | S&P 500 | S&P 500 | **19,000+** | 19,000+ + foreign | Contract |
| **History** | 5 yr | 1993→ | 15-yr rolling (2011→) | 1993→ | Contract |
| **Workspace + 28 SOPs** | — | ✓ | ✓ | ✓ | ✓ |
| **BYO-LLM chat** | — | ✓ | ✓ | ✓ | ✓ |
| **Theses / Watchlists / Alerts / Reports** | — | ✓ | ✓ | ✓ | ✓ |
| **Public profile + reputation** | — | — | ✓ | ✓ | ✓ |
| **DCF + forensic + DOCX/XLSX export** | — | — | — | ✓ | ✓ |
| **Smart-money (insider + 13F + 13D/G)** | — | — | — | ✓ | ✓ |
| **Webhooks · priority freshness · redistribution · SLA** | — | — | — | ✓ | ✓ |
| **Dedicated infra · zero-retention** | — | — | — | — | ✓ |

See **[full pricing](https://valuein.biz/pricing)** for the complete breakdown.

---

## 6. Reference — the full toolkit

### 28 SOPs (your ready-made playbooks)

**Flagships**
- **`equity_research_brief`** — single-ticker institutional brief. Depth: `quick` / `full` / `forensic`.
- **`screen_and_shortlist`** — PM idea generation: screen a universe by objective → QC top 3 → hand off to the brief.

**Analyst** — `margin_and_moat_teardown` · `earnings_pulse` · `forensic_earnings_brief` · `sector_overview_flow` · `dcf_build_flow` · `restatement_radar`
**Portfolio Manager** — `quality_and_risk_audit` · `capital_allocation_review` · `smart_money_pulse`* · `morning_briefing` · `portfolio_health_check`
**Quant** — `survivorship_free_backtest` · `pit_factor_constructor` · `screen_to_thesis`
**Ratio specialist** — `ratio_deep_dive` · `sector_ratio_screen`
**Smart money*** — `smart_money_brief` · `activist_surveillance` · `activist_radar` · `peer_benchmarking_memo`

*\* Smart-money SOPs require the Institutional tier.*

### Key tools (57 total, behind chat + MCP)

- **Data:** `get_company_fundamentals`, `get_financial_ratios`, `get_valuation_metrics`, `get_capital_allocation_profile`, `compare_periods`, `get_earnings_signals`, `get_sec_filing_links`
- **Discovery / trust:** `search_companies`, `describe_schema`, `verify_fact_lineage`, citation overrides
- **Screening:** `screen_universe`, `get_peer_comparables`, `get_pit_universe`, `get_compute_ready_stream`
- **Valuation (Institutional):** `compute_dcf`, `forensic_audit`
- **Smart money (Institutional):** `get_insider_transactions`, `get_insider_sentiment`, `get_institutional_holdings`, `get_manager_portfolio`, `get_blockholders`, `get_top_holders`, `get_smart_money_flow`
- **State (CRUD):** theses, watchlists, alerts, reports, inbox
- **Document generation (Institutional):** `generate_dcf_xlsx` (Excel model + 5×5 sensitivity), `generate_research_brief_docx` (branded Word memo with citations), `generate_comps_xlsx` (peer comps table), `render_report` (Markdown/DOCX download)

### Connect once, use everywhere (`/workspace/connect`)

| Client | Config file |
|---|---|
| **Claude Desktop** *(recommended)* | `claude_desktop_config.json` |
| **Cursor** | `.cursor/mcp.json` |
| **Codex CLI** | `~/.codex/config.toml` |
| **Any HTTP client / Python SDK** | `https://mcp.valuein.biz/mcp` + `Authorization: Bearer <token>` |

Your token is at `/account/settings/api` (regenerate any time). One token unlocks chat, MCP, the Python SDK, and the Bulk Data API at your tier.

---

## 7. First-week scorecard

You'll know the Workspace is delivering when, by end of week one, you have:

- [ ] A connected LLM key and your desktop AI wired to the MCP
- [ ] At least one **watchlist** that mirrors your real attention
- [ ] At least one **alert** firing into your Inbox
- [ ] At least one **thesis** on record (so your track record has started)
- [ ] One **research brief** run end-to-end and saved as a Report
- [ ] One report **published** at `/r/[slug]` (your first credibility deposit)

Five minutes a day on the Inbox, thirty minutes a week on a brief, and one published report a week. That's the whole habit — and it compounds into a research desk that runs itself and a reputation that sells for you.

---

<div align="center">

**[Open the Workspace →](https://valuein.biz/workspace)**  ·  **[Read this guide online →](https://valuein.biz/workspace-guide)**  ·  **[See pricing →](https://valuein.biz/pricing)**

<sub>Questions or friction? Email <a href="mailto:support@valuein.biz">support@valuein.biz</a> — we read every message.</sub>

</div>
