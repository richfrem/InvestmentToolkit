---
work_package_id: WP03
title: Analyst Forecast Overlay
lane: planned
dependencies:
- WP01
subtasks:
- T013
- T014
- T015
- T016
- T017
phase: Phase 2 - Core Features
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T02:11:51Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Analyst Forecast Overlay

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- On the Revenue & Earnings chart mode, extend the timeline with analyst forecast data for 2026-2027.
- Show three dotted lines: High estimate, Low estimate, Average consensus.
- Clear visual distinction between historical (solid) and forecast (dashed) data.
- Shaded or annotated "Forecast" region.
- Graceful handling when no forecast data is available.

## Context & Constraints

- **Depends on WP01**: Analyst forecast data (`analyst_revenue_forecast`) must be returned by the backend.
- **Depends on WP02**: The `FinancialChart.tsx` component must exist with the revenue mode.
- **Charts**: Recharts — use `Line` with `strokeDasharray` for dashed lines, `ReferenceArea` for shaded regions.
- **Key Files**:
  - `frontend/src/components/Charts/FinancialChart.tsx` (from WP02)
  - `frontend/src/services/api.ts`
  - `backend/py_services/fetch_financials.py`

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

## Subtasks & Detailed Guidance

### Subtask T013 – Verify Backend Returns Structured Forecast Data

- **Purpose**: Confirm WP01's T003 outputs the correct format; adjust if needed.
- **Steps**:
  1. Run `python3 fetch_financials.py AAPL` and verify `analyst_revenue_forecast` contains:
     ```json
     [
       { "period": "2026", "avg": 420000000000, "low": 400000000000, "high": 440000000000 },
       { "period": "2027", "avg": 460000000000, "low": 430000000000, "high": 490000000000 }
     ]
     ```
  2. If the period labels are quarters ("+1q") instead of years, map them to calendar years.
  3. Ensure values are in the same unit as `historical_revenue` (absolute dollars, not millions).
- **Files**: `backend/py_services/fetch_financials.py`

### Subtask T014 – Update api.ts with Forecast Interface

- **Purpose**: Ensure the TypeScript interface matches the forecast data structure.
- **Steps**:
  1. Verify `StockData.analyst_revenue_forecast` type from WP01's T005 is correct:
     ```typescript
     analyst_revenue_forecast?: Array<{
       period: string;
       avg: number;
       low: number;
       high: number;
     }>;
     ```
  2. Add `analyst_earnings_forecast` if not already present.
- **Files**: `frontend/src/services/api.ts`

### Subtask T015 – Render Forecast Dashed Lines on Chart

- **Purpose**: Extend the Revenue & Earnings chart timeline with forecast data points.
- **Steps**:
  1. In `FinancialChart.tsx`, when `mode === 'revenue'` and `stockData.analyst_revenue_forecast` exists:
  2. Merge historical + forecast into a single data array:
     ```typescript
     const chartData = [
       ...historicalData,  // { year: "2022", revenue: 394B, netIncome: 99B }
       ...forecastData.map(f => ({
         year: f.period,
         revenueAvg: f.avg,
         revenueLow: f.low,
         revenueHigh: f.high,
         isForecast: true,
       }))
     ];
     ```
  3. Render forecast lines using Recharts `Line` components:
     ```tsx
     <Line dataKey="revenueAvg" stroke="#f59e0b" strokeDasharray="8 4" name="Avg Forecast" />
     <Line dataKey="revenueHigh" stroke="#22c55e" strokeDasharray="4 4" strokeWidth={1} name="High Estimate" />
     <Line dataKey="revenueLow" stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1} name="Low Estimate" />
     ```
  4. Historical revenue remains as a solid area fill; forecast lines are dashed.
- **Files**: `frontend/src/components/Charts/FinancialChart.tsx`

### Subtask T016 – Add Forecast Region Annotation

- **Purpose**: Visually distinguish the forecast zone from historical data.
- **Steps**:
  1. Use Recharts `ReferenceArea` to shade the forecast region:
     ```tsx
     <ReferenceArea
       x1={lastHistoricalYear}
       x2={lastForecastYear}
       fill="#f59e0b"
       fillOpacity={0.05}
       label={{ value: "Forecast", position: "insideTopRight", fill: "#94a3b8", fontSize: 12 }}
     />
     ```
  2. Add a vertical reference line at the boundary between historical and forecast:
     ```tsx
     <ReferenceLine x={lastHistoricalYear} stroke="#475569" strokeDasharray="3 3" />
     ```
  3. Update the tooltip to show "Estimate" label for forecast data points.
- **Files**: `frontend/src/components/Charts/FinancialChart.tsx`

### Subtask T017 – Handle Missing Forecast Data Gracefully

- **Purpose**: Not all tickers have analyst coverage — chart should still work.
- **Steps**:
  1. If `analyst_revenue_forecast` is undefined or empty, render only historical data (no forecast section).
  2. No error messages needed — just don't render the dashed lines or shaded region.
  3. The toggle buttons and chart still function normally.
  4. Consider a subtle "No analyst estimates available" note below the chart if in revenue mode and no forecast data.
- **Files**: `frontend/src/components/Charts/FinancialChart.tsx`

## Risks & Mitigations

- Forecast data units may not match historical data units → normalize to same scale.
- yfinance may return quarterly estimates instead of annual → aggregate or filter.

## Review Guidance

- Test with AAPL (should have forecasts) and a micro-cap (should gracefully show no forecast).
- Verify dashed lines are visually distinct from solid historical lines.
- Check that the forecast region label is readable in dark theme.

## Activity Log

- 2026-02-08T02:11:51Z – system – lane=planned – Prompt created.