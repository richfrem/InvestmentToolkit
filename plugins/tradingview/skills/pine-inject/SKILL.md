---
name: pine_inject
plugin: tradingview
description: >
  Generates custom Pine Script v6 indicators or strategies and injects them directly
  into the TradingView Pine Editor via CDP. Handles compilation errors with an
  auto-correction loop. Serves as a Pine Script expert for creating, saving, and adding to charts.
allowed-tools: Bash, Read, Writei
---

# Pine Script v6 Expert & Injector Skill

## Prerequisites

> **Runtime Dependency:** This skill requires the TradingView CDP engine.

Before using this skill, ensure:

1. **TradingView CDP engine is installed** at the project root:
   ```bash
   cd tradingview-cdp && npm ci
   ```
   
2. **TradingView Desktop is running** with remote debugging enabled:
   ```bash
   # macOS:
   open -a "TradingView" --args --remote-debugging-port=9222
   ```

3. **Health check passes:**
   ```bash
   python3 scripts/tv_health_check.py
   ```

If the CDP engine is not found, set `TV_CDP_DIR` to its location:
```bash
export TV_CDP_DIR=/path/to/tradingview-cdp
```

**Trigger:** `/pine-inject {description}`

**Description:** You are a Pine Script v6 expert. Given the user's description,
generate a complete, valid Pine Script v6 indicator or strategy, inject it into
TradingView Desktop via CDP, and auto-correct on compilation errors. You also assist
with opening the Pine Script Editor, saving scripts and chart layouts, and analyzing errors.

---

## Phase 1 — Parse Intent & Role

Assume the role of a Senior Pine Script Developer.
Extract from the trigger:
- `/pine-inject moving average crossover` → description = "moving average crossover"
- If no description provided, ask: `"What indicator or strategy should I generate for you today?"`

---

## Phase 2 — Generate Pine Script v6

Write a complete, valid Pine Script v6 script following these rules strictly:

**Mandatory v6 rules:**
1. First line MUST be `//@version=6`
2. Second line MUST be `indicator(...)` or `strategy(...)`
3. Use `ta.*` built-ins for all standard calculations (e.g., `ta.sma()`, `ta.ema()`, `ta.rsi()`, `ta.macd()`)
4. MACD tuple unpacking: `[macd, signal, hist] = ta.macd(close, 12, 26, 9)`
5. No deprecated v4/v5 constructs — do not use `study()`, `transp=`, or `iff()`
6. All variables typed or inferable — no bare `na` assignments without a type hint
7. Use `var` for persistent state, `varip` for persistent per-bar-update state
8. Inputs via `input.int()`, `input.float()`, `input.bool()`, `input.string()`
9. `plot()`, `plotshape()`, `bgcolor()` for visualization
10. Keep scripts self-contained — no external library imports

Save the generated script to `temp/generated_script.pine` using the Write tool.

---

## Phase 3 — Inject via CDP & Manage UI

Run the injection command to push the script into TradingView:

```bash
python3 scripts/tv_pine_inject.py -f temp/generated_script.pine
```

*Note: The underlying automation script (`pine.js`) will automatically open the Pine Editor if it is closed, replace the contents of the active tab, and click "Add to chart".*

---

## Phase 4 — Error Checking & Correction

### On success (`{"success": true}`)
Inform the user:
> "Script injected successfully — your indicator is now on the chart."

Then, provide the user with saving instructions for their custom layout:
> **Next steps to save your work:**
> 1. Click the **Save** button in the Pine Editor (or press Cmd/Ctrl + S) to name and save this script to your personal library.
> 2. To persist this indicator on your current chart, click the cloud **Save** button in the top right of the TradingView interface to save your custom layout.

### On failure (`{"success": false, "error": "..."}`)
1. Read the error message from the JSON output.
2. If the error is a compilation issue (e.g., syntax error), assume your role as a Pine Script expert:
   - Analyze the compilation error and identify the cause.
   - Fix the `.pine` file (Write tool → `temp/generated_script.pine`).
   - Re-run the inject command (Phase 3).
   - Retry up to **3 times** before stopping and reporting the unresolved error to the user.
3. If the error is a UI issue (e.g., "Pine Editor tab not found"):
   - Instruct the user to manually click the "Pine Editor" tab at the bottom of the TradingView window, then re-run the skill.
4. If TradingView Desktop is not reachable:
   - Stop and say: > "TradingView Desktop is not running. Launch it with `python3 launch_tradingview_with_debugport.py` and try again."
