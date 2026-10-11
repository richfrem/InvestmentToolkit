---
description: Invariant rules for standing investment decisions, valuation deltas, and thesis re-evaluation thresholds.
globs: ["investment_screener/backend/**/*", "plugins/portfolio-advisor/**/*"]
---

# Standing Decision & Valuation Invariants

## Invariants
1. **Standing Decision is Anchor**: Read `investment.standing_decision_type` and `standing_decision_reason` in `domain_model.sqlite` before generating any trade recommendation or action change.
2. **Material Delta Required**: DCF models NEVER silently override a standing decision. Only a material delta (>15% fair value change) or confirmed new catalyst justifies revisiting.
3. **No Flips on Noise**: NEVER flip BUY to SELL (or vice versa) on less than 15% valuation variance.
