---
work_package_id: "WP06"
subtasks:
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
title: "Saved Projections Management"
phase: "Phase 3 - Enhancements"
lane: "planned"
dependencies: ["WP05"]
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

# Work Package Prompt: WP06 – Saved Projections Management

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- "My Projections" button visible near "Save Projection" button.
- Clicking opens a panel listing all saved projections for the current ticker.
- Each entry shows: date, scenario summary, notes preview.
- Users can Load (populate sliders), Edit (notes + values), and Delete projections.
- Multiple projections per ticker supported (migration from single-projection format).

## Context & Constraints

- **Current state**: `ValuationModeler.tsx` saves to `projection_{SYMBOL}` in LocalStorage as a single object.
- **Change needed**: Migrate to array format `projections_{SYMBOL}` to support multiple saved projections per ticker.
- **Depends on WP05**: Button placement depends on the redesigned Valuation layout.
- **Key Files**:
  - `frontend/src/components/ValuationModeler.tsx` (374+ lines after WP05)

## Implementation Command

```bash
spec-kitty implement WP06 --base WP05
```

## Subtasks & Detailed Guidance

### Subtask T029 – Create ProjectionsPanel Component

- **Purpose**: Modal or slide-out panel for managing saved projections.
- **Steps**:
  1. Create `frontend/src/components/ProjectionsPanel.tsx`.
  2. Props:
     ```typescript
     interface ProjectionEntry {
       id: string;          // unique ID (timestamp-based)
       scenarios: Record<ScenarioType, ScenarioInputs>;
       notes: string;
       savedAt: string;     // ISO date
     }
     interface Props {
       isOpen: boolean;
       onClose: () => void;
       projections: ProjectionEntry[];
       onLoad: (projection: ProjectionEntry) => void;
       onDelete: (id: string) => void;
       onUpdate: (id: string, updates: Partial<ProjectionEntry>) => void;
       tickerSymbol: string;
     }
     ```
  3. Layout: Full-height slide-out panel from the right (or modal overlay).
  4. Header: "My Projections — {TICKER}" with close button.
  5. Body: Scrollable list of projection entries.
  6. Empty state: "No saved projections for {TICKER}. Save your first projection using the Save button."
- **Files**: `frontend/src/components/ProjectionsPanel.tsx` (new, ~120 lines)

### Subtask T030 – Display Projection Entries

- **Purpose**: Each entry shows a summary of the saved projection.
- **Steps**:
  1. Entry card layout:
     ```
     ┌──────────────────────────────────────┐
     │ Feb 7, 2026 at 6:04 PM              │
     │ Bear $16 | Base $53 | Bull $173     │
     │ Growth: 10% | Margin: 20% | PE: 25x │
     │ "INTC turnaround thesis..."          │
     │ [Load] [Edit] [Delete]               │
     └──────────────────────────────────────┘
     ```
  2. Date: formatted relative or absolute (e.g., "2 days ago" or "Feb 7, 2026").
  3. Scenario prices: recalculate from saved inputs using the same formula.
  4. Notes: truncated to 1-2 lines with "..." ellipsis.
  5. Action buttons: small, inline at the bottom of each card.
- **Files**: `frontend/src/components/ProjectionsPanel.tsx`

### Subtask T031 – Implement Load Action

- **Purpose**: Populate the Valuation Modeler sliders with a saved projection's values.
- **Steps**:
  1. When user clicks "Load", call `onLoad(projection)`.
  2. In ValuationModeler, `onLoad` sets:
     ```typescript
     setScenarios(projection.scenarios);
     setNotes(projection.notes);
     ```
  3. Close the projections panel after loading.
  4. Show a brief toast/notification: "Loaded projection from {date}".
- **Files**: `frontend/src/components/ValuationModeler.tsx`, `ProjectionsPanel.tsx`

### Subtask T032 – Implement Edit Action

- **Purpose**: Allow editing notes and updating saved projection values.
- **Steps**:
  1. "Edit" button toggles the entry into edit mode:
     - Notes text area becomes editable (full height).
     - "Save Changes" and "Cancel" buttons appear.
  2. On save, call `onUpdate(id, { notes: newNotes })`.
  3. In ValuationModeler, `onUpdate` finds the projection by ID in LocalStorage and updates it.
  4. Optionally: allow saving current slider values as an update to an existing projection (overwrite scenarios).
- **Files**: `frontend/src/components/ProjectionsPanel.tsx`, `ValuationModeler.tsx`

### Subtask T033 – Implement Delete with Confirmation

- **Purpose**: Remove a saved projection with safety confirmation.
- **Steps**:
  1. "Delete" button shows inline confirmation: "Delete this projection? [Yes] [No]"
  2. On confirm, call `onDelete(id)`.
  3. In ValuationModeler, `onDelete` removes the entry from the LocalStorage array.
  4. Panel re-renders with the entry removed.
- **Files**: `frontend/src/components/ProjectionsPanel.tsx`, `ValuationModeler.tsx`

### Subtask T034 – Add "My Projections" Button + Storage Migration

- **Purpose**: Button to open the panel, and migrate from single to multi-projection storage.
- **Steps**:
  1. Add "My Projections" button in the ValuationModeler header area, near "Save Projection".
  2. Show a count badge if projections exist (e.g., "My Projections (3)").
  3. Button toggles the ProjectionsPanel open/closed.
  4. **Storage migration**: On component mount, check for old format (`projection_{SYMBOL}` as single object):
     ```typescript
     const oldData = localStorage.getItem(`projection_${symbol}`);
     if (oldData) {
       const parsed = JSON.parse(oldData);
       if (!Array.isArray(parsed)) {
         // Migrate: wrap in array with generated ID
         const migrated = [{ id: Date.now().toString(), ...parsed }];
         localStorage.setItem(`projections_${symbol}`, JSON.stringify(migrated));
         localStorage.removeItem(`projection_${symbol}`);
       }
     }
     ```
  5. All new saves go to `projections_{SYMBOL}` (plural, array format).
- **Files**: `frontend/src/components/ValuationModeler.tsx`
- **Parallel?**: Yes — can be built alongside T029.

## Risks & Mitigations

- LocalStorage ~5MB limit — unlikely to hit, but could log a warning if approaching limit.
- Migration from old format must be backward-compatible — don't lose existing saved data.

## Review Guidance

- Save a projection → open "My Projections" → verify it appears.
- Load a saved projection → verify sliders update.
- Edit notes → verify changes persist after closing panel.
- Delete a projection → verify it's gone from the list.
- Test migration: manually set old-format data in LocalStorage → verify it migrates.

## Activity Log

- 2026-02-08T02:11:51Z – system – lane=planned – Prompt created.