# GEMINI.md - InvestmentToolkit Context

## 🌟 Project Overview
**InvestmentToolkit** is a high-end investment analysis suite designed for sophisticated retail investors. It features a "Luxury Dark Mode" web dashboard, professional fundamental analysis tools, valuation modeling, and autonomous AI agents for deep-dive research and portfolio alignment.

### Core Stack:
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
*Creates the Python venv, installs all dependencies (npm & pip), builds the backend, and launches both services.*

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

---

## 🔐 Authentication & Security (Questrade)
The project uses a professional-grade brokerage sync engine for Questrade, prioritizing security through **AES-256-GCM hardware-backed encryption** and stateful token rotation.

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

## 🤖 AI Agent Skills — Quick Reference

| Trigger | Plugin | Purpose |
|---------|--------|---------|
| `/evaluate-stock {TICKER}` | stock-valuation | Full DCF valuation — Bear/Base/Bull scenarios, fair value, research report |
| `/research-stock {TICKER}` | stock-valuation | Qualitative research sweep — classifies findings, gates re-valuation on confirmation |
| `/review-portfolio` | portfolio-advisor | Drift monitor + pillar conviction audit + thesis formula health score (0–100) |
| `/strategic-review` | portfolio-advisor | Adversarial thesis challenger — surfaces failing pillars, proposes formula improvements |
| `/rebalance` | portfolio-advisor | Valuation-gated trade optimizer — never buys SELL-rated holdings to restore drift |
| `/start-screener` | toolkit-manager | Launch full suite (frontend + backend) |
| `/setup-questrade` | toolkit-manager | Interactive Questrade token setup |

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

---

## 🔑 Key Files for AI Context

| File | Purpose |
|------|---------|
| `GEMINI.md` | Primary context file for Gemini agents (this file) |
| `.claude/CLAUDE.md` | Primary context file for Claude agents |
| `.github/copilot-instructions.md` | Primary context for GitHub Copilot |
| `docs/architecture/Questrade/questrade_token_setup.md` | Full Questrade token protocol |
| `investment_screener/backend/src/utils/QuestradeAPIClient.py` | Core OAuth2 client |
| `investment_screener/backend/src/services/QuestradeSyncService.ts` | Node→Python sync bridge |
