---
name: tv-draw
plugin: tradingview
description: >
  Draws and annotates horizontal level lines, entry/exit price zones, and text tags
  directly onto the active TradingView Desktop chart via CDP.
  Trigger on /tv-draw, "draw horizontal line", "draw buy pocket", or "annotate chart".
allowed-tools: Bash, Read
---

# TradingView Chart Drawing Skill

## What This Skill Does

1. **Draws Horizontal Price Levels**: Injects persistent horizontal lines at key support, resistance, and DCF targets.
2. **Creates Price Accumulation Bands**: Draws top/bottom boundaries for buy pockets and accumulation ranges.
3. **Adds Chart Annotations**: Labels key levels with descriptive text badges.

---

## Execution Examples

### Draw a single horizontal support line:
```bash
python3 plugins/tradingview/scripts/tv_draw.py --horizontal 48.56 --label "200 EMA Support" --color green
```

### Draw a buy pocket accumulation zone:
```bash
python3 plugins/tradingview/scripts/tv_draw.py --box-top 50.56 --box-bottom 48.50 --label "Primary Buy Pocket"
```
