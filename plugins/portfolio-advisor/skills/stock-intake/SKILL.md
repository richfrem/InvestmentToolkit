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
4. **Comprehensive Metric Suite & Education**: In Step 3, present the COMPLETE institutional metric suite extracted from `fetch_financials.py` (Revenue, Margins, FCF, Rule of 40, Piotroski F-Score, Forward Estimates) and always include plain-English definitions for complex metrics (e.g. what the Piotroski score measures and how Rule of 40 evaluates growth vs profitability).
5. **Standard Transition Phrasing & Clarification Check**: Always ask the user if they have any questions or need clarification on any metric before advancing: *"Are you ready for me to guide you through the financial analysis and scenario calibration, or do you have any questions on these metrics?"*
6. **Provide High-Conviction Defaults**: Always offer a recommended option first, clearly labeled, so the user can confirm with a single click or word.

---

## What This Skill Does (The 6-in-1 Pipeline)

When given ANY ticker (even one not currently in your database or watchlist), this skill executes an automated pipeline:

1. **Step 1 — Foundation: Strategy Pillar & Thesis Alignment**: Confirms user's investment intent and assigns the stock to an official strategy pillar (`power`, `compute`, `datainfra`, `robotics`, etc.).
2. **Step 2 — Agent Pre-Flight & Grok News Sweep Review**: Agent synthesizes initial thesis brief, generates targeted Grok prompt, digests user's Grok output into dense structural takeaways, and pauses to confirm alignment before advancing.
3. **Step 3 — Financials & Baseline Ingest**: Calls `fetch_financials.py {TICKER}` to extract revenue, shares, margins, sector, industry, and analyst growth consensus.
4. **Step 4 — Live Technical Telemetry (TradingView CDP)**: Sets chart symbol to `{TICKER}`, reads the 1D & 1W Data Window (21/50/200 EMAs, RSI, Squeeze, ADX, SuperTrend, Volume Bias), and defines the dynamic entry pocket ($Buy Zone, Stop Loss, Take Profit 1 & 2).
5. **Step 5 — DCF Valuation & Reverse DCF Modeling**: Runs `dcf_scenarios.py` with user-selected growth/margin trajectory to establish Bear, Base, and Bull present values.
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

---

## Step 6: Grok News & Catalyst Sweep Prompt Generation (Copy-Paste Ready)

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
