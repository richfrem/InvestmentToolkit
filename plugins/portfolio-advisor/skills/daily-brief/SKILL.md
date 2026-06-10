---
name: daily_brief
plugin: portfolio-advisor
description: >
  One daily command that synthesizes macro regime, TA sweep, DCF valuations,
  and thesis weight gaps into a ranked conviction-scored action list. Saves a
  JSON snapshot that compounds over time — each run surfaces delta vs.
  yesterday and trend patterns across the portfolio. The continuous improvement
  loop for long-term thesis-driven investing.
  Trigger on /daily-brief, "run daily brief", "morning scan", or "what should I do today".
allowed-tools: Bash, Read, Write
---

# Daily Brief Skill

## What This Runs

One script orchestrates the full loop:

```bash
python3 plugins/portfolio-advisor/scripts/daily_brief.py
```

**With flags:**
```bash
# Skip TA sweep refresh (use stale data if TV not running)
python3 plugins/portfolio-advisor/scripts/daily_brief.py --skip-ta

# Raw JSON output (for programmatic processing)
python3 plugins/portfolio-advisor/scripts/daily_brief.py --json
```

**Direct component scripts (when you need just one signal):**
```bash
# Macro regime only
python3 investment_screener/backend/py_services/macro_regime.py

# Earnings calendar (next 14 days)
python3 investment_screener/backend/py_services/earnings_calendar.py --days 14

# Conviction scores only
python3 investment_screener/backend/py_services/compute_conviction_scores.py
```

---

## What the Brief Contains

| Section | Source | Action |
|---------|--------|--------|
| **Macro Regime** | VIX + SPY 200D + HYG/LQD | Hard gate — RISK-OFF blocks all ACCUMULATE |
| **Binary Events** | yfinance earnings calendar | Pre-event size flags for holdings within 14 days |
| **REDUCE / EXIT** | Conviction ≤ −1 | Ranked by urgency; act on these first |
| **ACCUMULATE** | Conviction ≥ +3 + RISK-ON/NEUTRAL macro | Underweight + cheap + momentum |
| **Score Deltas** | vs. yesterday's snapshot | Surfaces deteriorating positions early |
| **Pillar Health** | Sub-strategy aggregation | Catches pillar-level thesis drift |

---

## Conviction Score Formula

```
total = dcf_pts + ta_pts + weight_gap_pts + momentum_pts

dcf_pts       : +2 (BUY/ACCUMULATE) | +1 (MAINTAIN/HOLD) | -1 (TRIM) | -2 (SELL)
ta_pts        : +1 (RSI<35) | -1 (RSI>70 or RSI_COOLING) | -1 (vol_bias<-25%) [max +1]
weight_gap_pts: +1 (underweight + BUY) | -1 (overweight + SELL)
momentum_pts  : +1 (ADX≥30 + no cooling) | -1 (ADX≥30 + RSI_COOLING)

Bands:
  ≥ +3 : ACCUMULATE
  +1–+2: HOLD
   0   : WATCH
  -1–-2: REDUCE
  ≤ -3 : EXIT
```

---

## Macro Gate — Hard Rules

| Regime | Rule |
|--------|------|
| RISK-ON  | All signals valid. ACCUMULATE candidates are actionable. |
| NEUTRAL  | Only score ≥ +4 ACCUMULATE candidates. Hold cash otherwise. |
| RISK-OFF | No new buys. Execute REDUCE/EXIT list only. Cash is the position. |

**Never accumulate into a RISK-OFF environment**, regardless of DCF upside. Undervalued
growth stocks stay cheap for 12–18 months during risk-off regimes.

---

## Binary Event Protocol

For any holding flagged IMMINENT (< 7 days) or APPROACHING (< 14 days):

1. **Before event**: Reduce to 50–75% of target if currently at or above target weight
2. **After event — thesis intact**: Reload to full target at best price post-reaction
3. **After event — thesis broken**: Exit. Do not average down into a broken thesis.

State this protocol to the user for each flagged holding before taking any other action.

---

## After the Brief — Routing to Action

Once the brief is presented, ask the user which signals they want to act on:

| User Intent | Route To |
|-------------|----------|
| "Trim / exit [TICKER]" | `/rebalance` or `/place-order sell` |
| "Accumulate [TICKER]" | Check `targetEntryPrice` in target-portfolio.json first; then `/place-order buy` |
| "News context on [TICKER]" | `/x-news-sweep` |
| "Re-evaluate thesis after this data" | `/strategic-review` |
| "Update DCF for [TICKER]" | `/evaluate-stock [TICKER]` |
| "Set entry price for [TICKER]" | `update_targets.py --set-entry TICKER=PRICE --write` |

---

## Continuous Improvement Loop

The brief saves a daily snapshot to:
```
investment_screener/backend/data/daily-briefs/YYYY-MM-DD.json
```

**What compounds over time:**
- **Score deltas**: Each brief shows conviction changes vs. yesterday — catches deteriorating
  theses before they become crisis exits
- **Pillar trends**: Sub-strategy aggregation catches sector-level conviction drift
- **7-day pattern rule**: After 7+ daily-brief runs, if a holding shows negative deltas for
  4+ consecutive days → escalate to `/strategic-review` for that position
- **Macro regime history**: Reviewing regime classifications over weeks reveals whether you are
  operating in a persistent risk-off environment that should gate all accumulation

**Trigger a strategic review when:**
- Any pillar's avg_score drops below −1.0
- 3+ holdings in the same pillar both score EXIT
- Macro has been RISK-OFF for 3+ consecutive sessions

---

## TA Sweep Auto-Refresh Logic

The brief auto-runs `ta_sweep_batch.py` when:
- TA sweep results are older than 4 hours
- TradingView Desktop is accessible on port 9222

If TradingView is not running, the brief uses the most recent saved sweep and notes the
staleness age in the output. Run `python3 launch_tradingview_with_debugport.py` to start TV.

---

## Execution Rules

1. **Always present the brief before recommending any specific trade.** Never skip to trade
   recommendations without running the full pipeline.
2. **Macro gate is absolute.** If RISK-OFF, do not present ACCUMULATE candidates as actionable
   — show them as "queued for when macro improves."
3. **Binary event protocol first.** If a holding within 14 days of earnings appears in either
   REDUCE or ACCUMULATE, address the binary event sizing before the drift/valuation logic.
4. **Score staleness warning.** If TA sweep is > 24 hours old and TV is running, warn the user
   that conviction scores are partially stale and offer to re-run the sweep.
