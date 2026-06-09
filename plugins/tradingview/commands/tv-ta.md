---
description: Technical Analysis snapshot — screenshot + visual analysis with Data Window numeric readings and DCF cross-reference
argument-hint: "<TICKER> [TIMEFRAME]"
---

# /tv-ta

Invoke the `tv_ta_snapshot` skill.

**Usage:** `/tv-ta {TICKER}` or `/tv-ta {TICKER} {TIMEFRAME}`

**Examples:**
- `/tv-ta CRWV` — TA snapshot of CRWV using current chart settings
- `/tv-ta NVDA 1W` — weekly chart TA snapshot of NVDA
- `/tv-ta INTC` — TA snapshot, cross-referenced against DCF projection if available

**Setup tip:** For richer analysis, ensure "AI TA Levels" is on the chart first:
```bash
node tradingview-cdp/cli.js chart addIndicator "AI TA Levels"
node tradingview-cdp/cli.js chart read   # verify EMA + volume bias visible
```
The Data Window read gives precise EMA levels without relying on screenshot OCR.

**For a full deep-dive with custom indicator setup and adversarial review:** use `/tv-ta-deep {TICKER}`
**For an interactive guided TA session with explanations:** use `ta-guide` agent
