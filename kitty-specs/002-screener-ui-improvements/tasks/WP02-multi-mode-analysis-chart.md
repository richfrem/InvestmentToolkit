---
work_package_id: "WP02"
title: "Multi-Mode Analysis Chart"
lane: "planned"
dependencies: ["WP01"]
subtasks: ["T007", "T008", "T009", "T010", "T011", "T012"]
---

# Work Package: Multi-Mode Analysis Chart
**Priority**: P1 (MVP Feature)
**Goal**: Consolidate analysis charts into a single dynamic view with toggle buttons for Revenue, FCF, Margins, and EPS.

## Context
The current Analysis tab is cluttered with fixed charts. Users want to toggle between different financial views without scrolling. We need a "FinancialChart" component that can render different data series based on user selection.

## Subtasks

### T007: Extend `fetch_financials.py` with historical data
**Objective**: Fetch 4-5 years of history for FCF, Margins, and EPS.
**Files**: `tools/investment-screener/backend/py_services/fetch_financials.py`
**Guidance**:
- Calculate Historical Margins: `Gross Profit / Revenue`, `Operating Income / Revenue`, `Net Income / Revenue` for each year.
- Calculate Historical FCF: `Operating Cash Flow - CapEx` (from cashflow statement).
- Calculate Historical EPS: `Basic EPS` (from financials).
- Return as arrays in JSON: `historical_fcf`, `historical_gross_margin`, etc.

### T008: Update `api.ts` interface
**Objective**: Add new historical arrays to frontend types.
**Files**: `tools/investment-screener/frontend/src/services/api.ts`
**Guidance**:
- Add `historical_fcf: number[]`, `historical_gross_margin: number[]`, etc., to `FinancialData` interface.

### T009: Create `AnalysisChartToggle` component
**Objective**: Build the UI control for switching views.
**Files**: `tools/investment-screener/frontend/src/components/analysis/AnalysisChartToggle.tsx` (NEW)
**Guidance**:
- Props: `activeMode: string`, `onModeChange: (mode: string) => void`.
- Modes: 'revenue', 'fcf', 'margins', 'eps'.
- Apply "Luxury Dark" styling (active state = amber text/border, inactive = gray).

### T010: Refactor to generic `FinancialChart`
**Objective**: Create a chart component that accepts dynamic data/config.
**Files**: `tools/investment-screener/frontend/src/components/analysis/FinancialChart.tsx` (REFACTOR/NEW)
**Guidance**:
- Adapt `FundamentalChart.tsx`.
- Props: `data: any[]`, `mode: string`.
- Logic:
  - If mode=='revenue': Render Area (Revenue) + Bar (Earnings).
  - If mode=='fcf': Render Bar (FCF).
  - If mode=='eps': Render Line (EPS).
- Maintain existing Recharts styling (colors, tooltips).

### T011: Build Margins chart variant
**Objective**: Implement the visualization for the 'margins' mode.
**Files**: `tools/investment-screener/frontend/src/components/analysis/FinancialChart.tsx`
**Guidance**:
- Render 3 lines/areas:
  - Gross Margin (Top/Lightest)
  - Operating Margin (Middle)
  - Net Margin (Bottom/Darkest or Accent)
- Y-axis should be percentage formatted.

### T012: Update Dashboard Analysis tab
**Objective**: Replace the old layout with the new toggle + chart system.
**Files**: `tools/investment-screener/frontend/src/components/Dashboard.tsx`
**Steps**:
1. Remove `RuleOf40Chart` (will move in WP04).
2. Add `AnalysisChartToggle` at the top of the Analysis card.
3. Manage `activeChartMode` state.
4. Render `FinancialChart` with data corresponding to the active mode.

## Validation
- **Manual Test**: Click "Analysis" tab.
- **Success Criteria**:
  - 4 toggle buttons visible.
  - Default view is Revenue & Earnings.
  - Clicking "Margins" switches chart to show 3 margin lines.
  - Switching is instant (no loading spinner).

## Risks
- Data gaps (e.g., missing FCF for banks) -> Component should render "Data Unavailable" or empty chart comfortably.