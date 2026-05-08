# InvestmentToolkit

A premium, "Luxury Dark Mode" investment analysis suite built for sophisticated retail investors. This toolkit provides deep fundamental analysis, DCF valuation modeling, real-time portfolio monitoring, and autonomous AI agents for research and thesis management — without the need for expensive terminal subscriptions.

---

## 🚀 Getting Started (Start Here)

The easiest way to set up and use this toolkit is to use the **Interactive Onboarding Agent**. 

Simply launch your CLI agent (Gemini CLI, Claude Code, or Copilot CLI) and type:

> **"Help me set up the toolkit"**

This will trigger the **Toolkit Onboarding Guide**, a dedicated AI concierge that will:
1.  **Check Dependencies**: Verify your Node.js and Python versions.
2.  **Sync Portfolio**: Securely guide you through the Questrade API link process.
3.  **Link Charts**: Help you connect TradingView Desktop for real-time prices.
4.  **First Run**: Guide you through your first `/evaluate-stock` or `/review-portfolio` command.

---

## 💎 The Core Value: An "Agentic OS" for Investors

Unlike traditional investment apps, **the true power of this repository is not the frontend UI—it is the Agentic Operating System behind it.** 

This repo is designed to be used interactively with **Pro-tier AI subscriptions** (Claude code, Gemini pro, github copilot pro or chatgpt pro) via **CLI agents** like `gemini-cli`, `claude-code`, or `copilot-cli`. 

### Why this matters:
- **Autonomous Deep Research**: Instead of reading PDFs, you command your CLI agent: `/research-stock NVDA`. The agent autonomously fetches financials, parses news, runs a DCF model, and writes a professional-grade research report to your `backend/data/research/` folder.
- **Adversarial Thesis Review**: The `portfolio-advisor` plugin acts as a cold-blooded hedge fund auditor. It challenges your "bull cases," flags failing investment pillars, and proposes formula-driven weight changes based on real-time drift and AI fair-value signals.
- **Real-Time Data Bridge**: CLI tools bridge your brokerage (Questrade) and charts (TradingView Premium) with your local investment thesis. You can ask: *"How does the NVDA earnings beat affect my Power pillar sizing?"* and get an answer rooted in your actual holdings and cost basis.

> [!IMPORTANT]
> **Subscription Prerequisite**: To use the sub-agents and execute specialized commands like `/strategic-review`, `/x-news-sweep`, and `/evaluate-stock`, you **must** have an active Pro-tier subscription for your chosen CLI environment (e.g., Claude Code, GitHub Copilot Pro, or Google Gemini Pro).

---

## External Account Requirements
... (rest of the file)
This toolkit integrates with two external services that require accounts:

### Questrade (brokerage)

**Required for live portfolio sync.** The toolkit connects to your Questrade brokerage account to retrieve current holdings, positions, and cost-basis data.

- Account: https://www.questrade.com/
- The toolkit uses Questrade's OAuth2 API with AES-256-GCM encrypted token storage (macOS Keychain). Your credentials never leave your machine.
- See [Questrade Setup](#questrade-setup) below.

### TradingView Premium (real-time prices)

**Required for real-time market data.** The toolkit integrates with TradingView Desktop to pull live prices directly from your Premium feed.

- Desktop app: https://www.tradingview.com/desktop/
- Subscription plans (Premium or higher required): https://www.tradingview.com/pricing/
- Without a Premium subscription, current prices are delayed 15–20 minutes — identical to the yfinance fallback that is already in place. The integration adds no value below Premium tier.
- **Free and Essential plans:** yfinance remains the data source; TradingView integration is inactive.
- **Premium and above:** real-time prices, 1d change%, and DCF price alerts via the TradingView plugin.

> **Note:** yfinance is not replaced. It remains the source for historical OHLCV, financial fundamentals (revenue, margins, EPS, ratios), and all data when TradingView Desktop is not running.

---

## Core Components

### 1. Investment Screener (`investment_screener`)
A web-based financial analysis dashboard featuring:
- **Luxury Dark Mode**: Professional Black/Gold aesthetic.
- **Expert Metrics**: Instant access to PEG Ratio, Piotroski F-Score, and Insider Ownership.
- **Valuation Modeler**: Interactive Bear/Base/Bull scenario modeling to project 5-year price targets.
- **Comparative Analysis**: Side-by-side ticker comparison.

### 2. Questrade Portfolio Integration
A professional-grade brokerage sync engine featuring:
- **Dynamic Sync**: Real-time retrieval of account positions and balances.
- **Secure Token Bridge**: AES-256-GCM encryption with hardware-backed master keys (macOS Keychain).
- **Metadata Enrichment**: Intelligent fallback to `yfinance` for sector/industry categorization of broker holdings.
- **Onboarding Flow**: Guided UI for secure account linking and rotation management.

### Portfolio Summary
![Portfolio Summary](screenshots/2026-05-08-portfolio-summary.png)
*(Total market value, performance metrics, and strategy allocation)*

### Portfolio Table
![Portfolio Table](screenshots/2026-05-08-portfolio-table.png)
*(Detailed positions view with real-time performance and fair value targets)*

### Market Heatmap
![Market Heatmap](screenshots/2026-05-08-heatmap.png)
*(Real-time sector performance visualization and strategy mapping)*

### Stock Analysis & Metrics
![Analysis Metrics](screenshots/2026-05-08-nbis-overview.png)
*(Deep-dive AI Expert Thesis and 15+ Premium fundamental metrics)*

### Portfolio Advisor & Thesis Review
![Thesis Review](screenshots/2026-05-08-portfolio-analysis-recommendations.png)
*(Autonomous advisor proposing rebalance actions based on thesis alignment)*

### Investment Thesis
![Investment Thesis](screenshots/2026-05-08-investment-thesis-overview.png)
*(Living document tracking version history and core investment pillars)*

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite, Tailwind CSS 4.0 |
| Backend | Node.js (Express), Python 3.11 bridge |
| Market data | `yfinance` (historical + fundamentals) + TradingView Premium (real-time current price) |
| Portfolio data | Questrade API (positions, cost basis) |
| Schema | Zod validation — `lastActualPS` nullable-safe for pre-revenue stocks |
| AI agents | Modular Plugin Architecture + Exploration Cycle workflow |

---

## AI Agent Plugins

All agent tooling is organized as portable plugins in `plugins/`. Each plugin contains commands, skills, scripts, and documentation.

### 1. Stock Valuation Analyst (`plugins/stock-valuation`)
An autonomous buy-side analyst. Fetches real-time financial data, builds Bear/Base/Bull DCF scenarios, and generates a fair value with BUY/HOLD/SELL recommendation.

- `/evaluate-stock {TICKER}` — Full DCF valuation with scenario analysis and persistence to the Valuation Modeler
- `/research-stock {TICKER}` — Qualitative sweep; classifies findings as Class A/B/C/D and gates re-valuation on confirmation

### 2. Strategic Thesis Suite (`plugins/portfolio-advisor`)
A multi-skill suite that monitors, challenges, and optimizes your portfolio against your investment thesis.

- `/review-portfolio` — Drift monitor + pillar conviction audit + thesis formula health score (0–100)
- `/strategic-review` — Adversarial thesis challenger; surfaces failing pillars and proposes formula improvements
- `/rebalance` — Valuation-gated trade optimizer; never buys a SELL-rated holding to restore drift
- `/x-news-sweep` — Daily Grok/X.com news sweep gated against DCF + 8 hard gates

### 3. TradingView Integration (`plugins/tradingview`)
Real-time price and alert integration via TradingView Desktop and Chrome DevTools Protocol.

**Requires:** TradingView Desktop + Premium subscription (see [above](#tradingview-premium-real-time-prices)).

- `/tv-price-refresh` — Live prices for all portfolio positions (TV → yfinance fallback per ticker)
- `/tv-alert-sync` — Create TradingView price alerts at DCF bear/base/bull targets for all holdings
- `/tv-alert-sync CRWV` — Single-ticker alert sync
- `/tv-snapshot CRWV` — Capture chart screenshot → `PortfolioAnalysis/screenshots/`

See [`plugins/tradingview/README.md`](plugins/tradingview/README.md) for full setup and usage.

### 4. Toolkit Manager (`plugins/toolkit-manager`)
Orchestrator for server startup and Questrade token management.

- `/start-screener` — Launch full suite (frontend + backend)
- `/setup-questrade` — Interactive Questrade token setup

---

## Getting Started

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| Node.js 18+ | `node --version` |
| Python 3.11+ | `python3 --version` |
| Pro-tier AI | Required for CLI agents (Claude Code, Copilot Pro, or Gemini Pro) |
| Questrade account | https://www.questrade.com/ |
| TradingView Desktop | https://www.tradingview.com/desktop/ — optional but recommended |
| TradingView Premium | https://www.tradingview.com/pricing/ — required for real-time prices |

### Quick Start

```bash
python3 run_investment_toolkit.py
```

This handles everything automatically:
- Creates Python venv and installs dependencies
- Installs Node dependencies and builds the backend
- **Launches TradingView Desktop** with CDP enabled (if installed)
- Starts the backend API (port 3001) and frontend dashboard (port 5173)

### Plugin Installation

**1. Install Project-Specific Plugins (Local):**
```bash
uvx --from git+https://github.com/richfrem/agent-plugins-skills plugin-add /Users/richardfremmerlid/Projects/InvestmentToolkit/plugins
```

**2. Install Core Library Plugins (Remote):**
```bash
uvx --from git+https://github.com/richfrem/agent-plugins-skills plugin-add richfrem/agent-plugins-skills
```

### TradingView Plugin Setup (one-time)

```bash
cd plugins/tradingview/node
npm install
cd ../../..

# Verify connection (run after TradingView Desktop is open)
python3 plugins/tradingview/scripts/tv_health_check.py
```

---

## Questrade Setup

Setting up Questrade is secure — your token is encrypted in a local cache (AES-256-GCM, macOS Keychain) and never leaves your machine.

**Easiest method (built-in UI):**
Use the "Questrade Integration" modal in the web app. It guides you through obtaining your one-week token and seeds it automatically.

![Questrade Integration Setup](screenshots/2026-05-02-questrade-integration-modal.png)

**AI agent method:**
```
/setup-questrade
```

**Manual method (CLI):**
```bash
# 1. Redeem one-week app token from https://apphub.questrade.com/UI/UserApps.aspx
curl -s -X POST \
  "https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=<ONE_WEEK_TOKEN>" \
  -d '' -H 'Content-Type: application/x-www-form-urlencoded'

# 2. Seed the returned refresh_token
python3 investment_screener/backend/src/QuestradeDataEngine.py \
  --seed "<refresh_token>" \
  --cache-dir investment_screener/backend/
```

---

## Running Services Separately

```bash
# Backend (port 3001)
npm --prefix investment_screener run dev -w backend

# Frontend (port 5173)
npm --prefix investment_screener run dev -w frontend
```

---

## AI Development Architecture

This project uses the **Exploration Cycle** architecture to systematize AI agent workflows, moving away from template-driven missions toward a modular, phase-gated development loop.

- **Orchestration**: Managed via the `exploration-workflow` skill.
- **Phases**: 4-phase loop (Discovery → Blueprinting → Prototyping → Handoff).
- **Dashboard**: `exploration/exploration-dashboard.md` (state management).
- **Plugins**: Modular AI logic housed in `plugins/`.
- **Reference**: See ADR [022-exploration-cycle-pivot.md](docs/adrs/022-exploration-cycle-pivot.md) for the design rationale.

---

## Acknowledgements

The TradingView Desktop integration in this project was informed by research into the following open-source projects. Our implementation (`plugins/tradingview/node/`) is an owned, minimal adaptation — not a dependency on either repo at runtime.

### tradingview-mcp (CDP bridge)
- **Repository:** https://github.com/tradesdontlie/tradingview-mcp (cloned to `temp/tradingview-mcp/`)
- **Author:** tradesdontlie
- **License:** MIT — Copyright (c) 2026 tradesdontlie
- **What it does:** 68-tool MCP server connecting to TradingView Desktop via Chrome DevTools Protocol (CDP). Full chart control, Pine Script editor, alerts, OHLCV, screenshots, replay, DOM-level interaction.
- **Our approach:** We extracted only the CDP connection, quote, alert, and screenshot logic (~360 lines) into `plugins/tradingview/node/`. No MCP server process required; Python calls Node directly via subprocess. This removes the need for a persistent background server and eliminates the external dependency at runtime.

### tradingview-mcp-server (REST aggregator)
- **Repository:** https://github.com/atilaahmettaner/tradingview-mcp (cloned to `temp/atilaahmettaner-tradingview-mcp/`)
- **Author:** Ahmet Taner Atila
- **License:** MIT — Copyright (c) 2025 Ahmet Taner Atila
- **What it does:** Python MCP server using TradingView public REST APIs (`tradingview-screener`, `tradingview-ta`). Supports screener scans, multi-exchange sentiment, technical analysis signals, and walk-forward backtesting — no TradingView Desktop required.
- **Why we prefer the CDP approach:** The REST APIs used by this repo aggregate public/delayed data and cannot access your Premium real-time feed. CDP connects directly to your authenticated TradingView session — real-time prices, your watchlists, your alerts, your charts. For a personal portfolio tool where Premium data is the point, CDP is the right layer.

Both projects are MIT licensed. Their licenses apply to their respective source code only and do not grant any rights to TradingView Inc.'s software, data, or intellectual property.

---

*Personal use only. Data from TradingView is subject to their Terms of Use: https://www.tradingview.com/policies/*
