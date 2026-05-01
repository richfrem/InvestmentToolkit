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
│   ├── stock-valuation/        ← Bear/Base/Bull valuation model agent
│   ├── thesis-balancer/        ← Portfolio drift monitoring agent
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
- Always run `pip-compile` after modifying `.in` files.

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
