---
trigger: always_on
description: Every recommendation shown to the owner reflects this cycle's analysis, is saved to the record and matches the app; nothing followed is left unanalysed.
---

# Recommendation coherence

## The Iron Law

A call the owner sees, in chat, the brief or the app, comes from analysis done this cycle, is saved to
the record before it is said, and is the same everywhere.

## Invariants

1. **One source of calls.** Present only stances from `python3 investment_screener/backend/py_services/recommendation.py --all`
   (`decision_check.effective`). NEVER present a ranking or BUY/TRIM list derived outside it.
2. **Analysis reaches the record in the same session.** A valuation is saved with `persist_valuation.py`
   (plus `persist_research.py`); a change of stance goes through `set_standing_decision.py` or
   `update_targets.py`. Unsaved analysis is labelled "draft, not in the record" and is never a call.
3. **Every cycle starts with `review_gate.py begin` and ends with `review_gate.py verify` exiting 0.**
   HARD triggers (no valuation, earnings since the valuation, price moved >20% since the last review or the
   saved valuation, a TRIGGERED thesis breaker) need a valuation saved today, then `review_gate.py mark`.
   An age-only trigger may be marked with a written reason; the name still gets no buy/trim call.
4. **No call from stale or unreviewed analysis.** `recommendation.py` withholds INITIATE, ACCUMULATE, TRIM
   and EXIT (except a breaker EXIT) for a `NEEDS_ANALYSIS` name or a valuation older than 30 days.
5. **Never reverse a recent trade** without dated new facts: no TRIM/EXIT within 30 days of a buy, no
   ACCUMULATE/INITIATE within 30 days of a sale (`recent_trades.flip_hold_note`).
6. **Daily order before advice.** On a new trading day, run the daily loop's readiness (sync, prices,
   `review_gate.py begin`), brief (macro gate, binary events) and news sweep before answering any buy, sell,
   entry-price or chart question. A chart read never replaces them.
7. **Record what you say.** A buy price, size, skip list or wait condition is saved before it is presented:
   a standing decision with the price in its type and, when the trade would exceed its target, a new target
   set with the owner's agreement.
8. **Close by checking the app.** After `refresh_all.py --publish`, the stances you told the owner are the
   ones `recommendation.py --all` returns and the app shows; if they differ, fix the record before ending.

## Forbidden Actions

- Giving an entry price, size or skip list that exists only in chat.
- Presenting a model's or a prompt's label (ACCUMULATE, EXIT) instead of the canonical stance.
- Ending a cycle while `review_gate.py verify` exits 1.

## Why

Calls drift when analysis stays in chat, when old valuations keep producing actions, and when several
surfaces derive their own labels. Each invariant closes one of those paths: one source, saved analysis,
a review of every name each cycle, and a final check that chat and app agree.

## Evaluation Checklist

- [ ] Every stance presented matches `recommendation.py --all` for that ticker.
- [ ] Every price or plan given appears as a standing decision or target in `domain_model.sqlite`.
- [ ] `review_gate.py verify` exits 0 and the app shows the same stances.
