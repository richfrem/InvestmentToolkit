# Work Packages: Questrade Portfolio Integration

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Status**: Planned

## Summary
The implementation is broken into 4 work packages focusing on security, data retrieval, backend bridging, and user interface.

---

## WP01: Security & Token Infrastructure (Priority: P1)
**Goal**: Implement the secure, hardware-backed token storage and atomic rotation logic.
**Independent Test**: Python utility can encrypt/decrypt a test token via the macOS Keychain and perform an atomic overwrite of the cache file.

### Included Subtasks
- [ ] **T001**: Implement `QuestradeTokenManager.py` core with AES-256 encryption via `keyring`.
- [ ] **T002**: Implement Atomic Swap rotation logic for `.questrade_cache`.

### Implementation Sketch
1. Set up the `keyring` integration for macOS Keychain.
2. Build the encryption wrapper for JSON data.
3. Implement the `os.replace()` pattern for atomic cache updates.

---

## WP02: Questrade Data Engine (Priority: P1)
**Goal**: Implement the core data retrieval and aggregation logic in Python.
**Dependencies**: WP01
**Independent Test**: Script fetches positions from multiple accounts and produces a correctly aggregated `portfolio.json` structure.

### Included Subtasks
- [ ] **T003**: Implement Questrade API client for account discovery and position fetching.
- [ ] **T004**: Implement position aggregation and currency normalization logic.

### Implementation Sketch
1. Build the API client using `requests`.
2. Map account discovery -> position fetching loop.
3. Aggregate holdings by ticker and compute weighted average costs.

---

## WP03: Node.js Service Bridge (Priority: P2)
**Goal**: Connect the Node.js backend to the Python data engine.
**Dependencies**: WP02
**Independent Test**: API endpoint returns successfully after triggering the Python child process.

### Included Subtasks
- [ ] **T005**: Create `QuestradeSyncService.ts` to spawn the Python child process.
- [ ] **T006**: Expose API endpoint for manual sync trigger.

### Implementation Sketch
1. Use `child_process.spawn` to call the Python script.
2. Handle stdout/stderr and exit codes for error reporting.

---

## WP04: UI Onboarding & Sync Trigger (Priority: P2)
**Goal**: Provide the user-facing setup and refresh controls.
**Dependencies**: WP03
**Independent Test**: User can enter a token in the modal and trigger a sync from the dashboard.

### Included Subtasks
- [ ] **T007**: Implement `QuestradeSetupModal.tsx` for initial token seeding.
- [ ] **T008**: Add "Sync Now" button and status indicators to the Portfolio dashboard.
- [ ] **T009**: Connect UI to the sync API endpoint.

### Implementation Sketch
1. Build the guided setup modal with step-by-step instructions.
2. Update the dashboard with sync status (loading, success, error).
