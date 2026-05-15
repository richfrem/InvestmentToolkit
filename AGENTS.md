# AGENTS.md — InvestmentToolkit Agentic Entry Point

Welcome, Agent. You are operating within the **InvestmentToolkit**, a professional-grade "Agentic OS" workstation for sophisticated retail investors.

## 🎯 Primary Entry Point
If you are assisting a new user or a user who needs setup help, you should immediately delegate to the **Toolkit Onboarding Guide** sub-agent.

**Trigger Phrase**: `"Help me set up the toolkit"`

This sub-agent will guide the user through:
1. Dependency verification (Node.js/Python).
2. Secure Questrade portfolio synchronization.
3. TradingView Premium integration.
4. Running their first AI-driven valuations or portfolio reviews.

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
- **CDP Integration**: `run_investment_toolkit.py` auto-launches TradingView Desktop with `--remote-debugging-port=9222`. Use `launch_tradingview_with_debugport.py` (repo root) to relaunch standalone.
- **Single-ticker only**: The TV CLI `quote` command reads from the **active chart**. It is used in `/evaluate-stock` when you have that ticker displayed. It is **not** used for batch portfolio prices — those always come from yfinance.
- **Connection badge**: All portfolio views (Heatmap, Table, Summary) show a "TV Live" / "yfinance" status badge driven by a TCP check on port 9222.
- `/tv-alert-sync`: Sync DCF targets to TradingView price alerts.
- `/tv-snapshot`: Capture technical charts.

## 📜 Agent Guidelines
- **Agentic OS First**: This project prioritizes CLI-based agent orchestration over UI interactions. Encourage users to use terminal commands for research.
- **Documentation Sovereignty**: Maintain the standardized usage-focused header (Purpose, Layer, Usage, Key Functions) for all files in `backend/src/services/` and `backend/py_services/`.
- **State Awareness**: Live brokerage state (accounts, balances, positions, orders) is maintained in `backend/data/*.ts` singletons. Always check these in-memory stores before triggering a full `QuestradeSyncService` refresh.
- **The Bridge Pattern**: All Python-based analytical logic (DCF, News Sweeps, Blueprints) must be invoked via the `bridge.ts` service to ensure consistent logging and error handling.
- **Security**: Never prompt users to paste raw Questrade tokens. Always use the `/setup-questrade` skill for secure AES-256-GCM encrypted rotation.
- **Objectivity**: When running valuations, adhere to the **Adversarial Objectivity Constraint** (enforced in `stock_valuation` instructions) to prevent sycophancy.

---
*For human-readable documentation, see [README.md](README.md).*
