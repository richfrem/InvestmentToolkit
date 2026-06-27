# GEMINI.md - InvestmentToolkit Context

## 🌟 Project Overview
**InvestmentToolkit** is a high-end investment analysis suite designed for sophisticated retail investors. It features a "Luxury Dark Mode" web dashboard, professional fundamental analysis tools, valuation modeling, and autonomous AI agents for research and thesis management.

### 🚀 Getting Started (Interactive Onboarding)

Two dedicated setup agents handle onboarding:

| Trigger | Agent | Purpose |
|---------|-------|---------|
| `"Help me set up the toolkit"` | `toolkit-onboarding-guide` | Master coordinator: checks dependencies, runs startup script, routes to TV setup |
| `"Set up TradingView for me"` | `tradingview-onboarding` | Deep-dive TV setup: install, subscription check, broker panel, CDP verify, first sync |
| `/setup-questrade` | skill | Optional Questrade API fallback (skip if TV sync works) |

**Quick path for returning users**: `python3 run_investment_toolkit.py` → `/tv-portfolio-sync`

### 🔐 Prerequisites (Subscription)
> [!IMPORTANT]
> **Pro-tier AI Required**: To execute autonomous sub-agent skills like `/strategic-review`, `/x-news-sweep`, and `/evaluate-stock`, you **must** have an active Pro-tier subscription for your CLI environment (Claude Code, GitHub Copilot Pro, or Google Gemini Pro).

### Core Stack:
... (rest of the file)
- **Frontend**: React 19, Vite, Tailwind CSS 4.0.
- **Backend**: Node.js (Express) with a Python bridge for financial data.
- **Data Sources**: `yfinance` (real-time/historical) and Questrade API (brokerage sync).
- **AI Framework**: Autonomous agents built on a plugin architecture, orchestrated by the **Exploration Workflow**.

---

## 🏗️ Architecture & Structure

```
InvestmentToolkit/
├── investment_screener/        ← Main application (npm workspace root)
│   ├── frontend/               ← React 19 + Vite + Tailwind CSS 4.0
│   └── backend/                ← Node.js Express API (port 3001)
│       └── src/
│           ├── services/       ← QuestradeSyncService.ts, etc.
│           └── utils/          ← QuestradeAPIClient.py, QuestradeTokenManager.py
├── plugins/                    ← Modular AI agent plugins
│   ├── stock-valuation/        ← DCF valuation + research sweep skills
│   ├── portfolio-advisor/        ← Portfolio drift, strategic review, rebalance skills
│   └── toolkit-manager/        ← Orchestrator (token setup, startup)
├── .agents/                    ← Agent skills, prompts, and evaluations
├── .claude/                    ← Claude Code configuration
├── docs/                       ← Architecture decision records and guides
└── run_investment_toolkit.py   ← Unified startup script (venv + npm + services)
```

---

## 🚀 Building and Running

### Complete Suite Startup (Recommended)
Run from repo root:
```bash
python3 run_investment_toolkit.py
```
*Creates the Python venv, installs all dependencies (npm & pip), builds the backend, launches both services, and **auto-launches TradingView Desktop with CDP on port 9222** (if installed). To relaunch TradingView independently after closing it:*
```bash
python3 tools/launch_tradingview_with_debugport.py
```

### 🤖 Orchestration Command
You can also use the **Toolkit Manager** plugin to launch the suite:
- `/start-screener` — Launch the Investment Screener suite (Frontend and Backend).

---

## 🔐 Authentication & Security (Questrade)
The project uses a professional-grade brokerage sync engine for Questrade, prioritizing security through **AES-256-GCM hardware-backed encryption** and stateful token rotation.

### 🤖 Interactive Token Setup
Use the **Toolkit Manager** plugin to guide the user through the initial token setup or re-seeding:
- `/setup-questrade` — Interactively guide the user through setting up their Questrade API refresh token.

### Individual Service Commands
Run from `investment_screener/`:
```bash
npm run dev -w backend      # Backend dev server → port 3001
npm run dev -w frontend     # Frontend dev server → port 5173
npm run build -w backend    # Build backend
npm run build -w frontend   # Build frontend
npm run lint -w frontend    # Lint frontend
```

> [!IMPORTANT]
> **NPM Path Mandate**: Always run npm commands from `investment_screener/` (the workspace root). Never use `--prefix investment_screener` from inside `investment_screener/` — it doubles the path and fails.

### Token Lifecycle
```
[Questrade Portal] → One-Week App Token
        ↓  (redeem once with curl)
[Questrade OAuth2] → refresh_token (long-lived, single-use)
        ↓  (seed once)
[QuestradeDataEngine --seed] → investment_screener/backend/.questrade_cache
        ↓  (every sync — fully automatic)
[Backend auto-rotates] → new refresh_token saved back to cache
```

### Initial Setup (Do This Once Per Machine)
Users seed the system once using a one-week application token from the Questrade API Centre. After the initial seed, the engine handles all token rotation automatically via `.questrade_cache`.

```bash
# 1. Redeem one-week app token from https://apphub.questrade.com/UI/UserApps.aspx
# NOTE: Must include -d '' to avoid HTTP 411 error.
curl -s -X POST \
  "https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=<ONE_WEEK_TOKEN>" \
  -d '' -H 'Content-Type: application/x-www-form-urlencoded'

# 2. Seed the returned refresh_token
# IMPORTANT: --cache-dir investment_screener/backend/ is REQUIRED when run from repo root.
python3 investment_screener/backend/src/QuestradeDataEngine.py \
  --seed "<refresh_token_from_step_1>" \
  --cache-dir investment_screener/backend/

# 3. Test via the API (backend must be running on port 3001)
curl -s -X POST http://localhost:3001/api/portfolio/sync-questrade \
  -H 'Content-Type: application/json' -d '{}'
```

### ⚠️ Agent Token Expiry Protocol
Questrade refresh tokens can expire. **If you (as an agent) encounter `Token rotation failed: 400`:**
1. Inform the user: *"Your Questrade token has expired and needs to be refreshed."*
2. Ask them to visit [apphub.questrade.com](https://apphub.questrade.com/UI/UserApps.aspx) and generate a new **One-Week App Token**
3. Once they provide it, run the full seed sequence (Steps 1-3) yourself.

---

## 🔄 Daily Session Protocol

**One command starts the day:**
```
/daily
```
The `daily-loop-agent` interactively guides through every step. No checklist.

**What `/daily` does (in order):**
1. Checks portfolio.json freshness — syncs from TradingView if stale
2. Runs morning brief: macro regime (VIX + SPY 200D + HYG/LQD), TA sweep, conviction scores, earnings calendar
3. Ranked triage: IMMINENT events → EXIT signals → REDUCE → ACCUMULATE
4. Interactive action cards — one per holding, proposes trade, waits for approval
5. Offers `/x-news-sweep` on news days
6. Logs session to `plugins/portfolio-advisor/references/evolution-log.md`

**x-news-sweep (when agent prompts or catalyst day):**
1. Generates a fresh Grok prompt from live `target-portfolio.json`
2. Paste into [x.com/i/grok](https://x.com/i/grok) and submit
3. Paste Grok's response back — the skill gates every recommendation against DCF + 8 hard gates

---

## 🤖 AI Agent Skills — Quick Reference

> **Skill location:** `.agents/` at repo root — project-local skills usable by Gemini CLI,
> Claude Code, GitHub Copilot, and any other AI tool. Not from any marketplace.
> Always check `.agents/skills/` before assuming a skill doesn't exist.

| Trigger | Plugin | Purpose |
|---------|--------|---------|
| `/evaluate-stock {TICKER}` | stock-valuation | Full DCF valuation — Bear/Base/Bull scenarios, fair value, research report. Uses live TV price when CDP active. |
| `/research-stock {TICKER}` | stock-valuation | Qualitative research sweep — classifies findings, gates re-valuation on confirmation |
| `/analyze-etf {TICKER}` | etf-analysis | Thematic ETF analysis — holdings alignment, expense ratio, BUY/HOLD/AVOID. Writes `data/etf_analysis/` + co-writes `data/projections/` so AI Expert Thesis panel appears in Dashboard. |
| **`/daily`** | **portfolio-advisor** | **The one daily command.** Interactive loop: sync check → brief → triage cards → execution → evolution log. |
| `/review-portfolio` | portfolio-advisor | Drift monitor + pillar conviction audit + thesis formula health score (0–100) |
| `/strategic-review` | portfolio-advisor | Adversarial thesis challenger — surfaces failing pillars, proposes formula improvements |
| `/rebalance` | portfolio-advisor | Valuation-gated trade optimizer — never buys SELL-rated holdings to restore drift |
| `/calibrate-targets` | portfolio-advisor | Interactive target-weight calibration session |
| `/update-portfolio-targets` | portfolio-advisor | Apply formula/weight changes to `target-portfolio.json` |
| `/x-news-sweep` | portfolio-advisor | Daily Grok/X.com news sweep — posts to grok.com via browser automation, gates recs against DCF + 8 hard gates |
| `/13f-tracker` | portfolio-advisor | Poll SEC EDGAR for new 13F filings, download holdings JSON, diff quarter-over-quarter |
| `/13f-analyze` | portfolio-advisor | Surgical 13F analysis — cross-references SA LP holdings vs your targets, outputs gated INITIATE/ACCUMULATE/TRIM/EXIT recs, applies approved changes to target-portfolio.json |
| `/bundle-thesis-review` | portfolio-advisor | Package thesis + DCF projections for paste into external LLM (Grok, ChatGPT, Gemini) |
| `/run-advisor` | portfolio-advisor | Interactive Portfolio Advisor orchestrator — full review → calibrate → rebalance lifecycle (post-catalyst) |
| `/weekly-review` | portfolio-advisor | Weekend review cycle — range-based drift audit, weekly Grok sweep prompt generation, and TradingView technical checks |
| `/place-order {buy\|sell} {N} {TICKER} in {ACCOUNT}` | **tradingview** | **Live order execution** via TradingView CDP broker automation. 3-step HITL: preflight card → CONFIRM → dialog filled + submitted + portfolio.json synced. Requires TradingView Desktop with Questrade broker connected. |
| `/cancel-order {tvOrderId}` | **tradingview** | **Cancel a Working/Inactive order** via CDP — finds order by UUID, clicks ×, handles TV confirmation dialog, marks trade-log entry cancelled. |
| `/modify-order {tvOrderId} {newPrice}` | **tradingview** | **Modify a limit price** on a Working/Inactive order via CDP keyboard events. |
| `/get-orders` | **tradingview** | **List open orders** (Working + Inactive) from TV broker panel — returns orderId UUIDs and raw row text. |
| `/tv-portfolio-sync` | **tradingview** | **Sync portfolio.json from TradingView** — reads live positions across all accounts (TFSA + RRSP + Cash) via CDP. Shows diff before writing. Works with any TV-connected broker; no Questrade credentials required. |
| `/tv-watchlist-sync` | **tradingview** | **Sync TradingView watchlists** (`TA-Full Watchlist` and `TA-Current Holdings`) with `watchlist.json` / projections and `portfolio.json`. Direct script: `watchlist_manager.py`. |
| `/setup-tradingview` | **tradingview** | **Programmatic diagnostics check** for `tradingview-cdp` installation and Port 9222 health. |
| `/pine-inject {description}` | **tradingview** | Generate a custom Pine Script v6 indicator from a description and inject it into TradingView via CDP. Auto-corrects compilation errors (3 attempts). Preflight validates version/indicator declarations before hitting TV. Script: `tv_pine_inject.py`. |
| `/author-pine-script {description}` | **tradingview** | Full Pine Script v6 authoring workflow: Phase 0 source research (reads community indicator source via `pine_source_reader.py`), lint gate (`pine_linter.py`), inject, and save to TV library. Teaches itself from top-10 indicators before writing. |
| `/tv-ta-deep {TICKER} [TIMEFRAME]` | **tradingview** | Deep Technical Analysis: builds the optimal indicator view for the job (adds built-ins, injects custom bundle, or authors indicators), multi-timeframe context check, synthesizes entry/accumulate/trim/exit levels, adversarial red-team review. Agent: `ta-guide` for interactive guided session. |
| `/start-screener` | toolkit-manager | Launch full suite (frontend + backend) |
| `/setup-questrade` | toolkit-manager | Interactive Questrade token setup (optional — TV sync works without it) |

---

## 📜 Agent Rules & Conventions (MANDATORY)

You must read and strictly adhere to all rules defined in `.agent/rules/`:
- **TDD (`test-driven-development.md`)**: NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST. Mocking is strictly prohibited on critical runtime paths.
- **No Inline Python (`no-inline-python.md`)**: Never perform financial or analytical calculations inline using ad-hoc bash/python snippets. Always extract to versioned scripts.
- **Coding Conventions (`coding-conventions.md`)**: Dual-layer docs, type hints, proper casing, and strict refactoring thresholds.
- **Dependency Management (`dependency-management.md`)**: No manual `pip install`. Edit `.in` files and use `pip-compile`.
- **Plugin Architecture (`plugin-architecture.md` & `symlink-cross-platform.md`)**: Use file-level symlinks ONLY via `symlink_manager.py`. Never raw `ln -s`. No cross-plugin script execution.
- **Self-Evolution (`self-evolution-policy.md`)**: Classify failures, max 3 repair attempts, update playbooks. Deletions are forbidden. Synchronize daily/weekly sweep templates in `assets/templates/` whenever strategies or target weights change. Refine prompt templates on ingesting Grok responses based on quality delta.

---

## 🤖 AI Development: Exploration Workflow
We use the **Exploration Workflow** (a modification of the orba/superpowers plugin) for building and discovery.

### Canonical Workflow:
1. **Intake**: Invoke the `intake-agent` (`.agents/agents/exploration-cycle-plugin-intake-agent.md`)
2. **Orchestration**: `exploration-workflow` skill manages the 4-phase loop via `exploration/exploration-dashboard.md`
3. **Phase 1 — Problem Framing**: `discovery-planning` skill
4. **Phase 2 — Visual Blueprinting**: `visual-companion` skill
5. **Phase 3 — Prototyping**: `subagent-driven-prototyping` skill
6. **Phase 4 — Handoff & Specs**: `exploration-handoff` skill

---

## 📦 Dependency Management
- Python deps tracked in root `requirements.in`
- Sub-services inherit via `-r ../../requirements.in`
- Always run `pip-compile requirements.in -o requirements.txt` after modifying `.in` files
- The startup script (`run_investment_toolkit.py`) installs from `requirements.txt` — new Python imports **must** be in `requirements.in` or the venv will be missing them at runtime

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

**ADR**: `plugins/stock-valuation/references/ADR-dcf-calculator.md`

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
Invoke the `superpowers:test-driven-development` skill (Claude) or check `.agent/rules/test-driven-development.md` (all AI tools). Write the test. Watch it fail. Then write minimal code to pass it.

**Why this rule exists**: A one-line import path bug (`validate_weights` not found in `py_services/`) broke `getPythonActions()` silently. A unit test would have caught it in 30 seconds. See the test suite vision: `docs/superpowers/specs/2026-05-17-test-suite-vision-design.md`

---

## 📋 Trade Log UI

The Trade Log (`/trade-log`) mirrors TradingView's order panel. Tabs: **All | Working | Inactive | Suggested | Filled | Cancelled**.

- **Inactive tab** = limit orders placed in TV waiting for price trigger (`status: 'inactive'`)
- **Suggested tab** = AI-proposed trades + manually logged entries (`suggested` / `logged`)
- **Avg Fill / Total** only show values when `status === 'filled'`; all other rows show `—`
- Trades are auto-logged by `TradePrepModal` on submission — no separate "Log Trade" button
- Buy/Sell buttons (in Stock Analysis, Portfolio Table, Portfolio Advisor) are just "Buy" / "Sell"
- Price badge uses `PriceSourceBadge`: shows "TV Live" when TV Desktop connected, "yfinance" otherwise

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
`investment_screener/backend/src/utils/zod-schemas.ts`: `lastActualPS` is `.nullable().transform(v => v ?? 0)`. Pre-revenue stocks and some mining companies return `null` from yfinance for this field. If adding similar numeric fields, use the same nullable pattern — strict `z.number()` causes 400 validation errors.

### 6. TradingView CDP — Node snippets MUST call process.exit()
All Node.js snippets in `tradingview-cdp/` **must** end with `.then(() => process.exit(0)).catch(() => process.exit(1))`. Without it, the CDP WebSocket holds the event loop open indefinitely — `subprocess.run()` from Python never returns. This caused all Phase 1 harness timeouts.

### 7. TradingView CDP — Use React fiber traversal for Pine Editor / Monaco
Do **not** rely solely on CSS class selectors for Pine Editor / Monaco editor — TV class names change. Scan DOM nodes for the `__reactFiber` key prefix and walk the fiber tree to find Monaco internals. Reference: [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) `pine.js`.

### 8. Temp files: use InvestmentToolkit/temp/ subfolder, not /tmp/ root
All scripts writing temp artifacts must use `InvestmentToolkit/temp/<artifact>` (gitignored), not `/tmp/<artifact>`. Task #0003 tracks legacy migration.

### 9. TradingView CDP — close Pine Editor before `addIndicator`
When the Pine Editor panel is open, `chart addIndicator` fails — the Indicators dialog search input is not reachable with the panel overlapping. Close the Pine Editor first. Implementation: `Input.dispatchMouseEvent` at the button's `getBoundingClientRect()` center (not `.click()`, which opens the timezone dropdown). Result rows: `div[class*="container-WeNdU0sq"]`. Match priority: exact → first result (TV's ranking) → contains.

### 10. TradingView CDP — source code viewing from Indicators dialog
Source code for open-source indicators is accessible two ways: (1) chart legend More menu → `"Source code…"` (unicode `…` not `...`), (2) Indicators toolbar button → search → source icon on result. **PA Toolkit Lite [UAlgo] IS open source** (CC BY-NC-SA 4.0) — source saved at `plugins/tradingview/assets/pinescript-indicators/community-reference/pa-toolkit-lite-ualgo.pine`. Closed-source (paid/private) scripts show neither option.

### 11. Custom Pine Script indicator library
Agent-authored indicators: `plugins/tradingview/assets/pinescript-indicators/`
- `ai-ta-levels.pine` — Multi-EMA (21/50/200) + volume bias %, saved in TV personal library as "AI TA Levels"
- `community-reference/pa-toolkit-lite-ualgo.pine` — PA Toolkit source for learning order block, liquidity, ZigZag patterns
Always lint before injecting: `python3 plugins/tradingview/skills/author-pine-script/scripts/pine_linter.py <file>`

### 9. TradingView CDP — shared runtime lives at `tradingview-cdp/`, NOT inside `plugins/`
The Node.js CDP engine was extracted from the legacy plugins directory to `tradingview-cdp/` at the project root (ADR-024 "Thin Skill + Thick Engine"). This directory is a standalone runtime, installed once via `cd tradingview-cdp && npm ci`. **Never create new scripts that hardcode this path** — always import from `tv_client.py`:
```python
from tv_client import tv_call, TV_NODE_DIR, REPO_ROOT
```
`tv_client.py` locates `tradingview-cdp/cli.js` via `TV_CDP_DIR` env var or directory walk-up (10 levels).

### 10. TradingView Pine inject — pass content, not file path
`tv_pine_inject.py` reads the script file in Python (correct cwd) then passes the **content** via `--content` to Node — not the file path. Node's cwd is `tradingview-cdp/` so relative paths from Node would silently fail (Node would inject the path string as Pine Script). If you create a new inject wrapper, always resolve absolute paths before passing to `tv_call`. The preflight check in `tv_pine_inject.py` catches missing `//@version=` and `indicator()` declarations before the CDP round-trip.

### 11. TradingView CDP — Account Dropdown Selection Events
Standard `.click()` method fails on the account dropdown options inside the order ticket and broker panel because TradingView relies on specific React and DOM MouseEvents. You MUST dispatch a sequence of `mousedown`, `mouseup`, and `click` MouseEvents to both the option span (matching `s.className === ''` + text match) and its `parentElement` to reliably switch accounts.

### 12. PSU.U.TO and PSU-U.TO are the same fund
`PSU.U.TO` (dot — Questrade/TradingView broker panel) and `PSU-U.TO` (hyphen — Yahoo Finance / TSX canonical) refer to the **same ETF**: Purpose US Cash Fund. The alias is hardcoded in `fetch_broker_data.py` `write_snapshot()`. Canonical thesis entry is always `PSU-U.TO`. Never create a second entry for `PSU.U.TO`.

### 13. targetEntryPrice — GTC limit buy price field
`target-portfolio.json` holdings support a `targetEntryPrice` (optional float) — the GTC limit order price for adding to a position. Set via:
```bash
python3 plugins/portfolio-advisor/scripts/update_targets.py --set-entry TICKER=PRICE --write
```
Never add to a position above its `targetEntryPrice`. The Grok sweep prompt surfaces this field and asks for entry price suggestions on ACCUMULATE recommendations.

### 14. Limit orders default to Day — GTC requires manual TV change
CDP order automation does NOT yet set "Good till cancelled". Limit orders from `/place-order` are **Day orders**. For long-dated GTC entries, manually change the duration in TradingView → broker panel → Orders → edit → "Good till cancelled" after placing.

### 15. Portfolio sync fallback chain
After order fills: (1) Express API `POST /api/portfolio/sync-tv/apply`, (2) direct `fetch_broker_data.py --snapshot` (works without backend, updates cash + holdings from live TV), (3) Questrade REST. Run `fetch_broker_data.py --snapshot` directly when the backend is down.

---

## 🙏 Acknowledgements & Prior Art

### TradingView CDP Community
| Project | What It Does |
|---------|-------------|
| [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) | Most complete CDP TradingView library — 5,000+ lines, 15+ namespaces. React fiber traversal technique for Monaco editor. No live broker execution. |
| [atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp) | TV screener/scanner via REST API (`tradingview-screener` library). No CDP, no live orders. |

**Our differentiator:** InvestmentToolkit is a **live broker execution layer** — places, modifies, and cancels real Questrade orders through TradingView's broker panel via CDP, with HITL confirmation, safety gates, multi-account support, and portfolio sync after fills.

### AI Agent Infrastructure
- **[orba/superpowers](https://github.com/orba/superpowers)** — TDD Iron Law, brainstorming, and sub-agent driven development skills used throughout this project.
- **[richfrem/agent-plugins-skills](https://github.com/richfrem/agent-plugins-skills)** — Exploration Workflow (4-phase) and all project-local AI agent plugins and skills.

---

## 🔑 Key Files for AI Context

| File | Purpose |
|------|---------|
| `run_investment_toolkit.py` | Unified toolkit startup and orchestration script |
| `GEMINI.md` | Primary context file for Gemini agents (this file) |
| `.claude/CLAUDE.md` | Primary context file for Claude agents |
| `.github/copilot-instructions.md` | Primary context for GitHub Copilot |
| `plugins/toolkit-manager/references/Questrade/questrade_token_setup.md` | Full Questrade token protocol |
| `investment_screener/backend/src/utils/QuestradeAPIClient.py` | Core OAuth2 client |
| `investment_screener/backend/src/services/QuestradeSyncService.ts` | Node→Python sync bridge |
