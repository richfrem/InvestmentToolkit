---
name: tv-manage-indicators
plugin: tradingview
description: Unified manager for controlling and querying indicators loaded on the active TradingView chart. Trigger on /tv-indicators or 'list indicators'.
allowed-tools: Bash, Read, Write
---

# TradingView Manage Indicators

Unified manager for controlling and querying indicators loaded on the active TradingView chart.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Exact name matching: Indicators are identified by exact display title in chart legend.
- Duplicate prevention: Avoid adding existing indicators multiple times.
- Preserve layout: Removing an indicator must not affect other loaded series.

## Quick start

```bash
python3 plugins/tradingview/scripts/tv_manage_indicators.py --list
```

## Workflow

1. Query loaded indicators: `tv_manage_indicators.py --list`.
2. Add indicator if requested: `tv_manage_indicators.py --add "{NAME}"`.
3. Remove indicator if requested: `tv_manage_indicators.py --remove "{NAME}"`.
4. Display updated indicator inventory in chat.

## Verification

- Confirm indicator list reflects added or removed items.
- Validate routing cases against `evals/evals.json`.
