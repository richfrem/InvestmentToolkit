# GitHub Copilot Instructions — InvestmentToolkit

## 🌟 Project Overview
**InvestmentToolkit** is a high-end investment analysis suite for sophisticated retail investors. It features a "Luxury Dark Mode" web dashboard, fundamental analysis tools, valuation modeling, and autonomous AI agents for deep-dive research and portfolio alignment.

### Core Stack
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
├── plugins/                    ← AI agent plugins (stock-valuation, thesis-balancer, toolkit-manager)
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

## 📦 Dependency Management
- Python deps: root `requirements.in` → compile with `pip-compile requirements.in -o requirements.txt`
- Sub-services inherit via `-r ../../requirements.in`
- The startup script installs from `requirements.txt` — new Python imports **must** be in `requirements.in` or the venv will be missing them at runtime

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
