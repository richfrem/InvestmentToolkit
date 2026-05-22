# ADR 025 — Deliberate Testing Architecture Segmentation in the InvestmentToolkit Monorepo

**Date:** 2026-05-21
**Status:** Accepted
**Deciders:** richfrem, Antigravity (AI Architect)
**Scope:** Root test suite (tests/), backend test suite (investment_screener/backend/tests/), monorepo testing conventions

---

## Context
The **InvestmentToolkit** is a highly complex, hybrid monorepo consisting of multiple distinct runtimes and programming languages working in concert:
1. **Node.js/Express Backend:** Serves the API, rotates Questrade tokens, and bridges Python services.
2. **React/Vite Frontend:** Renders the "Luxury Dark Mode" analytics workspace.
3. **Python Analytical Engine:** Powers DCF valuations, SEC 13F parsing, and thesis synchronization.
4. **TradingView CDP Engine:** A standalone, shared Node.js automation utility at `tradingview-cdp/`.

Due to this multi-language architecture, the workspace historically developed two separate test folders:
- `/tests` at the project root.
- `/investment_screener/backend/tests` inside the backend sub-workspace.

To a developer expecting a single monolithic `test/` directory, this segmentation might appear redundant. We needed to formally document the architectural rationale behind this structure and define clear guidelines for where future tests must be authored.

## Decision
We formally adopt and codify a **segmented, multi-tiered testing architecture** structured into two distinct boundaries:

### Tier 1: Global Orchestration & Integration Gate (Root `/tests`)
The root `tests/` directory is reserved for **monorepo-wide sanity gates, cross-runtime parity verifications, and regression tests** that span across multiple folders.
* **Key Artifacts:**
  - `run_tests.py` (T0/T0.5 Compile/Syntax Gate): The primary monorepo orchestrator. Compiles TypeScript frontend and backend, verifies Python/Node syntax across core scripts, validates symlink path invariance (symlink CWD invariance), and checks for stale path regressions.
  - `test_math_parity.py`: Runs monte-carlo parity checks between Python's quantitative engine (`dcf_scenarios.py`) and TypeScript's frontend math engine (`math_cli.js`) to guarantee they produce identical DCF valuations.
  - `validate_all_projections.py`: Audits quantitative output integrity across all saved JSON records.
* **Execution:** Run globally from the project root using `python3 tests/run_tests.py`.

### Tier 2: Isolated Package Unit & Service Tests (`/investment_screener/backend/tests`)
This folder is dedicated entirely to the **unit, integration, and mock-based testing of backend business logic, API endpoints, and database engines**.
* **Key Artifacts:**
  - `api/` and `services/` (Mocha/Chai/TypeScript): Asserts the correctness of Express routers, local helpers, and JSON persistence utilities (e.g. `stockLookup.spec.ts` for fuzzy search lookup, `portfolioSnapshot.spec.ts` for aggregated cash/holding balances).
  - `py_services/` (Pytest/Python): Asserts the correctness of Python modules run inside the backend service (e.g., `test_verify_thesis_sync.py` and `test_place_order_gates.py` for pre-placement validation).
* **Execution:** Run locally inside the backend workspace using `npm test -w backend` (for Mocha specs) and `pytest` (for Python unit tests).

---

## Consequences

### Positive
* **Dependency Isolation:** Prevents root-level package pollution. Test packages (like Mocha, Chai, ts-node, pytest) are defined locally within the sub-workspaces, keeping the root environment clean.
* **Configuration Clarity:** TS compiler options (`tsconfig.json`) and Python virtual environments stay isolated to their respective runtime boundaries without namespace clashes.
* **Developer Velocity:** Allows developers working on the Express API or specific backend utilities to run fast, targeted unit test suites (e.g., `npm test -w backend` taking <10ms) without triggering heavy cross-runtime math calculations.
* **TDD Enforcement:** Simplifies enforcement of **The Iron Law of TDD** (no production code without a failing test first) by providing instant feedback loop capabilities.

### Negative
* **Learning Curve:** Developers must learn separate test runners and commands depending on their work focus (`python3 tests/run_tests.py` for monorepo-wide gates, `npm test -w backend` for backend Node code, `pytest` for backend Python code).
* **Configuration Overhead:** Minor duplication of path and environment setups across different test runners.

---

## Alternatives Considered

### 1. Unified Root Test Directory
Placing all backend and integration tests inside a single root-level `test/` directory.  
* **Why Rejected:** This forces a single hybrid configuration, pollutes the root workspace with heavy Node test packages, complicates CI pipeline design, and breaks the clean boundary between self-contained monorepo packages.

### 2. Standardizing purely on Pytest for all runtimes
Running Mocha/Chai specs by wrapping them inside Python subprocesses executed by Pytest.  
* **Why Rejected:** Adds severe execution overhead and destroys the native developer experience (including VS Code/Cursor test runner integration, hot-reloading, and autocomplete) during TypeScript backend development.
