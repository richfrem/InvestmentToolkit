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

### 1. Main Application (`investment_screener/`)
- **`frontend/`**: Vite-powered React app. Uses Recharts and D3 for visualizations.
- **`backend/`**: Node.js API server that orchestrates data from Python services.
- **`backend/py_services/`**: Python scripts for `yfinance` data fetching and Questrade authentication.

### 2. Plugin Ecosystem (`plugins/`)
Modular AI capabilities implemented as portable plugins:
- **Stock Valuation (`plugins/stock-valuation`)**: Buy-side analyst agent that generates Bear/Base/Bull valuation models and research reports.
- **Thesis Balancer (`plugins/thesis-balancer`)**: Strategic guardian agent that monitors portfolio drift against a core investment thesis.

### 3. Agent Configuration (`.agents/`)
Contains the brains of the AI agents, including specialized skills, prompts, and evaluation suites.

---

## 🤖 AI Development: Exploration Workflow
We have pivoted away from Spec Kitty and now use the **Exploration Workflow** (a modification of the orba/superpowers plugin) for building and discovery.

### Canonical Workflow:
1.  **Intake**: Invoke the `intake-agent` (`.agents/agents/exploration-cycle-plugin-intake-agent.md`) to clarify intent and pre-fill the session brief.
2.  **Orchestration**: The `exploration-workflow` skill manages the 4-phase loop via `exploration/exploration-dashboard.md`.
3.  **Phase 1 — Problem Framing**: Uses `discovery-planning` skill to define requirements.
4.  **Phase 2 — Visual Blueprinting**: Uses `visual-companion` to confirm design.
5.  **Phase 3 — Prototyping**: Uses `subagent-driven-prototyping` for iterative building.
6.  **Phase 4 — Handoff & Specs**: Uses `exploration-handoff` to generate final technical specs.

### Key Agents:
- **Intake Agent**: Front-door interviewer for clarifying domain and nature of exploration.
- **Exploration Orchestrator Agent**: Director for Phase A discovery sessions, requirements capture, and handoff prep.

---

## 🚀 Building and Running

The project uses a unified management script to handle dependencies and services.

### Complete Suite Startup:
```bash
python3 manage.py
```
*This command creates the Python venv, installs all dependencies (npm & pip), builds the backend, and launches both services.*

### Individual Service Commands:
- **Backend Dev**: `npm run dev -w backend` (Runs on port 3001)
- **Frontend Dev**: `npm run dev -w frontend` (Runs on port 5173)
- **Build Backend**: `npm run build -w backend`
- **Build Frontend**: `npm run build -w frontend`
- **Lint Frontend**: `npm run lint -w frontend`

---

## 📦 Dependency Management
Python dependencies are tracked in the root **`requirements.in`**.
- Sub-services (like `backend`) inherit from this using `-r ../../requirements.in`.
- Always run `pip-compile` after modifying `.in` files to update `requirements.txt`.

---

## 🔐 Authentication & Security (Questrade)
The project uses a professional-grade brokerage sync engine for Questrade, prioritizing security through hardware-backed encryption and stateful token rotation.

### 1. Stateful Token Rotation (ADR 015)
Questrade refresh tokens are **single-use**. To prevent loss of access, the system implements an **Atomic Swap** pattern:
1. **Fetch**: Retrieve the current encrypted token from the local cache (`.questrade_cache`).
2. **Redeem**: Exchange the token via Questrade's OAuth2 API for a new session.
3. **Rotate**: Write the *new* refresh token to a temporary file and perform an atomic rename to `.questrade_cache`.
4. **Fallback**: If the cache is missing or invalid, the system falls back to the `QUESTRADE_REFRESH_TOKEN` environment variable (the "Seed").

### 2. Hardware-Backed Encryption (ADR 019)
Tokens are never stored in plaintext.
- **Algorithm**: AES-256-GCM for authenticated encryption.
- **Master Key**: Managed via the **macOS Keychain** (using the `keyring` Python library). The key never leaves the secure hardware enclave.
- **Storage**: The encrypted payload is stored in `.questrade_cache` (binary format), which is rigorously ignored by git.

### 3. Setup & Onboarding
Users seed the system once using a one-week application token from the Questrade API Centre. After the initial seed, the engine handles all token rotation automatically via `.questrade_cache`. The `QUESTRADE_REFRESH_TOKEN` env var is only an emergency fallback.

**Full setup protocol**: See `docs/architecture/Questrade/questrade_token_setup.md`

**Quick reference — seed from repo root:**
```bash
# Step 1: Redeem a one-week app token (must include -d '' to avoid HTTP 411)
curl -s -X POST \
  "https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=<ONE_WEEK_TOKEN>" \
  -d '' -H 'Content-Type: application/x-www-form-urlencoded'

# Step 2: Seed the returned refresh_token into the backend cache dir
python3 investment_screener/backend/src/QuestradeDataEngine.py \
  --seed "<refresh_token>" \
  --cache-dir investment_screener/backend/

# Step 3: Verify via the API (backend must be running on port 3001)
curl -s -X POST http://localhost:3001/api/portfolio/sync-questrade \
  -H 'Content-Type: application/json' -d '{}'
```

> **Cache path matters**: The Node backend resolves its cache to `investment_screener/backend/.questrade_cache`. Always include `--cache-dir investment_screener/backend/` when seeding from the repo root.

### ⚠️ Agent Token Expiry Protocol
Questrade refresh tokens can expire. **If you (as an agent) encounter `Token rotation failed: 400`:**
1. Inform the user: *"Your Questrade token has expired and needs to be refreshed."*
2. Ask them to visit [apphub.questrade.com](https://apphub.questrade.com/UI/UserApps.aspx) and generate a new **One-Week App Token**
3. Once they provide it, redeem it via curl, seed it with `QuestradeDataEngine.py --seed ... --cache-dir investment_screener/backend/`, and verify via the API — the user does not need to do any of this manually.

---
