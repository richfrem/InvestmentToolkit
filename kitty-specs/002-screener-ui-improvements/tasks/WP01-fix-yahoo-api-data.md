---
work_package_id: "WP01"
title: "Fix Yahoo API Data & Backend Bridge"
lane: "doing"
dependencies: []
subtasks: ["T001", "T002", "T003", "T004", "T005", "T006"]
agent: "Gemini"
shell_pid: "96248"
---

# Work Package: Fix Yahoo API Data & Backend Bridge
**Priority**: P0 (Critical Path)
**Goal**: Restore data flow from Yahoo Finance so valuation metrics (Growth, Margins, P/E) and new Analyst Forecasts populate correctly.

## Context
The current `fetch_financials.py` script is failing to retrieve key metrics because `yfinance` field names or data structures have changed. This causes "Yahoo: N/A%" to appear on all sliders, breaking the valuation modeler's core value proposition. We also need to add analyst forecast data to support WP03.

## Subtasks

### T001: Debug `fetch_financials.py`
**Objective**: Identify why `revenue_growth`, `profit_margin`, `forward_pe` return None/N/A.
**Files**: `tools/investment-screener/backend/py_services/fetch_financials.py`
**Steps**:
1. Run script locally: `python3 fetch_financials.py AAPL`
2. Inspect raw `yfinance` output (`stock.info`, `stock.financials`).
3. specific fields to check: `revenueGrowth`, `profitMargins`, `forwardPE`, `trailingPE`.
4. Document findings if keys have merely changed case or name.

### T002: Fix yfinance field extraction
**Objective**: Update the script to interpret `stock.info` correctly and fallback gracefully.
**Files**: `tools/investment-screener/backend/py_services/fetch_financials.py`
**Guidance**:
- Map `revenue_growth` ← `info.get('revenueGrowth', 0)`
- Map `profit_margin` ← `info.get('profitMargins', 0)`
- Map `forward_pe` ← `info.get('forwardPE', 0)` or fallback to `trailingPE`
- Implement robust fallback: if 0/None, return 0 (frontend handles "N/A" display logic).

### T003: Add analyst forecast data extraction
**Objective**: Extract revenue and earnings estimates for current (2026) and next (2027) fiscal years.
**Files**: `tools/investment-screener/backend/py_services/fetch_financials.py`
**Guidance**:
- Use `stock.revenue_estimate` and `stock.earnings_estimate` (DataFrames).
- Extract `avg`, `low`, `high` for rows `0e` (current) and `+1e` (next).
- Structure output as:
  ```json
  "analyst_revenue_forecast": [
    {"year": 2026, "high": 100, "low": 80, "avg": 90},
    {"year": 2027, "high": 120, "low": 90, "avg": 105}
  ]
  ```
- Handle empty DataFrames gracefully (return empty list).

### T004: Update backend response handling
**Objective**: Ensure the Node.js API passes the new fields to the frontend.
**Files**: `tools/investment-screener/backend/src/index.ts`
**Steps**:
1. Verify `fetch_financials.py` output is correctly parsed as JSON.
2. Ensure no fields are stripped before sending `res.json(data)`.
3. (Optional) Add logging for the number of forecast years found.

### T005: Update `api.ts` interfaces
**Objective**: Update frontend types to match the new data structure.
**Files**: `tools/investment-screener/frontend/src/services/api.ts`
**Guidance**:
- Update `StockData` interface to include `analyst_revenue_forecast` and `analyst_earnings_forecast`.
- Ensure types match the JSON structure from T003.

### T006: Fix ValuationModeler Yahoo display
**Objective**: Wire up the UI to read the corrected data.
**Files**: `tools/investment-screener/frontend/src/components/ValuationModeler.tsx`
**Steps**:
1. In `useEffect` or data loading hook, ensure `stockData.metrics` values are being read.
2. Update the "Yahoo: N/A%" text logic:
   - If value > 0, display `Yahoo: {value}%`.
   - If 0/undefined, display `Yahoo: N/A` with tooltip.
3. Wire "Reset to Yahoo" button to set slider value to `stockData.metrics.revenue_growth` (etc.) if valid.

## Validation
- **Manual Test**: Run application, search `NVDA`.
- **Success Criteria**:
  - Growth Rate slider shows a real % (e.g., "Yahoo: 55%") below it.
  - Net Margin slider shows a real % (e.g., "Yahoo: 50%").
  - "Reset to Yahoo" button updates the slider knob.
  - API response (`/api/stock/NVDA`) contains `analyst_revenue_forecast` array.

## Risks
- Yahoo Finance HTML changes frequently; `yfinance` might need an upgrade (`pip install --upgrade yfinance`).
- Some tickers genuinely lack data; ensure UI doesn't crash.

## Activity Log

- 2026-02-08T02:40:05Z – Gemini – shell_pid=96248 – lane=doing – Started implementation via workflow command
