---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Fix Yahoo API Data & Backend Bridge"
phase: "Phase 1 - Foundation"
lane: "planned"
dependencies: []
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-02-08T02:11:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Fix Yahoo API Data & Backend Bridge

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- **Primary**: Fix the broken Yahoo Finance data integration so all reference values populate on the Valuation Modeler sliders.
- **Secondary**: Add analyst revenue/earnings forecast data for use by WP03 (forecast overlay).
- **Success Criteria**:
  - Searching for AAPL, NVDA, MSFT, INTC → all sliders show Yahoo reference values (Growth Rate, Net Margin, Forward P/E).
  - "Reset to Yahoo" button resets sliders to actual analyst estimates.
  - Backend returns `analyst_revenue_forecast` with high/low/avg for 2026-2027.
  - Tickers without analyst data show "N/A" with explanatory tooltip.

## Context & Constraints

- **Architecture**: Frontend (React 19/Vite) → Backend (Express/TS) → Python bridge (`fetch_financials.py`) → yfinance.
- **Current Bug**: All Yahoo reference values show "N/A%" — the Python script is likely not extracting the correct `stock.info` keys or the data mapping is broken.
- **Key Files**:
  - `tools/investment-screener/backend/py_services/fetch_financials.py` (204 lines) — Python yfinance data fetcher
  - `tools/investment-screener/backend/src/services/bridge.ts` (73 lines) — Node.js Python bridge
  - `tools/investment-screener/backend/src/index.ts` (33 lines) — Express server
  - `tools/investment-screener/frontend/src/services/api.ts` (66 lines) — Frontend API client + types
  - `tools/investment-screener/frontend/src/components/ValuationModeler.tsx` (374 lines) — Slider UI

## Implementation Command

No dependencies — start from main:
```bash
spec-kitty implement WP01
```

## Subtasks & Detailed Guidance

### Subtask T001 – Debug fetch_financials.py Missing Data

- **Purpose**: Identify exactly which yfinance fields are returning None/missing for major tickers.
- **Steps**:
  1. Run `python3 tools/investment-screener/backend/py_services/fetch_financials.py AAPL` and capture the full JSON output.
  2. Check the `analyst_estimates` section — are `revenue_growth`, `profit_margin`, `forward_pe` present and non-null?
  3. If missing, add debug logging: `print(stock.info.keys(), file=sys.stderr)` to see all available yfinance keys.
  4. Cross-reference with yfinance docs — the library has changed key names in recent versions.
  5. Common yfinance key changes:
     - `revenueGrowth` (not `revenue_growth`)
     - `profitMargins` (not `profit_margin`)
     - `forwardPE` (not `forward_pe`)
     - `sharesOutstanding` vs `shares_outstanding`
- **Files**: `backend/py_services/fetch_financials.py`
- **Parallel?**: No — this is the diagnostic step.
- **Notes**: Test with at least 3 tickers (AAPL, NVDA, INTC) to verify consistency.

### Subtask T002 – Fix yfinance Field Extraction

- **Purpose**: Correct the mapping between yfinance `stock.info` keys and the expected output JSON fields.
- **Steps**:
  1. In `fetch_financials.py`, locate where `analyst_estimates` dict is built (around line 150-180).
  2. Fix key mappings based on T001 findings. Likely fixes:
     ```python
     # Old (broken):
     'revenue_growth': info.get('revenue_growth'),
     # New (correct):
     'revenue_growth': info.get('revenueGrowth'),
     'profit_margin': info.get('profitMargins'),
     'forward_pe': info.get('forwardPE') or info.get('forwardPe'),
     ```
  3. Add share change estimation: compare current vs previous year `sharesOutstanding` from financial statements.
  4. Add safe fallback for each field: if key returns None, try alternative keys before falling back to None.
  5. Ensure NaN/numpy values are handled by the existing `NpEncoder` class.
- **Files**: `backend/py_services/fetch_financials.py`
- **Parallel?**: No — depends on T001.
- **Notes**: The `get_value()` helper already has try/except — extend it if needed.

### Subtask T003 – Add Analyst Revenue/Earnings Forecast Data

- **Purpose**: Extract analyst consensus revenue forecasts (high/low/avg) for current year and next year, needed by WP03 for chart overlays.
- **Steps**:
  1. Investigate available yfinance analyst data:
     ```python
     stock = yf.Ticker('AAPL')
     print(stock.analyst_price_targets)
     print(stock.earnings_estimate)
     print(stock.revenue_estimate)
     print(stock.earnings_forecasts)
     ```
  2. Extract revenue estimates for current year (2026) and next year (2027):
     ```python
     revenue_forecast = []
     if hasattr(stock, 'revenue_estimate') and stock.revenue_estimate is not None:
         for period in stock.revenue_estimate.columns:
             revenue_forecast.append({
                 'period': str(period),
                 'avg': float(stock.revenue_estimate.loc['avg', period]),
                 'low': float(stock.revenue_estimate.loc['low', period]),
                 'high': float(stock.revenue_estimate.loc['high', period]),
             })
     ```
  3. Similarly extract earnings estimates.
  4. Add to the output JSON under `analyst_revenue_forecast` and `analyst_earnings_forecast` keys.
- **Files**: `backend/py_services/fetch_financials.py`
- **Parallel?**: No — depends on T002.
- **Notes**: yfinance DataFrame column names may be period strings like "0q", "+1q", "0y", "+1y" — map these to actual years.

### Subtask T004 – Update Backend Response Handling

- **Purpose**: Ensure the Express server passes through the new forecast fields without modification.
- **Steps**:
  1. In `backend/src/index.ts`, the `/api/stock/:ticker` route already returns the full Python JSON output.
  2. Verify the bridge doesn't strip or modify fields — check `bridge.ts` `spawnPythonScript` return handling.
  3. If the response is being selectively mapped (not raw passthrough), add the new fields:
     - `analyst_revenue_forecast`
     - `analyst_earnings_forecast`
  4. Add basic validation: if Python returns an error object, forward it with appropriate HTTP status.
- **Files**: `backend/src/index.ts`, `backend/src/services/bridge.ts`
- **Parallel?**: No — depends on T003.
- **Notes**: The bridge likely does raw JSON passthrough — minimal changes expected here.

### Subtask T005 – Update Frontend StockData Interface

- **Purpose**: Add TypeScript types for new backend response fields.
- **Steps**:
  1. In `frontend/src/services/api.ts`, add to the `StockData` interface:
     ```typescript
     analyst_revenue_forecast?: Array<{
       period: string;
       avg: number;
       low: number;
       high: number;
     }>;
     analyst_earnings_forecast?: Array<{
       period: string;
       avg: number;
       low: number;
       high: number;
     }>;
     ```
  2. Ensure the `analyst_estimates` sub-interface has correct optional typing for `revenue_growth`, `profit_margin`, `forward_pe`.
- **Files**: `frontend/src/services/api.ts`
- **Parallel?**: Yes — can be done alongside T006.
- **Notes**: Keep fields optional (`?`) since not all tickers will have estimates.

### Subtask T006 – Fix ValuationModeler Yahoo Display

- **Purpose**: Make the Valuation Modeler correctly read and display Yahoo reference values below each slider.
- **Steps**:
  1. In `ValuationModeler.tsx`, locate where Yahoo reference values are displayed (look for "Yahoo:" text).
  2. The component already reads `stockData.analyst_estimates?.revenue_growth` etc. — the issue is backend returning null.
  3. Once T001-T004 fix the backend, verify the frontend reads correctly:
     - Growth Rate slider: `analyst_estimates.revenue_growth` → format as percentage
     - Net Margin slider: `analyst_estimates.profit_margin` → format as percentage
     - Exit P/E slider: `analyst_estimates.forward_pe` → format as "x" multiplier
     - Share Change: may need new field from backend
  4. Fix "Reset to Yahoo" button handler:
     - Currently resets active scenario from `analyst_estimates` fields
     - Verify the field mapping matches what backend now returns
     - If fields were renamed in T002, update the frontend mapping accordingly
  5. For N/A cases, show tooltip: "No analyst estimates available for {TICKER}"
- **Files**: `frontend/src/components/ValuationModeler.tsx`
- **Parallel?**: Yes — can be done alongside T005.
- **Notes**: The reset logic auto-populates bear (-5%), base, bull (+10%) from Yahoo values — ensure this still works.

## Risks & Mitigations

- **yfinance version changes**: Key names change between versions. Pin yfinance version in requirements.txt.
- **Rate limiting**: yfinance may throttle repeated requests. The spec calls for 15-minute caching — consider adding a simple file-based cache in a later WP.
- **Missing data for small-cap tickers**: Some tickers genuinely lack analyst coverage. Always handle None gracefully.

## Review Guidance

- Verify with at least 3 tickers: AAPL (large cap), NVDA (tech), INTC (turnaround — may have unusual metrics).
- Check that "Reset to Yahoo" button actually resets sliders to real values.
- Confirm `analyst_revenue_forecast` and `analyst_earnings_forecast` are populated in the API response (needed by WP03).

## Activity Log

- 2026-02-08T02:11:51Z – system – lane=planned – Prompt created.