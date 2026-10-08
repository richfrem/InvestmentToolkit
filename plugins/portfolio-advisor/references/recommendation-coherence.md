# Keeping recommendations coherent

Shared procedure for every skill that reads, explains or changes a recommendation:
`daily-loop`, `weekly-review`, `strategic-review`, `stock-intake`, `update-stock-analysis`
and `stock-research`. A recommendation is coherent when it reflects what was actually
traded, agrees with (or openly reconciles) the owner's standing decision, is ranked by
today's priority, and states its condition against real chart levels.

## Contents

- [Refresh reality first](#1-refresh-reality-first)
- [Read the canonical record](#2-read-the-canonical-record)
- [Reconcile standing decisions](#3-reconcile-standing-decisions)
- [Rank by today's priority](#4-rank-by-todays-priority)
- [State conditions against the chart](#5-state-conditions-against-the-chart)
- [After the owner acts](#6-after-the-owner-acts)
- [Refresh stale analysis before acting](#7-refresh-stale-analysis-before-acting)

## 1. Refresh reality first

Before presenting any action, make positions and executed trades current with
`/tv-portfolio-sync`: TradingView is the default source for every user. Check
`python3 investment_screener/backend/py_services/broker_sources.py --json`; only when it
lists `questrade` (the owner set `QUESTRADE_ENABLED=true`) ask which source to use for
this refresh. Never present a TRIM or ACCUMULATE while the latest executed trade in the
Trade Log is older than the owner's last known trade.

## 2. Read the canonical record

`python3 plugins/portfolio-advisor/scripts/recommendation.py --all` is the only source
for a recommendation. Use its fields; never re-derive them:

| Field | Meaning |
|---|---|
| `action`, `reason` | Valuation action from price against fair value |
| `recent_trades` | Shares sold and bought in the last 14 days, and whether that already follows the action (`ACTED`, `OPPOSED`, `RECENT`) |
| `decision_check` | Whether the standing decision agrees; `effective` is the stance to present |
| `risk_reward`, `support` | Reward against risk, and how well the fair value is evidenced |

Present `decision_check.effective` as the one stance. When `action` differs from it, never
show it as a second label ("MAINTAIN" beside "ACCUMULATE" reads as two recommendations);
state the valuation's view as a sentence: "for reference, the valuation model rates it a
buy, +72% to fair value".

## 3. Reconcile standing decisions

A standing decision is the owner's recorded call and the anchor: valuation never
silently overrides it. That makes a stale decision costly, so reconcile every session:

- **CONFIRMED** (the owner set a decision in the last 30 days and valuation points the
  other way): the owner has answered. Present their stance, mention the valuation view
  once, and do not ask again until the decision is older than 30 days.
- **CONFLICT** (valuation and decision point opposite ways on a held position): state
  both, propose no trade, and ask the owner which is out of date. If they traded against
  the decision recently, say so.
- **OUTDATED** (an entry or watchlist decision on a position now held): it no longer
  applies. Ask to replace it with a decision for the held position, or clear it.
- **UNCLEAR** (type cannot be read): ask for a decision whose type starts with its direction.
- **WAITS** (valuation would start a position, the decision says wait): present the
  wait, with the level that ends it (section 5).

Change a decision only with the owner's agreement, and only through:

```bash
python3 plugins/portfolio-advisor/scripts/set_standing_decision.py --ticker IREN \
  --type TRIM_ON_STRENGTH --reason "Trim above $45 into strength." --review "After Q1 results"
python3 plugins/portfolio-advisor/scripts/set_standing_decision.py --ticker GEV --clear
```

Start the type with its direction (`HOLD`, `MAINTAIN`, `NO_ADD`, `TRIM`, `EXIT`,
`ACCUMULATE`, `INITIATE`, `WATCHLIST`, `WAIT`, `AVOID`), then the condition. The reason
must name a specific level or event, not "on pullback" alone. The script stamps the date,
so every decision's age is known.

## 4. Rank by today's priority

Priorities are set fresh each session, never carried over. Present in this order:

1. **Ready to act**: a sized trade with nothing blocking it, or a card whose standing
   decision condition is met ("Your condition is met").
2. **Needs your decision**: the standing decision conflicts, is outdated or is unclear.
3. **No trade proposed**: signal stands but there is no basis to size it, or the owner
   is holding by a decision they confirmed recently.
4. **Waiting**: for the owner's condition (with the distance to it) or the macro gate.
5. **Already acted on**: the owner traded in this direction in the last 14 days.

Within a group, sells before buys, then the larger gap to fair value first. An item the
owner already acted on is never presented as a new recommendation; state what was
traded and whether anything further is sized.

## 5. State conditions against the chart

When technical data is current (`ta_staleness_days` of 0 or 1, or a chart read in this
session), turn every condition into a statement about today's price:

- "Accumulate on the 200 EMA retest" becomes "Price $212 is 19% above the 200 EMA
  ($178): condition not met" or "Price is at the 200 EMA: condition met, act now".
- "Trim on bounce" names the level (21 EMA, a trim tier, a resistance) and the distance to it.
- "Wait for pullback" names the buy tier or entry price and how far away it is.

The Daily Brief evaluates two kinds of condition in code
(`standing_decision_check.decision_condition`, shown on each card as `condition`):

- A price in the decision type: `ACCUMULATE_BELOW_9`, `TRIM_ABOVE_54_60`. Checked against
  the current price.
- A moving average in the type: `HOLD_AT_200_EMA`. The technical sweep does not store EMA
  values, so the level is the dollar figure written in the decision's reason
  ("200 EMA ($48.60)") and the card says it is the recorded level. Read the live EMA from
  the chart in this session and update the reason when it has moved.

Write new decisions so they can be checked: put the price in the type, or the EMA period
in the type and its current dollar level in the reason. For anything else (trim tiers,
resistance), read the chart or the price levels yourself. If technical data is older than
a day, refresh it with `/tv-ta-daily-sweep` or say plainly that the levels are stale;
never give a generic instruction where a level exists.

## 6. After the owner acts

Sync trades and positions again (section 1), update or clear any standing decision the
trade resolved (section 3), then run
`python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so every page
re-ranks. Confirm the acted-on item now shows as already acted on.

## 7. Refresh stale analysis before acting

The five highest-priority cards carry `refreshFirst` when the valuation behind them is
older than 30 days, has no forward-earnings review, or is flagged for revaluation. Do not
ask the owner to act on those figures. For each such card, in priority order:

1. Tell the owner the valuation is stale and why (the `reasons` list), and offer to run
   `/update-stock-analysis TICKER` now.
2. Run it, then walk the owner through the result: old and new fair value, the scenario
   range, what changed in the forward earnings, and the resulting action.
3. Ask for the decision the result supports (act, hold with a level, wait) and record it
   with `set_standing_decision.py` (section 3), with a checkable level (section 5).
4. Re-read the canonical record and move to the next card; priorities are re-ranked.

A card outside the top five is refreshed when it rises into it, not in bulk.
