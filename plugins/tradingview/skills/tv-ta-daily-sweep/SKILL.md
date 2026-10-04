---
name: tv-ta-daily-sweep
plugin: tradingview
description: Batch daily Technical Analysis sweep across all portfolio holdings. Trigger on /tv-ta-daily-sweep or 'run ta sweep'.
allowed-tools: Bash, Read, Write
---

# TradingView TA Daily Sweep

Batch daily Technical Analysis sweep across all portfolio holdings.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- CDP automation: Requires TradingView Desktop port 9222 open.
- Full portfolio sweep: Evaluates all active holdings sequentially.
- Standard indicators: Uses Multi-EMA (21/50/200) and volume bias levels.

## Quick start

```bash
python3 plugins/tradingview/scripts/ta_sweep_batch.py
```

## Workflow

1. Pre-flight check on port 9222.
2. Load all portfolio holdings from `domain_model.sqlite`.
3. For each ticker: switch chart, read Data Window EMA levels, capture screenshot.
4. Synthesize technical posture (Bullish, Neutral, Bearish, At Key Support).
5. Compile batch sweep report in chat.

## Verification

- Confirm sweep report generated for all active holdings.
- Validate routing cases against `evals/evals.json`.
