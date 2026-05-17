---
name: technical_analysis_expert
plugin: tradingview
description: >
  Acts as a seasoned Technical Analyst. Manipulates the TradingView chart to
  the requested ticker and timeframe, reads active indicator values from the
  Data Window, optionally injects custom Pine Script via /pine-inject, and
  synthesizes entry, accumulate, trim, and exit price levels.
allowed-tools: Bash, Read, Write
---

# Technical Analysis Expert Skill

**Trigger:** `/tv-ta-deep {TICKER}` or `/tv-ta-deep {TICKER} {TIMEFRAME}`

**Examples:**
- `/tv-ta-deep NVDA` — daily TA on NVDA
- `/tv-ta-deep AAPL 4H` — 4-hour TA on AAPL

**Requirements:** TradingView Desktop running with `--remote-debugging-port=9222`
and the correct ticker already on the active chart (or navigate there first).

---

## Phase 1 — Parse Arguments

Extract from the trigger:
- Ticker (required): `NVDA`, `AAPL`, `PSU-U.TO`, etc.
- Timeframe (optional, default `1D`): `1D`, `4H`, `1H`, `15`, `W`

If no ticker provided, ask: `"Which ticker would you like to analyze?"`

---

## Phase 2 — Health Check

```bash
node plugins/tradingview/node/cli.js status
```

If TradingView Desktop is not reachable, stop immediately:
> "TradingView Desktop is not running. Launch it with `python3 launch_tradingview_with_debugport.py` and try again."

---

## Phase 3 — Set Timeframe

```bash
node plugins/tradingview/node/cli.js chart timeframe {TIMEFRAME}
```

On failure, note the error and continue with whatever timeframe is currently active.

---

## Phase 4 — Read Data Window

```bash
node plugins/tradingview/node/cli.js chart read
```

If the Data Window returns empty or errors, prompt the user:
> "The Data Window is not visible. Open it in TradingView via View > Data Window, then run this command again."

If the Data Window has fewer than 3 indicators, offer to inject a standard TA bundle:
> "Only {N} indicator(s) visible. Should I inject a standard TA bundle (EMA 20/50/200, RSI 14, MACD) via /pine-inject?"

---

## Phase 5 — Inject Custom Indicators (Optional)

If the user confirms or requests custom indicators, use the `/pine-inject` skill:

> Generate a Pine Script v6 indicator with: EMA(20), EMA(50), EMA(200), RSI(14),
> MACD(12,26,9), volume bars. Name the indicator "AI_Custom_TA".

Then re-read the Data Window:

```bash
node plugins/tradingview/node/cli.js chart read
```

---

## Phase 6 — Technical Analysis Synthesis

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

## Phase 7 — Compile Draft Thesis

Using the structure in `assets/templates/ta_thesis_template.md` as a guide, populate
all fields with the data and analysis from Phases 3–6. Save the completed draft to:

```
temp/ta_thesis_draft.md
```

Replace every `{{placeholder}}` with real values. Set **Review Status** to `[DRAFT]`.

---

## Phase 8 — Adversarial Red Team Review

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

## Phase 9 — Present Vetted Thesis & Cleanup

Present the approved thesis to the user with a brief summary:

> "**TA Analysis — {TICKER} ({TIMEFRAME}) — APPROVED by red team review**
>
> [Paste the final draft content here]
>
> Red team summary: [One sentence on what was challenged and resolved]"

Then offer cleanup if a custom indicator was injected in Phase 5:

```bash
node plugins/tradingview/node/cli.js pine remove -i AI_Custom_TA
```

> "Custom TA indicator removed. Your chart is clean."
