---
work_package_id: "WP05"
title: "Valuation Layout Redesign"
lane: "planned"
dependencies: ["WP01"]
subtasks: ["T023", "T024", "T025", "T026", "T027", "T028"]
---

# Work Package: Valuation Layout Redesign
**Priority**: P1
**Goal**: Implement a compact, side-by-side layout for the Valuation Modeler to eliminate vertical scrolling on standard displays.

## Context
The current Valuation Modeler stacks everything vertically, wasting horizontal space. Users have to scroll up and down to tweak inputs and see results. We need a dense, dashboard-style layout.

## Subtasks

### T023: Implement Side-by-Side Grid
**Objective**: Split the main container into two columns.
**Files**: `tools/investment-screener/frontend/src/components/ValuationModeler.tsx`
**Guidance**:
- Use CSS Grid: `grid grid-cols-1 lg:grid-cols-12 gap-6`.
- Left Panel (Inputs): `lg:col-span-7` or `lg:col-span-8`.
- Right Panel (Results): `lg:col-span-5` or `lg:col-span-4`.
- Ensure mobile falls back to single column.

### T024: Compact Slider Inputs
**Objective**: Reduce vertical padding and font sizes for sliders.
**Files**: `tools/investment-screener/frontend/src/components/ValuationModeler.tsx`
**Guidance**:
- Current: Likely `mb-6` or `py-4`. Reduce to `mb-3` or `py-2`.
- Organize sliders into a grid within the Left Panel: `grid-cols-1 md:grid-cols-2`.
- Makes 6 sliders fit in 3 rows (Growth/Margin, PE/ShareChange, Discount/Time).

### T025: Redesign Scenario Cards
**Objective**: Make the output cards (Bear/Base/Bull) compact.
**Files**: `tools/investment-screener/frontend/src/components/ValuationModeler.tsx`
**Guidance**:
- Move to the Right Panel.
- Instead of 3 large separate cards, use a single "Scenario Dashboard" card.
- Layout: 3 columns within the card (Bear | Base | Bull).
- Highlight "Base" as the primary connected outcome.

### T026: Move Expert Analysis
**Objective**: Place the qualitative analysis text in the Right Panel.
**Files**: `tools/investment-screener/frontend/src/components/ValuationModeler.tsx`
**Guidance**:
- Below the Scenario Dashboard.
- Use a condensed font style (smaller text, maybe scrollable if very long, but usually it's short).

### T027: Add mini comparison chart
**Objective**: Visual confirmation of the valuation spread.
**Files**: `tools/investment-screener/frontend/src/components/ValuationModeler.tsx`
**Guidance**:
- Add a tiny Recharts BarChart in the Right Panel.
- X-axis: Bear, Base, Bull, Current Price.
- Visualizes the potential upside/downside immediately.

### T028: Header optimization
**Objective**: Move search bar to top right to save vertical space.
**Files**: `tools/investment-screener/frontend/src/components/ValuationModeler.tsx` (and `Dashboard.tsx` if lifted up)
**Guidance**:
- Verify if Search Bar is inside ValuationModeler or part of the main Dashboard header.
- If in Modeler, move it to the main header row (beside the "Valuation Modeler" title).
- Ensure "Reset to Yahoo" and "Save Projection" buttons are compact (icon-only on mobile, small buttons on desktop).

## Validation
- **Manual Test**: Open Valuation tab on 1080p screen (1920x1080).
- **Success Criteria**:
  - Entire modeler (Inputs + Results) visible without browser scrollbar.
  - Sliders are usable (not too small).
  - Responsive: resizing to mobile (<768px) stacks them vertically again.

## Risks
- "Compact" can mean "Unusable" on touch screens. Ensure slider thumb touch target remains 44px+ even if visual representation is smaller.