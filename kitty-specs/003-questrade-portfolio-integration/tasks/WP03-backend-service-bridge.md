---
work_package_id: WP03
title: Node.js Service Bridge
lane: "for_review"
dependencies: []
subtasks: [T005, T006]
agent: "Antigravity"
shell_pid: "77854"
---

# WP03: Node.js Service Bridge

## Objective
Enable the Node.js backend to trigger the Questrade sync process and expose an API endpoint for the UI.

## Context
Based on **ADR 017** (Multi-Language Bridge Pattern), the Node.js backend acts as a coordinator, spawning the Python "engine" when requested.

## Guidance

### T005: Create QuestradeSyncService.ts
- **Goal**: Implement a service class to manage the Python lifecycle.
- **Details**:
  - Use `child_process.spawn` to execute `QuestradeAPIClient.py`.
  - Listen for stdout and stderr to capture log data and errors.
  - Return a Promise that resolves when the Python process exits with 0.
- **Files**: `tools/investment-screener/backend/src/services/QuestradeSyncService.ts`

### T006: Expose Sync API Endpoint
- **Goal**: Add an Express route to trigger the manual sync.
- **Details**:
  - Route: `POST /api/portfolio/sync-questrade`.
  - Integrate with existing authentication (if any).
  - Return success/failure response based on process exit status.

## Definition of Done
- [ ] Backend successfully triggers the Python sync script.
- [ ] Sync endpoint returns meaningful errors to the client.
- [ ] Service handles process timeouts gracefully.

## Activity Log

- 2026-02-13T18:53:24Z – Antigravity – shell_pid=77854 – lane=doing – Started implementation via workflow command
- 2026-02-13T19:02:14Z – Antigravity – shell_pid=77854 – lane=for_review – Service bridge implementation and API endpoint verified with tests.
