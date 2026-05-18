# Task 0003 Implementation Plan: Standardize Temp Paths & Refresh Projections

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standardize temp output paths across Python scripts to use `InvestmentToolkit/temp/` and re-evaluate stale DCF projections.

**Architecture:** A utility function will manage the path creation for temp files. A batch script will orchestrate re-evaluating the stale tickers.

**Tech Stack:** Python, Bash.

---

### Task 1: Setup Temp Directory

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add `temp/` to `.gitignore`**

```bash
echo "temp/" >> .gitignore
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add temp directory to gitignore"
```

### Task 2: Standardize Python Scripts

**Files:**
- Create/Modify: `investment_screener/backend/py_services/utils/paths.py` (if it exists, else add `get_temp_dir()`)
- Modify: Scripts writing to `/tmp/` (e.g., `fetch_financials.py`, `dcf_scenarios.py`)

- [ ] **Step 1: Create utility function**

```python
import os
def get_temp_dir() -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    temp_dir = os.path.join(root, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir
```
*(Add this to the relevant utils file and import it across scripts)*

- [ ] **Step 2: Replace `/tmp/` references in scripts**
Search for `/tmp/` in `investment_screener/backend/py_services/` and `plugins/` and replace with the output of `get_temp_dir()`.

- [ ] **Step 3: Run tests**
`python3 tests/run_tests.py`

- [ ] **Step 4: Commit**
```bash
git add .
git commit -m "refactor: standardize temp paths to use InvestmentToolkit/temp/"
```

### Task 3: Refresh Stale Projections

**Files:**
- Modify: `backend/data/projections/*.json`

- [ ] **Step 1: Get the list of stale tickers**
Run `python3 tests/validate_all_projections.py` to get the list of tickers.

- [ ] **Step 2: Run `/evaluate-stock` on each ticker**
This step is likely manual or orchestrated by an agent via the stock-valuation plugin.

- [ ] **Step 3: Verify all projections pass**
Run `python3 tests/validate_all_projections.py` and ensure 0 mismatches.

- [ ] **Step 4: Commit**
```bash
git add investment_screener/backend/data/projections/
git commit -m "chore: refresh stale DCF projections"
```