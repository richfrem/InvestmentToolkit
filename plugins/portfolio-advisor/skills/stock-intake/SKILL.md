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

## What This Skill Does (The 5-in-1 Pipeline)

When given ANY ticker (even one not currently in your database or watchlist), this skill executes an automated 5-step intake:

1. **Step 1 — Financials & Baseline Ingest**: Calls `fetch_financials.py {TICKER}` to extract revenue, shares, margins, sector, industry, and analyst growth consensus.
2. **Step 2 — Live Technical Telemetry (TradingView CDP)**: Sets chart symbol to `{TICKER}`, reads the 1D & 1W Data Window (21/50/200 EMAs, RSI, Squeeze, ADX, SuperTrend, Volume Bias), and defines the dynamic entry pocket ($Buy Zone, Stop Loss, Take Profit 1 & 2).
3. **Step 3 — DCF Valuation & Reverse DCF Modeling**: Runs `dcf_scenarios.py` to establish Bear, Base, and Bull present values and weighted fair value, then computes implied 5Y CAGR with `reverse_dcf.py`.
4. **Step 4 — Research Ledger Ingestion**: Writes a structured research event body and commits it to `intelligence.sqlite` via `intelligence.event_store`, then updates the canonical view.
5. **Step 5 — Dual-Layer Persistence & Watchlist Registration**:
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
1. Insert into `domain_model.sqlite` (`investment`, `investment_price`, `projection_version`, `projection_scenario`).
2. Write `investment_screener/backend/data/projections/{TICKER}.json`.

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
```
