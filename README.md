# InvestmentToolkit

An institutional-grade portfolio management and automated research suite built natively around the TradingView Desktop application. Designed for advanced power users, this toolkit combines **TradingView CDP visual/chart automation** with an **Agentic AI operating system**—enabling autonomous research, multi-scenario DCF valuation, adversarial portfolio audits, and human-supervised portfolio synchronization.

> [!TIP]
> ### ✅ 100% Fully Compliant: Human-in-the-Loop (HITL) Architecture
> **InvestmentToolkit is strictly an interactive decision-support system, NOT an unattended bot.**
> * **Active Human Review & Approval:** Every trade calculation (shares, limit price, sizing) is staged interactively on your screen (via `TradePrepModal` or the active TradingView Desktop GUI). **No order is ever placed without the human user reviewing, accepting, and confirming it.**
> * **Personal Display & Local Workstation:** All CDP automation runs on your local licensed workstation directly alongside your active TradingView Desktop display for personal portfolio tracking and visual analysis.
> * **No Unattended Auto-Trading:** Background AI agents and scripts are strictly forbidden from placing live orders autonomously while unattended. See [`.agent/rules/trade-execution-policy.md`](file:///.agent/rules/trade-execution-policy.md).

> [!WARNING]
> ### ⚠️ Notice Regarding TradingView Terms of Use (Prohibited Non-Display Usage)
> TradingView’s Terms of Use strictly prohibit **headless, unattended "black-box" algorithmic trading and third-party automated execution APIs** operating without direct human display interaction. InvestmentToolkit's architecture explicitly adheres to these terms by enforcing a 100% human-supervised workflow.

---

## 📸 Visual Tour & Application Suite

| **Live Stock Heatmap** | **Portfolio Summary & Allocation** |
| :---: | :---: |
| ![Live Stock Heatmap](screenshots/stock-heatmap.png) | ![Portfolio Summary](screenshots/portfolio-summary.png) |
| *Real-time performance treemap across technology, power, compute, and sovereign finance sectors.* | *Strategy allocation donut, time-weighted returns, and cross-account KPI rollups.* |

| **Portfolio: scope toggle, action chips and valuation ranges** | **Positions with target vs actual weights** |
| :---: | :---: |
| ![Portfolio page](screenshots/screener-advisor.png) | ![Portfolio positions](screenshots/portfolio-table.png) |
| *One page for holdings, watchlist and everything else: Holdings / Watchlist / All toggle, action chips, sector and strategy filters, valuation range bars (screenshots predate the merge).* | *Per-holding target vs actual weights, gain/loss metrics, and single-click staging.* |

| **Stock Analysis & Thesis Tiers (SNDK)** | **Interactive 5-Year DCF Modeler** |
| :---: | :---: |
| ![Stock Analysis](screenshots/stock-analysis-overview.png) | ![DCF Modeler](screenshots/dcf-valuation-modeler.png) |
| *AI Thesis Buy/Accumulate tiers, Trim targets, stop loss triggers, and financial scorecard.* | *Multi-scenario (Bear/Base/Bull) DCF projection modeler with real-time sensitivity matrix.* |

| **Daily Portfolio Brief & Morning Triage** | **Institutional 13F Filing Diff (SA LP)** |
| :---: | :---: |
| ![Daily Brief](screenshots/daily-portfolio-brief.png) | ![13F Filing Diff](screenshots/13f-institutional-filings.png) |
| *Morning macro regime check, binary earnings events, and ranked urgency triage cards.* | *Institutional quarter-over-quarter 13F diff tracker (Q2 2026 Long/Put barbell analysis).* |

---

## 🚀 First Things First: Getting Started with Agents

The true power of this repository is not just the frontend UI—it is the **Agentic Operating System** behind it.

> [!TIP]
> ### 📖 Fresh Clone Setup Guide
> `INIT_AGENTS.md` is the single, ordered setup guide: prerequisites, `.env`, the Agentic OS substrate and plugin contribution policy, `tradingview-cdp` dependencies, creating and verifying the SQLite databases, TradingView, and optional Questrade.

### 💬 Just Cloned the Repo? Paste This Prompt to Your AI Agent:

> **"Please read INIT_AGENTS.md and work through it in order, then run `/toolkit-onboarding` to bootstrap my investment environment."**

---

### 1. Master Setup & Portfolio Bootstrap (New Users — Start Here)

> **`/toolkit-onboarding`** or **`/portfolio-bootstrap`** or **"Help me set up the toolkit"**

Runs the **`onboarding`** mode of the `managing-the-toolkit` skill (the master wizard). This coordinator guides you end-to-end through:

0. **Agentic OS Substrate & Contribution Alignment**: Interactively configures plugin maintenance policy (`context/plugin-config.json` via `fork-and-pr`, `local-patch-and-issue`, or `domain-override`), initializes the `context/control_plane.db` SQLite state store, configures pre-commit evolution guards, and verifies substrate liveness via `os-health-check`.
1. **Runtime check and database protection**: confirms the environment set up in `INIT_AGENTS.md` (venv, npm and `tradingview-cdp` dependencies, plugins, `.env`), backs up `domain_model.sqlite` before the first write, and starts the app through the `run-app` mode.
2. **Accounts**: the TFSA, RRSP and CASH accounts are created by the first broker sync (`/tv-portfolio-sync`). Strategy pillars are not seeded yet; they are created as theses are written (open item in `references/map-debt.md`).
3. **Portfolio Ingestion**: Scrapes active holdings, shares, and USD cash from TradingView Desktop via `/tv-portfolio-sync` (or manual intake via `/stock-intake`).
4. **Automated DCF & Quality Baseline**: Computes Rule of 40 scores, Piotroski metrics, and Bear/Base/Bull 5-year DCF models across all holdings.
5. **TradingView Visual Sync & Dashboard Launch**: Injects `AI TA Levels v6` (21/50/200 EMAs + DCF Fair Value + action tiers) onto your live chart and starts the full suite on ports 5173/3001/9222!

### 2. TradingView Setup (Primary Data + Execution Layer)

> **`/tv-onboarding`** or **"Set up TradingView for me"**

Runs the **`setup`** mode of the `operating-tradingview-charts` skill (`/tv-onboarding`). This deep-dive guide covers:

1. TradingView Desktop install check
2. Subscription tier verification (Premium recommended for real-time data)
3. Broker panel connection inside TradingView (no separate API credentials needed)
4. CDP health check and remote debugging port 9222 verification
5. First `/tv-portfolio-sync` — pulls live positions from all accounts (TFSA + RRSP + Cash)

### 3. Returning Users Quick Start

```bash
python3 run_investment_toolkit.py
```

This automatically starts the backend, frontend, and TradingView Desktop with CDP debugging enabled.

Then, ask your agent to run: `/tv-portfolio-sync` or `/daily`

---

## 🧩 AI Agent Plugins & Skills

Agent tooling is packaged as four [APM](https://github.com/microsoft/apm) plugins under `plugins/`. Each plugin keeps its skills and agents in `.apm/` and each skill ("hub") carries its own scripts, references, assets and tests, with one `references/modes/<mode>.md` file per mode. There are no symlinks. Slash commands are unchanged; each one selects a mode of a hub. The old-path to new-path ledger is in `docs/plans/apm-migration/`.

| Plugin | Hubs (skills) |
| :--- | :--- |
| `plugins/portfolio-advisor` | `valuing-investments`, `running-portfolio-reviews`, `setting-portfolio-targets`, `tracking-13f-filings`, `auditing-portfolio-data` |
| `plugins/tradingview` | `operating-tradingview-charts`, `trading-via-tradingview`, `analyzing-charts` |
| `plugins/toolkit-manager` | `managing-the-toolkit` |
| `plugins/questrade` (optional) | `syncing-questrade-accounts`, `trading-with-questrade` |

Scripts that the backend imports, or that more than one hub uses, live in `investment_screener/backend/py_services/`; scripts used by one hub live in that hub's `scripts/`.

### 1. Portfolio Advisor (`plugins/portfolio-advisor`)

An adversarial suite that acts as a hedge fund auditor, now also holding the stock valuation and ETF analysis skills. It challenges your bull cases, flags failing investment pillars, and proposes weight changes based on real-time drift.

* **Daily command**: `/daily`: one interactive loop: portfolio sync → morning brief (macro + TA + DCF + earnings) → ranked triage cards → trade execution → self-evolution log.
* **Valuation and intake** (`valuing-investments`): `/update-stock-analysis`, `/research-stock`, `/forward-valuation-challenge`, `/valuation-math-validation`, `/analyze-etf`, `/stock-intake`.
* **Reviews** (`running-portfolio-reviews`): `/daily`, `/weekly-review`, `/news-sweep`, `/adversarial-review`, `/bundle-thesis-review`, `/run-advisor` (post-catalyst orchestrator).
* **Targets** (`setting-portfolio-targets`): `/review-portfolio`, `/strategic-review`, `/rebalance`, `/calibrate-targets`, `/update-portfolio-targets`, `/ytd-return`, `/set-thesis-breakers`.
* **13F** (`tracking-13f-filings`): `/13f-tracker`, `/13f-analyze`.
* **Audits** (`auditing-portfolio-data`): `/portfolio-coverage-audit`, `/data-quality-audit`, screener integrity.
* **Agents**: `portfolio-advisor-orchestrator`, `red-team-agent`, `risk-officer-agent`, `thesis-review-agent`.

### 2. TradingView Integration (`plugins/tradingview` + `tradingview-cdp/`)

TradingView Desktop is the primary layer for live prices, portfolio sync, order execution, Pine Script authoring, and deep technical analysis via CDP (Chrome DevTools Protocol) automation.

* **Skills**: `/tv-setup`, `/tv-onboarding`, `/tv-portfolio-sync`, `/tv-indicators`, `/tv-thesis-overlay`, `/tv-alert-reconcile`, `/tv-ta`, `/tv-ta-deep`, `/tv-ta-daily-sweep`, `/tv-snapshot`, `/tv-price-refresh`, `/tv-alert-sync`, `/tv-alert-list`, `/tv-pine-inject`, `/tv-author-pine`, `/tv-chart-setup`, `/tv-change-symbol`, `/tv-change-type`, `/tv-place-order`, `/tv-modify-order`, `/tv-cancel-order`, `/tv-get-orders`, `/tv-watchlist-sync`
* **Agents**: `ta-guide`: interactive TA tutor and Pine Script architect; walks users through live chart analysis step-by-step and builds custom indicator views.

### 3. Toolkit Manager (`plugins/toolkit-manager`)

Orchestrator for managing server startup, onboarding, SQLite administration and maintenance audits.

* **Skills**: `/start-screener`, `/toolkit-onboarding`

### 4. Questrade (`plugins/questrade`, optional)

Questrade brokerage connection through the Questrade MCP server: an optional second source for positions and trades (TradingView stays the default), plus deposits and currency conversion in your Questrade accounts.

* **Skills**: `/questrade-setup` (sign-in and enable), `/questrade-get-balances`, `/questrade-get-positions`, `/questrade-sync-portfolio` (balances, holdings and executed trades into SQLite), `/questrade-refresh-prices`, `/questrade-activities` (dividends, deposits, cash-flow ledger), `/questrade-order-draft` (orders approved on your phone), `/questrade-deposit-funds` (Interac e-Transfer deposits, recorded as contributions), `/norberts-gambit` (CAD/USD conversion via DLR.TO/DLR.U)

---

## 💻 Core Application: Investment Screener

The `investment_screener/` app is the web-based financial analysis dashboard.

### Tech Stack

* **Frontend**: React 19, Vite, Tailwind CSS 4.0


* **Backend**: Node.js (Express), TypeScript, SQLite (WAL mode indexing via `better-sqlite3`)


* **Analytical Engine**: Python 3.11 Utility Layer (`py_services/`) leveraging standard `sqlite3` for local indexing and `yfinance` for math, validation, and historical financials.



### Key Features

* **Portfolio Summary & Table**: Live views synced from TV CDP.


* **Market Heatmap**: Real-time sector performance mapping.


* **Stock Analysis & Metrics**: Deep-dive AI Expert Thesis and 15+ fundamental metrics.


* **Valuation Modeler**: Interactive Bear/Base/Bull scenario modeling with automatic persistence to projection JSON files.


* **Trade Log**: Real-time mirror of the TradingView order panel via CDP.



### Querying the SQLite Databases

The backend is **SQLite-first** as of the Domain Data Model v3.2 migration program (Waves 0-5E,
closed by Wave 6, 2026-07-25 — see `docs/superpowers/status/wave6-program-closure-report.md` for
the full closure report, KPI rollup, and retained-JSON rationale). Two gitignored, self-creating
SQLite files under `investment_screener/backend/data/`:

| File | Domain | Key tables |
| --- | --- | --- |
| `domain_model.sqlite` | Investment/target/watchlist/pillars/price-levels/notes/alerts/projections/trade-log/orders/cash-flow/portfolio-policy (Waves 0-5E) | `account`, `strategy_pillar`, `sub_strategy`, `investment`, `investment_price`, `account_investment`, `price_level_set`, `price_level_tier`, `alert`, `investment_note`, `projection_version`, `projection_scenario`, `trade_log_entry`, `order_execution`, `cash_flow`, `cash_flow_baseline`, `portfolio_policy`, `broker_exchange_rate`, `broker_reported_total` (20 tables total) |
| `intelligence.sqlite` | Research/TA-sweep/prediction event ledger | `instrument`, `ledger_checkpoint`, `intelligence_event` (+ FTS5 virtual table), queried via `py_services/intelligence/` |

Both are **gitignored** — a fresh checkout won't have them. Rebuild `domain_model.sqlite` via:

```bash
cd investment_screener/backend/py_services
python3 -m domain_model.migrate_projections_to_sqlite --write
python3 -m domain_model.migrate_target_portfolio_to_sqlite --write

```

Common read-only inspection commands (never open a write transaction by hand — always go through the `py_services/domain_model/` repository layer for real writes):

```bash
# Open a shell against the domain model
sqlite3 investment_screener/backend/data/domain_model.sqlite

# List all tables
sqlite3 investment_screener/backend/data/domain_model.sqlite ".tables"

# Row counts across every table
sqlite3 investment_screener/backend/data/domain_model.sqlite \
  "SELECT 'investment', COUNT(*) FROM investment
   UNION ALL SELECT 'projection_version', COUNT(*) FROM projection_version
   UNION ALL SELECT 'alert', COUNT(*) FROM alert;"

# Look up one ticker's full row
sqlite3 -header -column investment_screener/backend/data/domain_model.sqlite \
  "SELECT * FROM investment WHERE symbol = 'NVDA';"

# Same pattern for the research/event ledger
sqlite3 investment_screener/backend/data/intelligence.sqlite ".tables"

```

`domain_model.sqlite` is the sole source of truth for portfolio holdings, thesis targets, pillars, price levels,
standing decisions, trades, cash flows and thesis breakers (ADR-038). Research and analysis live in the ledger
`intelligence.sqlite`. A test (`test_no_retired_file_access`) fails if any code or document reads or writes a
file in place of these databases.

---

## 🔌 How to Install Plugins

The four project plugins install with [APM](https://github.com/microsoft/apm) (verified with APM 0.33.0; see `INIT_AGENTS.md` Step 2a for installing APM). The root `apm.yml` lists them, so from the repository root:

```bash
apm install --target agent-skills
```

This deploys the skills into `.agents/skills/` and writes `apm.lock.yaml`. Questrade also declares an MCP server; `apm` reports that the `agent-skills` target cannot configure it (the skills still install), so set the Questrade MCP up with `/questrade-setup`. Never edit the deployed copies; change the plugin source and reinstall.

The shared library `agent-plugins-skills` (Agentic OS substrate, developer skills) is a separate package set installed **globally** with APM from your own clone, not through this repo's `apm.yml`. `INIT_AGENTS.md` Step 2b shows how to check it and install it; the library's own `INSTALL.md` is the full guide.

---

## 🔐 External Integrations & Fallbacks

### TradingView Premium (Primary Layer)

* **Required for real-time market data and live order execution.** The toolkit integrates directly with TradingView Desktop (running with `--remote-debugging-port=9222`).


* **Free/Essential Plans**: yfinance remains the fallback source for delayed data (15-20 min).



---

## 🛠 Architecture & Development Rules

> 📖 **Deep Dive**: For a comprehensive system map, context diagrams, and component interactions, read the **[Architecture Overview](https://www.google.com/search?q=docs/architecture/README.md)**.
> 
> 

### The Iron Law: Test-Driven Development (TDD)

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.

```

* The primary test harnesses must shell out via subprocess to exactly mirror the execution paths of the AI plugins and the Node Express bridge.


* Mocking is strictly prohibited on critical runtime paths.



### Agent Calculation Policy

* Never perform financial calculations inline (bash/python snippets).


* Always use or create versioned `.py` scripts in `investment_screener/backend/py_services/`.



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
| --- | --- | --- |
| **tradingview-mcp** (tradesdontlie) | [https://github.com/tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) | The most complete CDP-based TradingView automation library available. 5,000+ lines, 15+ command namespaces. Its `pine.js` uses **React fiber tree traversal** (`__reactFiber` prefix) to locate Monaco editor internals — more resilient than CSS selectors alone. No live broker order execution.

 |
| **tradingview-mcp** (atilaahmettaner) | [https://github.com/atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp) | TradingView screener/scanner using the `tradingview-screener` Python library (REST API). 30+ tools for market scanning and symbol filtering. No CDP, no live orders.

 |

**Our key architectural difference:** Both reference projects are chart analysis and research tools. InvestmentToolkit is a **live broker execution layer** — it navigates TradingView's built-in connected broker panel via CDP to place, modify, and cancel real orders, with 3-step HITL confirmation, safety gates (stale portfolio exit 4, size cap exit 3), multi-account support, `tvOrderId` tracking, and automatic portfolio sync after fills. Pine Script injection (via `/pine-inject`) uses the React fiber traversal technique from tradesdontlie's implementation to locate Monaco editor internals without relying on fragile CSS class selectors.

### AI Agent Infrastructure

* **[browser-use/browser-harness](https://github.com/browser-use/browser-harness)** — Inspired our approach to self-healing, self-evolving skills and direct CDP automation. By allowing the agent to write its own helpers and domain skills when it encounters issues or gaps, the system continuously improves itself during execution.


* **[orba/superpowers](https://www.google.com/search?q=https://github.com/orba/superpowers)** — The TDD (Iron Law: no production code without a failing test first), brainstorming, and sub-agent driven development skills used throughout this project come from the superpowers plugin library. These skills enforce rigorous Red-Green-Refactor discipline and orchestrate parallel multi-agent task execution.


* **[richfrem/agent-plugins-skills](https://github.com/richfrem/agent-plugins-skills)** — The Exploration Workflow (4-phase: Discovery Planning → Visual Blueprinting → Prototyping → Handoff & Specs) and all project-local AI agent plugins and skills are organized and distributed through this repository.



---

## ⚖️ Legal & Financial Disclaimer

> **IMPORTANT DISCLAIMER:**
> **InvestmentToolkit is strictly an analytical and educational suite.** It does **not** provide financial, investment, tax, or legal advice. 
> - All valuation models (DCF scenarios), technical indicators, and AI agent outputs are **informational and advisory only**.
> - Past performance and quantitative projections do not guarantee future returns.
> - The software is provided "as is", without warranty of any kind. You are solely responsible for your own investment decisions and any broker order executions.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

*Data and desktop integration from TradingView are subject to their Terms of Use: [https://www.tradingview.com/policies/](https://www.tradingview.com/policies/)*