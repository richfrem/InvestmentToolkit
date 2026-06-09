# /ta-daily-sweep

Invoke the `tradingview:ta-daily-sweep` skill.

**Usage:** `/ta-daily-sweep`

**What it does:**
Batch technical analysis scan of all current portfolio holdings via TradingView CDP.
Reads Data Window (RSI, ADX, Vol Bias, Squeeze, Volume) for each ticker in one session —
no screenshots, all numeric. Cross-references DCF projections. Outputs a ranked report.

**Complement to `/x-news-sweep`:** Run both at the start of a trading session for
a complete fundamental + technical picture.

**Requirements:**
- TradingView Desktop running with `--remote-debugging-port=9222`
- "AI TA Levels" indicator on the chart (provides RSI, ADX, Vol Bias, Squeeze, ATR)
- `portfolio.json` current (run `/tv-portfolio-sync` if stale)

**Output:**
1. Action items — flagged holdings ranked by urgency (REDUCE / MONITOR / ACCUMULATE)
2. Full scan table — all holdings with RSI, ADX, Vol Bias, Volume ratio, Squeeze status
3. Session summary — action breakdown and top flags across the portfolio

**Direct script:**
```bash
python3 plugins/tradingview/scripts/ta_sweep_batch.py
# With options:
python3 plugins/tradingview/scripts/ta_sweep_batch.py --skip HUMN,WYFI --delay 1200
```
