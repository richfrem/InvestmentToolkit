# InvestmentToolkit

A premium, "Luxury Dark Mode" investment analysis suite built for sophisticated retail investors. This toolkit provides deep fundamental analysis, DCF valuation modeling, real-time portfolio monitoring, and autonomous AI agents for research and thesis management — without the need for expensive terminal subscriptions.

---

## 🚀 First Things First: Getting Started with Agents

The true power of this repository is not just the frontend UI—it is the **Agentic Operating System** behind it. Launch your CLI agent (Claude Code, Gemini CLI, or Copilot CLI) and use one of these triggers:

### 1. Master Setup (New Users — Start Here)
> **"Help me set up the toolkit"**

Runs the **`toolkit-onboarding-guide`** agent. This master coordinator checks your dependencies, runs the startup script, and routes you directly to the TradingView setup agent.

### 2. TradingView Setup (Primary Data + Execution Layer)
> **"Set up TradingView for me"**

Runs the **`tradingview-onboarding`** agent. This deep-dive guide covers:
1. TradingView Desktop install check
2. Subscription tier verification (Premium recommended for real-time data)
3. Broker panel connection inside TradingView (no separate API credentials needed)
4. CDP health check and broker data verification
5. First `/tv-portfolio-sync` — pulls live positions from all accounts (TFSA + RRSP + Cash)

### 3. Returning Users Quick Start
```bash
python3 run_investment_toolkit.py
```
*This automatically starts the backend, frontend, and TradingView Desktop with CDP debugging enabled.*

Then, ask your agent to run: `/tv-portfolio-sync`

---

## 🧩 AI Agent Plugins & Skills

All agent tooling is organized as portable plugins inside the `plugins/` directory and loaded as skills within `.agents/`. You must have a **Pro-tier AI subscription** to utilize the full autonomous research and execution loops.

### 1. Portfolio Advisor (`plugins/portfolio-advisor`)
An adversarial suite that acts as a hedge fund auditor. It challenges your bull cases, flags failing investment pillars, and proposes weight changes based on real-time drift.
- **Commands/Skills**: `/review-portfolio`, `/strategic-review`, `/rebalance`, `/calibrate-targets`, `/update-portfolio-targets`, `/x-news-sweep`, `/bundle-thesis-review`, `/13f-tracker`, `/13f-analyze`

### 2. Stock Valuation Analyst (`plugins/stock-valuation`)
An autonomous buy-side analyst. Fetches real-time financial data, builds Bear/Base/Bull DCF scenarios, and generates fair value recommendations (BUY/HOLD/SELL).
- **Commands/Skills**: `/evaluate-stock`, `/research-stock`

### 3. ETF Analysis (`plugins/etf-analysis`)
Purpose-built for thematic, closed-end, and cash fund ETFs.
- **Commands/Skills**: `/analyze-etf`

### 4. TradingView Integration (`plugins/tradingview`)
TradingView Desktop is the primary layer for live prices, portfolio sync, and order execution via CDP (Chrome DevTools Protocol) automation.
- **Commands/Skills**: `/tv-portfolio-sync`, `/place-order`, `/modify-order`, `/cancel-order`, `/get-orders`, `/tv-alert-sync`, `/tv-price-refresh`, `/tv-snapshot`, `/tv-ta`

### 5. Toolkit Manager (`plugins/toolkit-manager`)
Orchestrator for managing server startup and fallback API token seeding.
- **Commands/Skills**: `/start-screener`, `/setup-questrade`

---

## 💻 Core Application: Investment Screener

The `investment_screener/` app is the web-based financial analysis dashboard.

### Tech Stack
- **Frontend**: React 19, Vite, Tailwind CSS 4.0
- **Backend**: Node.js (Express), TypeScript
- **Analytical Engine**: Python 3.11 Utility Layer (`py_services/`) leveraging `yfinance` for math, validation, and historical financials.

### Key Features
- **Portfolio Summary & Table**: Live views synced from TV CDP or Questrade API.
- **Market Heatmap**: Real-time sector performance mapping.
- **Stock Analysis & Metrics**: Deep-dive AI Expert Thesis and 15+ fundamental metrics.
- **Valuation Modeler**: Interactive Bear/Base/Bull scenario modeling with automatic persistence to projection JSON files.
- **Trade Log**: Real-time mirror of the TradingView order panel via CDP.

---

## 🔌 How to Install Plugins

Plugins are self-contained. To link or reinstall them into your local agent environment:

**1. Install Project-Specific Plugins (Local):**
```bash
uvx --from git+https://github.com/richfrem/agent-plugins-skills plugin-add /Users/richardfremmerlid/Projects/InvestmentToolkit/plugins
```

**2. Install Core Library Plugins (Remote):**
```bash
uvx --from git+https://github.com/richfrem/agent-plugins-skills plugin-add richfrem/agent-plugins-skills
```

---

## 🔐 External Integrations & Fallbacks

### TradingView Premium (Primary Layer)
- **Required for real-time market data and live order execution.** The toolkit integrates directly with TradingView Desktop (running with `--remote-debugging-port=9222`).
- **Free/Essential Plans**: yfinance remains the fallback source for delayed data (15-20 min).

### Questrade API (Fallback)
- **Optional — TradingView handles sync and execution natively.**
- If TradingView Desktop is not running, the toolkit can fall back to the Questrade REST API.
- Token storage uses AES-256-GCM hardware-backed encryption (macOS Keychain).
- Run `/setup-questrade` to handle the OAuth2 exchange.

---

## 🛠 Architecture & Development Rules

> 📖 **Deep Dive**: For a comprehensive system map, context diagrams, and component interactions, read the **[Architecture Overview](docs/architecture/README.md)**.

### The Iron Law: Test-Driven Development (TDD)
```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.
```
- The primary test harnesses must shell out via subprocess to exactly mirror the execution paths of the AI plugins and the Node Express bridge.
- Mocking is strictly prohibited on critical runtime paths.

### Agent Calculation Policy
- Never perform financial calculations inline (bash/python snippets).
- Always use or create versioned `.py` scripts in `investment_screener/backend/py_services/`.

### Exploration Workflow
The project leverages the **Exploration Cycle** architecture to systematize AI agent workflows in 4 phases:
1. Discovery Planning
2. Visual Blueprinting
3. Prototyping
4. Handoff & Specs
*(Managed by the `exploration-workflow` skill and `exploration-dashboard.md` state file)*

---

*Personal use only. Data from TradingView is subject to their Terms of Use: https://www.tradingview.com/policies/*
