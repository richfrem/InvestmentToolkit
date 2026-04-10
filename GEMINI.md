# GEMINI.md - InvestmentToolkit Context

## 🌟 Project Overview
**InvestmentToolkit** is a high-end investment analysis suite designed for sophisticated retail investors. It features a "Luxury Dark Mode" web dashboard, professional fundamental analysis tools, valuation modeling, and autonomous AI agents for deep-dive research and portfolio alignment.

### Core Stack:
- **Frontend**: React 19, Vite, Tailwind CSS 4.0.
- **Backend**: Node.js (Express) with a Python bridge for financial data.
- **Data Sources**: `yfinance` (real-time/historical) and Questrade API (brokerage sync).
- **AI Framework**: Autonomous agents built on a plugin architecture with Spec Kitty/Antigravity integration.

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
- **Lint Frontend**: `npm run lint -w frontend`

---

## 🧪 Testing

- **Backend Tests**: `npm run test -w backend` (Uses Mocha and Chai).
- **Plugin Evals**: Located in `plugins/{plugin-name}/skills/{skill-name}/evals/evals.json`.

---

## 📝 Development Conventions

Follow these non-negotiable standards (detailed in `.agent/rules/coding-conventions.md`):

1. **Dual-Layer Documentation**: 
   - External comment block above every non-trivial function/class.
   - Internal docstring (Python) or JSDoc (TS/JS) inside.
2. **File Headers**: Every source file must start with a purpose header.
3. **Type Safety**:
   - Python: Strict type hints in all function signatures.
   - TypeScript: Strong typing, avoid `any`.
4. **Naming Conventions**:
   - Python: `snake_case`.
   - TypeScript/JavaScript: `camelCase`.
5. **Refactor Rule**: Any function exceeding 50 lines or 3 levels of nesting must be refactored into helpers.
6. **Tool Registration**: New scripts in `plugins/` must be registered in `plugins/tool_inventory.json`.

---

## 🤖 AI Agent Commands

Interact with the autonomous analysts using these triggers:
- `/stock-valuation_evaluate-stock {TICKER}`: Performs full cognitive valuation analysis.
- `/thesis-balancer_review-portfolio`: Checks portfolio health and thesis alignment.

---

## 📂 Key Directories
- `docs/adrs/`: Architecture Decision Records (Read these to understand design choices).
- `investment_screener/backend/data/`: Persistence layer for projections and research reports.
- `plugins/`: This is where the two plugins stock-valuation and thesis-behavior are modified, the location in .agents are the installed folders.  run from .agents and use the plugins folder as the source of truth for the plugins.
- `.agents/skills/`: source of truth for agent skills, subagents, commands, workflows.  Use skills from here
