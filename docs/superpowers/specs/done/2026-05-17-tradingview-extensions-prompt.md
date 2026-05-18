# New Session Prompt — TradingView Extended Capabilities

## Context for a New Session

You are working on **InvestmentToolkit**, a live-trading investment analysis suite.

This project already has a working TradingView CDP layer for live order execution (place/cancel/modify/get-orders, portfolio sync). The next phase extends it with Pine Script injection capabilities so the AI agent can autonomously generate, apply, and read custom technical indicators.

**Before writing any code, invoke:** `superpowers:test-driven-development`
**Before starting parallel tasks, invoke:** `superpowers:subagent-driven-development`

The Iron Law: `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.`

---

## Reference Implementations (Attribution + Architecture Notes)

Two open-source TradingView CDP projects were studied to inform this implementation:

### 1. [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp)
The most complete CDP-based TradingView automation library available.
- 5,000+ lines, 15+ command namespaces
- **Key technique to adopt:** `pine.js` uses **React fiber tree traversal** (`__reactFiber` prefix on DOM nodes) to locate Monaco editor internals. This is far more resilient than CSS class selectors (which change with TV deployments). Walk the fiber tree to find Monaco's internal `setValue` / `getValue` methods.
- No live broker order execution — purely chart analysis.

### 2. [atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp)
- TradingView screener/scanner using `tradingview-screener` Python library (REST API)
- 30+ tools for market scanning — no CDP, no live orders
- Shows how to structure MCP tool definitions for TV data

**Our differentiator:** InvestmentToolkit is a **live broker execution layer** — it navigates TradingView's built-in Questrade broker panel via CDP to place real orders, with HITL confirmation, safety gates, multi-account support, and portfolio sync after fills. The Pine Script work adds an analysis capability on top of the already-working execution layer.

---

## Architecture: Where Things Live

```
plugins/tradingview/
├── node/
│   ├── cli.js              ← CLI entry point — add 'pine' namespace here
│   ├── router.js           ← Command routing — wire pine inject/read/remove
│   └── core/
│       ├── pine.js         ← NEW: CDP Pine editor automation (Tasks 1–4)
│       └── broker_data.js  ← Existing DOM selector patterns — follow these conventions
├── scripts/
│   └── tv_pine_manager.py  ← NEW: Python wrapper around Node CLI pine commands
└── tests/
    ├── tv_test_harness.py  ← Existing harness — extend with Section 1: live pine cycle
    └── test_tv_pine_manager.py  ← NEW: subprocess-based pytest for Python wrapper
```

---

## Key Constraints (Learned from Phase 1)

### 1. ALL Node snippets MUST end with `process.exit()`
Without it, the CDP WebSocket holds the Node.js event loop open indefinitely — the Python `subprocess.run()` call never returns and the test times out. This was the root cause of all Section 0 timeout failures during Phase 1.
```javascript
// Every Node snippet must end like this:
.then(() => process.exit(0))
.catch(() => process.exit(1));
```

### 2. React fiber traversal for Monaco editor
**Do NOT rely on CSS class selectors alone for the Pine Editor or Monaco.** TradingView class names change with deployments. Use fiber traversal:
```javascript
// Scan for __reactFiber key prefix — this is how tradesdontlie's pine.js does it
const fiberKey = Object.keys(domNode).find(k => k.startsWith('__reactFiber'));
if (fiberKey) {
    let fiber = domNode[fiberKey];
    // Walk fiber.return / fiber.child to find Monaco editor props
}
```
Before writing the real CDP logic in Task 4, use the Section 0.5 selector discovery pattern in `tv_test_harness.py` to confirm the actual live selector for the Pine Editor tab. Update `broker_data.js` comments with any confirmed new selectors.

### 3. Temp files go in `InvestmentToolkit/temp/` subfolder
**Do NOT write to `/tmp/` root.** Use the repo-local `temp/` directory (gitignored) so artifacts are namespaced and easy to clean up. Create the dir if it doesn't exist:
```python
import os
TEMP_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)
pine_file = os.path.join(TEMP_DIR, 'ai_indicator.pine')
```

### 4. Subprocess-first for Python tests
`tv_pine_manager.py` tests call it via subprocess, not by importing functions directly. Mock at the `subprocess.run` boundary, not deeper.

### 5. Sacred data files
Never overwrite `portfolio.json`, `trade-log.json`, or any gitignored file.

---

## Implementation Plan: 5 Tasks, In This Order

### Task 1: Node CLI Pine Editor — stubs + Jest tests
**Files to create:**
- `plugins/tradingview/node/tests/pine.test.js`
- `plugins/tradingview/node/core/pine.js`

Write Jest tests for `injectPineScript` and `removePineScript` first. Watch them fail. Then implement the minimal stub (not real CDP logic — that's Task 4).

### Task 2: Node CLI Data Window Extraction — stubs + Jest tests
**Files to modify:**
- `plugins/tradingview/node/tests/pine.test.js`
- `plugins/tradingview/node/core/pine.js`

Add `readIndicatorValues` test and stub.

### Task 3: Python wrapper + CLI router wiring
**Files to create/modify:**
- `plugins/tradingview/tests/test_tv_pine_manager.py`
- `plugins/tradingview/scripts/tv_pine_manager.py`
- `plugins/tradingview/node/cli.js` (add `pine` router namespace)
- `plugins/tradingview/node/router.js`

Write subprocess-based pytest test first (mock `subprocess.run`). Watch fail. Then implement. Also wire `pine inject / read / remove` into the Node CLI router.

### Task 4: Real CDP implementation + live test harness
**Files to modify:**
- `plugins/tradingview/node/core/pine.js` (replace stubs with real DOM logic — use React fiber traversal)
- `plugins/tradingview/tests/tv_test_harness.py` (add Section 1: live inject/read/remove cycle)

Write `test_live_pine_cycle()` in the harness first. Watch it fail (stubs return hardcoded values). Then implement using React fiber traversal to find Monaco editor.

### Task 5: AI agent skill scaffold
**Files to create:**
- `tests/test_pine_advisor_skill.py`
- `.agents/skills/tv_pine_advisor/SKILL.md`

Write the skill existence/content test first. Watch fail. Then create the skill file.

---

## Key Files to Read First

| File | Why |
|------|-----|
| `docs/superpowers/specs/2026-05-17-tradingview-pine-script-capabilities.md` | Full design spec — architecture, React fiber technique, data flow |
| `docs/superpowers/plans/2026-05-17-tradingview-pine-script-capabilities.md` | Step-by-step implementation plan with TDD tasks, code stubs, and fiber traversal code |
| `plugins/tradingview/node/core/broker_data.js` | DOM selector patterns — follow these conventions for pine.js |
| `plugins/tradingview/node/connection.js` | CDP connect/evaluate/disconnect pattern — all Node snippets need `process.exit()` |
| `plugins/tradingview/tests/tv_test_harness.py` | Existing harness — extend Section 1 here for live pine tests |
| `.agent/rules/test-driven-development.md` | TDD rule — read and follow exactly |

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
- Original prompt: `docs/superpowers/specs/2026-05-17-tradingview-pine-script-implementation-prompt.md`
- Kanban task: `tasks/backlog/0002-tradingview-pine-script-analysis-capabilities.md`
- Reference repo 1: https://github.com/tradesdontlie/tradingview-mcp (React fiber technique)
- Reference repo 2: https://github.com/atilaahmettaner/tradingview-mcp (screener/scanner patterns)
