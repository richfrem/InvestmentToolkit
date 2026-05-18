# GitHub Copilot Instructions — InvestmentToolkit

## 🌟 Project Overview
**InvestmentToolkit** is a high-end investment analysis suite for sophisticated retail investors. It features a "Luxury Dark Mode" web dashboard, fundamental analysis tools, valuation modeling, and autonomous AI agents for research and thesis management.

### 🚀 Getting Started (Interactive Onboarding)

Two dedicated setup agents handle onboarding — always route new users here first:

| Trigger | Agent | Purpose |
|---------|-------|---------|
| `"Help me set up the toolkit"` | `toolkit-onboarding-guide` | Master coordinator: checks dependencies, runs startup script, routes to TV setup |
| `"Set up TradingView for me"` | `tradingview-onboarding` | Deep-dive TV setup: install, subscription check, broker panel, CDP verify, first sync |
| `/setup-questrade` | skill | Optional Questrade API fallback (skip if TV sync works) |

**Quick path for returning users**: `python3 run_investment_toolkit.py` → `/tv-portfolio-sync`

### 🔐 Prerequisites (Subscription)
> [!IMPORTANT]
> **Pro-tier AI Required**: To execute autonomous sub-agent skills like `/strategic-review`, `/x-news-sweep`, and `/evaluate-stock`, you **must** have an active Pro-tier subscription for your CLI environment (Claude Code, GitHub Copilot Pro, or Google Gemini Pro).

### Core Stack
... (rest of the file)
- **Frontend**: React 19, Vite, Tailwind CSS 4.0 (port 5173)
- **Backend**: Node.js (Express) with Python bridge (port 3001)
- **Data Sources**: `yfinance` and Questrade API (brokerage sync)
- **AI Agents**: Plugin architecture orchestrated by the Exploration Workflow

---

## 🏗️ Project Structure

```
InvestmentToolkit/
├── investment_screener/        ← npm workspace root — run all npm commands from here
│   ├── frontend/               ← React 19 + Vite + Tailwind 4.0
│   └── backend/                ← Node.js Express API
│       └── src/
│           ├── services/       ← QuestradeSyncService.ts
│           └── utils/          ← QuestradeAPIClient.py, QuestradeTokenManager.py
├── plugins/                    ← AI agent plugins (stock-valuation, portfolio-advisor, toolkit-manager)
├── .agents/                    ← Agent skills and prompts
├── .claude/                    ← Claude Code config + CLAUDE.md
├── .github/                    ← Copilot instructions (this file)
└── docs/architecture/          ← ADRs and Mermaid sequence diagrams
```

---

## 🚀 Dev Commands

Run from `investment_screener/`:
```bash
npm run dev -w backend      # Backend → port 3001
npm run dev -w frontend     # Frontend → port 5173
npm run build -w backend
npm run build -w frontend
npm run lint -w frontend
python3 run_investment_toolkit.py           # Full suite startup (from repo root)
```

### 🤖 Orchestration
Use the **toolkit-manager** plugin skills:
- `/start-screener` — Launch the full suite.
- `/setup-questrade` — Guide user through token setup.

> [!IMPORTANT]
> **NPM Path Mandate**: Always run npm commands from `investment_screener/`. Never use `--prefix investment_screener` from within `investment_screener/` — it doubles the path and fails.

---

## 🔐 Questrade Authentication & Security

The backend uses a stateful token rotation engine with **AES-256-GCM hardware-backed encryption** (macOS Keychain).

### 🤖 Interactive Token Setup
Use the **toolkit-manager** plugin to guide the user:
- `/setup-questrade` — Interactively guide the user through setting up their Questrade API refresh token.

### ⚠️ Tokens Expire — Agent Must Handle This

Questrade refresh tokens are **single-use and can expire**. When a sync returns `Token rotation failed: 400`, the token needs to be re-seeded.

**As an AI agent, if you encounter a 400 token error, you must:**
1. Inform the user their Questrade token has expired
2. Ask them to visit [Questrade API Centre](https://apphub.questrade.com/UI/UserApps.aspx) and generate a new one-week token
3. Once they provide the token, handle the seed sequence yourself.

### Initial Setup / Re-Seeding
```bash
# Step 1: Redeem the one-week token (-d '' required to avoid HTTP 411)
curl -s -X POST \
  "https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=<ONE_WEEK_TOKEN>" \
  -d '' -H 'Content-Type: application/x-www-form-urlencoded'

# 2. Seed the returned refresh_token into backend cache (--cache-dir required)
# IMPORTANT: --cache-dir investment_screener/backend/ is REQUIRED when run from repo root.
python3 investment_screener/backend/src/QuestradeDataEngine.py \
  --seed "<refresh_token>" \
  --cache-dir investment_screener/backend/

# Step 3: Verify via the API
curl -s -X POST http://localhost:3001/api/portfolio/sync-questrade \
  -H 'Content-Type: application/json' -d '{}'
```

### Token Storage Rules
- **Location**: `investment_screener/backend/.questrade_cache` (binary, AES-256-GCM encrypted)
- **Encryption key**: Managed via **macOS Keychain** (keyring library) — never on disk in plaintext.
- **Git**: `.questrade_cache` is **git-ignored at all paths** — never committed.
- **`~/.zshrc`**: `QUESTRADE_REFRESH_TOKEN` is an emergency fallback only.

---

## 🔄 Daily Session Protocol

At the start of each new trading day session, run `/x-news-sweep`:
1. Generates a fresh Grok prompt from live `target-portfolio.json`
2. Paste into [x.com/i/grok](https://x.com/i/grok) and submit
3. Paste Grok's response back — the skill gates every recommendation against DCF + 8 hard gates before applying anything

This keeps thesis targets, `agentRationale`, and projection catalyst notes current with market developments.

---

## 🤖 AI Agent Skills — Quick Reference

> **Skill location:** `.agents/` at repo root — project-local skills usable by GitHub Copilot,
> Claude Code, Gemini CLI, and any other AI tool. Not from the Copilot marketplace.
> Always check `.agents/skills/` before assuming a skill doesn't exist.

| Trigger | Plugin | Purpose |
|---------|--------|---------|
| `/evaluate-stock {TICKER}` | stock-valuation | Full DCF valuation — Bear/Base/Bull scenarios, fair value, analyticsLog, research report. Uses live TV price (active chart via CDP) when TradingView Desktop is running. |
| `/research-stock {TICKER}` | stock-valuation | Qualitative research sweep — Class A/B/C/D change classification, gates re-valuation |
| `/analyze-etf {TICKER}` | etf-analysis | Thematic ETF analysis — holdings alignment vs thesis, expense ratio, BUY/HOLD/AVOID. Writes `data/etf_analysis/` + co-writes `data/projections/` so AI Expert Thesis panel appears in Dashboard. |
| `/review-portfolio` | portfolio-advisor | Drift monitor + pillar conviction audit + thesis formula health score (0–100) |
| `/strategic-review` | portfolio-advisor | Adversarial thesis challenger — surfaces failing pillars, proposes formula improvements |
| `/rebalance` | portfolio-advisor | Valuation-gated trade optimizer — skips SELL-rated holdings when restoring drift |
| `/calibrate-targets` | portfolio-advisor | Interactive target-weight calibration session |
| `/update-portfolio-targets` | portfolio-advisor | Apply formula/weight changes to `target-portfolio.json` |
| `/x-news-sweep` | portfolio-advisor | Daily Grok/X.com news sweep — posts to grok.com via browser automation, gates recs against DCF + 8 hard gates |
| `/13f-tracker` | portfolio-advisor | Poll SEC EDGAR for new 13F filings, download holdings JSON, diff quarter-over-quarter |
| `/13f-analyze` | portfolio-advisor | Surgical 13F analysis — cross-references SA LP holdings vs your targets, outputs gated INITIATE/ACCUMULATE/TRIM/EXIT recs, applies approved changes to target-portfolio.json |
| `/bundle-thesis-review` | portfolio-advisor | Package thesis + DCF projections for paste into external LLM (Grok, ChatGPT, Gemini) |
| `/run-advisor` | portfolio-advisor | Interactive Portfolio Advisor orchestrator — full review → calibrate → rebalance lifecycle |
| `/place-order {buy\|sell} {N} {TICKER} in {ACCOUNT}` | **tradingview** | **Live order execution** via TradingView CDP broker automation. 3-step HITL: preflight card → CONFIRM → dialog filled + submitted + portfolio.json synced. Requires TradingView Desktop with Questrade broker connected. |
| `/cancel-order {tvOrderId}` | **tradingview** | **Cancel a Working/Inactive order** via CDP — finds order by UUID, clicks ×, handles TV confirmation dialog, marks trade-log entry cancelled. |
| `/modify-order {tvOrderId} {newPrice}` | **tradingview** | **Modify a limit price** on a Working/Inactive order via CDP keyboard events. |
| `/get-orders` | **tradingview** | **List open orders** (Working + Inactive) from TV broker panel — returns orderId UUIDs and raw row text. |
| `/tv-portfolio-sync` | **tradingview** | **Sync portfolio.json from TradingView** — reads live positions across all accounts (TFSA + RRSP + Cash) via CDP. Shows diff before writing. Works with any TV-connected broker; no Questrade credentials required. |
| `/pine-inject {description}` | **tradingview** | Generate a custom Pine Script v6 indicator from a description and inject it into TradingView via CDP. Auto-corrects compilation errors (3 attempts). Preflight validates version/indicator declarations before hitting TV. Script: `tv_pine_inject.py`. |
| `/author-pine-script {description}` | **tradingview** | Full Pine Script v6 authoring workflow: Phase 0 source research (reads community indicator source via `pine_source_reader.py`), lint gate (`pine_linter.py`), inject, and save to TV library. Teaches itself from top-10 indicators before writing. |
| `/tv-ta-deep {TICKER} [TIMEFRAME]` | **tradingview** | Deep Technical Analysis: builds the optimal indicator view for the job (adds built-ins, injects custom bundle, or authors indicators), multi-timeframe context check, synthesizes entry/accumulate/trim/exit levels, adversarial red-team review. Agent: `ta-guide` for interactive guided session. |
| `/start-screener` | toolkit-manager | Launch full suite (frontend + backend) |
| `/setup-questrade` | toolkit-manager | Interactive Questrade token setup (optional — TV sync works without it) |

---

## 📦 Dependency Management
- Python deps: root `requirements.in` → compile with `pip-compile requirements.in -o requirements.txt`
- Sub-services inherit via `-r ../../requirements.in`
- The startup script installs from `requirements.txt` — new Python imports **must** be in `requirements.in` or the venv will be missing them at runtime

---

## 🧮 AI Agent Calculation Policy — Fix Once, Reuse Always

> **Rule**: Never perform financial or analytical calculations inline (ad-hoc bash/python snippets in tool calls). Always use or create a versioned `.py` script in `investment_screener/backend/py_services/`. Fix bugs once in the script; every future run benefits automatically.

### Canonical scripts

| Script | Purpose | How to call |
|--------|---------|-------------|
| `fetch_financials.py {TICKER}` | Fetch raw financial data from yfinance | `python3 investment_screener/backend/py_services/fetch_financials.py AAPL > /tmp/AAPL_raw.json` |
| `dcf_scenarios.py --raw ... --scenarios ...` | DCF scenario math — validates constraints, computes all intermediates, outputs weighted fair value | `python3 investment_screener/backend/py_services/dcf_scenarios.py --raw /tmp/AAPL_raw.json --scenarios /tmp/AAPL_scenarios.json --pretty` |
| `validate_projection.py` | Pre-persistence JSON schema validator | `cat /tmp/AAPL_projection.json \| python3 plugins/stock-valuation/skills/stock_valuation/scripts/validate_projection.py --verbose` |

### When to create a new script
If you find yourself computing the same formula more than once across sessions → extract it into a new `py_services/` script, add a row to this table, and add a corresponding ADR in `docs/architecture/`.

### When NOT to inline calculations
- ❌ DCF math (use `dcf_scenarios.py`)
- ❌ Financial ratio derivations that appear in multiple valuations
- ❌ Any calculation where a bug would silently affect multiple outputs

**ADR**: `docs/architecture/stock-valuation/ADR-dcf-calculator.md`

---

## 🧪 Test-Driven Development — Mandatory

> **Rule**: No production code is written before a failing test exists. This applies to every Python service, Express route, TradingView CDP function, and plugin script.
> **Full rule**: `.agent/rules/test-driven-development.md`

### The Iron Law
```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.
```

### Where tests live

| What you're building | Test location |
|---|---|
| Python service in `py_services/` | `investment_screener/backend/tests/py_services/` |
| Express route | `investment_screener/backend/tests/api/` |
| TradingView CDP function | `plugins/tradingview/tests/tv_test_harness.py` |
| Plugin script | `plugins/<plugin>/tests/` |
| React component | `investment_screener/frontend/tests/` |

### Before writing any implementation
Check `.agent/rules/test-driven-development.md`. Write the test. Watch it fail. Then write minimal code to pass it.

**Why this rule exists**: A one-line import path bug (`validate_weights` not found in `py_services/`) broke `getPythonActions()` silently. A unit test would have caught it in 30 seconds. See the test suite vision: `docs/superpowers/specs/2026-05-17-test-suite-vision-design.md`

---

## 📋 Trade Log UI

The Trade Log (`/trade-log`) mirrors TradingView's order panel. Tabs: **All | Working | Inactive | Suggested | Filled | Cancelled**.

- **Inactive tab** = limit orders placed in TV waiting for price trigger (`status: 'inactive'`)
- **Suggested tab** = AI-proposed trades + manually logged entries (`suggested` / `logged`)
- **Avg Fill / Total** only show values when `status === 'filled'`; all other rows show `—`
- Trades are auto-logged by `TradePrepModal` on submission — no separate "Log Trade" button
- Buy/Sell buttons are just "Buy" / "Sell" everywhere (TradeButtons.tsx)

---

## ⚠️ Known Pitfalls — Read Before Touching These Areas

### 1. Python `__dirname` path in TypeScript backend
`__dirname` in `dist/index.js` (production) resolves to `backend/dist/`, **not** `backend/src/`. Python scripts live in `src/` and are never copied to `dist/`. Always use:
```ts
path.resolve(__dirname, '../src/QuestradeDataEngine.py')  // correct for dist/
```
**Reference**: `QuestradeSyncService.ts` uses `../../src/QuestradeDataEngine.py` (from `dist/services/`) — follow that pattern. Never use `path.resolve(__dirname, 'script.py')` — works in ts-node-dev, silently breaks in production.

### 2. Venv dependency gaps
The startup script sets up a venv and installs from `requirements.txt`. If you add a Python import to any backend file and forget to add it to `requirements.in`:
- It will work in the terminal (system Python may have it)
- It will fail at runtime when Node spawns the venv Python
- **Required packages**: `keyring`, `cryptography`, `yfinance`, `pandas`, `fastapi`, `uvicorn`, `pydantic`, `rich`, `typer`, `python-dotenv`
- After adding to `requirements.in`, run: `venv/bin/pip-compile requirements.in -o requirements.txt`

### 3. Backend requires explicit restart in production
The startup script runs `node dist/index.js` — **not** ts-node-dev. Changes to `src/` require:
1. `npm run build -w backend` (recompile)
2. Restart the backend process
Frontend hot-reloads via Vite; backend does not.

### 4. Questrade seed endpoint — do not bypass the OAuth exchange
The `/api/questrade/seed` endpoint accepts a raw **One-Week App Token** from the portal and internally exchanges it via OAuth before seeding. Do not seed raw one-week tokens directly via `QuestradeDataEngine.py --seed` unless you have already done the curl exchange yourself.

### 5. `lastActualPS` nullable in Zod schema
`investment_screener/backend/src/utils/zod-schemas.ts` line ~34: `lastActualPS` is `.nullable().transform(v => v ?? 0)`. Pre-revenue stocks and some mining companies return `null` from yfinance for this field. If you revert this or add a similar numeric field, use the same nullable pattern — a strict `z.number()` here causes 400 validation errors for any stock without price-to-sales data.

### 6. Projection JSON `action` field — expanded enum
`aiThesis.action` is no longer limited to `BUY | HOLD | SELL`. It now carries the full portfolio recommendation vocabulary:
- `INITIATE` — thesis confirmed, position not yet opened
- `ACCUMULATE` — thesis confirmed, position undersized vs target
- `MAINTAIN` — thesis confirmed, position appropriately sized
- `TRIM` — DCF stretched but thesis intact, reduce sizing
- `EXIT` — structural thesis failure (not cyclical)
- `WATCHLIST` — thesis valid but valuation too stretched to act

The original DCF valuation signal (BUY/HOLD/SELL) is preserved in `analyticsLog.valuationAction`. Portfolio-level rationale lives in `analyticsLog.portfolioRationale`. Urgency in `analyticsLog.portfolioUrgency`.

**Frontend:** The AI screener table shows action as a colour-coded pill (cyan=INITIATE, green=ACCUMULATE, slate=MAINTAIN, amber=TRIM, red=EXIT, purple=WATCHLIST). Hovering shows the full rationale. The AIAnalysisModal shows the DCF signal as a sub-badge alongside the portfolio action.

### 7. TradingView CDP — Node snippets MUST call process.exit()
All Node.js snippets in `tradingview-cdp/` **must** end with `.then(() => process.exit(0)).catch(() => process.exit(1))`. Without it, the CDP WebSocket holds the event loop open indefinitely — Python `subprocess.run()` never returns. Root cause of all Phase 1 harness timeouts.

### 8. TradingView CDP — Use React fiber traversal for Pine Editor / Monaco
Do **not** rely solely on CSS class selectors — TV class names change across deployments. Scan DOM nodes for the `__reactFiber` key prefix and walk the React fiber tree to locate Monaco internals. Reference: [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) `pine.js`.

### 9. Temp files: use InvestmentToolkit/temp/ subfolder, not /tmp/ root
All scripts writing temp artifacts must use `InvestmentToolkit/temp/<artifact>` (gitignored), not `/tmp/<artifact>`. Task #0003 tracks legacy migration.

### 10. TradingView CDP — shared runtime lives at `tradingview-cdp/`, NOT inside `plugins/`
The Node.js CDP engine was extracted from `plugins/tradingview/node/` to `tradingview-cdp/` at the project root (ADR-024 "Thin Skill + Thick Engine"). This directory is a standalone runtime, installed once via `cd tradingview-cdp && npm ci`. **Never create new scripts that hardcode this path** — always import from `tv_client.py`:
```python
from tv_client import tv_call, TV_NODE_DIR, REPO_ROOT
```
`tv_client.py` locates `tradingview-cdp/cli.js` via `TV_CDP_DIR` env var or directory walk-up (10 levels).

### 11. TradingView Pine inject — pass content, not file path
`tv_pine_inject.py` reads the script file in Python (correct cwd) then passes the **content** via `--content` to Node — not the file path. Node's cwd is `tradingview-cdp/` so relative paths from Node would silently fail (Node would inject the path string as Pine Script). If you create a new inject wrapper, always resolve absolute paths before passing to `tv_call`. The preflight check in `tv_pine_inject.py` catches missing `//@version=` and `indicator()` declarations before the CDP round-trip.

---

## 🙏 Acknowledgements & Prior Art

### TradingView CDP Community
- **[tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp)** — Most complete open-source TradingView CDP library. React fiber traversal technique for Monaco editor. No live broker execution.
- **[atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp)** — TradingView screener/scanner via REST API. No CDP, no live orders.

**Our differentiator:** InvestmentToolkit is a **live broker execution layer** with HITL order execution, safety gates, multi-account support, and portfolio sync after fills.

### AI Agent Infrastructure
- **[orba/superpowers](https://github.com/orba/superpowers)** — TDD Iron Law, brainstorming, and sub-agent driven development skills.
- **[richfrem/agent-plugins-skills](https://github.com/richfrem/agent-plugins-skills)** — Exploration Workflow (4-phase) and all project-local AI agent plugins and skills.

---

## 🔑 Key Files for AI Context

| File | Purpose |
|------|---------|
| `GEMINI.md` | Primary context file for Gemini agents |
| `.claude/CLAUDE.md` | Primary context file for Claude agents |
| `.github/copilot-instructions.md` | Primary context for GitHub Copilot (this file) |
| `docs/architecture/Questrade/questrade_token_setup.md` | Full token protocol |
| `investment_screener/backend/src/utils/QuestradeAPIClient.py` | OAuth2 client |
| `investment_screener/backend/src/services/QuestradeSyncService.ts` | Node→Python bridge |
