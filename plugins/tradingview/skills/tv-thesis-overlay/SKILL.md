---
name: tv-thesis-overlay
description: "Generates a dynamic Pine Script indicator containing Fair Value, Target Entry, and Breaker levels from SQLite and injects it onto the active TradingView chart."
triggers:
  - "/tv-thesis-overlay"
  - "inject thesis overlay"
  - "overlay thesis levels"
---

# /tv-thesis-overlay — AI Thesis Chart Overlay

Injects fundamental valuation levels (Fair Value from projections, Target Entry from price levels, and Breaker status) from `domain_model.sqlite` onto the active TradingView chart.

## Flow
1. Resolves ticker's fundamental levels across SQLite tables.
2. Switches active chart to the target ticker via CDP (`chart symbol <TICKER>`).
3. Generates and lints a Pine Script v6 indicator (`pine_linter.py`).
4. Injects indicator onto the chart via CDP.

## Usage
```bash
python3 plugins/tradingview/scripts/tv_thesis_overlay.py --ticker <TICKER>
```
To test without injecting:
```bash
python3 plugins/tradingview/scripts/tv_thesis_overlay.py --ticker <TICKER> --dry-run
```
