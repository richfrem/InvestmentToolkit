---
description: Deep Technical Analysis with custom indicator view construction, multi-timeframe context, and adversarial red-team review
argument-hint: "<TICKER> [TIMEFRAME]"
---

# /tv-ta-deep

Invoke the `technical-analysis-expert` skill for a full deep TA session.

**Usage:** `/tv-ta-deep {TICKER}` or `/tv-ta-deep {TICKER} {TIMEFRAME}`

**Examples:**
- `/tv-ta-deep CRWV` — deep TA on CRWV, daily timeframe
- `/tv-ta-deep NVDA 1W` — weekly macro context first, then daily entry analysis
- `/tv-ta-deep IREN 4H` — 4-hour intraday analysis

**What it does (vs basic `/tv-ta`):**
1. Switches chart to the requested ticker + timeframe
2. Builds the optimal indicator view: tries `chart addIndicator` for existing personal/built-in indicators first; authors new Pine Script if needed
3. Reads numeric values from Data Window for precision analysis (not just screenshot OCR)
4. Checks weekly/monthly macro context before zooming into entry timeframe
5. Synthesizes entry, accumulate, trim, and exit levels with specific price targets
6. Runs adversarial red-team review — surfaces reasons the trade could fail
7. Cross-references DCF fair value if projection exists

**Preferred indicators for view setup:**
- "AI TA Levels" (personal library) — EMA 21/50/200 + volume bias
- RSI, MACD — built-in, use `chart addIndicator`

**For interactive guided session:** use `ta-guide` agent — it explains every reading in plain language and pauses for questions at each phase.
