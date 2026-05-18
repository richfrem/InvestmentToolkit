---
name: technical_analysis_expert
plugin: tradingview
description: >
  Acts as a seasoned Technical Analyst and Pine Script expert. Navigates
  TradingView to the requested ticker and timeframe, builds the optimal
  indicator view (reading existing indicators or authoring custom ones via
  author-pine-script), reads the Data Window, and synthesizes entry,
  accumulate, trim, and exit price levels with adversarial red-team review.
allowed-tools: Bash, Read, Write
---

# Technical Analysis Expert Skill

**Trigger:** `/tv-ta-deep {TICKER}` or `/tv-ta-deep {TICKER} {TIMEFRAME}`

**Examples:**
- `/tv-ta-deep NVDA` — daily TA on NVDA
- `/tv-ta-deep AAPL 4H` — 4-hour TA on AAPL
- `/tv-ta-deep BTC 1W` — weekly TA on Bitcoin

**Requirements:** TradingView Desktop running with `--remote-debugging-port=9222`.

**Role:** You are a hybrid TradingView expert, Technical Analyst, and Pine Script
architect. You do not just read whatever indicators happen to be on the chart —
you **build the right view** for the job. If the chart lacks the indicators you
need, you add them or author custom ones. You read across multiple timeframes
when necessary to confirm trend context.

---

## Phase 1 — Parse Arguments

Extract from the trigger:
- Ticker (required): `NVDA`, `AAPL`, `PSU-U.TO`, etc.
- Timeframe (optional, default `1D`): `1D`, `4H`, `1H`, `15`, `W`

If no ticker provided, ask: `"Which ticker would you like to analyze?"`

---

## Phase 2 — Health Check

```bash
node tradingview-cdp/cli.js status
```

If TradingView Desktop is not reachable, stop immediately:
> "TradingView Desktop is not running. Launch it with `python3 launch_tradingview_with_debugport.py` and try again."

---

## Phase 3 — Set Timeframe

```bash
node tradingview-cdp/cli.js chart timeframe {TIMEFRAME}
```

On failure, note the error and continue with whatever timeframe is currently active.

---

## Phase 4 — Build the Optimal Indicator View

You are a TradingView expert. Do not just read whatever is on the chart — build
the correct view for this analysis.

### 4a — Check what is currently loaded

```bash
node tradingview-cdp/cli.js chart indicators
node tradingview-cdp/cli.js chart read
```

### 4b — Evaluate the indicator set

A complete TA view requires at minimum:
- **Trend:** EMA(20), EMA(50), EMA(200) on the price pane
- **Momentum:** RSI(14) in a sub-pane
- **MACD:** MACD(12,26,9) in a sub-pane
- **Volatility:** ATR or Bollinger Bands (for stop placement)

If fewer than 3 of these are present, build the view:

**Option A — Add individual built-in indicators:**
```bash
node tradingview-cdp/cli.js chart addIndicator "EMA"
node tradingview-cdp/cli.js chart addIndicator "RSI"
node tradingview-cdp/cli.js chart addIndicator "MACD"
```

**Option B — Inject a consolidated custom bundle (preferred for clean charts):**
Follow the `author-pine-script` skill to generate and inject a single indicator
named `"AI_TA_Bundle"` that plots all required values in one script:

```pine
//@version=6
indicator("AI_TA_Bundle", overlay=true)
plot(ta.ema(close, 20),  title="EMA20",  color=color.aqua,   linewidth=1)
plot(ta.ema(close, 50),  title="EMA50",  color=color.orange,  linewidth=1)
plot(ta.ema(close, 200), title="EMA200", color=color.red,     linewidth=2)
// RSI and MACD in sub-panes handled via separate indicator() calls or plots
```

### 4c — Research community indicators when relevant

If the user's request involves a specialized indicator (e.g., "add Squeeze Momentum",
"show me Smart Money Concepts"), first read its source to understand the logic:

```bash
python3 plugins/tradingview/skills/author-pine-script/scripts/pine_source_reader.py --name "Squeeze Momentum Indicator [LazyBear]"
```

This saves the source to `temp/indicator_sources/` for inspection before
deciding whether to add the community version or author a custom equivalent.

### 4d — Multi-timeframe context check

For daily (1D) analysis, also read the weekly (1W) to confirm macro trend context:

```bash
node tradingview-cdp/cli.js chart timeframe W
node tradingview-cdp/cli.js chart read
# Note weekly EMA alignment and RSI, then restore
node tradingview-cdp/cli.js chart timeframe {TIMEFRAME}
```

Record the weekly trend context in your synthesis notes.

### 4e — Re-read with complete view

```bash
node tradingview-cdp/cli.js chart read
```

If the Data Window is still empty, open it:
```bash
node tradingview-cdp/cli.js chart openDataWindow
node tradingview-cdp/cli.js chart read
```

---

## Phase 5 — Technical Analysis Synthesis

You are an expert Technical Analyst. Using the Data Window values from Phase 4/5
and any DCF fair value from `investment_screener/backend/data/projections/{TICKER}.json`
(if available), provide a structured analysis:

### Output Format

```
## Technical Analysis — {TICKER} ({TIMEFRAME})

### Trend
- Primary trend: [Bullish / Bearish / Sideways]
- Strength: [strong / moderate / weak]
- Basis: [e.g., "Price above EMA20/50/200, all aligned"]

### Key Levels
| Level | Price | Basis |
|-------|-------|-------|
| Resistance | $X.XX | [e.g., prior high, EMA200] |
| Support | $X.XX | [e.g., EMA50, prior swing low] |

### Momentum
- RSI({period}): {value} — [Overbought / Neutral / Oversold]
- MACD: {value} vs Signal {value} — [Bullish cross / Bearish cross / Flat]

### TA Recommendations
| Action | Price | Condition |
|--------|-------|-----------|
| Initiate | $X.XX | [e.g., "pullback to EMA50 with RSI < 45"] |
| Accumulate | $X.XX | [e.g., "hold above EMA20, RSI 40–60"] |
| Trim | $X.XX | [e.g., "approach to resistance, RSI > 70"] |
| Exit | $X.XX | [e.g., "close below EMA200"] |

### Cross-reference
- DCF Fair Value: ${fairValue} ({action}) — from projections/{TICKER}.json
- TA vs DCF alignment: [Aligned / Diverging — explain]
```

---

## Phase 6 — Compile Draft Thesis

Using the structure in `assets/templates/ta_thesis_template.md` as a guide, populate
all fields with the data and analysis from Phases 3–6. Save the completed draft to:

```
temp/ta_thesis_draft.md
```

Replace every `{{placeholder}}` with real values. Set **Review Status** to `[DRAFT]`.

---

## Phase 7 — Adversarial Red Team Review

Dispatch the `ta-red-team` skill to challenge the draft:

> "Please act as the `ta_red_team` skill and review `temp/ta_thesis_draft.md`."

The red team will respond with `[APPROVED]` or `[REJECTED]` plus specific feedback.

**If `[REJECTED]`:**
1. Read the feedback carefully
2. Re-examine the chart data that was challenged
3. Revise `temp/ta_thesis_draft.md` to address every flagged issue
4. Update **Review Status** to `[REVISED]`
5. Return to Phase 8 and repeat

Retry up to **3 times**. If still rejected after 3 rounds, present the draft to
the user with the unresolved red team objections clearly noted.

**If `[APPROVED]`:** proceed to Phase 9.

---

## Phase 8 — Present Vetted Thesis & Cleanup

Present the approved thesis to the user with a brief summary:

> "**TA Analysis — {TICKER} ({TIMEFRAME}) — APPROVED by red team review**
>
> [Paste the final draft content here]
>
> Red team summary: [One sentence on what was challenged and resolved]"

Then offer cleanup if a custom indicator was injected in Phase 4:

```bash
node tradingview-cdp/cli.js pine remove -i AI_TA_Bundle
node tradingview-cdp/cli.js pine remove -i AI_Custom_TA
```

> "Custom TA indicator(s) removed. Your chart is clean."

---

## Self-Evolution Protocol

If any CDP command fails during this skill (chart read, timeframe change, addIndicator,
pine inject, Data Window open), invoke the `self-evolution` skill before retrying:

1. Read `plugins/tradingview/references/self-evolution-profile.md` for the allowed
   edit directories and error pattern classification table.
2. Classify the failure as Gap / Failure / Regression using the table.
3. Follow the full `self-evolution` protocol (evidence → plan → patch → verify → update map).

**Standing permission:** This skill has permission to patch any file inside
`tradingview-cdp/core/` and `plugins/tradingview/scripts/` when a CDP failure is
classified as Regression or Gap. Modifications to existing functions require a
`git diff` appended to `plugins/tradingview/references/evolution-log.md`.
Deletions always require user confirmation.
