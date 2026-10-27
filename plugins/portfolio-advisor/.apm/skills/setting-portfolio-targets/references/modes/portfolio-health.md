# Mode: portfolio-health

Quick portfolio health check monitoring drift, pillar conviction, and thesis formula score. Surfaces allocation imbalances and valuation conflicts.

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
1. **Load Thesis**: Ingest active target weights and pillar structures from `domain_model.sqlite` (`portfolio_io.load_thesis_holdings()`).
2. **Fetch Positions**: Pull live holding values and cash splits from `domain_model.sqlite`.
3. **Calculate Drift**: Compute drift percentages per holding and aggregate conviction scores per pillar.
4. **Assess Health**: Evaluate formula health score (0-100) and identify thesis breaker breaches.
5. **Present Report**: Display health scorecard, significant drift items, and recommended review actions.

## Verification
```bash
python3 investment_screener/backend/py_services/verify_portfolio_invariants.py
```

## References
- Investment Thesis (`investment_screener/backend/data/theses/investment_thesis.md`) - Canonical portfolio thesis and sub-strategy targets.
- [Fallback Tree](../fallback-tree.md) - Fallback operational sequences for backend or data outages.
- [Rebalance Prompt](../rebalance_prompt.md) - Optimization prompt guidelines for drift correction.
- [Strategic Review Prompt](../strategic_review_prompt.md) - Deep-dive thesis evaluation prompt reference.
