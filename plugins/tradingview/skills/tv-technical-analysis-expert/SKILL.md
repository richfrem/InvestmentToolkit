---
name: tv-technical-analysis-expert
plugin: tradingview
description: Senior technical analyst workflow: sets up indicator view, reads Data Window, and synthesizes institutional price levels. Trigger on /tv-ta-expert or 'expert technical analysis'.
allowed-tools: Bash, Read, Write
---

# TradingView Technical Analysis Expert

Senior technical analyst workflow: sets up indicator view, reads Data Window, and synthesizes institutional price levels.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Multi-timeframe analysis: Evaluates 1W (macro trend) and 1D (tactical execution).
- Red-team review: Mandatory adversarial check before finalizing price levels.
- Data Window authority: Levels derived from actual Data Window values, not visual guesswork.

## Quick start

```bash
node tradingview-cdp/cli.js chart symbol {TICKER} && node tradingview-cdp/cli.js chart read
```

## Workflow

1. Establish chart setup on target symbol via `tv-chart-setup`.
2. Ensure AI TA Levels v6 indicator is active on chart.
3. Extract indicator metrics from Data Window via CDP.
4. Formulate support floors, trim shelves, and target entry levels.
5. Run adversarial red-team check.
6. Present comprehensive technical thesis.

## Verification

- Confirm technical report incorporates Data Window values.
- Validate routing cases against `evals/evals.json`.
