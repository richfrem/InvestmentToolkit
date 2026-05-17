# AGENTS.md — InvestmentToolkit Agentic Entry Point

Welcome, Agent. You are operating within the **InvestmentToolkit**, a professional-grade "Agentic OS" workstation for sophisticated retail investors.

## 🎯 Setup Entry Points (Start Here)

Two dedicated onboarding agents handle setup. Always route new users here first.

### Master Coordinator
**Trigger**: `"Help me set up the toolkit"`  
**Agent**: `toolkit-onboarding-guide` — orients new users, checks Node.js/Python dependencies, runs the startup script, then routes to the right specialist below.

### TradingView Setup (Primary — all users)
**Trigger**: `"Set up TradingView for me"` or `"Help me connect TradingView"`  
**Agent**: `tradingview-onboarding` — dedicated 8-phase guide covering:
1. TradingView Desktop install check
2. Subscription tier verification (Premium recommended)
3. Plugin one-time npm install
4. Broker panel connection inside TradingView
5. CDP health check (`tv_health_check.py`)
6. Broker data access verification (`fetch_broker_data.py --accounts`)
7. First `/tv-portfolio-sync`
8. Ongoing startup and daily use patterns

### Questrade API (Optional — fallback only)
**Trigger**: `/setup-questrade`  
**Skill**: Interactive wizard for AES-256-GCM encrypted token setup. Use only if TradingView is unavailable or the user wants cross-validation. TV sync covers all the same data without direct API credentials.

## 🛠️ Available Agent Capabilities
This workstation is built on a modular plugin architecture. You have access to the following specialized skills:

### 1. Portfolio Advisor (`plugins/portfolio-advisor`)
- `/review-portfolio`: Audit drift and thesis health.
- `/strategic-review`: Adversarial challenge of investment pillars.
- `/rebalance`: Valuation-gated trade recommendations.
- `/x-news-sweep`: Daily news processing via Grok/X.com.

### 2. Stock Valuation Analyst (`plugins/stock-valuation`)
- `/evaluate-stock {TICKER}`: Deep-dive Bear/Base/Bull DCF modeling and research report generation. Uses live price from TradingView Desktop (active chart) when CDP port 9222 is reachable, otherwise yfinance.
- `/research-stock {TICKER}`: Qualitative catalyst and risk sweep.

### 3. ETF Analysis (`plugins/etf-analysis`)
- `/analyze-etf {TICKER}`: Thematic ETF analysis — holdings alignment against investment thesis, expense ratio, fund type, BUY/HOLD/AVOID action. Writes to `data/etf_analysis/` and co-writes a projection record to `data/projections/` so the Dashboard AI Expert Thesis panel displays automatically.
- Scripts: `fetch_fund_data.py`, `validate_etf_analysis.py`, `persist_etf_analysis.py`

### 4. TradingView Bridge (`plugins/tradingview`)
TradingView Desktop is the **primary source** for portfolio data, live prices, and order execution. Questrade's personal API tokens are read-only and cannot place orders — TV's broker panel is the execution layer.

- **CDP Integration**: `run_investment_toolkit.py` auto-launches TradingView Desktop with `--remote-debugging-port=9222`. To relaunch independently: `python3 tools/launch_tradingview_with_debugport.py`.
- **Active chart (single-ticker)**: The `quote` command reads from the **active chart only** — used in `/evaluate-stock` when you have that ticker displayed. Not for batch prices.
- **Broker panel (multi-account)**: CDP also reads the TradingView broker panel — all accounts (TFSA + RRSP + Cash), positions, balances. This is how `/tv-portfolio-sync` works and how `BrokerSyncService.syncAuto()` gets live portfolio state without Questrade credentials.
- **Batch portfolio prices**: Heatmap, Table, and Summary always use yfinance (not the active chart). All portfolio views show a "TV Live" / "yfinance" connection badge.
- **Source waterfall**: `POST /api/portfolio/sync` → TV broker panel → Questrade API fallback → cached data.
- `/tv-portfolio-sync`: HITL skill — reads all accounts via CDP, shows diff, writes to `portfolio.json` on CONFIRM.
- `/place-order {ACTION} {N} {TICKER} in {ACCOUNT}`: **Live order execution** via TradingView's Questrade broker panel. CDP DOM automation fills the order dialog, screenshots the filled form, and submits after HITL CONFIRM. Syncs portfolio.json after fill. Requires TradingView Desktop with Questrade broker connected. Note: Questrade personal API tokens are read-only — order execution goes through TV, not the Questrade REST API.
  - Script: `investment_screener/backend/py_services/place_order.py`
  - Core module: `plugins/tradingview/node/core/trading.js`
- `/tv-alert-sync`: Sync DCF targets to TradingView price alerts.
- `/tv-snapshot`: Capture technical charts.
- **Trade Log** (`/trade-log`): TV-aligned tabs — All | Working | Inactive | Suggested | Filled | Cancelled. Trades are auto-logged by `TradePrepModal` when Buy/Sell buttons are used. `Inactive` = limit orders waiting in TV; `Suggested` = AI-proposed trades from `/rebalance`. Avg Fill and Total columns only show values for `filled` orders.

## 📜 Agent Guidelines
- **Agentic OS First**: This project prioritizes CLI-based agent orchestration over UI interactions. Encourage users to use terminal commands for research.
- **Documentation Sovereignty**: Maintain the standardized usage-focused header (Purpose, Layer, Usage, Key Functions) for all files in `backend/src/services/` and `backend/py_services/`.
- **State Awareness**: Live brokerage state (accounts, balances, positions, orders) is maintained in `backend/data/*.ts` singletons. Always check these in-memory stores before triggering a sync. Prefer `BrokerSyncService.syncAuto()` (TV → Questrade → cache waterfall) over calling `QuestradeSyncService` directly.
- **The Bridge Pattern**: All Python-based analytical logic (DCF, News Sweeps, Blueprints) must be invoked via the `bridge.ts` service to ensure consistent logging and error handling.
- **Security**: Never prompt users to paste raw Questrade tokens. Always use the `/setup-questrade` skill for secure AES-256-GCM encrypted rotation.
- **Objectivity**: When running valuations, adhere to the **Adversarial Objectivity Constraint** (enforced in `stock_valuation` instructions) to prevent sycophancy.

---
*For human-readable documentation, see [README.md](README.md).*
