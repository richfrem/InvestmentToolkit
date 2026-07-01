# Architecture Overview

Living reference for InvestmentToolkit. Update when structure, data flows, or integrations change. One copy — tool-agnostic.

---

## 1. Project Structure

```
InvestmentToolkit/                         ← repo root
├── run_investment_toolkit.py              ← unified startup (venv + npm + TV launch)
├── run_tests.py                           ← T0 compile gate + T0.5 bridge smoke
├── requirements.in / requirements.txt    ← Python deps (pip-compile managed)
├── symlinks.json                          ← cross-platform symlink manifest
│
├── investment_screener/                   ← npm workspace root
│   ├── frontend/                          ← React 19 + Vite + Tailwind CSS 4.0 (port 5173)
│   │   └── src/
│   │       ├── components/               ← shared UI (AIAnalysisModal, TradeButtons, etc.)
│   │       ├── pages/                    ← Dashboard, StockAnalysis, TradeLog, Portfolio
│   │       └── services/api.ts           ← typed fetch wrapper for backend API
│   └── backend/                          ← Node.js Express API (port 3001)
│       ├── src/
│       │   ├── index.ts                  ← Express entry point, route registration
│       │   ├── routes/                   ← /api/portfolio, /api/stock/:ticker, /api/ta-sweep
│       │   ├── services/                 ← QuestradeSyncService.ts (spawns Python)
│       │   └── utils/                    ← zod-schemas.ts, QuestradeAPIClient.py
│       ├── py_services/                  ← canonical Python scripts (never inline)
│       │   ├── portfolio_action.py       ← drift + DCF → BUY/HOLD/SELL actions
│       │   ├── fetch_financials.py       ← yfinance raw data fetch
│       │   ├── dcf_scenarios.py          ← DCF math (bear/base/bull)
│       │   └── extract_portfolio_symbols.py
│       ├── src/QuestradeDataEngine.py    ← OAuth2 token engine + brokerage data
│       ├── data/
│       │   ├── portfolio.json            ← live positions (gitignored)
│       │   ├── trade-log.json            ← order history (gitignored)
│       │   ├── target-portfolio.json     ← thesis + target weights + standingDecisions
│       │   ├── projections/              ← per-ticker DCF + aiThesis JSON
│       │   ├── etf_analysis/             ← ETF analysis results (versioned)
│       │   ├── theses/                   ← investment_thesis.md + sub_strategies/
│       │   └── ta-sweep-results.json     ← latest batch TA output
│       └── tests/
│           ├── fixtures/                 ← test portfolio + target JSON
│           ├── py_services/              ← unit tests for Python services
│           │   └── test_math_parity.py
│           ├── validate_all_projections.py
│           └── api/ services/ utils/
│
├── tradingview-cdp/                       ← standalone CDP engine (npm ci once)
│   ├── cli.js                            ← CLI entry: `node tradingview-cdp/cli.js <cmd>`
│   ├── core/
│   │   ├── trading.js                    ← order placement / cancellation / modification
│   │   ├── broker_data.js                ← account balances, positions snapshot
│   │   ├── data.js                       ← chart quotes (active chart only)
│   │   ├── pine.js                       ← Pine Script inject / save / read (Monaco fiber)
│   │   ├── chart.js                      ← symbol, timeframe, indicators, Data Window
│   │   └── sweep.js                      ← batch TA Data Window reads
│   └── package.json
│
├── plugins/                               ← modular AI agent plugins
│   ├── stock-valuation/                  ← DCF valuation + research sweep
│   │   └── skills/stock_valuation/scripts/
│   │       └── validate_projection.py
│   ├── portfolio-advisor/                ← drift monitor, triage, rebalance, Grok sweeps
│   │   ├── agents/                       ← daily-loop-agent.md, weekly-review-agent.md
│   │   ├── scripts/                      ← daily_brief.py, update_targets.py, portfolio_action.py
│   │   └── assets/templates/            ← daily_sweep.md.template, weekly_sweep.md.template
│   ├── tradingview/                      ← CDP automation skills
│   │   ├── scripts/                      ← tv_client.py (CDP bridge), tv_launch.py,
│   │   │                                    ta_sweep_batch.py, fetch_broker_data.py, place_order.py
│   │   ├── assets/pinescript-indicators/ ← ai-ta-levels.pine, community-reference/
│   │   └── tests/                        ← test_pine_advisor_skill.py, tv_test_harness.py
│   ├── toolkit-manager/                  ← onboarding, startup orchestration
│   ├── etf-analysis/                     ← ETF holdings alignment + dual-write
│   └── stock-valuation/
│
├── .agents/                               ← multi-tool skill/agent store (Claude, Gemini, Copilot)
│   ├── skills/                           ← project-local skills
│   └── agents/                           ← sub-agent definitions
│
├── .agent/rules/                          ← mandatory agent behaviour policies
│   ├── self-evolution-policy.md
│   ├── test-driven-development.md
│   ├── no-inline-python.md
│   ├── coding-conventions.md
│   ├── dependency-management.md
│   └── plugin-architecture.md
│
├── docs/architecture/                     ← ADRs and sequence diagrams
├── temp/                                  ← gitignored scratch space (never /tmp/)
└── context/events.jsonl                  ← agent self-evolution event log
```

---

## 2. High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  User / AI Agent                                                │
└───────────┬─────────────────────────────┬───────────────────────┘
            │ browser                     │ CLI skill / agent
            ▼                             ▼
┌─────────────────────┐       ┌──────────────────────────────────┐
│  React 19 Frontend  │       │  AI Agent Skills (.agents/)      │
│  Vite · port 5173   │       │  Claude Code / Gemini / Copilot  │
└─────────┬───────────┘       └──────────────┬───────────────────┘
          │ /api/* (Vite proxy)               │ subprocess / Bash
          ▼                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Express Backend  ·  Node.js / TypeScript  ·  port 3001        │
│                                                                 │
│  Routes: /api/portfolio  /api/stock/:ticker  /api/ta-sweep     │
│  QuestradeSyncService.ts — spawns Python via child_process     │
└──────┬────────────────────────────┬────────────────────────────┘
       │ spawn                      │ spawn
       ▼                            ▼
┌──────────────────┐    ┌──────────────────────────────────────┐
│  py_services/    │    │  QuestradeDataEngine.py              │
│  fetch_financials│    │  OAuth2 token rotation               │
│  dcf_scenarios   │    │  AES-256-GCM · macOS Keychain        │
│  portfolio_action│    └──────────────┬───────────────────────┘
└──────┬───────────┘                   │ REST
       │ HTTP                          ▼
       ▼                    ┌──────────────────────┐
┌──────────────────┐        │  Questrade API       │
│  yfinance        │        │  (read-only positions│
│  (market data)   │        │   + account data)    │
└──────────────────┘        └──────────────────────┘

─────────────────── TradingView CDP Layer ────────────────────────

┌──────────────────────────────────────────────────────────────┐
│  TradingView Desktop  (macOS app, --remote-debugging-port=9222)│
└──────────────────┬───────────────────────────────────────────┘
                   │ Chrome DevTools Protocol (WebSocket)
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  tradingview-cdp/  (Node.js CDP engine)                      │
│  cli.js · core/{chart,trading,pine,broker_data,sweep}.js     │
└──────────────────┬───────────────────────────────────────────┘
                   │ subprocess
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  plugins/tradingview/scripts/tv_client.py                    │
│  (Python bridge — locates CLI via TV_CDP_DIR or walk-up)    │
│  Used by: ta_sweep_batch.py, place_order.py, fetch_broker_  │
│           data.py, tv_pine_inject.py, tv_pine_manager.py    │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Core Components

### 3.1. Frontend — React Dashboard
**Technologies:** React 19, Vite, Tailwind CSS 4.0, TypeScript  
**Port:** 5173 (dev), served via Vite proxy for `/api/*`  
**Key pages:**
- `Dashboard.tsx` — portfolio heatmap, AI thesis panel, TA sweep results
- `StockAnalysis.tsx` — per-ticker DCF projections, thesis, trade buttons
- `TradeLog.tsx` — order history (Working / Inactive / Planned / Filled / Cancelled tabs)
- `Portfolio.tsx` — drift vs. target weights

**State:** No global store — pages fetch from `/api/*` on mount. `portfolio.json` is the source of truth for positions; `target-portfolio.json` for thesis + targets.

### 3.2. Backend — Express API
**Technologies:** Node.js, Express, TypeScript (compiled to `dist/`), Zod validation  
**Port:** 3001  
**Key routes:**
- `GET /api/portfolio` — reads `portfolio.json` + `target-portfolio.json`, computes drift
- `GET /api/stock/:ticker` — reads `projections/{TICKER}.json` or `etf_analysis/{TICKER}.json`
- `POST /api/portfolio/sync-tv/apply` — applies TV broker snapshot to `portfolio.json`
- `POST /api/questrade/seed` — seeds Questrade token (does OAuth exchange internally)
- `GET /api/ta-sweep/results` — reads `ta-sweep-results.json`

**Python bridge pattern:** `QuestradeSyncService.ts` spawns Python scripts via `child_process.spawn`. Scripts live in `src/` (NOT copied to `dist/`); always reference via `path.resolve(__dirname, '../src/script.py')`.

### 3.3. Python Services Layer
**Location:** `investment_screener/backend/py_services/`  
**Rule:** No inline calculations — all financial math lives in versioned scripts here.

| Script | Purpose |
|--------|---------|
| `portfolio_action.py` | Computes drift + DCF-gated actions (BUY/HOLD/SELL/EXIT etc.) |
| `fetch_financials.py` | Fetches raw yfinance data for a ticker |
| `dcf_scenarios.py` | Bear/Base/Bull DCF math, outputs weighted fair value |
| `extract_portfolio_symbols.py` | Reads `temp/stocks.xlsx`, outputs symbols JSON |

### 3.4. TradingView CDP Engine
**Location:** `tradingview-cdp/` (standalone Node.js package, `npm ci` once)  
**Entry:** `node tradingview-cdp/cli.js <namespace> <command> [args]`  
**Python bridge:** `plugins/tradingview/scripts/tv_client.py` — locates the CLI via `TV_CDP_DIR` env var or 10-level directory walk-up. Import: `from tv_client import TV_CLI, tv_call, TV_NODE_DIR`

**Key capabilities:**
- `chart symbol/timeframe/addIndicator/openDataWindow/read` — chart control
- `pine inject/save/read` — Pine Script v6 authoring (Monaco fiber traversal)
- `trading placeOrder/cancelOrder/modifyOrder/listOpenOrders` — live broker execution
- `brokerData getAccounts/getPositions/getAccountTotals` — portfolio sync
- `sweep readDataWindow` — batch TA reads across all holdings

**Critical rule:** All Node.js CDP snippets must end with `.then(() => process.exit(0)).catch(() => process.exit(1))` — otherwise the WebSocket holds the event loop open indefinitely.

### 3.5. AI Agent Plugin Layer
**Location:** `plugins/` (canonical source), `.agents/` (multi-tool skill store)  
**Convention:** Each plugin has `skills/`, `agents/`, `scripts/`, `tests/`, `references/`.

| Plugin | Key Skills | Key Scripts |
|--------|-----------|-------------|
| `portfolio-advisor` | `/daily`, `/weekly-review`, `/run-advisor`, `/x-news-sweep`, `/rebalance` | `daily_brief.py`, `update_targets.py` |
| `stock-valuation` | `/evaluate-stock`, `/research-stock` | `validate_projection.py` |
| `tradingview` | `/place-order`, `/tv-ta-deep`, `/tv-portfolio-sync`, `/pine-inject` | `ta_sweep_batch.py`, `place_order.py`, `tv_launch.py` |
| `etf-analysis` | `/analyze-etf` | `persist_etf_analysis.py` |
| `toolkit-manager` | `/start-screener`, `/setup-questrade` | — |

---

## 4. Data Stores

All persistence is flat-file JSON (no database). No server infrastructure required.

| File / Dir | Type | Contents | Gitignored? |
|-----------|------|----------|-------------|
| `backend/data/portfolio.json` | JSON | Live positions from TV broker sync | Yes |
| `backend/data/target-portfolio.json` | JSON | Thesis, pillar targets, per-ticker standingDecision, targetWeight, targetEntryPrice | No |
| `backend/data/projections/*.json` | JSON | DCF Bear/Base/Bull, aiThesis action/rationale, analyticsLog | No |
| `backend/data/etf_analysis/*.json` | JSON | ETF holdings analysis (versioned array) | No |
| `backend/data/trade-log.json` | JSON | Order history: suggested → submitted → inactive/filled/cancelled | Yes |
| `backend/data/ta-sweep-results.json` | JSON | Latest batch TA sweep (RSI, ADX, Vol Bias, Squeeze per ticker) | No |
| `backend/.questrade_cache` | Binary | AES-256-GCM encrypted Questrade refresh token | Yes |
| `backend/data/theses/` | Markdown + JSON | Investment thesis narrative + sub-strategies | No |
| `plugins/portfolio-advisor/assets/templates/` | Markdown | Grok sweep prompt templates (daily + weekly) | No |
| `plugins/portfolio-advisor/references/evolution-log.md` | Markdown | Daily session log (scores, overrides, tool failures) | No |
| `temp/` | Various | Scratch space for scripts (never /tmp/) | Yes |

**`aiThesis.action` vocabulary:** `INITIATE | ACCUMULATE | MAINTAIN | TRIM | EXIT | WATCHLIST`  
(DCF valuation signal is separate: `analyticsLog.valuationAction` = `BUY | HOLD | SELL`)

---

## 5. External Integrations

| Service | Purpose | Method |
|---------|---------|--------|
| **yfinance** (Python) | Market data: OHLCV, financials, balance sheet, income statement | Python library — `fetch_financials.py` |
| **Questrade API** | Brokerage account positions, balances (read-only via personal token) | OAuth2 REST — `QuestradeDataEngine.py` |
| **TradingView Desktop** | Live chart prices, order execution, broker panel sync | Chrome DevTools Protocol (WebSocket port 9222) |
| **X.com / Grok** | News sweep and portfolio analysis | Manual paste workflow — agent generates prompt, user pastes to grok.com |
| **SEC EDGAR** | 13F institutional filing downloads | REST (`/13f-tracker` skill) |

---

## 6. Deployment & Infrastructure

This is a **local-only** personal investment toolkit — no cloud infrastructure.

| Concern | Implementation |
|---------|---------------|
| Runtime environment | macOS (Apple Silicon) |
| Python venv | Created by `run_investment_toolkit.py`, installed from `requirements.txt` |
| Node.js | System install; npm workspaces via `investment_screener/` |
| TradingView CDP | `tradingview-cdp/` node_modules via `npm ci` (one-time) |
| Startup | `python3 run_investment_toolkit.py` — orchestrates venv, npm, backend, frontend, TV Desktop |
| Process model | Backend: `node dist/index.js` (requires rebuild on change). Frontend: Vite HMR. |
| Ports | Frontend: 5173, Backend: 3001, TradingView CDP: 9222 |

---

## 7. Security

| Concern | Implementation |
|---------|---------------|
| Questrade token storage | AES-256-GCM encryption, key in macOS Keychain via `keyring` library. Binary cache at `backend/.questrade_cache` (gitignored). |
| Order execution | Human-in-the-loop (HITL) at every trade: preflight card → explicit CONFIRM before CDP submits. |
| API keys / secrets | `.env` at repo root (gitignored). `.env.example` is tracked. |
| Scope | Personal local tool — no network exposure, no auth layer on Express. |
| Token rotation | Questrade refresh tokens are single-use. `QuestradeDataEngine.py` auto-rotates on every sync. On `400` error: token expired, re-seed required. |

---

## 8. Development & Testing

**Local setup:**
```bash
python3 run_investment_toolkit.py   # first run bootstraps everything
```

**Individual service commands** (from `investment_screener/`):
```bash
npm run dev -w backend      # port 3001 with ts-node-dev hot reload
npm run dev -w frontend     # port 5173 with Vite HMR
npm run build -w backend    # compile TypeScript → dist/
npm run lint -w frontend
```

**Test runner:**
```bash
python3 run_tests.py            # T0 compile gate + T0.5 bridge smoke
python3 run_tests.py --t0-only  # compile + syntax only
pytest investment_screener/backend/tests/    # unit tests
pytest plugins/tradingview/tests/            # TV CDP unit tests
```

**Test locations:**
| Area | Path |
|------|------|
| Python py_services | `investment_screener/backend/tests/py_services/` |
| Express routes | `investment_screener/backend/tests/api/` |
| TV CDP | `plugins/tradingview/tests/` |
| Plugin scripts | `plugins/<plugin>/tests/` |
| React | `investment_screener/frontend/tests/` |

**Code quality:** ESLint (frontend), Pyright (Python), `python3 -m py_compile` in T0 gate.  
**Dependency management:** Python — edit `requirements.in` → `pip-compile requirements.in -o requirements.txt`. Never manual `pip install`.

---

## 9. Key Architectural Decisions

| ADR | Decision |
|-----|---------|
| ADR-024 | CDP engine extracted to `tradingview-cdp/` root ("Thin Skill + Thick Engine") — plugins import via `tv_client.py`, never hardcode paths |
| ADR-dcf-calculator | DCF math lives in `dcf_scenarios.py`, never inlined. One script, one bug surface. |
| No database | All state in JSON files. Simplicity > scalability for a single-user local tool. |
| Standing Decision anchor | `standingDecision` in `target-portfolio.json` is the source of truth. A fresh DCF run never silently overrides it — only material delta (>15% FV change) triggers a conflict flag. |
| Symlink policy | Cross-plugin file sharing via `symlinks.json` + `symlink_manager.py`. Never raw `ln -s`. |

---

## 10. Project Identification

**Project:** InvestmentToolkit  
**Owner:** richfrem  
**Primary AI context files:** `.claude/CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`  
**Last updated:** 2026-07-01

---

## 11. Glossary

| Term | Definition |
|------|-----------|
| CDP | Chrome DevTools Protocol — WebSocket API used to automate TradingView Desktop |
| DCF | Discounted Cash Flow — valuation model producing Bear/Base/Bull fair value per share |
| `standingDecision` | User-confirmed buy/sell/hold decision stored in `target-portfolio.json`. Not overridden by automated DCF runs. |
| `targetEntryPrice` | GTC limit price for accumulating a position; sourced from TA support + DCF margin of safety |
| `aiThesis.action` | Portfolio-level recommendation (`INITIATE/ACCUMULATE/MAINTAIN/TRIM/EXIT/WATCHLIST`) — distinct from the raw DCF signal |
| PSU-U.TO | Purpose US Cash ETF (~$100 USD/share on TSX) — the idle cash parking vehicle. All new purchases are funded by trimming this. |
| HITL | Human-in-the-loop — mandatory confirmation step before any order is submitted to the broker |
| T0 gate | Compile + syntax + path regression checks (`run_tests.py`) — must pass before any commit |
| T0.5 gate | Bridge smoke test — verifies `portfolio_action.py` returns valid JSON via symlink |
| Grok sweep | Portfolio news analysis workflow: agent generates prompt → user pastes to x.com/i/grok → pastes response back → agent gates against DCF + 8 hard gates |
| Sweep template | `daily_sweep.md.template` / `weekly_sweep.md.template` — Grok prompt templates; must be updated when thesis/pillars change |
| py_services | Canonical Python scripts in `investment_screener/backend/py_services/`. All financial calculations go here — never inline. |
