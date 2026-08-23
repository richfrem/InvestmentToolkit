---
name: tv-chart-setup
plugin: tradingview
description: >
  Complete agent workspace setup: switch to agent-layout, change symbol, and
  set timeframe in one shot. Always run this before any chart analysis work.
allowed-tools: Bash
---

# TV Chart Setup Skill

**Trigger:** `/tv-chart-setup {SYMBOL} {TIMEFRAME}` — e.g. `/tv-chart-setup AAPL 1D`

Sets up the agent's dedicated workspace in TradingView before any analysis.

---

## Step 1 — Switch to agent-layout

Always work in agent-layout. Never modify the user's main layout.

```bash
node tradingview-cdp/cli.js chart saveLayout --name agent-layout
```

Expected: `{ "success": true, "action": "saved" | "switched" | "created" }`

On failure → stop and tell the user: *"Could not switch to agent-layout. Is TradingView Desktop running with `--remote-debugging-port=9222`?"*

---

## Step 2 — Change Symbol

```bash
node tradingview-cdp/cli.js chart symbol {SYMBOL}
```

Expected: `{ "success": true, "symbol": "AAPL" }`

If the user didn't provide a symbol, skip this step and use the current chart symbol.

---

## Step 3 — Change Timeframe

```bash
node tradingview-cdp/cli.js chart timeframe {TIMEFRAME}
```

Common values: `1m`, `5`, `15`, `30`, `60`, `240`, `1D`, `D`, `W`, `M`

If the user didn't provide a timeframe, skip this step.

---

## Step 4 — Confirm Ready

Report back:
> "Chart workspace ready: **{SYMBOL}** on **{TIMEFRAME}** in agent-layout."

If any step failed, report the failure and stop — do not silently continue with wrong state.

---

## Notes

- `saveLayout --name agent-layout` is idempotent: creates on first run, switches on subsequent runs.
- After setup, the user's "main layout" is untouched.
- Run `node tradingview-cdp/cli.js status` to verify CDP connection if setup fails.
