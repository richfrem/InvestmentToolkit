# New Session Prompt — TradingView Pine Script Capabilities

## Context for a New Session

You are working on **InvestmentToolkit**, a live-trading investment analysis toolkit.
The project has:
- Node.js/Express backend (`investment_screener/backend/`)
- TradingView CDP automation (`plugins/tradingview/`)
- Python service scripts (`plugins/tradingview/scripts/`)
- AI agent skills (`.agents/skills/`)
- An existing test harness (`plugins/tradingview/tests/tv_test_harness.py`) that confirms TV Desktop is reachable

Current branch: `feature/test-suite-phase1` (or create a new branch off it: `feature/tv-pine-script`)

A full spec and implementation plan have been designed and are **ready for implementation**.

**Before writing any code, invoke:** `superpowers:test-driven-development`
**Before starting parallel tasks, invoke:** `superpowers:subagent-driven-development`

The Iron Law: `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.`

---

## Key Files to Read First

| File | Why |
|------|-----|
| `docs/superpowers/specs/2026-05-17-tradingview-pine-script-capabilities.md` | Full design spec — architecture decisions, component design, data flow |
| `docs/superpowers/plans/2026-05-17-tradingview-pine-script-capabilities.md` | Step-by-step implementation plan with TDD tasks and code stubs |
| `plugins/tradingview/node/core/broker_data.js` | DOM selector patterns — follow these conventions for pine.js |
| `plugins/tradingview/node/connection.js` | CDP connect/evaluate/disconnect pattern — all Node snippets need `process.exit()` |
| `plugins/tradingview/tests/tv_test_harness.py` | Existing harness — extend Section 1 here for live pine tests |
| `.agent/rules/test-driven-development.md` | TDD rule — read and follow exactly |

---

## Implementation — 5 Tasks, In This Order

### Task 1: Node CLI Pine Editor — stubs + Jest tests
**Files to create:**
- `plugins/tradingview/node/tests/pine.test.js`
- `plugins/tradingview/node/core/pine.js`

Write Jest tests for `injectPineScript` and `removePineScript` first. Watch them fail. Then implement the minimal stub (not the real CDP logic — that's Task 4). See plan for exact test + stub code.

### Task 2: Node CLI Data Window Extraction — stubs + Jest tests
**Files to modify:**
- `plugins/tradingview/node/tests/pine.test.js`
- `plugins/tradingview/node/core/pine.js`

Add `readIndicatorValues` test and stub. Same pattern.

### Task 3: Python wrapper + CLI router wiring
**Files to create/modify:**
- `plugins/tradingview/tests/test_tv_pine_manager.py`
- `plugins/tradingview/scripts/tv_pine_manager.py`
- `plugins/tradingview/node/cli.js` (add `pine` router namespace)
- `plugins/tradingview/node/router.js`

Write subprocess-based pytest test first (mock `subprocess.run`). Watch fail. Then implement the wrapper. Also wire `pine inject / read / remove` into the Node CLI router.

### Task 4: Real CDP implementation + live test harness
**Files to modify:**
- `plugins/tradingview/node/core/pine.js` (replace stubs with real DOM logic)
- `plugins/tradingview/tests/tv_test_harness.py` (add Section 1: live inject/read/remove cycle)

Write `test_live_pine_cycle()` in the harness first. Watch it fail (stubs return hardcoded values). Then implement:
- `injectPineScript`: click `.js-pine-editor-tab`, focus Monaco, `Input.insertText`, click "Add to chart"
- `readIndicatorValues`: open Data Window via CDP, scrape key-value pairs for the indicator
- `removePineScript`: find indicator in legend, click remove icon

**Critical:** All Node snippets must end with `process.exit(0)` / `process.exit(1)` — without it, the CDP WebSocket keeps the process alive and times out.

### Task 5: AI agent skill scaffold
**Files to create:**
- `tests/test_pine_advisor_skill.py`
- `.agents/skills/tv_pine_advisor/SKILL.md`

Write the skill existence/content test first. Watch fail. Then create the skill file. See plan for exact trigger and workflow steps.

---

## Important Constraints

1. **All Node snippets need `process.exit()`** — the CDP WebSocket holds the event loop open indefinitely without it. This burned us in Phase 1 before it was found. Every `_run_node()` call must terminate.

2. **Subprocess-first for Python tests.** `tv_pine_manager.py` tests call it via subprocess, not by importing functions directly. Mock at the `subprocess.run` boundary, not deeper.

3. **Temp files go in `InvestmentToolkit/temp/` subfolder** (task #0003 is cleaning this up). Do NOT write to `/tmp/` root like the spec says — use the namespaced path. Create the dir if needed.

4. **DOM selectors will need live discovery.** The plan's `.js-pine-editor-tab` selector is a starting guess. Before wiring it up in Task 4, open TV and use the Section 0.5 pattern from `tv_test_harness.py` to confirm the actual selector. Update `broker_data.js` comments with any new confirmed selectors.

5. **gitignored data files are sacred.** Never overwrite `portfolio.json`, `trade-log.json`, or any gitignored file.

---

## Where Tests Live

| Test file | Location |
|-----------|---------|
| `pine.test.js` (Jest) | `plugins/tradingview/node/tests/` |
| `test_tv_pine_manager.py` | `plugins/tradingview/tests/` |
| `test_live_pine_cycle` (harness section 1) | `plugins/tradingview/tests/tv_test_harness.py` |
| `test_pine_advisor_skill.py` | `tests/` (repo root) |

---

## Full References
- Spec: `docs/superpowers/specs/2026-05-17-tradingview-pine-script-capabilities.md`
- Plan: `docs/superpowers/plans/2026-05-17-tradingview-pine-script-capabilities.md`
- Kanban task: `tasks/backlog/0002-tradingview-pine-script-analysis-capabilities.md`
