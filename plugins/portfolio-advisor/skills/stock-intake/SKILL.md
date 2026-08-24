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
**Example:** `/stock-intake MP` | `/stock-intake LITE` | `/stock-intake ASTS` | `/stock-intake STM`

---

## 🧭 Non-Expert Interactive UX Protocol (One Checkpoint at a Time)

To ensure a comfortable, institutional-grade experience for non-expert investors:

1. **Strategic Foundation First**: Before discussing price or complex formulas, establish *why* the stock is being considered and match it to a clear, high-level **Portfolio Strategy Pillar** (e.g. `Power / Energy`, `Compute / Hardware`, `Data Infra`).
2. **Strictly One Question at a Time**: Never ask multiple questions or provide dense checklists in a single turn. Guide the user step-by-step through clear conversational checkpoints.
3. **Always Explain the "Why" in Plain English**:
   - Translate technical indicators into real-world analogies (*"200 EMA = the institutional floor where large funds buy"*).
   - Explain financial ratios simply (*"Rule of 40 = Growth + Margin balance; scores over 40% represent elite compounders"*).
4. **4-Part Educational Financial Walkthrough**:
   - **Part 1 — Revenue Lifecycle & Root Cause**: Why did revenue peak or drop in past years, and what triggers the rebound?
   - **Part 2 — Margins, Fixed-Cost Operating Leverage & Strategic Pivot**: How do factories/operating leverage expand profits as sales recover?
   - **Part 3 — Institutional Health Scores & Peer Scorecard**: Compare Rule of 40, Piotroski score, and gross margins directly against 2–3 sector peers.
   - **Part 4 — Forward Consensus & DCF Calibration**: Ground valuation targets in Wall Street estimates and management guidance.
5. **Provide High-Conviction Recommended Defaults**: Always offer the recommended path first (marked with `(Recommended)`) so the user can proceed with a single click or word.

---

## 🛠️ The Canonical 6-Step Intake Pipeline

```
[1. Strategy Pillar] ➔ [2. Grok News Sweep] ➔ [3. Technicals & TV Sync] ➔ [4. Financial Narrative] ➔ [5. DCF Calibration] ➔ [6. Dual Persistence]
```

### 1. Step 1 — Foundation: Strategy Pillar & Intent Alignment
- Confirm investment thesis and assign the stock to an active portfolio strategy pillar (`power`, `compute`, `datainfra`, `robotics`, etc.) using `plugins/portfolio-advisor/skills/stock-intake/scripts/list_strategy_pillars.py`.

### 2. Step 2 — Real-Time News & Catalyst Ingestion (Grok Front-Door)
- Synthesize an initial thesis brief.
- Provide the user with a customized, copy-paste ready Grok news sweep prompt.
- Ingest the user's Grok output into core structural takeaways (customer wins, supply chain inflection points, 13F smart money accumulation).

### 3. Step 3 — Live Technical Telemetry & TradingView Visual Sync
- Query live technical indicators via TradingView CDP: 21/50/200 EMAs, ADX (trend strength), ATR (daily swing size), RSI, and Volume Bias.
- Translate levels into clear **Execution Action Tiers**:
  - 🟢 **Buy Pocket 1 / Initiate** (Current support zone)
  - 💎 **Primary Buy / Accumulate** (Institutional 200 EMA floor)
  - 🟡 **Trim Target 1** / 🟠 **Trim Target 2** (Resistance profit-taking levels)
  - 🛑 **Stop Loss / Breaker** (Thesis invalidation shelf)
- Automatically sync horizontal levels to the live TradingView chart using `AI TA Levels v6` and close the Pine Editor panel.

### 4. Step 4 — Financials, Quality Health & Peer Benchmarking
- Pull live financials via `investment_screener/backend/py_services/fetch_financials.py {TICKER}`.
- Conduct the 4-part narrative walkthrough (Revenue lifecycle, Gross/Operating margin leverage, Peer comparison scorecard, Forward consensus).

### 5. Step 5 — 5-Year Scenario DCF Valuation Matrix
- Calibrate Bear (20%), Base (50%), and Bull (30%) growth and margin trajectories with `investment_screener/backend/py_services/dcf_scenarios.py`.
- Calculate the probability-weighted Present Value (Fair Value) and determine the margin of safety vs current market price.

### 6. Step 6 — Dual Persistence & Intelligence Event Logging
1. **Record Research Event**: Ingest the complete thesis and Rule of 40 metrics into `intelligence.sqlite` using the canonical script:
   ```bash
   python3 investment_screener/backend/py_services/record_intelligence_event.py \
     --ticker {TICKER} \
     --type THESIS_UPDATE \
     --title "{TICKER} Initiated into {PILLAR_TITLE} Strategy Pillar (${FAIR_VALUE} DCF FV)" \
     --summary "{ONE_SENTENCE_THESIS_SUMMARY}" \
     --payload '{"pillar": "{PILLAR_ID}", "fair_value": {FAIR_VALUE}, "target_entry": {TARGET_ENTRY}, "rule_of_40": {RULE_40_SCORE}}'
   ```
2. **Persist Domain Model**: Insert/update `investment`, `investment_price`, `projection_version`, and `price_level_tier` rows in `domain_model.sqlite`.
3. **Emit Projection JSON**: Write `investment_screener/backend/data/projections/{TICKER}.json` (Schema v1.2) for instant React dashboard display.

---

## 🎯 Concluding Summary Card Format

Always finish with a clean, executive summary:

```
🎯 [TICKER] Onboarding & Intake Complete

Pillar:          [Pillar Name] ([pillar_id])
Role:            WATCHLIST (is_watchlisted = 1, target_weight = 0.0%)
Market Price:    $[Price] USD
DCF Fair Value:  $[FairValue] ([+/-X]% upside — [Action])
Rule of 40:      [Score]% ([Pass/Watch])
Piotroski Score: [Score] / 9 ([Quality Tier])

Technical Execution Tiers:
- Overhead Resistance:  $[Trim 2] (50 EMA) / $[Trim 1] (21 EMA)
- Confluence Buy Floor: $[Primary Buy] (200 EMA institutional support)
- Invalidation / Stop:  $[Stop Loss] (Structural breaker)

DCF Scenarios:
🐻 Bear (20%): $[PV] — [One sentence scenario]
⚖️ Base (50%): $[PV] — [One sentence scenario]
🐂 Bull (30%): $[PV] — [One sentence scenario]

✅ Stored in domain_model.sqlite & data/projections/{TICKER}.json
✅ Ingested in intelligence.sqlite
✅ Rendered live on TradingView Desktop with AI TA Levels v6
```


