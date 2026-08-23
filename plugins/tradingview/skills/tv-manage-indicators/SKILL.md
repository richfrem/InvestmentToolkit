---
name: tv-manage-indicators
plugin: tradingview
description: >
  Manage indicators on the active TradingView chart. Allows listing loaded indicators,
  adding built-in or personal Pine indicators (with duplicate prevention), and removing
  active indicators from the chart layout.
allowed-tools: Bash
---

# TradingView Indicator Manager Skill

Unified manager for controlling and querying indicators loaded on the active TradingView chart.

**Triggers:**
- `/tv-indicators` (List loaded indicators)
- `/tv-indicators add {NAME}`
- `/tv-indicators remove {NAME}`

---

## 1. List Indicators on Active Chart

```bash
python3 plugins/tradingview/scripts/tv_manage_indicators.py --list
```

**Expected Response:**
```json
{
  "success": true,
  "indicators": [
    "SQZMOM_LB",
    "High Volume Points [BigBeluga]",
    "PA Toolkit Lite [UAlgo]",
    "EMA 20/50/100/200",
    "AI-TA",
    "Volume Buoyancy",
    "RSI"
  ],
  "count": 7,
  "source": "legend"
}
```

---

## 2. Add an Indicator to Chart

Adds built-in indicators or personal saved Pine scripts from your library. Automatically guards against adding duplicate copies.

```bash
# Add built-in indicator:
python3 plugins/tradingview/scripts/tv_manage_indicators.py --add "Relative Strength Index"

# Add personal Pine script:
python3 plugins/tradingview/scripts/tv_manage_indicators.py --add "AI Thesis & Valuation Overlay"
```

---

## 3. Remove an Indicator from Chart

```bash
python3 plugins/tradingview/scripts/tv_manage_indicators.py --remove "RSI"
```
