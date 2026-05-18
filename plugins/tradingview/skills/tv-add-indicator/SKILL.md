---
name: tv_add_indicator
plugin: tradingview
description: >
  Add a built-in TradingView indicator or personal Pine Script to the active
  chart. Opens the Indicators dialog, searches by name, and clicks the first result.
allowed-tools: Bash
---

# TV Add Indicator Skill

**Trigger:** `/add-indicator {NAME}` — e.g. `/add-indicator RSI`

---

## Common Built-in Indicators

```
RSI                   — Relative Strength Index
MACD                  — Moving Average Convergence Divergence
Bollinger Bands       — BB with stddev bands
Volume                — Volume histogram
EMA                   — Exponential Moving Average
SMA                   — Simple Moving Average
Stochastic            — Stochastic oscillator
ATR                   — Average True Range
ADX                   — Average Directional Index
OBV                   — On Balance Volume
VWAP                  — Volume Weighted Average Price
Ichimoku Cloud        — Ichimoku Kinko Hyo
Supertrend            — Supertrend indicator
```

---

## Execution

```bash
node tradingview-cdp/cli.js chart addIndicator "{NAME}"
```

Expected: `{ "success": true, "added": "Relative Strength Index (RSI)" }`

---

## Adding a Personal Pine Script

Personal scripts appear under the **"My scripts"** tab in TV's Indicators dialog.
The same `addIndicator` command works — just provide your script's exact display name:

```bash
node tradingview-cdp/cli.js chart addIndicator "My Custom MA"
```

---

## Loading Multiple Indicators

Run the command once per indicator. Each call opens the dialog, clicks the first
matching result, and closes the dialog.

```bash
node tradingview-cdp/cli.js chart addIndicator "RSI"
node tradingview-cdp/cli.js chart addIndicator "MACD"
node tradingview-cdp/cli.js chart addIndicator "Bollinger Bands"
```

---

## Notes

- After adding indicators, save your workspace: `chart saveLayout --name agent-layout`
- If `success: false, error: "No results found"` — the name didn't match any TV indicator. Try a shorter search term.
- For removing an indicator: `pine remove --indicator "{NAME}"`
