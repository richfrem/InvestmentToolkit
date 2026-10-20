---
trigger: always_on
description: Every recommendation shown to the owner reflects this cycle's analysis and matches the app; nothing followed is left unanalysed.
---

# Recommendation coherence

A call the owner sees (in chat, the brief or the app) must come from analysis done this cycle, saved
to the record, and be the same everywhere.

## Invariants

1. **One source of calls.** Present only stances from `python3 plugins/portfolio-advisor/scripts/recommendation.py --all`
   (`decision_check.effective`). NEVER present a ranking or BUY/TRIM list derived outside it.
2. **Analysis reaches the record in the same session.** A valuation is saved with `persist_valuation.py`
   (plus `persist_research.py`); a change of stance goes through `set_standing_decision.py` or
   `update_targets.py`. Analysis not yet saved is labelled "draft, not in the record" and is never
   presented as a call.
3. **Every cycle starts with `review_gate.py begin` and ends with `review_gate.py verify` exiting 0.**
   `begin` resets every holding and watchlist name to `NEEDS_ANALYSIS` (also the default for a new ticker)
   and clears, deterministically, only names with nothing new. Work the queue holdings first:
   - HARD triggers (no valuation, earnings since the valuation, price moved >20% since the last review,
     a TRIGGERED thesis breaker) need a valuation saved today, then `review_gate.py mark`.
   - An age-only trigger (valuation older than 30 days) may be marked with a written reason; the name
     still gets no buy/trim call until it is re-valued.
   NEVER end a daily loop, weekly review or analysis session while `verify` exits 1.
4. **No call from stale or unreviewed analysis.** `recommendation.py` withholds INITIATE, ACCUMULATE, TRIM
   and EXIT (except a breaker EXIT) for a name that is `NEEDS_ANALYSIS` or whose valuation is older than
   30 days; it shows MAINTAIN (held) or WATCHLIST with the reason.
5. **Never reverse a recent trade** without dated new facts (`recent_trades.flip_hold_note`): no TRIM/EXIT
   within 30 days of a buy, no ACCUMULATE/INITIATE within 30 days of a sale.
6. **Close by checking the app.** After `refresh_all.py --publish`, the stances you told the owner are the
   ones `recommendation.py --all` returns; if they differ, the record is wrong, so fix it before ending.

## Why

On 2026-10-20 the agent recommended buys from ad-hoc calculations while the app showed different calls
from 47-to-76-day-old valuations, said "no more CRWV adds" while CRWV's standing decision still produced
ACCUMULATE, and presented re-valuations it had not saved. Each invariant above closes one of those gaps.
