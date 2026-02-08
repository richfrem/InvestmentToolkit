---
work_package_id: "WP06"
title: "Saved Projections Management"
lane: "planned"
dependencies: ["WP05"]
subtasks: ["T029", "T030", "T031", "T032", "T033", "T034"]
---

# Work Package: Saved Projections Management
**Priority**: P2
**Goal**: Allow users to manage multiple saved scenarios and notes.

## Context
Currently, "Save Projection" might just overwrite a single slot or do nothing visible. Users need to recall previous assumptions.

## Subtasks

### T029: Create `ProjectionsPanel`
**Objective**: A slide-out drawer or modal to list saved items.
**Files**: `tools/investment-screener/frontend/src/components/ProjectionsPanel.tsx` (NEW)
**Guidance**:
- Use fixed positioning (right side drawer) or absolute positioning over the Right Panel.
- Header: "My Projections ({count})".
- Close button.

### T030: Display projection list
**Objective**: Render saved items.
**Files**: `tools/investment-screener/frontend/src/components/ProjectionsPanel.tsx`
**Guidance**:
- Read from LocalStorage. keys: `projections_{TICKER}`.
- List items showing:
  - Date (e.g., "Oct 24, 2025")
  - Summary: "Gr: 15% | Mar: 20% | PE: 25"
  - Truncated Note: "Optimistic on new product..."

### T031: Load Action
**Objective**: Restore state from a saved item.
**Files**: `tools/investment-screener/frontend/src/components/ValuationModeler.tsx`
**Guidance**:
- Pass `onLoad(projection)` callback to panel.
- When clicked, update all state variables (growth, margin, etc.) with values from the projection object.
- Show toast notification: "Projection Loaded".

### T032: Edit Action
**Objective**: Update notes or values of a saved item.
**Files**: `tools/investment-screener/frontend/src/components/ProjectionsPanel.tsx`
**Guidance**:
- Inline edit for Notes.
- For values, user should probably "Load", tweak, and "Save as New" or "Update".
- For this task, strictly allow editing the *Note* text.

### T033: Delete Action
**Objective**: Remove from history.
**Files**: `tools/investment-screener/frontend/src/components/ProjectionsPanel.tsx`
**Guidance**:
- Trash icon.
- Confirm: "Are you sure?"
- Remove from LocalStorage array.

### T034: Add entry button
**Objective**: Button to open the panel.
**Files**: `tools/investment-screener/frontend/src/components/ValuationModeler.tsx`
**Guidance**:
- Add "History" or "My Projections" button next to "Save".
- Show a badge count if > 0.

## Validation
- **Manual Test**:
  1. Set sliders to specific values. Save.
  2. Change sliders.
  3. Open Panel -> Click Load.
  4. Verify sliders return to step 1 values.
- **Success Criteria**:
  - Data persists across browser refresh.

## Risks
- LocalStorage limits (5MB) - unlikely to hit with text data, but good to keep in mind.