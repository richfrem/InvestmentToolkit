---
name: tv-change-type
plugin: tradingview
description: >
  Change the active TradingView chart type (candle style). Supports candlestick,
  Heikin Ashi, line, area, Renko, bars, and all other TV chart types.
allowed-tools: Bash
---

# TV Change Chart Type Skill

**Trigger:** `/change-chart-type {TYPE}` — e.g. `/change-chart-type heikin-ashi`

---

## Supported Types

| Alias | TV label |
|---|---|
| `candle` / `candlestick` | Candlestick |
| `heikin-ashi` / `ha` | Heikin Ashi |
| `bars` | Bars |
| `hollow` / `hollow-candle` | Hollow candles |
| `volume-candle` | Volume candles |
| `line` | Line |
| `line-markers` | Line with markers |
| `step` | Step line |
| `area` | Area |
| `hlc` | HLC area |
| `baseline` | Baseline |
| `columns` | Columns |
| `high-low` | High-low |
| `renko` | Renko |
| `line-break` | Line break |
| `kagi` | Kagi |
| `point-figure` | Point & figure |
| `range` | Range |

---

## Execution

```bash
node tradingview-cdp/cli.js chart type {TYPE}
```

Expected: `{ "success": true, "type": "Heikin Ashi" }`

On failure: the button with that aria-label wasn't visible. Check that no dialog is blocking the toolbar, then retry.

---

## Notes

- After changing chart type, call `chart saveLayout --name agent-layout` to persist the change.
- Heikin Ashi smooths price action and is useful for trend-following analysis.
- Renko and Kagi filter out noise but require the chart to be in the right timeframe context.
