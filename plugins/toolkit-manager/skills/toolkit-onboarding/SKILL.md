---
name: toolkit-onboarding
plugin: toolkit-manager
description: >
  Master onboarding coordinator and holistic portfolio bootstrap wizard for InvestmentToolkit.
  Guides new users through zero-config engine installation, account & pillar setup,
  broker/TradingView CDP ingestion, automated DCF baseline analysis, and live visual chart sync.
  Trigger on /toolkit-onboarding or "help me set up the toolkit" or "bootstrap my portfolio".
allowed-tools: Bash, Read, Write
---

# Master Portfolio Bootstrap & Onboarding Wizard

**Trigger:** `/toolkit-onboarding` or `/portfolio-bootstrap` or `"help me set up the toolkit"`

---

## 🧭 Overview & Architecture

This master coordinator takes an investor from a clean repository clone directly to an institutional-grade, fully operating investment operating system:

```
[1. Pre-Flight Engine Check] ➔ [2. Accounts & Strategy Pillars] ➔ [3. Broker/TV Ingestion] ➔ [4. Automated DCF Baseline] ➔ [5. Live Chart Overlay & Launch]
```

---

## 🛠️ Step 1 — Zero-Config Engine & Plugin Installation

1. **Verify Runtime Prerequisites**:
   - Node.js 18.0+ (`node --version`)
   - Python 3.11+ (`python3 --version`)
2. **Compile Virtual Environment & Dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   npm install --prefix investment_screener
   npm ci --prefix tradingview-cdp
   ```
3. **Deploy & Reinstall All Plugins**:
   ```bash
   python3 .agents/skills/plugin-syncer/scripts/sync_with_inventory.py
   ```
4. **Initialize Private Data & Configuration Templates**:
   ```bash
   python3 -c "
   import os, shutil
   base = 'investment_screener/backend/data'
   for f in ['cash_flows.json', 'portfolio-config.json']:
       src = os.path.join(base, f + '.example')
       dst = os.path.join(base, f)
       if not os.path.exists(dst) and os.path.exists(src):
           shutil.copy(src, dst)
           print(f'Initialized: {f}')
   "
   ```

---

## 🏛️ Step 2 — Conversational Account & Strategy Pillar Foundation

Guide the user through their core wealth architecture:

### Checkpoint A: Account Architecture
> **Wizard Question 1**:  
> *"What investment account structure would you like to set up?"*  
> - **Option A (Recommended — Dual Account)**: **TFSA (Primary ~75%) + RRSP (Mirror ~25%)** with auto-mirroring.  
> - **Option B (Single Account)**: Individual Taxable / Margin or TFSA only.  
> - **Option C (Corporate / Trust)**: Custom multi-entity structure.

### Checkpoint B: Core Strategy Pillars
> **Wizard Question 2**:  
> *"Let's establish your Core Strategy Pillars and target allocation weights (totaling 100%):"*  
> - **Option A (Recommended — High-Conviction Tech & Energy)**:  
>   - ⚡ **Power / Energy** (`power`): `25.0%`  
>   - 🧠 **Compute / Hardware** (`compute`): `30.0%`  
>   - 🌐 **Data Infrastructure** (`datainfra`): `20.0%`  
>   - 🚀 **Software / Growth** (`software`): `15.0%`  
>   - 💵 **Defensive Cash / Sourcing** (`cash`): `10.0%` (via `PSU-U.TO` / `BIL`)  
> - **Option B (Custom Allocation)**: Provide your custom pillars and percentages.

*Seed into `domain_model.sqlite` (`account`, `strategy_pillar`, `sub_strategy`).*

---

## 🔄 Step 3 — Portfolio Ingestion & Cash Reconciliation

> **Wizard Question 3**:  
> *"How would you like to import your active holdings and cash?"*  
> - **Option A (Recommended — Live TradingView Desktop CDP Sync)**: Open TradingView Desktop with your broker tab active (`--remote-debugging-port=9222`) and run `/tv-portfolio-sync`. Automatically scrapes live share counts, market values, and cash into SQLite.  
> - **Option B (Interactive Ticker Intake List)**: Provide a list of tickers (e.g. `STM, BE, PLTR, NVDA, CORZ`) to onboard via `/stock-intake`.  
> - **Option C (CSV / Snapshot Import)**: Import existing trade log from file.

---

## 📊 Step 4 — Automated DCF Baseline & Quality Sweep

Iterate across all imported tickers in a background sweep:
1. Fetch 5-year financials and transcript data via `fetch_financials.py {TICKER}`.
2. Calculate institutional health metrics (**Rule of 40 Score** and **Piotroski F-Score**).
3. Generate Bear (20%), Base (50%), and Bull (30%) DCF projection scenarios (`projections/{TICKER}.json`).
4. Ingest research baselines into `intelligence.sqlite` via `record_intelligence_event.py`.

---

## 🖥️ Step 5 — Visual Chart Overlay & Launch Application

1. **TradingView Visual Setup**:
   - Set active layout to `agent-layout`.
   - Inject `AI TA Levels v6` to render 21/50/200 EMAs + DCF Fair Value + Buy/Trim/Stop levels on the active chart.
2. **Launch the Full Suite**:
   ```bash
   python3 run_investment_toolkit.py
   ```
   - **React 19 Dashboard**: `http://localhost:5173`
   - **Node.js Express API**: `http://localhost:3001`
   - **TradingView CDP Bridge**: `http://localhost:9222`
3. **Run Initial Health Audit**:
   - Execute `/portfolio_health` or `/daily` to confirm all green!

---

## 🎯 Master Bootstrap Summary Card

```
🎯 InvestmentToolkit Bootstrap & Portfolio Onboarding Complete!

Accounts Configured:
- TFSA (Primary): $[Total USD]
- RRSP (Mirror):  $[Total USD]

Pillars Initialized:
- ⚡ Power / Energy:       [XX]%
- 🧠 Compute / Hardware:   [XX]%
- 🌐 Data Infrastructure:  [XX]%
- 🚀 Software / Growth:    [XX]%
- 💵 Defensive Cash:       [XX]%

Active Holdings Onboarded: [N] tickers ($[Total Market Value])
Cash Sourced:              $[Total Cash USD] ([N] sh PSU-U.TO)
DCF Projections Built:     [N] tickers in domain_model.sqlite & backend/data/projections/

✅ React 19 Dashboard Live: http://localhost:5173
✅ TradingView CDP Visual Overlays Injected (AI TA Levels v6)
✅ Daily Loop Ready: Run /daily for your first morning triage
```
