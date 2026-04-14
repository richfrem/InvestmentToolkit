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
├── plugins/                    ← AI agent plugins (stock-valuation, thesis-balancer)
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
python3 manage.py           # Full suite startup (from repo root)
```

> [!IMPORTANT]
> **NPM Path Mandate**: Always run npm commands from `investment_screener/`. Never use `--prefix investment_screener` from within `investment_screener/` — it doubles the path and fails.

---

## 🔐 Questrade Authentication & Security

The backend uses a stateful token rotation engine with **AES-256-GCM hardware-backed encryption** (macOS Keychain).

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

# Step 2: Seed the returned refresh_token into backend cache (--cache-dir required)
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
- Python deps: root `requirements.in` → compile with `pip-compile`
- Sub-services inherit via `-r ../../requirements.in`

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
