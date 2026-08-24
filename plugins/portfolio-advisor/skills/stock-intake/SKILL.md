---
name: stock_intake
plugin: portfolio-advisor
description: >
  Autonomous end-to-end stock intake & onboarding engine. Takes any stock ticker
  (held, watchlisted, or completely new), pulls live financials, queries TradingView
  CDP Data Window for technical levels (1D/1W), runs a 5-year scenario DCF model,
  generates a deep-dive research event in intelligence.sqlite, writes the v1.2
  projection JSON, and inserts/updates the ticker into domain_model.sqlite
  as an active watchlisted holding under its designated strategy pillar.
  Trigger with /stock-intake {TICKER} or "onboard {TICKER}".
allowed-tools: Bash, Read, Write
---

# Stock Intake & Automated Onboarding Skill

**Trigger:** `/stock-intake {TICKER}` or `/onboard-stock {TICKER}`  
**Example:** `/stock-intake MP` | `/stock-intake LITE` | `/stock-intake ASTS`

---

## Interactive UX Protocol (One Question at a Time)

To ensure a seamless and clear user experience:
1. **Foundation First (Strategic Alignment)**: Before jumping into valuation math, always ask **Question 1: Why are we considering this stock and which Portfolio Strategy Pillar does it serve?** Present all existing strategy pillars with target weights and recommend the closest match.
2. **One Question at a Time**: Never overwhelm the user with multiple simultaneous choices or long checklists. Ask a single, clear question at each calibration checkpoint.
3. **Explain the "Why" Transparently**: Whenever presenting valuation ranges, multiple choices, or technical levels, explain unclear design concepts (e.g. why 18x exit P/E is chosen for base case, or what the 200 EMA bounce signifies) in plain English before asking.
4. **Step 3 Narrative Walkthrough & Peer Benchmarking Protocol**:
   - **Part 1 — Revenue Lifecycle & Transcript Root Cause**: Do not just display raw figures. Synthesize the operational narrative from recent quarterly calls: diagnose *why* historical revenue reached peaks or troughs (e.g. customer inventory cycles, market pull-forwards, or macroeconomic headwinds vs secular decline) and *when* management guides forward growth inflections.
   - **Part 2 — Margins, Operating Leverage & Strategic Pivot**: Detail historical gross and operating margin trends, fixed-cost operating leverage dynamics (e.g. plant utilization, scale efficiencies, COGS optimization), and the strategic product/service pivot driving margin expansion back toward target profitability.
   - **Part 3 — Institutional Health Scores & Peer Comparison**: Present Rule of 40, Piotroski F-Score (with score thresholds: 0–3 Weak/Distressed, 4–6 Solid/Stable, 7–9 Elite Quality), and balance sheet health *side-by-side with 2–3 key sector/industry peers* so the user has relative valuation and performance context.
   - **Part 4 — Forward Consensus & DCF Horizon Alignment**: Connect Wall Street 1Y/2Y consensus revenue and EPS targets to the company's multi-year commercial backlog and management guidance, setting the foundation for DCF scenario bounds.
   *Ask the user if they have any questions or observations at each part before advancing.*
5. **Standard Transition Phrasing**: When the financial analysis walkthrough is complete, prompt: *"Are you ready for us to move to Step 4 (Live TradingView Technical Telemetry)?"*
6. **Provide High-Conviction Defaults**: Always offer a recommended option first, clearly labeled, so the user can confirm with a single click or word.

---

## What This Skill Does (The 6-in-1 Pipeline)

When given ANY ticker (even one not currently in your database or watchlist), this skill executes an automated pipeline:

1. **Step 1 — Foundation: Strategy Pillar & Thesis Alignment**: Confirms user's investment intent and assigns the stock to an official strategy pillar (`power`, `compute`, `datainfra`, `robotics`, etc.).
2. **Step 2 — Agent Pre-Flight & Grok News Sweep Review**: Agent synthesizes initial thesis brief, generates targeted Grok prompt, digests user's Grok output into dense structural takeaways, and pauses to confirm alignment before advancing.
3. **Step 3 — Live Technical Telemetry, Plain-English Education & Action Tiers (TradingView CDP)**:
   - **Plain-English Indicator Translations**: Never leave jargon unexplained. Assume the user is non-technical:
     - *200 EMA*: The long-term institutional floor — big funds buy when price touches this line.
     - *ADX*: The trend engine — tells us if a real breakout is building (>25) or if price is just drifting sideways (<20).
     - *ATR*: The normal daily swing size — helps set a smart stop-loss that won't get triggered by normal market noise.
     - *RSI*: The gas tank — 50 means neutral with plenty of room to run before getting exhausted/overbought (>70).
     - *Volume Bias*: Buying vs selling pressure — negative/drying volume at support means sellers are out of ammo.
   - **Action Tier Levels (Initiate / Add / Trim / Exit)**: Explicitly classify technical price zones into execution tiers:
     - **🟢 INITIATE Zone ($Buy Pocket 1)**: Initial entry tranche right at key support.
     - **💎 ACCUMULATE / ADD Zone ($Buy Pocket 2)**: Secondary dip-buying tranche if price tests lower boundary.
     - **✂️ TRIM 1 / TRIM 2 Targets**: Logical resistance levels to take initial 1/3 or 1/2 profits.
     - **🛑 HARD EXIT / STOP-LOSS**: Invalidation level where the technical thesis fails.
   - **TradingView Interactive Sync Offer**: Always ask the user if they want to:
     1. Sync these exact price alerts into TradingView via `/tv-alert-sync` so their phone/desktop pings when hit.
     2. Inject dynamic horizontal support/resistance lines directly onto their live TradingView chart via `/tv-thesis-overlay`.
4. **Step 4 — Financials & Baseline Ingest**: Calls `fetch_financials.py {TICKER}` and executes the 4-part narrative walkthrough (Revenue Lifecycle, Margins/Pivots, Peer Scorecards, Forward Consensus) with full live price and market cap awareness.
5. **Step 5 — DCF Valuation & Target Delta Matrix**: Runs `dcf_scenarios.py` with user-calibrated growth/margin trajectory to establish Bear, Base, and Bull present values and compares live price against technical/DCF levels.
6. **Step 6 — Research Ledger Ingestion**: Writes a structured research event body and commits it to `intelligence.sqlite` via `intelligence.event_store`, then updates the canonical view.
7. **Step 7 — Dual-Layer Persistence & Watchlist Registration**:
   - **SQLite (`domain_model.sqlite`)**: Inserts/updates `investment` with `is_watchlisted = 1`, `lifecycle_status = 'watchlist'`, assigned `pillar_id`, `sub_strategy_id`, and `investment_price`. Inserts `projection_version` and `projection_scenario` rows.
   - **Filesystem JSON (`backend/data/projections/{TICKER}.json`)**: Writes the official Schema v1.2 projection object for instant dashboard rendering.

---

## Execution Instructions

### Step 1: Fetch Financials
```bash
python3 investment_screener/backend/py_services/fetch_financials.py {TICKER} > temp/evaluations/{TICKER}_raw.json
```

### Step 2: Live TradingView Chart Read (CDP)
```bash
node tradingview-cdp/cli.js chart symbol {TICKER}
node tradingview-cdp/cli.js chart openDataWindow
node tradingview-cdp/cli.js chart read
```

### Step 3: DCF Scenario Engine & Valuation
Write calibrated Bear/Base/Bull assumptions to `temp/evaluations/{TICKER}_scenarios.json`:
```bash
python3 investment_screener/backend/py_services/dcf_scenarios.py \
  --raw temp/evaluations/{TICKER}_raw.json \
  --scenarios temp/evaluations/{TICKER}_scenarios.json \
  --pretty
```

### Step 4: Record Research in Intelligence Ledger
```bash
PYTHONPATH=investment_screener/backend/py_services python3 -m intelligence.event_store \
  --event-type RESEARCH_IMPORT --ticker {TICKER} --effective-at "$(date +%F)" \
  --status ACTIVE --title "{TICKER} Onboarding & Fundamental Research Profile" --body-file temp/research_body.md

PYTHONPATH=investment_screener/backend/py_services python3 -m intelligence.view_generator {TICKER}
```

### Step 5: Dual Persistence to SQLite & JSON
1. Use the skill's canonical `scripts/manage_watchlist.py` script to register the stock in `domain_model.sqlite`:
```bash
python3 scripts/manage_watchlist.py \
  --add {TICKER} \
  --name "{COMPANY_NAME}" \
  --pillar {PILLAR_ID} \
  --sub-strategy {SUB_STRATEGY_ID} \
  --price {PRICE} \
  --sector "{SECTOR}" \
  --industry "{INDUSTRY}" \
  --projection-id "{PROJECTION_ID}"
```
2. Write `investment_screener/backend/data/projections/{TICKER}.json` with `source: "AI_AGENT"`.

---

## Final Output Presentation

Always conclude with a concise, actionable summary card:
```
🎯 [TICKER] Onboarding & Intake Complete

Pillar:          [Pillar Name] ([sub_strategy_id])
Role:            WATCHLIST (is_watchlisted = 1)
Market Price:    $[Price]
DCF Fair Value:  $[FairValue] ([Action] — [+/-X]% upside)

Technical Structure (1D / 1W):
- Overhead Resistance:  $[200 EMA or Supply Zone]
- Confluence Buy Zone:  $[21/50 EMA dynamic support]
- Invalidation / Stop:  $[SuperTrend Floor]

Scenarios:
🐻 Bear (25%): $[PV] — [One sentence]
⚖️ Base (50%): $[PV] — [One sentence]
🐂 Bull (25%): $[PV] — [One sentence]

✅ Stored in domain_model.sqlite and data/projections/{TICKER}.json
✅ Active on your Web App Watchlist & Screener

## Step 6: Ingest Thesis Intelligence Event (Canonical Ledger Tool)

Record the calibrated valuation thesis, Rule of 40 score, and strategic catalysts into `intelligence.sqlite` using the canonical service tool:

```bash
python3 investment_screener/backend/py_services/record_intelligence_event.py \
  --ticker {TICKER} \
  --type THESIS_UPDATE \
  --title "{TICKER} Initiated into {PILLAR_TITLE} Strategy Pillar (${FAIR_VALUE} DCF FV)" \
  --summary "{ONE_SENTENCE_THESIS_SUMMARY}" \
  --payload '{"pillar": "{PILLAR_ID}", "fair_value": {FAIR_VALUE}, "target_entry": {TARGET_ENTRY}, "rule_of_40": {RULE_40_SCORE}}'
```

---

## Step 7: Grok News & Catalyst Sweep Prompt Generation (Copy-Paste Ready)

Always generate a customized, high-precision Grok prompt targeting current catalysts, customer wins, and hyperscaler power contracts:

```text
Targeted Grok Sweep Prompt for {TICKER}:
"Provide a comprehensive, real-time news, catalyst, and supply-chain analysis for {COMPANY_NAME} ({TICKER}) over the past 90 days. Focus on:
1. Hyperscaler AI data center power management and grid infrastructure adoption.
2. Silicon Carbide (SiC) / Gallium Nitride (GaN) power discrete design wins and order backlog.
3. Automotive & Industrial recovery inflection points vs consumer electronics cycle.
4. Recent earnings guidance surprises, margin expansion timelines, and CAPEX updates.
5. Technical catalyst calendar (upcoming investor conferences, product launches, earnings dates).
Format as concise, high-conviction bullet points with direct impact on 5-year revenue and margin expansion."
```
