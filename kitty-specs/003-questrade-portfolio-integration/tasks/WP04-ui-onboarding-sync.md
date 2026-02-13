---
work_package_id: WP04
title: UI Onboarding & Sync Trigger
lane: "doing"
dependencies: []
subtasks: [T007, T008, T009]
agent: "Antigravity"
shell_pid: "77854"
---

# WP04: UI Onboarding & Sync Trigger

## Objective
Provide a premium, guided UI for users to link their Questrade accounts and trigger data refreshes.

## Context
Following the project's **Luxury Dark** design theme, the onboarding flow should be step-by-step and visually polished.

## Guidance

### T007: Implement QuestradeSetupModal.tsx
- **Goal**: Create a step-by-step modal for initial token setup.
- **Details**:
  - Guide the user through the Questrade API Centre process.
  - Provide a single input for the manual refresh token.
  - Handle loading states and success/error feedback.
- **Files**: `tools/investment-screener/frontend/src/components/QuestradeSetupModal.tsx`

### T008: Add Sync Dashboard Controls
- **Goal**: Integrate sync controls into the Portfolio view.
- **Details**:
  - Add a "Refresh from Questrade" button with an icon.
  - Show a "Last Sync: [Time]" label.
  - Implement a loading spinner during active syncs.

### T009: Connect UI to Backend API
- **Goal**: Wiring it all together.
- **Details**:
  - Use `axios` or standard `fetch` to call `POST /api/portfolio/sync-questrade`.
  - Update local state (holding list) upon success.

## Definition of Done
- [ ] Setup modal provides a clear onboarding path.
- [ ] Sync button correctly triggers the backend process.
- [ ] UI reflects sync status and updates data without page refresh.

## Activity Log

- 2026-02-13T19:03:12Z – Antigravity – shell_pid=77854 – lane=doing – Started implementation via workflow command
