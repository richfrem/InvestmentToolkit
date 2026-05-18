---
name: tv_change_symbol
plugin: tradingview
description: >
  Change the active TradingView chart symbol. Clicks the symbol button in the
  chart header, types the ticker, and confirms with Enter.
allowed-tools: Bash
---

# TV Change Symbol Skill

**Trigger:** `/change-symbol {TICKER}` — e.g. `/change-symbol NVDA`

---

## Execution

```bash
node tradingview-cdp/cli.js chart symbol {TICKER}
```

Expected: `{ "success": true, "symbol": "NVDA" }`

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Symbol button not found` | TV might have an overlay open (Pine Editor, dialog). Close it first. |
| Symbol changed but wrong ticker shown | TV fuzzy-matched to a different symbol. Provide the full exchange-qualified symbol: `NASDAQ:NVDA` |
| No response after 1s | TV search dialog may have not opened. Run again. |

---

## Notes

- TV uses the first autocomplete result. For ambiguous symbols (e.g. `MA`), prefix with exchange: `NYSE:MA`.
- After changing symbol, run `chart saveLayout --name agent-layout` to persist.
- The `/tv-chart-setup` skill combines symbol + timeframe + workspace in one call.
