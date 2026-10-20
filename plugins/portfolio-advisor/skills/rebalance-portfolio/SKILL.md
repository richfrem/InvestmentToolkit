---
name: rebalance-portfolio
plugin: portfolio-advisor
description: Generates valuation-adjusted trade recommendations to rebalance the portfolio toward thesis target weights, prioritizing BUY-rated underweights and trimming SELL-rated positions.
---

# Rebalance Portfolio

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints
- **Review gate first**: `python3 plugins/portfolio-advisor/scripts/review_gate.py verify` must exit 0 before computing a plan, so every order rests on analysis saved this cycle and on the canonical actions from `recommendation.py --all` ([procedure](references/recommendation-coherence.md) section 0). If it fails, work the queue first.
- Never propose BUY orders on SELL-rated holdings to correct drift without explicit human override.
- Apply position sizing limits: max 15% holding post-trade, max 40% pillar post-trade, min trade $200.
- Maintain a minimum 2% uninvested cash buffer; cap single-session buys at $15,000.
- All capital sourcing must identify PSU-U.TO shares to sell in the same account.

## Quick start
```bash
python3 investment_screener/backend/py_services/rebalancer.py --pretty
```

## Workflow
1. **Review Gate**: `python3 plugins/portfolio-advisor/scripts/review_gate.py verify`; stop and work the queue if it exits 1.
2. **Audit Check**: Query active orders submitted today to suppress duplicate trade suggestions.
3. **Compute Plan**: Execute `rebalancer.py` to evaluate drift against AI valuation ratings and generate the rebalance plan (stored in `domain_model.sqlite` and printed as JSON).
4. **Risk Officer Gate**: Route proposed orders through `risk_officer.py` to evaluate concentration and cluster variance.
5. **Present Trades**: Display approved orders with tranche pricing, account allocation, and PSU-U.TO funding.
6. **HITL Review**: Await human confirmation before providing order drafting commands.

## Verification
```bash
python3 investment_screener/backend/py_services/verify_portfolio_invariants.py
```

## References
- [Keeping Recommendations Coherent](references/recommendation-coherence.md) - Review gate, canonical record and daily priority order.
