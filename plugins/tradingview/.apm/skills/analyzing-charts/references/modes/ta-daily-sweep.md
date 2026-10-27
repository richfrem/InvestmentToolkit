# Mode: ta-daily-sweep (`/tv-ta-daily-sweep`)

Batch daily Technical Analysis sweep across all portfolio holdings. Trigger on /tv-ta-daily-sweep or 'run ta sweep'.
Allowed tools: Bash, Read, Write.

Batch daily Technical Analysis sweep across all portfolio holdings.


## Constraints

- CDP automation: Requires TradingView Desktop port 9222 open.
- Full portfolio sweep: Evaluates all active holdings sequentially.
- Standard indicators: Uses Multi-EMA (21/50/200) and volume bias levels.

## Quick start

```bash
python3 scripts/ta_sweep_batch.py
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
