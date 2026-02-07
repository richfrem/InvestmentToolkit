---
work_package_id: "WP03"
title: "Expert Metrics & Charts"
lane: "planned"
dependencies: ["WP02"] 
subtasks: ["T012", "T013", "T014", "T015"]
---

# Work Package 03: Expert Metrics & Charts

**Goal**: Visualize the financial data using Recharts and display the calculated Expert Metrics in a responsive grid.

**Implementation Command**:
`spec-kitty implement WP03 --base WP02`

---

### Subtask T012: Build "Expert Metrics" Grid
**Purpose**: Display key indicators like PEG, Piotroski, and Rule of 40.
**Steps**:
1.  Create `frontend/src/components/MetricsGrid.tsx`.
2.  Design card layout for each metric (Title, Value, Guidance/Tooltip).
3.  **Piotroski Logic**:
    - Display Score / 9.
    - Color code (Green > 7, Red < 4).
    - Handle "Insufficient Data" case (per spec).
4.  **Rule of 40 Logic**:
    - Display Score %.
    - Warning icon if Sector != Technology/Communication Services ("⚠️ Best for SaaS").
5.  **Peg Ratio**:
    - Display value.
    - Context: "Undervalued < 1.0".

### Subtask T013: Implement Rule of 40 Chart
**Purpose**: Visual trend of Growth vs Profitability.
**Steps**:
1.  Create `frontend/src/components/Charts/RuleOf40Chart.tsx`.
2.  Use `Recharts` ComposedChart (Bar + Line or Scatter).
3.  X-Axis: Year (Last 5 years).
4.  Y-Axis: Percentage.
5.  Metrics: Revenue Growth % vs EBITDA Margin %.
6.  Reference Line at 40%.

### Subtask T014: Implement Fundamental Chart
**Purpose**: Historical Revenue vs Net Income trend.
**Steps**:
1.  Create `frontend/src/components/Charts/FundamentalChart.tsx`.
2.  Use `Recharts` AreaChart or BarChart.
3.  Dual Y-Axis (optional if scales differ significantly, or normalize).
4.  Series: Revenue (Green), Net Income (Gold/Amber).
5.  Tooltip with formatted currency (e.g., "$1.2B").

### Subtask T015: Integrate Components into Dashboard
**Purpose**: Wire up the visual components to the `stockData` state.
**Steps**:
1.  Update `Dashboard.tsx` layout.
2.  Place `MetricsGrid` below the search bar.
3.  Place Charts in a flexible grid layout (2 columns on desktop).
4.  Pass `stockData` props to all components.
5.  Verify data flows correctly from API to charts.

---

**Definition of Done**:
- [ ] Dashboad displays Metrics Grid with correct color coding.
- [ ] Rule of 40 Chart renders with reference line.
- [ ] Fundamental Chart shows Revenue/Income history.
- [ ] "Insufficient Data" states are handled gracefully (e.g., empty charts don't crash).
