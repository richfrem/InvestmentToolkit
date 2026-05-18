# Task 0003 Design: Standardize Temp Paths & Refresh Projections

## 1. Overview
This spec addresses Task 0003, which involves standardizing temporary file outputs to a dedicated `temp/` folder at the repo root and re-evaluating 23 stocks with stale DCF projections.

## 2. Architecture & Components

### 2.1 Standardizing Temp Output Paths
- **Current State:** Python scripts (`fetch_financials.py`, `dcf_scenarios.py`, `place_order.py`, etc.) write intermediate files to `/tmp/`.
- **Proposed State:** All scripts will use `InvestmentToolkit/temp/`. We will create a utility function `get_temp_dir()` in `investment_screener/backend/py_services/utils/paths.py` (or similar) that resolves to `os.path.join(REPO_ROOT, 'temp')` and ensures the directory exists.
- **Gitignore:** The `temp/` directory will be added to `.gitignore`.

### 2.2 Refreshing Stale DCF Projections
- **Current State:** `validate_all_projections.py` flags ~23 tickers where `aiThesis.action` or `fairValue` doesn't match the current DCF math (due to price drift or legacy missing fields).
- **Proposed State:** We will use the existing `/evaluate-stock` skill/command to re-run full valuations on these flagged tickers, generating fresh `backend/data/projections/<TICKER>.json` files and updating their status.

## 3. Data Flow
1. **Path Updates:** Python files are updated to use the new `temp/` directory via the utility function.
2. **Re-Evaluation:** A script or manual process invokes the evaluation flow on the stale tickers to overwrite the stale data.
3. **Verification:** `python3 tests/validate_all_projections.py` is run to confirm 0 mismatches.