# AGENTS.md — InvestmentToolkit Agentic Entry Point

Welcome, Agent. You are operating within the **InvestmentToolkit**, a professional-grade "Agentic OS" workstation for sophisticated retail investors. This document serves as your operational manual and routing guide.

## 🎯 Setup Entry Points (Start Here)

Two dedicated onboarding agents handle setup. Always route new users here first.

### Master Coordinator
**Trigger**: `"Help me set up the toolkit"`  
**Agent**: `toolkit-onboarding-guide` (`plugins/toolkit-manager`) — orients new users, checks Node.js/Python dependencies, runs the startup script, then routes to the right specialist below.

### TradingView Setup (Primary — all users)
**Trigger**: `"Set up TradingView for me"` or `"Help me connect TradingView"`  
**Agent**: `tradingview-onboarding` (`plugins/toolkit-manager`) — dedicated 8-phase guide covering:
1. TradingView Desktop install check
2. Subscription tier verification (Premium recommended)
3. Broker panel connection inside TradingView
4. CDP health check and broker data verification
5. First `/tv-portfolio-sync`

### Questrade API (Optional — fallback only)
**Trigger**: `/setup-questrade`  
**Skill**: Interactive wizard for AES-256-GCM encrypted token setup. Use only if TradingView is unavailable.

## 🛠️ Available Agent Capabilities

This workstation is built on a modular plugin architecture. You have access to the following specialized skills, organized by plugin:

### 1. Portfolio Advisor (`plugins/portfolio-advisor`)
*Adversarial thesis challenger and portfolio manager.*
- `/review-portfolio`: Audit drift, pillar conviction, and thesis health.
- `/strategic-review`: Adversarial challenge of investment pillars. Proposes weight changes based on real-time drift.
- `/rebalance`: Valuation-gated trade recommendations (never buys SELL-rated holdings).
- `/calibrate-targets`: Interactive target-weight calibration session.
- `/update-portfolio-targets`: Apply formula/weight changes.
- `/x-news-sweep`: Daily news processing via Grok/X.com.
- `/bundle-thesis-review`: Package thesis/DCF for external LLMs.
- `/13f-tracker` & `/13f-analyze`: Poll and analyze SEC 13F EDGAR filings.

### 2. Stock Valuation Analyst (`plugins/stock-valuation`)
*Autonomous buy-side analyst.*
- `/evaluate-stock {TICKER}`: Deep-dive Bear/Base/Bull DCF modeling and research report generation.
- `/research-stock {TICKER}`: Qualitative catalyst and risk sweep.

### 3. ETF Analysis (`plugins/etf-analysis`)
*Thematic, closed-end, and cash fund analyst.*
- `/analyze-etf {TICKER}`: Holdings alignment against investment thesis, expense ratio review, BUY/HOLD/AVOID action. Co-writes to `data/projections/`.

### 4. TradingView Integration (`plugins/tradingview`)
*Execution and live pricing layer via CDP.*
- `/tv-portfolio-sync`: Syncs all accounts (TFSA + RRSP + Cash) from TV broker panel via CDP.
- `/place-order`: Live order execution via CDP DOM automation. 3-step HITL confirmation.
- `/modify-order` & `/cancel-order`: Order management via CDP.
- `/get-orders`: Fetch current working/inactive orders.
- `/tv-alert-sync`: Sync DCF targets to TradingView price alerts.
- `/tv-price-refresh`: Pulls real-time prices.
- `/tv-snapshot` & `/tv-ta`: Capture technical charts and perform technical analysis.
- `/pine-inject {description}`: Generate a custom Pine Script v6 indicator from a description and inject it into TradingView via CDP. Preflight validates structure before hitting TV. Script: `tv_pine_inject.py`.

### 5. Toolkit Manager (`plugins/toolkit-manager`)
*Orchestrator.*
- `/start-screener`: Launch full suite (frontend + backend).
- `/setup-questrade`: Handle OAuth2 exchange for backup API sync.

## 📜 Agent Operating Guidelines

As an AI agent operating in this repository, you **MUST** adhere to the following directives:

### 1. The Iron Law of TDD
**NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.**
- The primary test harnesses must shell out via subprocess to exactly mirror the execution paths of the AI plugins and the Express bridge.
- Mocking is strictly prohibited on critical runtime paths.
- Read `.agent/rules/test-driven-development.md` before making any code changes.

### 2. Agent Calculation Policy
- **Never perform financial or analytical calculations inline** (using ad-hoc bash/python snippets).
- Always use or create versioned `.py` scripts in `investment_screener/backend/py_services/`.
- Fix bugs once in the script; every future run benefits automatically.

### 3. Exploration Workflow
- When building new features, prototyping, or exploring broad capabilities, use the **Exploration Workflow**.
- 4-phase loop: Discovery Planning → Visual Blueprinting → Prototyping → Handoff & Specs.
- Managed by the `exploration-workflow` skill and `exploration/exploration-dashboard.md` state file.

### 4. State Awareness & The Bridge Pattern
- Live brokerage state is maintained in `backend/data/*.ts` singletons.
- Portfolio syncing uses a source waterfall: TradingView CDP → Questrade API Fallback → Cached data.
- All Python-based analytical logic MUST be invoked via the `bridge.ts` service.

### 5. Security & Objectivity
- **Security**: Never prompt users to paste raw Questrade tokens or API keys. Always use built-in wizards that handle secure encryption.
- **Objectivity**: When running valuations, adhere to the **Adversarial Objectivity Constraint** to prevent sycophancy. Challenge the user's assumptions and ensure reports remain fiercely objective.

### 6. TradingView CDP — Critical Node.js Rules
- **Shared runtime at `tradingview-cdp/`**: The Node.js CDP engine lives at `tradingview-cdp/` (repo root), NOT inside `plugins/`. Installed once via `cd tradingview-cdp && npm ci`. Always import via `from tv_client import tv_call` — never hardcode the path. ADR-024.
- **process.exit() required**: Every Node.js CDP snippet in `tradingview-cdp/` MUST end with `.then(() => process.exit(0)).catch(() => process.exit(1))`. Without it, the CDP WebSocket holds the event loop open and `subprocess.run()` from Python never returns.
- **React fiber traversal for Monaco**: Do not rely solely on CSS selectors for Pine Editor / Monaco. Scan DOM nodes for the `__reactFiber` key prefix and walk the fiber tree. Reference: [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp).
- **Pine inject uses `--content`, not `--file`**: `tv_pine_inject.py` reads the file in Python (correct cwd), then passes content via `--content` to Node. Node's cwd is `tradingview-cdp/` — passing a relative path would inject the path string as Pine Script.
- **Temp files**: Use `InvestmentToolkit/temp/` subfolder (gitignored), not `/tmp/` root. Task #0003 tracks legacy migration.

---

## 🙏 Acknowledgements & Prior Art

### TradingView CDP Community
- **[tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp)** — Most complete open-source TradingView CDP library. React fiber traversal technique for Monaco editor. No live broker execution.
- **[atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp)** — TradingView screener/scanner via REST API. No CDP, no live orders.

**Our differentiator:** InvestmentToolkit is a **live broker execution layer** — places, modifies, and cancels real orders through TradingView's Questrade broker panel via CDP, with HITL confirmation, safety gates, multi-account support, and portfolio sync.

### AI Agent Infrastructure
- **[orba/superpowers](https://github.com/orba/superpowers)** — TDD Iron Law, brainstorming, and sub-agent driven development skills used throughout this project.
- **[richfrem/agent-plugins-skills](https://github.com/richfrem/agent-plugins-skills)** — Exploration Workflow (4-phase) and all project-local AI agent plugins and skills.

---
*For human-readable documentation, please direct the user to [README.md](README.md).*
*For a comprehensive system map and diagrams, see the [Architecture Overview](docs/architecture/README.md).*
