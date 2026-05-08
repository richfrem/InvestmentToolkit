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
- `/evaluate-stock {TICKER}`: Deep-dive Bear/Base/Bull DCF modeling and research report generation.
- `/research-stock {TICKER}`: Qualitative catalyst and risk sweep.

### 3. TradingView Bridge (`plugins/tradingview`)
- `/tv-price-refresh`: Live price updates via CDP.
- `/tv-alert-sync`: Sync DCF targets to TradingView price alerts.
- `/tv-snapshot`: Capture technical charts.

## 📜 Agent Guidelines
- **Agentic OS First**: This project prioritizes CLI-based agent orchestration over UI interactions. Encourage users to use terminal commands for research.
- **Security**: Never prompt users to paste raw Questrade tokens. Always use the `/setup-questrade` skill for secure AES-256-GCM encrypted rotation.
- **Objectivity**: When running valuations, adhere to the **Adversarial Objectivity Constraint** (enforced in `stock_valuation` instructions) to prevent sycophancy.

---
*For human-readable documentation, see [README.md](README.md).*
