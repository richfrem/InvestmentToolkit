# Session Prompt — Pine Script v6 Mechanical Test Implementation

> Paste this entire document into a new Claude Code session to begin implementation.

---

## Your Mission

Implement the Pine Script v6 mechanical test plan for the InvestmentToolkit project. The plan is fully written — your job is to execute it task by task, fix any obstacles that come up, and ask the user when you need live TradingView verification.

**Plan file:** `docs/superpowers/plans/2026-05-17-pine-script-mechanical-test-plan.md`  
**Spec file:** `docs/superpowers/specs/2026-05-17-pine-script-mechanical-test-design.md`

Read both files before doing anything else.

---

## Project Context

**InvestmentToolkit** is a personal investment analysis suite. You are working in the TradingView CDP automation layer — Node.js scripts that control TradingView Desktop (a GUI app) programmatically via Chrome DevTools Protocol.

**Key directories:**
- `tradingview-cdp/` — standalone Node.js CDP engine (install: `cd tradingview-cdp && npm ci`)
- `tradingview-cdp/core/chart.js` — chart control functions (you will add to this)
- `tradingview-cdp/cli.js` — CLI router (you will add subcommands here)
- `plugins/tradingview/tests/tv_test_harness.py` — Python test harness (you will extend this)
- `plugins/tradingview/scripts/tv_client.py` — Python→Node bridge (read-only reference)

**How the CDP layer works:**
1. TradingView Desktop runs with `--remote-debugging-port=9222`
2. Node.js connects via `connection.js` (`getClient()`) and sends CDP commands
3. Python scripts call Node via `subprocess.run(["node", "cli.js", ...])` in `tradingview-cdp/`
4. All Node modules use ESM (`import`/`export`), no CommonJS
5. Every Node handler must NOT call `process.exit()` — the router handles that

**Critical rules from CLAUDE.md:**
- Never hardcode `tradingview-cdp/` path — always use `tv_client.py` if importing in Python
- All Node snippets already handle `process.exit()` via the router — do not add it in handlers
- React fiber traversal for Monaco editor (already done in `pine.js`) — don't touch `pine.js`
- Temp files go in `InvestmentToolkit/temp/`, never `/tmp/`

---

## What You Are Building

Two new CDP commands and two new harness test sections:

### 1. `chart openDataWindow` (new)
- **Function:** `openDataWindow(client)` in `tradingview-cdp/core/chart.js`
- **CLI:** `node tradingview-cdp/cli.js chart openDataWindow`
- **Returns:** `{ success: true, wasAlreadyOpen: bool }` or `{ success: false, error: string }`
- **Logic:** Check if DW is visible → if not, try right-sidebar button → fall back to Alt+W keyboard event → verify visible → return result

### 2. `chart saveLayout [--name <str>]` (new)
- **Function:** `saveLayout(client, name)` in `tradingview-cdp/core/chart.js`
- **CLI:** `node tradingview-cdp/cli.js chart saveLayout --name "MyLayout"`
- **Returns:** `{ success: true, layoutName: string }` or `{ success: false, error: string }`
- **Logic:** Click toolbar save button → fall back to Cmd+S/Ctrl+S → handle naming modal if it appears

### 3. Harness Section 1.2 — Data Window Readable (new)
- Calls `chart openDataWindow` → injects `Test_HelloWorld` indicator → calls `chart read` → asserts `bar_idx` key in result

### 4. Harness Section 1.3 — Save Layout (new)
- Injects `Test_HelloWorld` → calls `chart saveLayout` → asserts `success: true`

---

## TDD Order (mandatory)

The plan enforces this sequence:
1. **Write failing tests first** (Task 1) — add Sections 1.2 and 1.3 to the harness
2. **Run to confirm they fail** (expected failure: "subcommand not yet implemented")
3. **Implement `openDataWindow`** (Task 2) → run harness → Section 1.2 passes
4. **Implement `saveLayout`** (Task 4) → run harness → Section 1.3 passes
5. **Run full suite** (Task 6) — all sections must pass

Do not skip the TDD order. Do not implement before writing the tests.

---

## User Gates — When to Ask for Help

The plan has explicit `⚠️ USER GATE` markers. These are moments where you **must** pause and ask the user a question before continuing:

1. **Before Task 0 tests:** "Is TradingView Desktop open with a chart showing?"
2. **If `openDataWindow` can't find the panel button:** Ask the user to hover over the Data Window button in TV's right sidebar and tell you its tooltip text
3. **If `bar_idx` key not found in DW:** Log the actual DW keys and ask the user what labels they see in the TV Data Window for the Test_HelloWorld indicator
4. **If `saveLayout` produces an unexpected modal:** Ask the user to describe or screenshot what appeared in TradingView after the save attempt

Never guess past a USER GATE. The user is watching TradingView and can verify things you cannot.

---

## Obstacle Handling Cheat Sheet

| Problem | Fix |
|---|---|
| `npm ci` fails in `tradingview-cdp/` | Run `npm install` instead; check Node version ≥ 18 |
| Section 0 fails (TV not reachable) | Ask user to run `python3 launch_tradingview_with_debugport.py` |
| `openDataWindow` sidebar button not found | Try `data-name` attribute variants; ask user for tooltip text |
| `bar_idx` not in DW keys | Log actual keys; adjust `matching` condition to match TV's label |
| `saveLayout` opens macOS system Save dialog | Remove keyboard fallback; use toolbar button click only |
| Save naming modal selector mismatch | Ask user to inspect element in TV dev tools; update `[class*="modal"]` selector |
| Section 1 (existing inject/remove) breaks | Do not modify `pine.js` or existing injection logic; this is unrelated |

---

## How to Start

```bash
# 1. Read the plan
cat docs/superpowers/plans/2026-05-17-pine-script-mechanical-test-plan.md

# 2. Read the spec  
cat docs/superpowers/specs/2026-05-17-pine-script-mechanical-test-design.md

# 3. Begin Task 0
git checkout main && git pull origin main
git checkout -b feature/pine-script-mechanical-test
cd tradingview-cdp && npm ci && cd ..
```

Then follow the plan task by task, in order. Mark each checkbox as you complete it.
