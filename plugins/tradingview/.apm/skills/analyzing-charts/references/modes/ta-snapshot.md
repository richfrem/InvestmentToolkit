# Mode: ta-snapshot (`/tv-ta`)

Captures chart screenshot and performs visual technical analysis for a single ticker. Trigger on /tv-ta [TICKER] or 'ta snapshot [TICKER]'.
Allowed tools: Bash, Read, Write.

Captures chart screenshot and performs visual technical analysis for a single ticker.


## Constraints

- Single ticker scope: Switches chart to requested ticker and performs deep technical analysis.
- DCF cross-reference: Cross-references DCF fair value from SQLite with chart technical levels.
- Screenshot persistence: Saves chart image to `PortfolioAnalysis/screenshots/{YYYY-MM-DD}/{TICKER}.png`.

## Quick start

```bash
python3 scripts/ta_sweep_single.py {TICKER}
```

## Workflow

1. Switch chart to requested ticker and timeframe (1D default).
2. Read Data Window indicator values (21/50/200 EMAs, RSI, Volume).
3. Capture the screenshot with the Node CLI: `node tradingview-cdp/cli.js screenshot --output {TICKER}` (the script `tv_snapshot.py` named by the earlier version of this skill does not exist).
4. Synthesize entry, accumulation, trim, and stop-loss price levels.
5. Output visual TA report with embedded screenshot link.

## Verification

- Confirm screenshot exists and TA report is output to chat.
- Validate routing cases against `evals/evals.json`.
