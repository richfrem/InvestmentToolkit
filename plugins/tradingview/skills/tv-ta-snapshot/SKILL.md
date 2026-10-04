---
name: tv-ta-snapshot
plugin: tradingview
description: Captures chart screenshot and performs visual technical analysis for a single ticker. Trigger on /tv-ta [TICKER] or 'ta snapshot [TICKER]'.
allowed-tools: Bash, Read, Write
---

# TradingView TA Snapshot

Captures chart screenshot and performs visual technical analysis for a single ticker.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Single ticker scope: Switches chart to requested ticker and performs deep technical analysis.
- DCF cross-reference: Cross-references DCF fair value from SQLite with chart technical levels.
- Screenshot persistence: Saves chart image to `PortfolioAnalysis/screenshots/{YYYY-MM-DD}/{TICKER}.png`.

## Quick start

```bash
python3 plugins/tradingview/scripts/ta_sweep_single.py {TICKER}
```

## Workflow

1. Switch chart to requested ticker and timeframe (1D default).
2. Read Data Window indicator values (21/50/200 EMAs, RSI, Volume).
3. Capture screenshot via `tv_snapshot.py`.
4. Synthesize entry, accumulation, trim, and stop-loss price levels.
5. Output visual TA report with embedded screenshot link.

## Verification

- Confirm screenshot exists and TA report is output to chat.
- Validate routing cases against `evals/evals.json`.
