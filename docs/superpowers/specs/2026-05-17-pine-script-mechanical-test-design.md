# Pine Script v6 Mechanical Test — Design Spec

**Date:** 2026-05-17  
**Status:** Approved for implementation  
**Branch:** `feature/pine-script-mechanical-test`

---

## Goal

Validate the full Pine Script v6 CDP injection pipeline end-to-end — inject, verify on chart, read from Data Window, save layout — before building any complex indicator work. This is a mechanical smoke test: if it all passes, the infrastructure is solid.

---

## What Already Exists

| Capability | CLI command | Status |
|---|---|---|
| Inject Pine Script | `node cli.js pine inject -f <file>` | ✅ Working |
| Remove indicator | `node cli.js pine remove -i <name>` | ✅ Working |
| Read Data Window (raw) | `node cli.js chart datawindow` | ✅ Exists but DW may be closed |
| Change timeframe | `node cli.js chart timeframe 1D` | ✅ Working |
| Harness Section 1 | inject → read → remove cycle | ✅ Passes |

**Gaps identified:**

| Missing Capability | Required for test |
|---|---|
| Open Data Window panel via CDP | Reading indicator values requires DW to be visible |
| Save chart layout via CDP | Verifying indicator persists in saved layout |
| Harness assertion: DW contains named indicator values | Currently passes even if DW is empty |

---

## Architecture

### New CDP functions in `tradingview-cdp/core/chart.js`

**`openDataWindow(client)`**  
Opens the TradingView Data Window panel if not already visible.  
Strategy: dispatch `Alt+W` keyboard event on the document body (TV Desktop shortcut). If the panel is still not visible after 800ms, fall back to clicking `View` menu → `Data Window` menu item.  
Returns: `{ success: true, wasAlreadyOpen: bool }` or `{ success: false, error: string }`

**`saveLayout(client, name?)`**  
Saves the current chart layout. Strategy: dispatch `Ctrl+S` (Mac: `Meta+S`) on the document. If a "Save as new layout" modal appears (first-time save with no prior layout name), fill the name input and press Enter.  
Returns: `{ success: true, layoutName: string }` or `{ success: false, error: string }`

### New CLI subcommands in `tradingview-cdp/cli.js`

```
chart openDataWindow             — open Data Window panel
chart saveLayout [--name <str>]  — save current chart layout (optional name)
```

### Extended harness sections in `plugins/tradingview/tests/tv_test_harness.py`

Section 1 becomes three distinct checks (TDD — tests written first, then implementation):

| Section | Name | What it asserts |
|---|---|---|
| 1.1 | inject + legend | Inject hello-world → indicator appears in chart legend |
| 1.2 | Data Window readable | `openDataWindow` → `readDataWindow` → `"bar_idx"` key present in result |
| 1.3 | Save layout | `saveLayout` returns `success: true` |
| 1.4 | Remove | Remove → indicator gone from legend |

---

## Hello-World Test Script

```pine
//@version=6
indicator("Test_HelloWorld", overlay=false)
plot(bar_index, title="bar_idx")
```

Why `bar_index`: it's always a positive integer, never zero, never null — trivial to assert "value is a number" in the harness.

---

## Obstacle Matrix

| Obstacle | How to detect | Resolution |
|---|---|---|
| TV Desktop not running | Section 0 health check fails | Ask user to run `python3 launch_tradingview_with_debugport.py` |
| `Alt+W` doesn't open DW on this TV version | DW still not visible after dispatch | Fall back to View menu DOM traversal; if that fails, ask user to open DW manually and re-run |
| `Meta+S` triggers browser save dialog instead of layout save | Modal/dialog appears unexpectedly | Use TV's layout save button selector directly instead of keyboard shortcut |
| "Name this layout" modal on first save | Modal visible after Ctrl+S | Handle in `saveLayout`: fill name input + press Enter |
| `bar_idx` not found in DW data dict | Assertion fails with key error | Log actual DW keys to stdout; adjust expected key name to match what TV shows |
| DW shows values for ALL indicators (not just ours) | No isolation issue — just need our key present | Filter test to just assert our key exists in the flat DW dict |
| Pine v6 compile error on inject | `inject` returns `success: false` | Log error, stop with clear message; don't retry in harness (harness is diagnostic, not the skill) |

---

## Files Changed

| File | Change type |
|---|---|
| `tradingview-cdp/core/chart.js` | Add `openDataWindow`, `saveLayout` |
| `tradingview-cdp/cli.js` | Add `chart openDataWindow`, `chart saveLayout` subcommands |
| `plugins/tradingview/tests/tv_test_harness.py` | Add Sections 1.2 and 1.3 (TDD-first) |
| `temp/test_hello_world.pine` | Test fixture (gitignored) |

No changes to `pine.js`, `connection.js`, or any skill SKILL.md — those are already correct.

---

## Definition of Done

- [ ] `node tradingview-cdp/cli.js chart openDataWindow` returns `{ success: true }` with TV running
- [ ] `node tradingview-cdp/cli.js chart saveLayout` returns `{ success: true }` with TV running
- [ ] `python3 plugins/tradingview/tests/tv_test_harness.py --suite pine` — all 4 checks pass
- [ ] No regressions in Section 0, 0.5, or 2
