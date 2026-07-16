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
- **Daily command**: `/daily` — one interactive loop: portfolio sync → morning brief (macro + TA + DCF + earnings) → ranked triage cards → trade execution → self-evolution log. Replaces the 10-step manual checklist.
- **Other skills**: `/review-portfolio`, `/strategic-review`, `/rebalance`, `/calibrate-targets`, `/update-portfolio-targets`, `/x-news-sweep`, `/bundle-thesis-review`, `/13f-tracker`, `/13f-analyze`, `/run-advisor` (post-catalyst orchestrator)

### 2. Stock Valuation Analyst (`plugins/stock-valuation`)
An autonomous buy-side analyst. Fetches real-time financial data, builds Bear/Base/Bull DCF scenarios, and generates fair value recommendations (BUY/HOLD/SELL).
- **Commands/Skills**: `/evaluate-stock`, `/research-stock`, `/forward-valuation-challenge`, `/valuation-math-validation`

### 3. ETF Analysis (`plugins/etf-analysis`)
Purpose-built for thematic, closed-end, and cash fund ETFs.
- **Commands/Skills**: `/analyze-etf`

### 4. TradingView Integration (`plugins/tradingview` + `tradingview-cdp/`)
TradingView Desktop is the primary layer for live prices, portfolio sync, order execution, Pine Script authoring, and deep technical analysis via CDP (Chrome DevTools Protocol) automation. The Node.js CDP engine lives at `tradingview-cdp/` (repo root) as a shared runtime installed once via `cd tradingview-cdp && npm ci`.
- **Commands/Skills**: `/setup-tradingview`, `/tv-portfolio-sync`, `/tv-watchlist-sync`, `/place-order`, `/modify-order`, `/cancel-order`, `/get-orders`, `/tv-alert-sync`, `/tv-price-refresh`, `/tv-snapshot`, `/pine-inject`, `/author-pine-script`, `/tv-ta-deep`
- **Agents**: `ta-guide` — interactive TA tutor and Pine Script architect; walks users through live chart analysis step-by-step, builds the required indicator view, authors custom Pine Script v6 indicators, and submits recommendations through adversarial red-team review
- **Pine Script tools**: `pine_linter.py` (static v6 linter — version, declaration, lookahead, drawing-var checks), `pine_source_reader.py` (fetch any community indicator's source directly from TV's Indicators dialog)

### 5. Toolkit Manager (`plugins/toolkit-manager`)
Orchestrator for managing server startup.
- **Commands/Skills**: `/start-screener`

---

## 💻 Core Application: Investment Screener

The `investment_screener/` app is the web-based financial analysis dashboard.

### Tech Stack
- **Frontend**: React 19, Vite, Tailwind CSS 4.0
- **Backend**: Node.js (Express), TypeScript
- **Analytical Engine**: Python 3.11 Utility Layer (`py_services/`) leveraging `yfinance` for math, validation, and historical financials.

### Key Features
- **Portfolio Summary & Table**: Live views synced from TV CDP.
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

---

## 🙏 Acknowledgements & Prior Art

### TradingView CDP Community

The TradingView CDP automation layer was informed by studying the following open-source projects:

| Project | GitHub | What It Does |
|---------|--------|--------------|
| **tradingview-mcp** (tradesdontlie) | https://github.com/tradesdontlie/tradingview-mcp | The most complete CDP-based TradingView automation library available. 5,000+ lines, 15+ command namespaces. Its `pine.js` uses **React fiber tree traversal** (`__reactFiber` prefix) to locate Monaco editor internals — more resilient than CSS selectors alone. No live broker order execution. |
| **tradingview-mcp** (atilaahmettaner) | https://github.com/atilaahmettaner/tradingview-mcp | TradingView screener/scanner using the `tradingview-screener` Python library (REST API). 30+ tools for market scanning and symbol filtering. No CDP, no live orders. |

**Our key architectural difference:** Both reference projects are chart analysis and research tools. InvestmentToolkit is a **live broker execution layer** — it navigates TradingView's built-in Questrade broker panel via CDP to place, modify, and cancel real orders, with 3-step HITL confirmation, safety gates (stale portfolio exit 4, size cap exit 3), multi-account support, `tvOrderId` tracking, and automatic portfolio sync after fills. Pine Script injection (via `/pine-inject`) uses the React fiber traversal technique from tradesdontlie's implementation to locate Monaco editor internals without relying on fragile CSS class selectors.

### AI Agent Infrastructure

- **[browser-use/browser-harness](https://github.com/browser-use/browser-harness)** — Inspired our approach to self-healing, self-evolving skills and direct CDP automation. By allowing the agent to write its own helpers and domain skills when it encounters issues or gaps, the system continuously improves itself during execution.

- **[orba/superpowers](https://github.com/orba/superpowers)** — The TDD (Iron Law: no production code without a failing test first), brainstorming, and sub-agent driven development skills used throughout this project come from the superpowers plugin library. These skills enforce rigorous Red-Green-Refactor discipline and orchestrate parallel multi-agent task execution.

- **[richfrem/agent-plugins-skills](https://github.com/richfrem/agent-plugins-skills)** — The Exploration Workflow (4-phase: Discovery Planning → Visual Blueprinting → Prototyping → Handoff & Specs) and all project-local AI agent plugins and skills are organized and distributed through this repository.

---

*Personal use only. Data from TradingView is subject to their Terms of Use: https://www.tradingview.com/policies/*
