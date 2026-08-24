---
name: stock_intake
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

---

## 🧭 The Non-Expert "Smooth Wizard" UX Principles

1. **One Guided Decision at a Time**: Never overwhelm the user with multiple simultaneous choices, dense checklists, or raw SQL. Ask exactly one simple, conversational question at each stage.
2. **Translate All Jargon into Real-World Analogies**:
   - *200 EMA* ➔ *"The institutional floor where large funds buy."*
   - *ADX* ➔ *"The trend engine (tells us if momentum is real or drifting sideways)."*
   - *Rule of 40* ➔ *"Growth + Margin balance (scores over 40% represent elite compounders)."*
   - *Gross Margin* ➔ *"Profit after factory costs (how much money is left to fund growth)."*
3. **High-Conviction `(Recommended)` Defaults**: Always present the most logical option first with a `(Recommended)` tag so non-experts can confirm with a single click or word.
4. **Concrete Dollar & Share Math**: Never ask users to calculate percentages or tranche sizes. Always convert percentages into exact dollar amounts and share counts based on live account equity.

---

## 🧙 The 6-Step Conversational Onboarding Pipeline

```
[1. Intent & Pillar] ➔ [2. Real-Time Grok Sweep] ➔ [3. Technical Action Tiers] ➔ [4. Financial Story & Peers] ➔ [5. DCF Valuation & Sizing] ➔ [6. Visual TV Sync & Save]
```

---

### 🏛️ Step 1 — Intent & Strategy Pillar Alignment (Wizard Checkpoint A)

Start with a warm, conversational goal alignment:

> **Wizard Question 1**:  
> *"What is your main investment goal for looking at **{TICKER}** today?"*  
> - **Option A (Recommended — Secular Growth)**: I believe in the long-term megatrend (e.g. AI power grids, datacenter infrastructure) and want to hold for 3–5 years under the **{PILLAR_NAME}** pillar.  
> - **Option B (Cyclical Turnaround)**: It was beaten down unfairly, and I expect an operational recovery over the next 12–18 months.  
> - **Option C (Watchlist & Wait for Dip)**: I want to track it on my dashboard and wait for a deeper pullback before putting money to work.

*Execute `scripts/list_strategy_pillars.py` to auto-assign the pillar ID.*

---

### 🌐 Step 2 — Real-Time Grok News & Catalyst Ingestion

Synthesize an initial 3-bullet briefing and provide the user with a copy-paste ready Grok prompt:

```text
Targeted Grok Sweep Prompt for {TICKER}:
"Provide a comprehensive, real-time news, catalyst, and supply-chain analysis for {COMPANY_NAME} ({TICKER}) over the past 90 days. Focus on:
1. Hyperscaler AI data center power/infrastructure adoption and tier-1 customer contracts.
2. Production capacity expansion, factory utilization, and technology yield improvements.
3. Industry inventory recovery inflection points vs macroeconomic headwinds.
4. Recent earnings guidance surprises, margin expansion timelines, and CAPEX updates.
Format as concise, high-conviction bullet points with direct impact on 5-year revenue and margin expansion."
```

*Digest the user's Grok output into structural catalysts (e.g. 13F institutional accumulation, factory yield unlocks).*

---

### 📈 Step 3 — Live Technical Levels & Tranche Plan (Wizard Checkpoint B)

Query live TradingView CDP technical data (21/50/200 EMAs, ADX, ATR, RSI) and explain the levels in plain English:

- 🟢 **Buy Pocket 1 ($Price)**: Current initial entry level.
- 💎 **Primary Buy Floor ($Price)**: The 200-day EMA institutional support zone.
- 🟡 **Trim Target 1 ($Price)** / 🟠 **Trim Target 2 ($Price)**: Natural profit-taking resistance shelves.
- 🛑 **Stop Loss / Breaker ($Price)**: Safety net level where the thesis fails.

> **Wizard Question 2**:  
> *"How would you like to handle buying if the price fluctuates?"*  
> - **Option A (Recommended — Staged Dip-Buying)**: Start with a 50% starter position now, and add the remaining 50% if price dips to our green institutional support line (${PRIMARY_BUY}).  
> - **Option B (Safety Net Alert)**: Buy our position now, but set a high-priority alert if price falls below our red line (${STOP_LOSS}) to protect capital.  
> - **Option C (Watchlist Only)**: Do not place orders yet; just monitor the levels on our chart.

---

### 📊 Step 4 — 4-Part Educational Financial Walkthrough

Pull live metrics via `investment_screener/backend/py_services/fetch_financials.py {TICKER}` and conduct a narrative story:
1. **Part 1 — Revenue Lifecycle**: Plain-English diagnosis of why sales dipped in prior years and what drives the forward rebound.
2. **Part 2 — Factory & Operating Leverage**: How expanding gross margins generate outsized bottom-line profit surges.
3. **Part 3 — Institutional Quality Scorecard**: Compare Rule of 40 and Piotroski F-Score *side-by-side with 2–3 key sector peers*.
4. **Part 4 — Forward Consensus**: Wall Street 1Y/2Y consensus targets aligned with multi-year company guidance.

---

### 💰 Step 5 — DCF Valuation & Position Sizing (Wizard Checkpoint C)

Run `investment_screener/backend/py_services/dcf_scenarios.py` to establish Bear (20%), Base (50%), and Bull (30%) present values and calculate probability-weighted Fair Value.

> **Wizard Question 3**:  
> *"What size role should **{TICKER}** play in your portfolio?"*  
> - **Option A (Recommended — Starter / Pilot)**: **2.0% allocation** (~${DOLLAR_AMOUNT} / ~{SHARE_COUNT} shares) — Low risk test position while monitoring next earnings.  
> - **Option B (Full Core Holding)**: **4.0% allocation** (~${DOLLAR_AMOUNT} / ~{SHARE_COUNT} shares) — High conviction holding alongside top portfolio winners.  
> - **Option C (Watchlist Badge Only)**: **0.0% allocation** — Track on screener and live chart without deploying capital.

---

### 💾 Step 6 — Visual Chart Sync & Dual Persistence

1. **Inject Visual Action Tiers on TradingView**:
   - Update `plugins/tradingview/assets/pinescript-indicators/ai-ta-levels.pine` (Pine Script v6) with the stock's custom levels.
   - Inject onto active TradingView chart via `plugins/tradingview/scripts/tv_pine_inject.py`.
   - Automatically close the Pine Editor panel to leave a clean, full-screen chart.
2. **Record in Intelligence Ledger**:
   - Call canonical tool `investment_screener/backend/py_services/record_intelligence_event.py`.
3. **Persist Domain Model & JSON Projections**:
   - Save to `domain_model.sqlite` (`investment`, `investment_price`, `projection_version`, `price_level_tier`).
   - Write `investment_screener/backend/data/projections/{TICKER}.json` for instant dashboard loading.

---

## 🎯 Executive Intake Summary Card

```
🎯 [TICKER] Onboarding & Intake Complete

Pillar:          [Pillar Name] ([pillar_id])
Role:            [WATCHLIST / CORE HOLDING] (Target Weight: [X.X]%)
Market Price:    $[Price] USD
DCF Fair Value:  $[FairValue] ([+/-X]% upside — [Action])
Rule of 40:      [Score]% ([Pass/Watch])
Piotroski Score: [Score] / 9 ([Quality Tier])

Technical Execution Plan:
- 🟡 Trim 1 / 🟠 Trim 2:  $[Trim 1] / $[Trim 2] (Profit-taking targets)
- 🟢 Entry / 💎 Add Zone: $[Entry 1] / $[Primary Buy] (200 EMA floor)
- 🛑 Safety Stop Breaker: $[Stop Loss] (Structural invalidation)

DCF Scenarios:
🐻 Bear (20%): $[PV] — [One sentence scenario]
⚖️ Base (50%): $[PV] — [One sentence scenario]
🐂 Bull (30%): $[PV] — [One sentence scenario]

✅ Stored in domain_model.sqlite & data/projections/{TICKER}.json
✅ Ingested in intelligence.sqlite
✅ Rendered live on TradingView Desktop with AI TA Levels v6
```
