# ADR-034: Reward-versus-risk and valuation-support view on canonical recommendations

Date: 2026-10-08
Status: Proposed

## Problem

The canonical action (ADR-032) is a ±15% band around the probability-weighted
fair value. It answers "is the price far from fair value" but not "is the
remaining upside worth the downside", and it says nothing about how well the
fair value itself is supported. Tables could not show which held positions sit
above fair value inside the band, and each table recomputed its own fair value,
upside and gain in the browser. One held position (MP) displayed a fair value
from a different saved projection than the one its action was computed from.
The Portfolio Table also read `currentPrice` from a heatmap row that returns
`price`, leaving Price, Gain and Upside blank.

## Decision

Add `plugins/portfolio-advisor/scripts/risk_reward.py` as the one
implementation of three pure functions, attached to every record returned by
`recommendation.py`:

- `assess_risk_reward(price, fair_value, scenarios)`: premium to fair value,
  probability-weighted gain ÷ probability-weighted loss across the saved bear,
  base and bull present values (`reward_risk`), the scenario probability below
  today's price (`loss_odds_pct`), downside to bear and a verdict. Bands: below
  1 UNFAVOURABLE, 1 to under 2 THIN, 2 or more FAVOURABLE; a price above fair
  value is always UNFAVOURABLE. Incomplete scenarios are UNRATED, never estimated.
- `valuation_support(saved_at, analytics_log, scenarios, today)`: four
  independent checks (saved within `STALE_DAYS`, complete ordered scenarios
  within the 50× review spread, audited discount rate, recorded forward-earnings
  review that is not flagged NEEDS_REVALUATION).
- `reduce_view(held, action, assessment, current, target)`: a reduce-candidate
  flag for held UNFAVOURABLE positions and an alignment status (ALIGNED, REVIEW,
  CONFLICT, UNKNOWN) comparing the canonical action with reward versus risk.

These fields explain and cross-check the action. They do not change it, and
target weight only adds context to the reasons (ADR-032's "targets play no
part" policy is unchanged).

The probability-weighted ratio was chosen over "upside to fair value ÷ downside
to bear" because the latter ignores scenario probabilities and marks nearly
every position with a deep bear case as poor.

Frontend: `utils/riskReward.ts`, `RiskRewardCell.tsx` and
`ValuationRangeBar.tsx` render the same columns on the Portfolio Table and the
Portfolio Advisor table from the shared recommendation snapshot. Both tables
now take fair value from the recommendation record and use one `fairValueGap`
helper for the Gain and Upside columns. `scan_opportunities.py` imports
`STALE_DAYS` from `risk_reward.py` so there is one staleness threshold.

## Consequences

- Reduce candidates are wider than TRIM: they include held positions above
  fair value that are still inside the ±15% band.
- Support is honest about legacy valuations: most holdings pass two of four
  checks until they are refreshed through `update-stock-analysis`.
- Gain and Upside use the live heatmap price, while the action, premium and
  reward:risk use the recommendation's stored price. Unifying the price source
  is separate work.
- Promoting reward:risk into the action rule itself is a policy change and is
  deliberately not part of this decision.
