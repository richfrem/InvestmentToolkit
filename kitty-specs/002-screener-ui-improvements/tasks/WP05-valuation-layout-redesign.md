---
work_package_id: "WP05"
subtasks:
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
title: "Valuation Layout Redesign"
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

# Work Package Prompt: WP05 – Valuation Layout Redesign

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Valuation Modeler fits on a 1080p screen without scrolling.
- Inputs (sliders) and outputs (scenario results) are visible simultaneously.
- Layout uses side-by-side arrangement: left panel inputs, right panel results.
- Bear/Base/Bull scenario cards are compact.
- Responsive: stacks vertically on smaller screens.

## Context & Constraints

- **Current layout**: `ValuationModeler.tsx` (374 lines) — sliders in 2-column grid, scenario cards as 3-column row, all stacked vertically requiring significant scrolling.
- **This is a layout-only refactor** — valuation calculation logic stays unchanged.
- **Depends on WP01**: Layout should show real Yahoo data, not N/A values.
- **Key Files**:
  - `frontend/src/components/ValuationModeler.tsx` (374 lines) — main target

## Implementation Command

```bash
spec-kitty implement WP05 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T023 – Redesign ValuationModeler Side-by-Side Layout

- **Purpose**: Create a 2-panel layout where inputs and results are visible simultaneously.
- **Steps**:
  1. Restructure ValuationModeler.tsx into a 2-column grid:
     ```tsx
     <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
       {/* Left panel: 3 columns wide - Inputs */}
       <div className="lg:col-span-3">
         {/* Scenario tabs (bear/base/bull) */}
         {/* Compact sliders */}
         {/* Action buttons (Reset/Save) */}
       </div>
       {/* Right panel: 2 columns wide - Results */}
       <div className="lg:col-span-2">
         {/* Active scenario target price + % change */}
         {/* Bear/Base/Bull summary cards */}
         {/* Expert Analysis Summary */}
         {/* Analyst Consensus bar */}
       </div>
     </div>
     ```
  2. On screens < `lg` breakpoint, stack to single column (inputs first, then results).
  3. Keep header (title + active scenario price badge) above both columns.
- **Files**: `frontend/src/components/ValuationModeler.tsx`

### Subtask T024 – Compact Slider Inputs

- **Purpose**: Reduce vertical space consumed by the 6 sliders.
- **Steps**:
  1. Change slider grid from 2 columns to 3 columns on wider screens:
     ```tsx
     <div className="grid grid-cols-2 xl:grid-cols-3 gap-x-6 gap-y-3">
     ```
  2. Reduce vertical gaps: `gap-y-3` instead of larger gaps.
  3. Make slider labels + inputs more compact:
     - Label + input on same row: `flex items-center justify-between`
     - Smaller font for labels: `text-xs` instead of `text-sm`
     - Smaller number input boxes: `w-16` instead of `w-20`
  4. Yahoo reference text below slider: `text-[10px]` in muted color.
  5. Reduce slider height/padding — tighter vertical rhythm.
- **Files**: `frontend/src/components/ValuationModeler.tsx`

### Subtask T025 – Redesign Scenario Cards

- **Purpose**: Bear/Base/Bull cards take up less vertical space.
- **Steps**:
  1. Change from 3 separate cards to a compact horizontal bar or inline tabs:
     ```tsx
     <div className="flex gap-2">
       {['bear', 'base', 'bull'].map(scenario => (
         <button
           key={scenario}
           className={`flex-1 py-2 px-3 rounded-lg text-center text-sm ${
             activeScenario === scenario ? 'bg-amber-500/20 border border-amber-500' : 'bg-slate-800'
           }`}
         >
           <span className="block text-xs uppercase">{scenario}</span>
           <span className="block text-lg font-bold">${targetPrice}</span>
         </button>
       ))}
     </div>
     ```
  2. Each card shows: scenario name + target price. That's it — compact.
  3. Active scenario has amber border/glow. Inactive cards are muted.
- **Files**: `frontend/src/components/ValuationModeler.tsx`

### Subtask T026 – Move Expert Analysis to Right Panel

- **Purpose**: The expert analysis summary (Strong Value / Fairly Valued / Overvalued) should live in the results panel for at-a-glance assessment.
- **Steps**:
  1. In the right panel, below the scenario cards, add the Expert Analysis section:
     - Valuation assessment badge: "Strong Value" (green), "Potential Value" (amber), "Fairly Valued" (blue), "Overvalued" (red)
     - Required CAGR to justify current price
     - Upside/downside percentage to base target
  2. Use a colored card/badge for the assessment — visually prominent.
  3. Show the calculation: "Current price implies X% growth vs your Y% assumption."
- **Files**: `frontend/src/components/ValuationModeler.tsx`

### Subtask T027 – Add Mini Scenario Comparison Chart

- **Purpose**: Visual bar chart showing bear/base/bull targets relative to current price.
- **Steps**:
  1. In the right panel, add a small horizontal bar chart:
     ```
     Current ——|——————————— $50.59
     Bear   ——|——— $16
     Base   ——|—————————— $53
     Bull   ——|————————————————————— $173
     ```
  2. Use Recharts `BarChart` (horizontal) or simple Tailwind divs with percentage widths.
  3. Current price shown as a reference line/marker.
  4. Color: bear=red, base=amber, bull=green, current=white.
  5. This is optional enhancement — skip if space is tight.
- **Files**: `frontend/src/components/ValuationModeler.tsx`
- **Parallel?**: Yes — additive component, can be built independently.

### Subtask T028 – Responsive Behavior

- **Purpose**: Ensure the layout works on different screen sizes.
- **Steps**:
  1. Below `lg` breakpoint (1024px): single column, inputs stacked above results.
  2. At `lg`: 2-panel side-by-side layout.
  3. Slider columns: `grid-cols-2` at `md`, `grid-cols-3` at `xl`.
  4. Test that sliders are usable (thumb not too small) on all breakpoints.
  5. Ensure the right panel doesn't get too narrow on `lg` — minimum content width.
- **Files**: `frontend/src/components/ValuationModeler.tsx`

## Risks & Mitigations

- 3-column slider layout may be too cramped → test on 1366px (common laptop) and fall back to 2 columns if needed.
- Side-by-side layout requires enough content in right panel to not look empty → ensure scenario cards + analysis summary fill the space.

## Review Guidance

- Open the Valuation tab on a 1080p display — everything should be visible without scrolling.
- Test slider usability: can you easily adjust sliders in the compact layout?
- Resize browser window to test responsive breakpoints.

## Activity Log

- 2026-02-08T02:11:51Z – system – lane=planned – Prompt created.