---
name: pine_inject
plugin: tradingview
description: >
  Generates custom Pine Script v6 indicators or strategies and injects them directly
  into the TradingView Pine Editor via CDP. Handles compilation errors with an
  auto-correction loop. Foundational primitive for the /pine-analyze TA agent.
allowed-tools: Bash, Read, Write
---

# Pine Script v6 Injector Skill

**Trigger:** `/pine-inject {description}`

**Description:** You are a Pine Script v6 expert. Given the user's description,
generate a complete, valid Pine Script v6 indicator or strategy, inject it into
TradingView Desktop via CDP, and auto-correct on compilation errors.

---

## Phase 1 — Parse Intent

Extract from the trigger:
- `/pine-inject moving average crossover` → description = "moving average crossover"
- If no description provided, ask: `"What indicator or strategy should I generate?"`

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

## Phase 3 — Inject via CDP

Run the injection command:

```bash
node plugins/tradingview/node/cli.js pine inject -f temp/generated_script.pine
```

**Requirements:** TradingView Desktop must be running with `--remote-debugging-port=9222`.

---

## Phase 4 — Handle Result

### On success (`{"success": true}`)
Inform the user:
> "Script injected successfully — your indicator is now on the chart."

### On failure (`{"success": false, "error": "..."}`)
1. Read the error message from the JSON output
2. Analyze the compilation error (e.g., "Undeclared identifier 'foo' at line 4")
3. Fix the `.pine` file (Write tool → `temp/generated_script.pine`)
4. Re-run the inject command (Phase 3)
5. Retry up to **3 times** before stopping and reporting the unresolved error to the user

If TradingView Desktop is not reachable (connection refused on port 9222), stop immediately:
> "TradingView Desktop is not running. Launch it with `python3 launch_tradingview_with_debugport.py` and try again."
