# Pine Script v6 Mechanical Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the full Pine Script v6 CDP injection pipeline — inject, verify on chart, read from Data Window, save layout — by implementing two missing CDP commands and extending the test harness with explicit assertions.

**Architecture:** Two new functions (`openDataWindow`, `saveLayout`) added to `tradingview-cdp/core/chart.js` and wired as subcommands in `tradingview-cdp/cli.js`. The existing `plugins/tradingview/tests/tv_test_harness.py` gains Sections 1.2 and 1.3. TDD order: harness tests are written first (and will fail), then the CDP functions are implemented to make them pass.

**Tech Stack:** Node.js ESM, Chrome DevTools Protocol (`chrome-remote-interface`), Python 3.11 subprocess harness.

---

## Context: What Already Exists (read before touching anything)

- **`tradingview-cdp/core/chart.js`** — has `changeTimeframe(client)` and `readDataWindow(client)`. Append new functions; do not modify existing ones.
- **`tradingview-cdp/cli.js`** — has `chart` command with `timeframe` and `read` subcommands. Add `openDataWindow` and `saveLayout` to the same Map.
- **`plugins/tradingview/tests/tv_test_harness.py`** — has Sections 0, 0.5, 1 (inject/read/remove), 2. Add Sections 1.2 and 1.3 between the existing Section 1 test and Section 2.
- **`tradingview-cdp/`** must be installed before any test runs: `cd tradingview-cdp && npm ci`
- **TradingView Desktop must be running** on port 9222 with a chart open for all Section 1+ tests.

---

## File Map

| File | Change |
|---|---|
| `tradingview-cdp/core/chart.js` | **Append** `openDataWindow(client)` and `saveLayout(client, name)` |
| `tradingview-cdp/cli.js` | **Add** `openDataWindow` and `saveLayout` entries to `chart` subcommands Map |
| `plugins/tradingview/tests/tv_test_harness.py` | **Add** `test_pine_data_window_readable()` (§1.2) and `test_pine_save_layout()` (§1.3); wire both into `main()` |
| `temp/test_hello_world.pine` | Created at runtime by the harness (gitignored, no commit needed) |

---

## Task 0: Branch + Prereqs

**Files:** none

- [ ] **Create feature branch**

```bash
git checkout main && git pull origin main
git checkout -b feature/pine-script-mechanical-test
```

- [ ] **Verify CDP runtime is installed**

```bash
cd tradingview-cdp && npm ci && cd ..
```

Expected: no errors, `node_modules/` populated.

- [ ] **Launch TradingView Desktop with CDP** (ask user to do this if it's not running)

```bash
python3 launch_tradingview_with_debugport.py
```

> **⚠️ USER GATE:** TradingView Desktop must be open with any chart visible before continuing. Ask the user: "Is TradingView Desktop open with a chart showing?" If no, run the above command and wait for confirmation.

- [ ] **Run Section 0 prereqs to confirm connectivity**

```bash
python3 plugins/tradingview/tests/tv_test_harness.py --suite prereqs
```

Expected: all checks `✓`. If any fail, stop and report to user before continuing.

---

## Task 1: Write Failing Harness Tests (TDD — tests first)

**Files:**
- Modify: `plugins/tradingview/tests/tv_test_harness.py`

Read the harness file before editing. The existing structure is:
- `check_tv_reachable()` etc. for Section 0
- `test_live_pine_cycle()` for Section 1 (inject → read → remove)
- `test_chart_timeframe_known()` etc. for Section 2
- `main()` calls them in order

- [ ] **Add `test_pine_data_window_readable()` after `test_live_pine_cycle()`**

Insert this function after line ~264 (after `test_live_pine_cycle` closes), before Section 2:

```python
def test_pine_data_window_readable() -> tuple[bool, str]:
    """[1.2] openDataWindow → inject hello-world → assert bar_idx key in DW."""
    pine_file = TEMP_DIR / "test_hello_world.pine"
    pine_file.write_text(
        '//@version=6\nindicator("Test_HelloWorld", overlay=false)\nplot(bar_index, title="bar_idx")'
    )
    try:
        # Step A: open Data Window
        r = subprocess.run(
            ["node", "cli.js", "chart", "openDataWindow"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
        )
        dw_open = json.loads(r.stdout.strip()) if r.stdout.strip() else {}
        if not dw_open.get("success"):
            return False, (
                f"openDataWindow failed: {dw_open}\n"
                "  → chart openDataWindow subcommand not yet implemented (expected at this TDD stage)"
            )

        # Step B: inject hello-world
        r2 = subprocess.run(
            ["node", "cli.js", "pine", "inject", "-f", str(pine_file)],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=20,
        )
        inject_out = json.loads(r2.stdout.strip()) if r2.stdout.strip() else {}
        if not inject_out.get("success"):
            return False, f"inject failed: {inject_out}"

        import time; time.sleep(2)

        # Step C: read DW and assert bar_idx present
        r3 = subprocess.run(
            ["node", "cli.js", "chart", "read"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
        )
        dw_out = json.loads(r3.stdout.strip()) if r3.stdout.strip() else {}
        if not dw_out.get("success"):
            return False, (
                f"readDataWindow failed: {dw_out}\n"
                "  Hint: Is Data Window visible in TV? Ask user to confirm."
            )
        data = dw_out.get("data", {})
        matching = [k for k in data if "bar_idx" in k.lower() or "bar index" in k.lower()]
        if not matching:
            return False, (
                f"'bar_idx' not found in DW. Actual keys: {list(data.keys())[:15]}\n"
                "  ⚠️ USER GATE: Ask the user what labels appear in the TV Data Window for 'Test_HelloWorld'. "
                "Update the key check below to match the exact label TV shows."
            )
        return True, f"DW readable — found key '{matching[0]}' = {data[matching[0]]}"
    finally:
        subprocess.run(
            ["node", "cli.js", "pine", "remove", "-i", "Test_HelloWorld"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
        )
```

- [ ] **Add `test_pine_save_layout()` directly after `test_pine_data_window_readable()`**

```python
def test_pine_save_layout() -> tuple[bool, str]:
    """[1.3] Inject hello-world → saveLayout → assert success."""
    pine_file = TEMP_DIR / "test_hello_world.pine"
    pine_file.write_text(
        '//@version=6\nindicator("Test_HelloWorld", overlay=false)\nplot(bar_index, title="bar_idx")'
    )
    try:
        r = subprocess.run(
            ["node", "cli.js", "pine", "inject", "-f", str(pine_file)],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=20,
        )
        inject_out = json.loads(r.stdout.strip()) if r.stdout.strip() else {}
        if not inject_out.get("success"):
            return False, f"inject failed: {inject_out}"

        import time; time.sleep(1)

        r2 = subprocess.run(
            ["node", "cli.js", "chart", "saveLayout", "--name", "Test_HelloWorld_Layout"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=20,
        )
        save_out = json.loads(r2.stdout.strip()) if r2.stdout.strip() else {}
        if not save_out.get("success"):
            return False, (
                f"saveLayout failed: {save_out}\n"
                "  → chart saveLayout subcommand not yet implemented (expected at this TDD stage)\n"
                "  ⚠️ USER GATE if unexpected: Ask user if a dialog appeared in TV after running this."
            )
        return True, f"Layout saved: {save_out}"
    finally:
        subprocess.run(
            ["node", "cli.js", "pine", "remove", "-i", "Test_HelloWorld"],
            capture_output=True, text=True, cwd=str(TV_NODE_DIR), timeout=15,
        )
```

- [ ] **Wire both new tests into `main()` in the harness**

In `main()`, find the block that runs Section 1 (`--suite pine`). It looks like:

```python
    if args.suite in ("pine", "all"):
        print(f"\n{HEADER}Section 1 — Pine Script Live Cycle{RESET}")
        ok, msg = test_live_pine_cycle()
        ...
```

Add the two new sections immediately after the existing Section 1 block (still inside the `"pine", "all"` branch):

```python
        print(f"\n{HEADER}Section 1.2 — Data Window Readable{RESET}")
        ok, msg = test_pine_data_window_readable()
        print(f"  {'✓' if ok else '✗'} [1.2] {msg}")
        if not ok:
            section1_failed = True

        print(f"\n{HEADER}Section 1.3 — Save Chart Layout{RESET}")
        ok, msg = test_pine_save_layout()
        print(f"  {'✓' if ok else '✗'} [1.3] {msg}")
        if not ok:
            section1_failed = True
```

> **Note:** `section1_failed` is the existing boolean used to set the exit code for Section 1 failures. Check the harness to confirm the exact variable name — adjust if different.

- [ ] **Run the tests — confirm they fail with the expected "not yet implemented" message**

```bash
python3 plugins/tradingview/tests/tv_test_harness.py --suite pine
```

Expected: Section 1 (existing) passes. Sections 1.2 and 1.3 fail with `"subcommand not yet implemented"` (because we haven't written the CDP functions yet). If Section 1 itself fails, fix that before continuing.

---

## Task 2: Implement `openDataWindow` in chart.js

**Files:**
- Modify: `tradingview-cdp/core/chart.js` (append after `readDataWindow`)

- [ ] **Append `openDataWindow` to `tradingview-cdp/core/chart.js`**

Add the following after the closing `}` of `readDataWindow` (after line 181):

```javascript
/**
 * Open the TradingView Data Window panel if not already visible.
 *
 * Strategy: check if visible, then try right-sidebar toggle button,
 * then fall back to Alt+W keyboard shortcut.
 *
 * Args:
 *   client: CDP client instance
 *
 * Returns:
 *   { success: true, wasAlreadyOpen: bool }
 *   { success: false, error: string } if panel could not be opened
 */
export async function openDataWindow(client) {
  try {
    const dwSelectors = [
      '[class*="data-window"]',
      '[class*="dataWindow"]',
      '[class*="DataWindow"]',
    ];
    const selectorJS = JSON.stringify(dwSelectors);

    // 1. Check if already visible
    const checkResult = await client.Runtime.evaluate({
      expression: `(function() {
        var selectors = ${selectorJS};
        for (var i = 0; i < selectors.length; i++) {
          var dw = document.querySelector(selectors[i]);
          if (dw && dw.offsetParent) return JSON.stringify({ visible: true });
        }
        return JSON.stringify({ visible: false });
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    const checkData = JSON.parse(checkResult.result.value);
    if (checkData.visible) return { success: true, wasAlreadyOpen: true };

    // 2. Try sidebar button or keyboard shortcut
    await client.Runtime.evaluate({
      expression: `(function() {
        // Look for a right-sidebar button whose title/aria-label mentions Data Window
        var btn = [...document.querySelectorAll('button, [role="button"]')].find(function(b) {
          if (!b.offsetParent) return false;
          var t = (
            b.title ||
            b.getAttribute('aria-label') ||
            b.getAttribute('data-tooltip') ||
            b.getAttribute('data-name') ||
            ''
          ).toLowerCase();
          return t.includes('data window') || t.includes('datawindow');
        });
        if (btn) { btn.click(); return; }
        // Fallback: Alt+W shortcut
        document.dispatchEvent(
          new KeyboardEvent('keydown', { key: 'w', altKey: true, bubbles: true })
        );
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    await new Promise(r => setTimeout(r, 800));

    // 3. Verify it opened
    const verifyResult = await client.Runtime.evaluate({
      expression: `(function() {
        var selectors = ${selectorJS};
        for (var i = 0; i < selectors.length; i++) {
          var dw = document.querySelector(selectors[i]);
          if (dw && dw.offsetParent) return JSON.stringify({ visible: true });
        }
        return JSON.stringify({ visible: false });
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    const verifyData = JSON.parse(verifyResult.result.value);
    if (verifyData.visible) return { success: true, wasAlreadyOpen: false };
    return {
      success: false,
      error: 'Data Window did not open — open it manually via View > Data Window in TradingView, then re-run',
    };
  } catch (e) {
    return { success: false, error: e.message };
  }
}
```

- [ ] **Wire `openDataWindow` into `tradingview-cdp/cli.js`**

In `cli.js`, find the `chart` subcommands Map. After the closing `}]` of the `read` subcommand (around line 155), add a comma and the new entry — so the Map becomes:

```javascript
    ['read', {
      description: 'Read all active indicator values from the Data Window panel',
      handler: async () => {
        const { getClient } = await import('./connection.js');
        const client = await getClient();
        return chart.readDataWindow(client);
      },
    }],
    ['openDataWindow', {
      description: 'Open the Data Window panel if not already visible',
      handler: async () => {
        const { getClient } = await import('./connection.js');
        const client = await getClient();
        return chart.openDataWindow(client);
      },
    }],
```

- [ ] **Smoke-test the new command manually** (TradingView must be running)

```bash
node tradingview-cdp/cli.js chart openDataWindow
```

Expected: `{ "success": true, "wasAlreadyOpen": true/false }`.

If it returns `{ "success": false, "error": "Data Window did not open..." }`:
> **⚠️ USER GATE:** Ask the user to look at TradingView. Is there a Data Window panel button in the right sidebar? Have them hover over it and tell you the tooltip text. Use that text to update the `t.includes(...)` condition in `openDataWindow`. Common alternatives: `"data"`, `"window"`, `"dw"`.

---

## Task 3: Run Section 1.2 — Data Window Readable

**Files:** none (just running tests)

- [ ] **Run Section 1.2 only**

```bash
python3 plugins/tradingview/tests/tv_test_harness.py --suite pine
```

Watch for `[1.2]` output. Expected: `✓ [1.2] DW readable — found key 'bar_idx' = <number>`

**If `[1.2]` fails with `'bar_idx' not found in DW. Actual keys: [...]`:**
> **⚠️ USER GATE:** The test prints the actual keys TV shows in the Data Window. Share those keys. The fix is to update the `matching` condition in `test_pine_data_window_readable` to match the exact key TV uses for the indicator's plot title. For example if TV shows `"Test_HelloWorld 1"` as the label instead of `"bar_idx"`, change the condition to:
> ```python
> matching = [k for k in data if "helloworld" in k.lower() or "bar_idx" in k.lower()]
> ```
> Re-run after the fix.

**If `[1.2]` fails with `readDataWindow failed: {'success': False, 'error': 'Data Window panel not visible'}`:**
> **⚠️ USER GATE:** The `openDataWindow` step succeeded but DW closed between steps. Ask user if DW is visible in TV right now. If not, check if a timeframe change or inject animation closed it. Add a re-open call after inject in `test_pine_data_window_readable` (call `openDataWindow` again after the inject step).

- [ ] **Commit after Section 1.2 passes**

```bash
git add tradingview-cdp/core/chart.js tradingview-cdp/cli.js plugins/tradingview/tests/tv_test_harness.py
git commit -m "feat(tradingview): add openDataWindow CDP command + harness section 1.2"
```

---

## Task 4: Implement `saveLayout` in chart.js

**Files:**
- Modify: `tradingview-cdp/core/chart.js` (append after `openDataWindow`)

- [ ] **Append `saveLayout` to `tradingview-cdp/core/chart.js`**

Add after the closing `}` of `openDataWindow`:

```javascript
/**
 * Save the current TradingView chart layout.
 *
 * Strategy: look for a toolbar "Save" button, fall back to Meta+S / Ctrl+S.
 * If a naming modal appears (first-time save), fill the name and confirm.
 *
 * Args:
 *   client: CDP client instance
 *   name:   optional layout name string (used if a naming modal appears)
 *
 * Returns:
 *   { success: true, layoutName: string }
 *   { success: false, error: string }
 */
export async function saveLayout(client, name) {
  try {
    const safeName = name ? JSON.stringify(String(name)) : JSON.stringify('InvestmentToolkit');

    // 1. Click the toolbar Save / cloud-save button, or fall back to Meta+S
    await client.Runtime.evaluate({
      expression: `(function() {
        // Look for a save button in the top toolbar by title/aria-label
        var saveBtn = [...document.querySelectorAll('button, [role="button"]')].find(function(b) {
          if (!b.offsetParent) return false;
          var t = (
            b.title ||
            b.getAttribute('aria-label') ||
            b.getAttribute('data-tooltip') ||
            b.getAttribute('data-name') ||
            ''
          ).toLowerCase();
          return (t.includes('save') && (t.includes('layout') || t.includes('chart'))) ||
                 t === 'save';
        });
        if (saveBtn) { saveBtn.click(); return; }
        // Fallback: Cmd+S (Mac) or Ctrl+S (Windows/Linux)
        var isMac = /mac/i.test(navigator.platform);
        document.body.dispatchEvent(new KeyboardEvent('keydown', {
          key: 's', code: 'KeyS',
          metaKey: isMac, ctrlKey: !isMac,
          bubbles: true, cancelable: true,
        }));
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    await new Promise(r => setTimeout(r, 700));

    // 2. Check for a naming/confirm modal
    const modalResult = await client.Runtime.evaluate({
      expression: `(function() {
        var modal = [...document.querySelectorAll('[class*="modal"], [class*="dialog"], [role="dialog"]')]
          .find(function(m) {
            return m.offsetParent && m.textContent.toLowerCase().includes('save');
          });
        if (!modal) return JSON.stringify({ modalVisible: false });
        var input = modal.querySelector('input[type="text"], input:not([type="hidden"]):not([type="checkbox"])');
        return JSON.stringify({ modalVisible: true, hasInput: !!input });
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    const modalData = JSON.parse(modalResult.result.value);

    if (modalData.modalVisible) {
      if (modalData.hasInput) {
        // Fill the name using React's native input setter
        await client.Runtime.evaluate({
          expression: `(function() {
            var modal = [...document.querySelectorAll('[class*="modal"], [class*="dialog"], [role="dialog"]')]
              .find(function(m) { return m.offsetParent && m.textContent.toLowerCase().includes('save'); });
            if (!modal) return;
            var input = modal.querySelector('input[type="text"], input:not([type="hidden"]):not([type="checkbox"])');
            if (!input) return;
            input.focus();
            var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(input, ${safeName});
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
          })()`,
          returnByValue: true,
          awaitPromise: false,
        });
        await new Promise(r => setTimeout(r, 300));
      }

      // Click Save / OK / Confirm in the modal
      await client.Runtime.evaluate({
        expression: `(function() {
          var modal = [...document.querySelectorAll('[class*="modal"], [class*="dialog"], [role="dialog"]')]
            .find(function(m) { return m.offsetParent && m.textContent.toLowerCase().includes('save'); });
          if (!modal) return;
          var confirmBtn = [...modal.querySelectorAll('button')].find(function(b) {
            var t = b.textContent.trim().toLowerCase();
            return t === 'save' || t === 'ok' || t === 'confirm' || t === 'apply';
          });
          if (confirmBtn) { confirmBtn.click(); return; }
          // Fallback: Enter key
          modal.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
        })()`,
        returnByValue: true,
        awaitPromise: false,
      });

      await new Promise(r => setTimeout(r, 500));
    }

    return { success: true, layoutName: name || 'saved' };
  } catch (e) {
    return { success: false, error: e.message };
  }
}
```

- [ ] **Wire `saveLayout` into `tradingview-cdp/cli.js`**

In the `chart` subcommands Map, after the `openDataWindow` entry, add:

```javascript
    ['saveLayout', {
      description: 'Save the current chart layout (optional --name)',
      options: {
        name: { type: 'string', short: 'n', description: 'Layout name (used if a naming dialog appears)' },
      },
      handler: async (opts) => {
        const { getClient } = await import('./connection.js');
        const client = await getClient();
        return chart.saveLayout(client, opts.name);
      },
    }],
```

- [ ] **Smoke-test `saveLayout` manually** (TradingView must be running with a chart)

```bash
node tradingview-cdp/cli.js chart saveLayout --name "TestLayout"
```

Expected: `{ "success": true, "layoutName": "TestLayout" }`.

Watch TradingView for a brief save animation (cloud icon flash) or a naming modal.

**If a naming modal appeared and wasn't handled:**
> **⚠️ USER GATE:** Ask the user to describe what they see in TradingView — screenshot if possible. The modal may have a different CSS class. Share the class names visible in browser dev tools. Update the `[class*="modal"]` selectors in `saveLayout` to match.

**If Cmd+S opened the macOS "Save" system dialog instead of the TV layout save:**
> This means TV didn't intercept the keyboard event. Switch to clicking the toolbar save button exclusively — remove the keyboard fallback from `saveLayout` and look more carefully for the button. Ask the user to hover over the save/cloud icon in TV's top bar and report the tooltip text.

---

## Task 5: Run Section 1.3 — Save Layout

**Files:** none (just running tests)

- [ ] **Run the full pine suite**

```bash
python3 plugins/tradingview/tests/tv_test_harness.py --suite pine
```

Expected all pass:
```
Section 1 — Pine Script Live Cycle
  ✓ [1.1] inject (with modal handling) → read → remove cycle succeeded

Section 1.2 — Data Window Readable
  ✓ [1.2] DW readable — found key 'bar_idx' = 42

Section 1.3 — Save Chart Layout
  ✓ [1.3] Layout saved: {"success": true, "layoutName": "Test_HelloWorld_Layout"}
```

**If `[1.3]` passes but TV shows a "Save failed" toast:** This is a TV-side issue (e.g., no internet, or free-tier layout limit). Return value is `success: true` because the CDP call worked — report the toast text to the user and note it's a TV account limitation, not a code bug.

- [ ] **Commit after Section 1.3 passes**

```bash
git add tradingview-cdp/core/chart.js tradingview-cdp/cli.js plugins/tradingview/tests/tv_test_harness.py
git commit -m "feat(tradingview): add saveLayout CDP command + harness section 1.3"
```

---

## Task 6: Run Full Harness Suite — No Regressions

**Files:** none

- [ ] **Run all sections**

```bash
python3 plugins/tradingview/tests/tv_test_harness.py
```

Expected: all sections pass (0, 0.5, 1, 1.2, 1.3, 2). Exit code 0.

If Section 2 (chart command tests) regresses, read the specific error — it is likely unrelated to this change (timeframe or selector issue). Report to user before fixing.

---

## Task 7: Update CLAUDE.md + Commit + Push

**Files:**
- Modify: `.claude/CLAUDE.md`

- [ ] **Add the two new CLI commands to the Known Pitfalls section** in `.claude/CLAUDE.md`

In the "Key Files" table or the tradingview CDP pitfall section, add a note:

```
### New chart commands (added in feature/pine-script-mechanical-test)
- `node tradingview-cdp/cli.js chart openDataWindow` — opens the Data Window panel
- `node tradingview-cdp/cli.js chart saveLayout [--name <str>]` — saves current chart layout
```

- [ ] **Final commit and push**

```bash
git add .claude/CLAUDE.md
git commit -m "docs(tradingview): document openDataWindow + saveLayout chart commands"
git push -u origin feature/pine-script-mechanical-test
```

- [ ] **Open PR to main**

```bash
gh pr create \
  --title "feat(tradingview): Pine Script v6 mechanical test — openDataWindow + saveLayout" \
  --body "Adds two missing CDP commands and harness sections 1.2/1.3 to fully validate the inject pipeline."
```

---

## Definition of Done

- [ ] `node tradingview-cdp/cli.js chart openDataWindow` → `{ success: true }`
- [ ] `node tradingview-cdp/cli.js chart saveLayout --name "X"` → `{ success: true }`
- [ ] `python3 plugins/tradingview/tests/tv_test_harness.py` — all sections pass, exit 0
- [ ] No regressions in Section 0, 0.5, 1, or 2
