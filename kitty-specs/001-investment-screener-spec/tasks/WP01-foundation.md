---
work_package_id: WP01
title: Foundation & Backend Core
lane: "done"
dependencies: []
base_branch: main
base_commit: bfc8cd252bba1c40a49b5251c2c16fceed74cd32
created_at: '2026-02-07T19:11:46.196437+00:00'
subtasks: [T001, T002, T003, T004, T005, T006]
shell_pid: "15842"
---

# Work Package 01: Foundation & Backend Core

**Goal**: Initialize the project structure, set up the Node.js backend with a Python bridge, and implement the core data fetching logic using `yfinance`.

**Implementation Command**:
`spec-kitty implement WP01`

---

### Subtask T001: Initialize Project Structure & Configurations
**Purpose**: Set up the monorepo structure and shared dependencies.
**Steps**:
1.  Initialize `tools/investment-screener/` with `backend/` and `frontend/` folders.
2.  Create root `package.json` for workspace management.
3.  Initialize `backend/package.json` (Express, CORS, TypeScript).
4.  Initialize `frontend/` using Vite (React + TypeScript) - just scaffolding.
5.  Create `.gitignore` handling Node modules, Python venv, and environment files.

### Subtask T002: Create Startup Script & Environment
**Purpose**: Ensure a single command launches the entire application.
**Steps**:
1.  Create `startup.sh` in project root:
    - Check for `Node.js` and `Python 3.11+`.
    - Check for `.env` or `QUESTRADE_REFRESH_TOKEN` in shell (per plan).
    - Install backend/frontend dependencies.
    - Create Python virtualenv and install `yfinance`.
    - Trap SIGINT to kill both processes on exit.
2.  Create `.env.example` with placeholder `QUESTRADE_REFRESH_TOKEN`.

### Subtask T003: Setup Express Backend
**Purpose**: foundational backend server.
**Steps**:
1.  Create `backend/src/index.ts`:
    - Express app setup.
    - CORS (allow localhost:5173).
    - Basic health check endpoint `/health`.
    - Error handling middleware.
2.  Configure `backend/tsconfig.json`.

### Subtask T004: Implement Python Bridge Service
**Purpose**: Node.js service to spawn Python processes for data fetching.
**Steps**:
1.  Create `backend/src/services/bridge.ts`:
    - Function `spawnPythonScript(script: string, args: string[]): Promise<any>`.
    - Use `child_process.spawn`.
    - Collect stdout, parse as JSON.
    - Handle stderr and exit codes.
2.  Ensure paths to `py_services/` are absolute or correctly resolved.

### Subtask T005: Implement Financials Fetcher (Python)
**Purpose**: The core logic to fetch and process stock data.
**Steps**:
1.  Create `backend/py_services/fetch_financials.py`.
2.  Implement `fetch_data(ticker)`:
    - `yf.Ticker(ticker)`.
    - Fetch `info` (Profile, Sector, Price).
    - Fetch `financials`, `balance_sheet`, `cashflow` (Quarterly & Annual).
3.  **Implement Expert Logic**:
    - **Piotroski F-Score**: Calculate 0-9 score based on GAAP metrics. Handle missing data by returning "null" or "partial".
    - **Rule of 40**: Calculate (Revenue Growth % + EBITDA Margin %). Note if TTM or Annual.
4.  Output JSON to stdout.

### Subtask T006: Backend Tests
**Purpose**: Verify the bridge and data fetching work.
**Steps**:
1.  Setup Mocha/Chai for Node.js tests.
2.  Determine if Pytest is strictly necessary or if Node integration tests suffice (Plan calls for "py_services test").
    - Create simple `backend/tests/test_bridge.spec.ts`: Call actual Python script with "AAPL", verify JSON structure features "revenue", "piotroski_score".

---

**Definition of Done**:
- [ ] `startup.sh` successfully launches backend and install dependencies.
- [ ] `curl localhost:3001/health` returns 200.
- [ ] Backend can successfully fetch AAPL data from yfinance via Python bridge.
- [ ] JSON response includes calculated Rule of 40 and Piotroski score.
