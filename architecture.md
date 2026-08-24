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
│       │   ├── services/                 ← BrokerSyncService.ts (TV CDP waterfall sync)
│       │   └── utils/                    ← zod-schemas.ts, tickerAliases.ts
│       ├── py_services/                  ← canonical Python scripts (never inline)
│       │   ├── portfolio_action.py       ← drift + DCF → BUY/HOLD/SELL actions
│       │   ├── fetch_financials.py       ← yfinance raw data fetch
│       │   ├── dcf_scenarios.py          ← DCF math (bear/base/bull)
│       │   ├── record_intelligence_event.py ← canonical event ledger tool
│       │   └── extract_portfolio_symbols.py
│       ├── data/
│       │   ├── domain_model.sqlite       ← investment/pillar/price-level/projection/trade/
│       │   │                                policy tables (gitignored, self-creating; see §4)
│       │   ├── intelligence.sqlite       ← research/TA-sweep/prediction event ledger (gitignored,
│       │   │                                self-creating)
│       │   ├── portfolio.json            ← live positions (gitignored, retained exception)
│       │   ├── trade-log.json            ← order history (gitignored, retained exception)
│       │   ├── theses/target-portfolio.json ← thesis + target weights + standingDecisions
│       │   │                                (retained exception — not yet fully migrated,
│       │   │                                see Wave 6 report)
│       │   ├── projections/              ← per-ticker DCF + aiThesis JSON (retained exception)
│       │   ├── etf_analysis/             ← ETF analysis results (versioned)
│       │   └── theses/                   ← investment_thesis.md + sub_strategies/
│       └── tests/
│           ├── fixtures/                 ← test portfolio + target JSON
│           ├── py_services/              ← unit tests for Python services
│           │   └── test_math_parity.py
│           ├── validate_all_projections.py
│           └── api/ services/ utils/
│
├── tradingview-cdp/                       ← standalone CDP engine (npm ci once)
│   ├── cli.js                            ← CLI entry: `node tradingview-cdp/cli.js <cmd>`
│   ├── README.md                         ← Engine setup, architecture, and CLI documentation
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
│   │   ├── agents/                       ← daily-loop-agent.md, portfolio-advisor-orchestrator.md
│   │   ├── skills/                       ← stock-intake, portfolio-coverage-audit, weekly-review, etc.
│   │   ├── scripts/                      ← audit_coverage.py, manage_watchlist.py, daily_brief.py
│   │   └── assets/templates/            ← daily_sweep.md.template, weekly_sweep.md.template
│   ├── tradingview/                      ← CDP automation skills
│   │   ├── agents/                       ← ta-guide.md
│   │   ├── skills/                       ← tv-onboarding, tv-price-refresh, tv-portfolio-sync, etc.
│   │   ├── scripts/                      ← tv_client.py, ta_sweep_batch.py, fetch_broker_data.py
│   │   ├── assets/pinescript-indicators/ ← ai-ta-levels.pine, community-reference/
│   │   └── tests/                        ← test_pine_advisor_skill.py, tv_test_harness.py
│   ├── toolkit-manager/                  ← onboarding, startup orchestration
│   │   └── skills/                       ← toolkit-onboarding, run-screener
│   └── etf-analysis/                     ← ETF holdings alignment + dual-write
│       └── skills/                       ← etf_analysis
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
│  BrokerSyncService.ts — TV CDP waterfall sync orchestrator     │
└──────┬──────────────────────────────────────────────────────────┘
       │ spawn
       ▼
┌──────────────────┐
│  py_services/    │
│  fetch_financials│
│  dcf_scenarios   │
│  portfolio_action│
└──────┬───────────┘
       │ HTTP
       ▼
┌──────────────────┐
│  yfinance        │
│  (market data)   │
└──────────────────┘

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
│           data.py, tv_pine_inject.py, tv_pine_manager.py,   │
│           tv_thesis_overlay.py, tv_create_alerts.py         │
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

**State:** No global store — pages fetch from `/api/*` on mount. `portfolio.json` is the source of truth for positions (backed by `domain_model.sqlite`'s `account_investment` table); `target-portfolio.json` for thesis + targets (retained JSON exception, see §4).

### 3.2. Backend — Express API
**Technologies:** Node.js, Express, TypeScript (compiled to `dist/`), Zod validation  
**Port:** 3001  
**Key routes:**
- `GET /api/portfolio` — reads `portfolio.json` + `target-portfolio.json`, computes drift
- `GET /api/stock/:ticker` — reads `projections/{TICKER}.json` or `etf_analysis/{TICKER}.json`
- `POST /api/portfolio/sync-tv/apply` — applies TV broker snapshot to `portfolio.json`
- `GET /api/ta-sweep/results` — reads `intelligence.sqlite`'s TA-sweep events (formerly `ta-sweep-results.json`, migrated Wave 5B)

**Python bridge pattern:** `bridge.ts` spawns Python scripts via `child_process.spawn`. Scripts live in `src/` (NOT copied to `dist/`); always reference via `path.resolve(__dirname, '../src/script.py')`.

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
| `toolkit-manager` | `/start-screener` | — |

---

## 4. Data Stores

**SQLite-first as of the Domain Data Model v3.2 migration (Waves 0-5E, closed by Wave 6,
2026-07-25 — see `docs/superpowers/status/wave6-program-closure-report.md`).** Most domains
(investment/pillar/price-level/projection/trade/portfolio-policy, research/TA-sweep/predictions)
now live in two gitignored, self-creating SQLite files. A small number of JSON files remain as
deliberate, documented retained exceptions — not something to migrate away casually — each with a
completed Retained-JSON Rationale Bar in the Wave 6 report.

| Database | Contents | Repository layer |
|---|---|---|
| `backend/data/domain_model.sqlite` | `account`, `strategy_pillar`, `sub_strategy`, `investment`, `investment_price`, `account_investment`, `price_level_set`, `price_level_tier`, `alert`, `investment_note`, `projection_version`, `projection_scenario`, `trade_log_entry`, `order_execution`, `cash_flow`, `cash_flow_baseline`, `portfolio_policy`, `broker_exchange_rate`, `broker_reported_total` (20 tables) | `py_services/domain_model/*_repository.py`, TS mirrors in `src/services/`/`src/repositories/` |
| `backend/data/intelligence.sqlite` | `instrument`, `ledger_checkpoint`, `intelligence_event` (+ FTS5 virtual table) | `py_services/intelligence/event_repository.py`/`event_store.py` |

Both are gitignored, private data files created automatically the first time a script calling
`initialize_db()` runs — see `docs/architecture/domain-data-model.md` and
`docs/architecture/supplementary-domain-schemas.md` for full DDL and rationale.

**Retained JSON exceptions** (each formally justified in the Wave 6 report's Retained-JSON
Rationale Bar, not a generic "out of scope"):

| File / Dir | Type | Contents | Gitignored? |
|-----------|------|----------|-------------|
| `backend/data/portfolio.json` | JSON | Live positions from TV broker sync | Yes |
| `backend/data/theses/target-portfolio.json` | JSON | Thesis, pillar targets, per-ticker standingDecision, targetWeight, targetEntryPrice — most fields have no remaining technical migration barrier; `changeLog`/`thesisBreakers` are the two fields needing new schema before full retirement | No |
| `backend/data/projections/*.json` | JSON | DCF Bear/Base/Bull, aiThesis action/rationale, analyticsLog (also mirrored into `projection_version`/`projection_scenario`) | No |
| `backend/data/thesis_breaker_state.json` | JSON | Evaluated thesis-breaker state (definitions + evaluation history) — live read/write path for 5 real consumers, not derivable from `investment.thesis_breaker_status` alone | No |
| `backend/data/etf_analysis/*.json` | JSON | ETF holdings analysis (versioned array) | No |
| `backend/data/trade-log.json` | JSON | Order history: suggested → submitted → inactive/filled/cancelled | Yes |
| `backend/data/cash_flows.json` | JSON | Deposits/withdrawals (also mirrored into `cash_flow`/`cash_flow_baseline`) | Yes |
| `backend/data/theses/` | Markdown + JSON | Investment thesis narrative + sub-strategies | No |
| `plugins/portfolio-advisor/assets/templates/` | Markdown | Grok sweep prompt templates (daily + weekly) | No |
| `plugins/portfolio-advisor/references/evolution-log.md` | Markdown | Daily session log (scores, overrides, tool failures) | No |
| `temp/` | Various | Scratch space for scripts (never /tmp/) | Yes |

**Migrated/archived** (formerly live JSON, now SQLite-backed; superseded files under
`./ARCHIVE/`): `ta-sweep-results.json` (Wave 5B), `predictions.jsonl` (Wave 5D),
`account_policy.json` (Wave 5E), `tradingview_alerts_actual.json` and `watchlist.json` (Wave 2),
82 per-ticker projection files migrated in Wave 1 (originals retained, see above).

**`aiThesis.action` vocabulary:** `INITIATE | ACCUMULATE | MAINTAIN | TRIM | EXIT | WATCHLIST`  
(DCF valuation signal is separate: `analyticsLog.valuationAction` = `BUY | HOLD | SELL`)

---

## 5. External Integrations

| Service | Purpose | Method |
|---------|---------|--------|
| **yfinance** (Python) | Market data: OHLCV, financials, balance sheet, income statement | Python library — `fetch_financials.py` |
| **TradingView Desktop** | Live chart prices, order execution, broker panel sync (broker: Broker) | Chrome DevTools Protocol (WebSocket port 9222) |
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
| Order execution | Human-in-the-loop (HITL) at every trade: preflight card → explicit CONFIRM before CDP submits. |
| API keys / secrets | `.env` at repo root (gitignored). `.env.example` is tracked. |
| Scope | Personal local tool — no network exposure, no auth layer on Express. |

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
| ADR-026/027/028 | Intelligence data layer: `observations.jsonl` (authority, ADR-026) → `intelligence.sqlite` (replayable read model, FTS5, SQLite selection rationale in ADR-027) → generated `research/{TICKER}.summary.md` views, behind a shared `py_services/intelligence/` repository layer (ADR-028). See `ADRs/026_canonical_research_consolidation_and_unified_ingest.md`, `ADRs/027_sqlite_database_selection.md`, `ADRs/028_shared_intelligence_data_access_layer.md`. |
| ADR-029/030 | Domain Data Model v3.2: persistence domain rationalization and gated migration from flat JSON to `domain_model.sqlite` (ADR-029, Waves 0-5E, closed by Wave 6 program-closure pass) — "store facts, compute aggregates" (ADR-030, e.g. portfolio totals always computed live from `account_investment`/`investment_price`, never stored). See `ADRs/029_persistence_domain_rationalization_and_retirement_gated_migration.md`, `ADRs/030_portfolio_totals_computed_not_stored.md`, and `docs/superpowers/status/wave6-program-closure-report.md` for the final state and retained-JSON rationale. |
| ADR-dcf-calculator | DCF math lives in `dcf_scenarios.py`, never inlined. One script, one bug surface. |
| SQLite-first, JSON by exception | Most domains live in `domain_model.sqlite`/`intelligence.sqlite` (gitignored, self-creating). A small, explicitly documented set of JSON files remain as retained exceptions (see §4) — not a permanent hybrid, per ADR-029's pivot objective. |
| Standing Decision anchor | `standingDecision` in `target-portfolio.json` is the source of truth (also mirrored in `investment.standing_decision_*` columns). A fresh DCF run never silently overrides it — only material delta (>15% FV change) triggers a conflict flag. |
| Symlink policy | Cross-plugin file sharing via `symlinks.json` + `symlink_manager.py`. Never raw `ln -s`. |

---

## 10. Project Identification

**Project:** InvestmentToolkit  
**Owner:** richfrem  
**Primary AI context files:** `.claude/CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`  
**Last updated:** 2026-07-25 (Wave 6 — Domain Data Model v3.2 program closure)

---

## 11. Glossary

| Term | Definition |
|------|-----------|
| CDP | Chrome DevTools Protocol — WebSocket API used to automate TradingView Desktop |
| DCF | Discounted Cash Flow — valuation model producing Bear/Base/Bull fair value per share |
| `standingDecision` | User-confirmed buy/sell/hold decision stored in `target-portfolio.json` (also mirrored in `investment.standing_decision_*` SQLite columns). Not overridden by automated DCF runs. |
| `targetEntryPrice` | GTC limit price for accumulating a position; sourced from TA support + DCF margin of safety |
| `aiThesis.action` | Portfolio-level recommendation (`INITIATE/ACCUMULATE/MAINTAIN/TRIM/EXIT/WATCHLIST`) — distinct from the raw DCF signal |
| PSU-U.TO | Purpose US Cash ETF (~$100 USD/share on TSX) — the idle cash parking vehicle. All new purchases are funded by trimming this. |
| HITL | Human-in-the-loop — mandatory confirmation step before any order is submitted to the broker |
| T0 gate | Compile + syntax + path regression checks (`run_tests.py`) — must pass before any commit |
| T0.5 gate | Bridge smoke test — verifies `portfolio_action.py` returns valid JSON via symlink |
| Grok sweep | Portfolio news analysis workflow: agent generates prompt → user pastes to x.com/i/grok → pastes response back → agent gates against DCF + 8 hard gates |
| Sweep template | `daily_sweep.md.template` / `weekly_sweep.md.template` — Grok prompt templates; must be updated when thesis/pillars change |
| py_services | Canonical Python scripts in `investment_screener/backend/py_services/`. All financial calculations go here — never inline. |
