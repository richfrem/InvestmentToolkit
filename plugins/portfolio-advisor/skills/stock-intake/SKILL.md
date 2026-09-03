---
name: stock-intake
plugin: portfolio-advisor
description: >
  Autonomous end-to-end stock intake & onboarding wizard designed for non-expert investors.
  Pulls live financials, conducts plain-English educational walkthroughs, queries TradingView
  CDP Data Window for technical levels (1D/1W), injects visual action tier lines on the chart,
  runs a 5-year scenario DCF model, logs research in intelligence.sqlite, and registers the stock
  into domain_model.sqlite under its designated strategy pillar.
  Trigger with /stock-intake {TICKER} or "onboard {TICKER}".
allowed-tools: Bash, Read, Write
---

# Stock Intake & Automated Onboarding Wizard

**Trigger:** `/stock-intake {TICKER}` or `/onboard-stock {TICKER}`  
**Examples:** `/stock-intake STM` | `/stock-intake MP` | `/stock-intake LITE` | `/stock-intake ASTS`

## Canonical Metric/Surface Reference
`references/stock-analysis-surface-checklist.md` maps every fundamentals/technicals/DCF metric this
wizard collects to its exact data source, calculation function, and persistence script (Rule of 40 →
`fetch_financials.py::expert_metrics`, Piotroski F-Score → `fetch_financials.py::piotroski_f_score`,
DCF Bear/Base/Bull → `dcf_scenarios.py`, live EMAs/ADX/RSI → `ta_sweep_single.py`, etc.). Steps 3–5
below should cite this checklist rather than restate the mapping loosely — if a metric's source or
function ever changes, fix it there first (single source), same discipline as
`questrade-tool-schemas.md` in the questrade plugin. `stock_valuation`'s `/update-stock-analysis` skill
already references this same file as its Step 10 post-completion verification gate — this wizard is
the intake-time counterpart to that same canonical mapping, not a separate one.

---

## 🧭 The Non-Expert "Smooth Wizard" UX Principles

1. **One Guided Decision at a Time**: Never overwhelm the user with multiple simultaneous choices, dense checklists, or raw SQL. Ask exactly one simple, conversational question at each stage.
2. **Translate ALL Jargon into Plain-English Real-World Analogies**:
   - *200 EMA* ➔ *"The institutional floor where large funds buy."*
   - *ADX* ➔ *"The trend engine (tells us if momentum is real [>25] or drifting sideways [<20])."*
   - *ATR* ➔ *"The normal daily swing size (helps place safety stops outside normal noise)."*
   - *RSI* ➔ *"The gas tank (50 is neutral, >70 is exhausted/overbought, <30 is deeply oversold)."*
   - *Rule of 40* ➔ *"Growth + Margin balance (scores over 40% represent elite compounders)."*
   - *Piotroski F-Score* ➔ *"Institutional financial health score out of 9 (7–9 is pristine, 4–6 is solid/stable, 0–3 is distressed)."*
   - *Gross Margin* ➔ *"Profit after factory costs (how much money is left over to fund growth)."*
3. **Respect Standing Decisions (Rule #8)**:
   - If the ticker already exists in `domain_model.sqlite`, read `standing_decision_type` and `standing_decision_reason` first.
   - Never override an existing decision unless there is a **material delta (>15% Fair Value change)** or new catalyst information.
4. **Concrete Capital Sourcing & Account Sizing (Rule #9 & Capital Policy)**:
   - Target share counts are advisory execution targets for the human user, **never** manually written into `account_investment` (which only populates via broker sync).
   - Cash is sourced by selling **PSU-U.TO** in the same account (`shares ≈ ceil(N × price / 100)`).
   - Allocation splits across **TFSA (primary, ~75%)** and **RRSP (mirror, ~25% / 1/3 share count)**.
5. **Pre-Persistence Confirmation Gate**:
   - Always present the assembled Executive Summary Card and require the user's explicit confirmation before writing to `domain_model.sqlite` or modifying the live TradingView chart.
6. **Cross-Plugin Architecture Compliance (ADR-001)**:
   - Chart level injection is performed via prompt-loop skill delegation (`/tv-pine-inject` or `/tv-thesis-overlay`), never via raw cross-plugin script imports.

---

## 🧙 The 6-Step Conversational Onboarding Pipeline

```
[1. Intent & Re-Onboard Check] ➔ [2. Grok News (w/ Skip)] ➔ [3. Technical Action Tiers] ➔ [4. Financial Story & Peers] ➔ [5. DCF, PSU Sourcing & Account Split] ➔ [6. Confirmation Gate & Persistence]
```

---

### 🏛️ Step 1 — Intent, Existing Standing Decision & Strategy Pillar (Wizard Checkpoint A)

1. **Pre-Check Existing Holdings**: Check if `{TICKER}` already exists in `domain_model.sqlite`. **This wizard is for net-new tickers only** (2026-08-28: narrowed scope — see `docs/architecture/skill-renames-2026-08-28.md`). If it already exists, redirect instead of proceeding here:
   > *"We already track {TICKER} under {PILLAR} with a Standing Decision of **{STANDING_DECISION}** ({REASON}). For an existing holding, use `/update-stock-analysis {TICKER}` to refresh its analysis (full DCF re-run + research report) — this onboarding wizard is for tickers not yet tracked. Want me to run that instead?"*
   Stop here if the user confirms — do not continue this pipeline for an existing ticker.
2. **Confirm Investment Intent**:
   > **Wizard Question 1**:  
   > *"What is your main investment goal for looking at **{TICKER}** today?"*  
   > - **Option A (Recommended — Secular Growth)**: I believe in the long-term megatrend (e.g. AI power grids, datacenter infrastructure) and want to hold for 3–5 years under the **{PILLAR_NAME}** pillar.  
   > - **Option B (Cyclical Turnaround)**: It was beaten down unfairly, and I expect an operational recovery over the next 12–18 months.  
   > - **Option C (Watchlist & Wait for Dip)**: I want to track it on my dashboard and wait for a deeper pullback before putting money to work.

*Execute `scripts/list_strategy_pillars.py` to match the target strategy pillar.*

---

### 🌐 Step 2 — Real-Time Grok News & Catalyst Ingestion (Proactive Prompt Output)

Immediately generate and display a customized, ticker-specific Grok prompt in Step 1/Step 2 so the user can copy-paste it directly without having to ask for it:

```text
Targeted Grok Sweep Prompt for {TICKER}:
"Provide a comprehensive, real-time news, catalyst, and supply-chain analysis for {COMPANY_NAME} ({TICKER}) over the past 90 days. Focus on:
1. Hyperscaler AI data center power/infrastructure adoption and tier-1 customer contracts.
2. Production capacity expansion, factory utilization, and technology yield improvements.
3. Industry inventory recovery inflection points vs macroeconomic headwinds.
4. Recent earnings guidance surprises, margin expansion timelines, and CAPEX updates.
Format as concise, high-conviction bullet points with direct impact on 5-year revenue and margin expansion."
```

- **If User Pastes Grok Output**: Ingest into structural catalyst events.
- **If User Replies "Skip" / "Proceed"**: Fall back gracefully to yfinance company profile news without blocking the pipeline.

---

### 📈 Step 3 — Live Technical Action Tiers & Tranche Plan (Wizard Checkpoint B)

Field/function mapping: see `references/stock-analysis-surface-checklist.md` § Tab 2 — Technicals.

Query live TradingView CDP technical data (21/50/200 EMAs, ADX, ATR, RSI) and explain the levels in plain English:

- 🟢 **Buy Pocket 1 ($Price)**: Current initial entry level.
- 💎 **Primary Buy Floor ($Price)**: The 200-day EMA institutional support zone.
- 🟡 **Trim Target 1 ($Price)** / 🟠 **Trim Target 2 ($Price)**: Natural profit-taking resistance shelves.
- 🛑 **Stop Loss / Breaker ($Price)**: Safety net level where the technical thesis fails.

> **Wizard Question 2**:  
> *"How would you like to handle buying if the price fluctuates?"*  
> - **Option A (Recommended — Staged Dip-Buying)**: Start with a 50% starter position now, and add the remaining 50% if price dips to our green institutional support line (${PRIMARY_BUY}).  
> - **Option B (Safety Net Alert)**: Buy our position now, but set a high-priority alert if price falls below our red line (${STOP_LOSS}) to protect capital.  
> - **Option C (Watchlist Only)**: Do not place orders yet; just monitor the levels on our chart.

---

### 📊 Step 4 — 4-Part Educational Financial Walkthrough

Field/function mapping: see `references/stock-analysis-surface-checklist.md` § Tab 1 — Overview (Rule of 40, Piotroski F-Score, margins, EPS, analyst targets).

Pull live metrics via `investment_screener/backend/py_services/fetch_financials.py {TICKER}`:
1. **Part 1 — Revenue Lifecycle**: Plain-English diagnosis of why sales dipped in prior years and what drives the forward rebound.
2. **Part 2 — Factory & Operating Leverage**: How expanding gross margins generate outsized bottom-line profit surges.
3. **Part 3 — Institutional Quality Scorecard**: Compare Rule of 40 and Piotroski F-Score *side-by-side with 2–3 key sector peers*.
4. **Part 4 — Forward Consensus**: Wall Street 1Y/2Y consensus targets aligned with multi-year company guidance.
5. **Part 5 — Strategic Outlook & Transcript Verification Checklist (Mandatory Gate)**:
   Review the last 2 earnings call transcripts and output the structured checklist block:
   ```markdown
   ### 📋 Strategic Outlook & Transcript Verification Checklist
   - [x] **Recent Earnings Calls Reviewed**: [e.g. Q1 2026, Q2 2026]
   - [x] **Guidance Trajectory**: [RAISED / MAINTAINED / LOWERED / WITHDRAWN]
   - [x] **Contracted Backlog & Pipeline**: [Firm Backlog vs Speculative Pipeline]
   - [x] **Strategy Alignment Lens**: [{PILLAR} - Product & Customer fit]
   - [x] **Adversarial Risk & Counterparty Audit**: [Credit quality, cash burn, execution hurdles]
   - [x] **Strategic Stance & Forward Outlook**: [Conviction summary before running DCF]
   ```
   *Note: This audit must be passed to `persist_valuation.py` inside `analyticsLog.outlookAudit`.*

---

### 💰 Step 5 — DCF Valuation, Position Sizing & Capital Sourcing (Wizard Checkpoint C)

Field/function mapping: see `references/stock-analysis-surface-checklist.md` § Tab 4 — Valuation Modeler (Bear/Base/Bull weighting, WACC, `dcf_scenarios.py`).

1. Run `investment_screener/backend/py_services/dcf_scenarios.py --raw temp/evaluations/{TICKER}_raw.json --scenarios temp/evaluations/{TICKER}_scenarios.json` to calculate Bear (20%), Base (50%), and Bull (30%) present values and blended Fair Value.
2. Calculate exact executable share counts, TFSA/RRSP breakdown, and PSU-U.TO funding leg:

> **Wizard Question 3**:  
> *"What size role should **{TICKER}** play in your portfolio?"*  
> - **Option A (Recommended — Starter / Pilot: 2.0% allocation)**:  
>   - **Total Target**: ~${TOTAL_USD} ({TOTAL_SHARES} shares)  
>   - **TFSA (Primary)**: {TFSA_SHARES} shares (~${TFSA_USD}) ➔ *Fund by selling {TFSA_PSU_SHARES} sh PSU-U.TO*  
>   - **RRSP (Mirror)**: {RRSP_SHARES} shares (~${RRSP_USD}) ➔ *Fund by selling {RRSP_PSU_SHARES} sh PSU-U.TO*  
> - **Option B (Full Core Holding: 4.0% allocation)**:  
>   - **Total Target**: ~${CORE_USD} ({CORE_SHARES} shares) with corresponding TFSA/RRSP split.  
> - **Option C (Watchlist Badge Only: 0.0% allocation)**:  
>   - Keep on watchlist and render visual chart levels without deploying capital.

---

### 🛑 Step 6 — Pre-Persistence Confirmation Gate & Comprehensive UI Surface Refresh

Present the completed Executive Summary Card:

```
🎯 [TICKER] Onboarding / Refresh Plan Summary

Pillar:          [Pillar Name] ([pillar_id])
Role:            [WATCHLIST / CORE HOLDING] (Target Weight: [X.X]%)
Market Price:    $[Price] USD
DCF Fair Value:  $[FairValue] ([+/-X]% upside — [Action])
Rule of 40:      [Score]% ([Pass/Watch])
Piotroski Score: [Score] / 9 ([Quality Tier])

Capital Execution Plan (Advisory):
- TFSA Buy: {TFSA_SHARES} sh @ $[Price] ➔ Sell {TFSA_PSU_SHARES} sh PSU-U.TO
- RRSP Buy: {RRSP_SHARES} sh @ $[Price] ➔ Sell {RRSP_PSU_SHARES} sh PSU-U.TO

Technical Execution Tiers:
- 🟡 Trim 1 / 🟠 Trim 2:  $[Trim 1] / $[Trim 2]
- 🟢 Entry / 💎 Add Zone: $[Entry 1] / $[Primary Buy] (200 EMA floor)
- 🛑 Safety Stop Breaker: $[Stop Loss]

DCF Scenarios:
🐻 Bear (20%): $[PV] — [One sentence scenario]
⚖️ Base (50%): $[PV] — [One sentence scenario]
🐂 Bull (30%): $[PV] — [One sentence scenario]
```

> **Final Confirmation Gate**:  
> *"Does this plan look good to save to your dashboard and render on your TradingView chart?"*  
> ➔ **Upon User "Yes" / "Confirm" (Comprehensive Full-Surface Atomic Sync)**:
> 1. **Update Valuation Modeler & DCF Projections**: Post updated full projection object with fresh `aiThesis`, `scenarios` (Bear/Base/Bull), `analyticsLog`, and current model author to `/api/projections` and `domain_model.sqlite` (`projection_version`).
> 2. **Update Thesis & Target Weights**: Call `stock_intake_persist.py` to persist `target_weight`, `lifecycle_status`, `standing_decision_*`, `agent_rationale`, and `price_level_tier` records.
> 3. **Record in Intelligence Event Ledger**:
>    ```bash
>    python3 plugins/portfolio-advisor/skills/stock-intake/scripts/record_intelligence_event.py \
>      --ticker {TICKER} \
>      --type THESIS_UPDATE \
>      --title "{TICKER} Intake/Refresh into {PILLAR_TITLE} Pillar (${FAIR_VALUE} DCF FV)" \
>      --summary "{ONE_SENTENCE_THESIS_SUMMARY}" \
>      --payload '{"pillar": "{PILLAR_ID}", "fair_value": {FAIR_VALUE}, "target_entry": {TARGET_ENTRY}, "rule_of_40": {RULE_40_SCORE}}'
>    ```
> 4. **Delegate TradingView Visual Sync**: Trigger `/tv-thesis-overlay` or `/tv-pine-inject` to update live price rays on TradingView Desktop.
