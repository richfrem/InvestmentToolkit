---
work_package_id: WP03
title: Analyst Forecast Overlay
lane: planned
dependencies:
- WP01
subtasks: [T013, T014, T015, T016, T017]
---

# Work Package: Analyst Forecast Overlay
**Priority**: P1
**Goal**: Visualize analyst revenue and earnings estimates for 2026-2027 on the primary chart.

## Context
Users want to see where the street thinks the stock is going. We need to overlay the forecast data (fetched in WP01) onto the Revenue & Earnings chart (built in WP02).

## Subtasks

### T013: Verify structured forecast data
**Objective**: Confirm backend (WP01) is returning the `analyst_revenue_forecast` structure correctly.
**Files**: `tools/investment-screener/backend/src/index.ts` (Review only)
**Guidance**:
- Quick check to ensure no regression from WP01.

### T014: Update `api.ts` (if needed)
**Objective**: Ensure forecast types are available to the chart component.
**Files**: `tools/investment-screener/frontend/src/services/api.ts`
**Guidance**:
- Double-check `StockData` includes the forecast arrays.

### T015: Render forecast lines
**Objective**: Add dashed lines for forecasts to `FinancialChart`.
**Files**: `tools/investment-screener/frontend/src/components/analysis/FinancialChart.tsx`
**Guidance**:
- Only applicable when `mode === 'revenue'`.
- Append forecast data points to the main `data` array passed to Recharts.
  - Add flag `isForecast: true`.
- Add `<Line ... strokeDasharray="5 5" />` for:
  - Avg Estimate (Primary color)
  - High Estimate (Green tint, thin)
  - Low Estimate (Red tint, thin)

### T016: Add forecast region annotation
**Objective**: Visually distinguish the forecast period.
**Files**: `tools/investment-screener/frontend/src/components/analysis/FinancialChart.tsx`
**Guidance**:
- use `<ReferenceArea />` in Recharts.
- Start x-axis: Current Year (e.g., "2025").
- End x-axis: Last Forecast Year ("2027").
- Fill: subtle pattern or lighter background opacity.
- Label: "Analyst Consensus".

### T017: Handle missing data
**Objective**: Ensure chart doesn't break if forecasts are missing.
**Files**: `tools/investment-screener/frontend/src/components/analysis/FinancialChart.tsx`
**Guidance**:
- If `analyst_revenue_forecast` is empty, just render historical data.
- Check for partial data (e.g., only revenue forecast but no earnings).

## Validation
- **Manual Test**: View NVDA Revenue chart.
- **Success Criteria**:
  - Solid line up to 2025.
  - Dashed lines extending to 2026, 2027.
  - Tooltip shows "Avg Estimate: $XX B".

## Risks
- Recharts x-axis categorization: mixing historical years (strings) with forecast years (numbers) might cause alignment issues. Convert all to strings ("2025", "2026E").