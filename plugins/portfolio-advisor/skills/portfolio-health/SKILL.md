---
name: portfolio-health
plugin: portfolio-advisor
description: Quick portfolio health check monitoring drift, pillar conviction, and thesis formula score. Surfaces allocation imbalances and valuation conflicts.
---

# Portfolio Health

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints
- Provide rapid diagnostic overview without unilaterally modifying target weights.
- If backend API is unreachable, invoke fallback procedure FB-01 from fallback tree.
- Validate portfolio total cash invariant: Total = Equities Value + Cash USD.
- Cross-reference DCF valuations before flagging underweight positions.

## Quick start
```bash
python3 investment_screener/backend/py_services/verify_thesis_sync.py
```

## Workflow
1. **Load Thesis**: Ingest active target weights and pillar structures from `target-portfolio.json`.
2. **Fetch Positions**: Pull live holding values and cash splits from `domain_model.sqlite`.
3. **Calculate Drift**: Compute drift percentages per holding and aggregate conviction scores per pillar.
4. **Assess Health**: Evaluate formula health score (0-100) and identify thesis breaker breaches.
5. **Present Report**: Display health scorecard, significant drift items, and recommended review actions.

## Verification
```bash
python3 investment_screener/backend/py_services/verify_portfolio_invariants.py
```

## References
- [Investment Thesis](references/investment_thesis.md) - Canonical portfolio thesis and sub-strategy targets.
- [Fallback Tree](references/fallback-tree.md) - Fallback operational sequences for backend or data outages.
- [Rebalance Prompt](references/rebalance_prompt.md) - Optimization prompt guidelines for drift correction.
- [Strategic Review Prompt](references/strategic_review_prompt.md) - Deep-dive thesis evaluation prompt reference.
