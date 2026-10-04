# Daily Brief Methodology (`/daily`, `/daily --scan`)

Canonical reference for how to read and act on the morning brief. Restored 2026-09-29
from the former `daily-brief` skill, which was merged into `daily-loop` in commit
`2319c261` without carrying this guidance over (map-debt DEBT-20260929-01).

Code is the authority for numbers; this document is the authority for **policy**:

| Concern | Source of truth |
|---|---|
| Conviction score formula, bands | `investment_screener/backend/py_services/compute_conviction_scores.py` (header + `_band()`) |
| Brief assembly, macro gate wording | `plugins/portfolio-advisor/scripts/daily_brief.py` |
| Gate / protocol / routing policy | this document |

---

## Contents
- [Where the brief lives](#where-the-brief-lives)
- [What the brief contains](#what-the-brief-contains)
- [Macro gate protocol](#macro-gate--hard-rules)
- [Binary-event protocol](#binary-event-protocol)

---

## Where the brief lives

A run writes the brief to the Intelligence Ledger (`intelligence_event`,
`event_type='REVIEW_DAILY'`) and to
`investment_screener/backend/data/daily-briefs/YYYY-MM-DD.json`. `run_daily.py --scan`
records only a summary receipt, so **present a scan from that JSON file**, not from the
runner's terminal output.

`daily_brief.py` flags: `--json` (raw JSON) and `--skip-ta` (use the last saved TA sweep).

## What the brief contains

| Section | Source | Action |
|---|---|---|
| Macro regime | VIX + SPY vs 200D + credit | Hard gate on ACCUMULATE (below) |
| Binary events | earnings calendar | Sizing protocol for holdings within 14 days |
| REDUCE / EXIT | conviction ≤ −1 | Ranked by urgency; address first |
| ACCUMULATE | conviction ≥ +3, gated by macro | Underweight + cheap + momentum |
| Score deltas | vs yesterday's brief | Catches deteriorating positions early |
| Pillar health | sub-strategy aggregation | Pillar-level thesis drift |

## Conviction score (read-only summary)

`total = dcf_pts + ta_pts + weight_gap_pts + momentum_pts` → bands
**≥ +3 ACCUMULATE · +1..+2 HOLD · 0 WATCH · −1..−2 REDUCE · ≤ −3 EXIT**.
See `compute_conviction_scores.py` for each component. Two invariants worth stating to
the user when explaining a score:

- **Momentum is direction-gated.** ADX measures trend *strength* only; a strong
  downtrend never earns the +1 momentum bonus (falling-knife amplifier).
- **% to fair value is price-denominated:** `(FV − price) / price`, recomputed from the
  live close at score time.

## Macro gate — hard rules

The gate is driven by **`macro_regime`**. The brief also carries **`market_regime`**
(breadth, term slope, `degraded` flag), which is **informational only** today — when
the two disagree, state both and apply the gate from `macro_regime`
(two-model divergence tracked as DEBT-20260929-02).

| Regime | Rule |
|---|---|
| RISK-ON | All signals valid. ACCUMULATE candidates are actionable. |
| NEUTRAL | Only ACCUMULATE candidates scoring **≥ +4** are actionable. Hold cash otherwise. |
| RISK-OFF | No new buys. Execute REDUCE/EXIT only. Cash is the position. |
| Degraded data (2+ macro inputs unavailable) | Treat as RISK-OFF: a data blackout is ignorance, not neutrality. Tell the user the gate is failing safe. |

**Never accumulate into a RISK-OFF environment**, regardless of DCF upside or the
user's conviction. Undervalued growth stays cheap for 12–18 months in risk-off regimes.

## Binary event protocol

For any holding flagged **IMMINENT (< 7 days)** or **APPROACHING (< 14 days)** to
earnings, state this before any other action on that holding:

1. **Before the event:** reduce to 50–75% of target if at or above target weight.
2. **After the event, thesis intact:** reload to full target at the best post-reaction price.
3. **After the event, thesis broken:** exit. Do not average down into a broken thesis.

If such a holding appears in REDUCE or ACCUMULATE, address event sizing **before**
drift or valuation logic.

## Routing from the brief to action

| User intent | Route |
|---|---|
| Trim / exit a ticker | `/rebalance` or `/place-order sell` |
| Accumulate a ticker | Check its `TARGET_ENTRY` price level (domain_model `price_level_tier`) first, then `/place-order buy` |
| News context | `/news-sweep` (model roles, fact-check gate and ETF handling: news-sweep-model-assessment) |
| Re-evaluate the thesis | `/strategic-review` |
| Update DCF | `/update-stock-analysis TICKER` |

All orders remain human-executed (AGENTS.md rule 17).

## Continuous improvement signals

Escalate to `/strategic-review` when:

- a holding shows negative score deltas on 4+ consecutive briefs (after 7+ briefs exist);
- any pillar's average score drops below −1.0;
- 3+ holdings in one pillar score EXIT;
- macro has been RISK-OFF for 3+ consecutive sessions.

## TA sweep freshness

The brief refreshes the TA sweep (`ta_sweep_batch.py`) when results are older than
4 hours and TradingView Desktop is reachable on port 9222; otherwise it uses the last
saved sweep and reports its age. If the sweep is > 24 hours old while TradingView is
running, warn that conviction scores are partially stale and offer to re-run it.

## Execution rules

1. Present the brief before recommending any specific trade.
2. The macro gate is absolute; show gated ACCUMULATE candidates as "queued for when
   macro improves", never as actionable.
3. Binary event protocol first for holdings within 14 days of earnings.
4. Warn about stale TA as above.

## ETFs in the brief

Thematic ETFs (e.g. FOTO, HUMN, KOID; detect via an `etf_analysis/{TICKER}.json` file or `industry LIKE 'ETF%'`) are not
stocks: a company DCF, fair value, earnings date, Rule of 40 or Piotroski does not apply. As of 2026-10-01 the brief still
scores them with DCF-style points and `pct_to_fv` whose source is not established, so do not present those as a valuation.
Judge them on NAV premium/discount, AUM/liquidity, expense ratio, top-holdings composition, overlap with directly held
stocks and INITIATE targets, and the theme's news (see the ETF card in the daily-loop skill).

