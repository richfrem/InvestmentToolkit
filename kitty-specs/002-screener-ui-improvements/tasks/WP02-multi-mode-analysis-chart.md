---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
title: "Multi-Mode Analysis Chart"
phase: "Phase 2 - Core Features"
lane: "planned"
dependencies: ["WP01"]
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

# Work Package Prompt: WP02 – Multi-Mode Analysis Chart

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Replace the fixed Analysis tab layout with a single chart area + toggle buttons.
- Four chart modes: Revenue & Earnings (default), Free Cash Flow, Margins, EPS Growth.
- Switching modes is instant (< 100ms) — no additional API calls.
- All data fetched in the single `/api/stock/:ticker` call.

## Context & Constraints

- **Current Analysis tab**: 2-column grid showing `RuleOf40Chart` (left) + `FundamentalChart` (right).
- **After this WP**: Analysis tab shows only the financial chart with toggle buttons. Rule of 40 moves to its own tab (WP04).
- **Charts library**: Recharts (already in use).
- **Data flow**: Backend returns all historical arrays; frontend selects which to render.
- **Key Files**:
  - `frontend/src/components/Charts/FundamentalChart.tsx` (70 lines)
  - `frontend/src/components/Charts/RuleOf40Chart.tsx` (69 lines)
  - `frontend/src/pages/Dashboard.tsx` (139 lines)
  - `frontend/src/services/api.ts` (66 lines)
  - `backend/py_services/fetch_financials.py` (204 lines)

## Implementation Command

Depends on WP01:
```bash
spec-kitty implement WP02 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T007 – Extend fetch_financials.py with FCF, Margins, EPS History

- **Purpose**: The backend currently only returns `historical_revenue` and `historical_net_income`. We need additional 5-year arrays for the chart modes.
- **Steps**:
  1. In `fetch_financials.py`, after the existing historical data extraction, add:
     ```python
     # Free Cash Flow (from cashflow statement)
     historical_fcf = []
     if cashflow is not None and not cashflow.empty:
         for col in cashflow.columns[:5]:  # Last 5 years
             try:
                 fcf = cashflow.loc['Free Cash Flow', col]
                 historical_fcf.append(float(fcf) if fcf is not None else 0)
             except (KeyError, TypeError):
                 historical_fcf.append(0)

     # Margins (from income statement + revenue)
     historical_margins = {
         'gross': [],    # Gross Profit / Revenue
         'operating': [], # Operating Income / Revenue
         'net': []        # Net Income / Revenue
     }

     # EPS history
     historical_eps = []
     ```
  2. Extract gross margin: `Gross Profit / Total Revenue` per year.
  3. Extract operating margin: `Operating Income / Total Revenue` per year.
  4. Extract net margin: `Net Income / Total Revenue` per year.
  5. Extract EPS: `stock.info.get('trailingEps')` for current, historical from earnings data.
  6. Add all to the output JSON under `financials`:
     ```python
     'financials': {
         'historical_revenue': [...],
         'historical_net_income': [...],
         'historical_fcf': [...],
         'historical_margins': { 'gross': [...], 'operating': [...], 'net': [...] },
         'historical_eps': [...]
     }
     ```
- **Files**: `backend/py_services/fetch_financials.py`
- **Notes**: Arrays should be ordered oldest→newest, matching existing convention. Use `reversed(cashflow.columns)` if needed.

### Subtask T008 – Update api.ts StockData Interface

- **Purpose**: Add TypeScript types for the new financial arrays.
- **Steps**:
  1. Extend the `financials` section of `StockData`:
     ```typescript
     financials: {
       historical_revenue: number[];
       historical_net_income: number[];
       historical_fcf: number[];
       historical_margins: {
         gross: number[];
         operating: number[];
         net: number[];
       };
       historical_eps: number[];
     };
     ```
- **Files**: `frontend/src/services/api.ts`

### Subtask T009 – Create AnalysisChartToggle Component

- **Purpose**: A button group component for switching between chart modes.
- **Steps**:
  1. Create `frontend/src/components/Charts/AnalysisChartToggle.tsx`.
  2. Props:
     ```typescript
     type ChartMode = 'revenue' | 'fcf' | 'margins' | 'eps';
     interface Props {
       activeMode: ChartMode;
       onModeChange: (mode: ChartMode) => void;
     }
     ```
  3. Render 4 buttons in a horizontal row:
     - "Revenue & Earnings" (default, active)
     - "Free Cash Flow"
     - "Margins"
     - "EPS Growth"
  4. Style: Luxury Dark theme — inactive buttons use `bg-slate-800 text-slate-400`, active uses `bg-amber-500/20 text-amber-400 border-amber-500`.
  5. Compact sizing: `px-3 py-1.5 text-sm rounded-lg`.
- **Files**: `frontend/src/components/Charts/AnalysisChartToggle.tsx` (new, ~50 lines)

### Subtask T010 – Refactor FundamentalChart to Generic FinancialChart

- **Purpose**: Make the chart component accept different data series based on active mode.
- **Steps**:
  1. Rename `FundamentalChart.tsx` → `FinancialChart.tsx` (or create new and deprecate old).
  2. New props:
     ```typescript
     interface Props {
       stockData: StockData;
       mode: ChartMode;
     }
     ```
  3. Based on `mode`, select the correct data and chart configuration:
     - `revenue`: Revenue (green area) + Net Income (amber area) — existing behavior
     - `fcf`: Free Cash Flow (single blue area)
     - `margins`: 3 lines (gross=green, operating=amber, net=red) — use LineChart
     - `eps`: EPS bars (use BarChart)
  4. Transform the raw arrays into Recharts-compatible `{ year, value1, value2 }` format.
  5. Dynamic Y-axis formatting: currency for revenue/fcf, percentage for margins, currency for EPS.
  6. Chart title changes based on mode.
- **Files**: `frontend/src/components/Charts/FinancialChart.tsx` (refactored, ~150 lines)
- **Notes**: Keep the Luxury Dark color scheme consistent. Use `fill="url(#colorGradient)"` patterns from existing chart.

### Subtask T011 – Build Margins Chart Variant

- **Purpose**: The Margins mode needs 3 overlapping lines, distinct from the area charts used by other modes.
- **Steps**:
  1. Within `FinancialChart.tsx`, the `margins` mode should render a `LineChart` with:
     - Gross Margin: `stroke="#22c55e"` (green)
     - Operating Margin: `stroke="#f59e0b"` (amber)
     - Net Margin: `stroke="#ef4444"` (red)
  2. Y-axis formatted as percentage (e.g., "30%").
  3. Legend showing all three margin types.
  4. Tooltip showing year + all three margin values.
  5. Reference line at 0% if any margin goes negative.
- **Files**: `frontend/src/components/Charts/FinancialChart.tsx`
- **Parallel?**: Yes — can be built independently as a mode branch within the chart component.

### Subtask T012 – Update Dashboard Analysis Tab

- **Purpose**: Wire the new toggle and chart into the Dashboard.
- **Steps**:
  1. In `Dashboard.tsx`, add state for chart mode:
     ```typescript
     const [chartMode, setChartMode] = useState<ChartMode>('revenue');
     ```
  2. Replace the Analysis tab content (currently 2-column grid with RuleOf40Chart + FundamentalChart) with:
     ```tsx
     <AnalysisChartToggle activeMode={chartMode} onModeChange={setChartMode} />
     <FinancialChart stockData={stockData} mode={chartMode} />
     ```
  3. Remove the `RuleOf40Chart` import from the Analysis tab (it moves to its own tab in WP04).
  4. The chart area should take full width of the content area.
- **Files**: `frontend/src/pages/Dashboard.tsx`
- **Notes**: Don't delete `RuleOf40Chart.tsx` — WP04 will reuse it in a dedicated tab.

## Risks & Mitigations

- Some tickers may not have FCF or margin history from yfinance → show "Insufficient data for this view" message.
- EPS history may only be available for 2-3 years for newer companies → chart renders whatever is available.

## Review Guidance

- Toggle between all 4 chart modes and verify data renders correctly.
- Check Revenue & Earnings mode matches the old FundamentalChart output.
- Verify no additional API calls are made when switching modes.

## Activity Log

- 2026-02-08T02:11:51Z – system – lane=planned – Prompt created.