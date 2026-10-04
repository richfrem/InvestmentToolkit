---
name: pre-trade-analysis
plugin: portfolio-advisor
description: Conducts comprehensive pre-trade analysis synthesizing earnings transcripts, guidance direction, contracted backlogs, chart structure, and tranche sizing before execution.
---

# Pre-Trade Analysis

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints
- Output the mandatory 5-Point Pre-Trade Checklist briefing before any trade recommendation.
- Respect standing decisions unless Fair Value delta exceeds 15% or material catalysts occur.
- Capital sourcing must strictly sell PSU-U.TO in the same account (never cross-account).
- Position sizing must comply with 15% holding and 40% pillar maximum limits.

## Quick start
```bash
python3 plugins/tradingview/scripts/ta_sweep_single.py --symbol AAPL --timeframe 1D
```

## Workflow
1. **Transcript Audit**: Review recent earnings call transcripts, 10-Q filings, guidance trends, and backlog/RPO.
2. **Chart Structure**: Evaluate technical regime relative to 200 EMA, 50 EMA, 21 EMA, RSI, and ADX momentum.
3. **Level Identification**: Establish tactical alert, entry tranches, trim resistance shelves, and invalidation stops.
4. **Tranche Sizing**: Compute concrete share counts and USD capital sourcing from PSU-U.TO.
5. **Output Checklist**: Deliver the complete 5-point pre-trade briefing to the user.

## Verification
```bash
python3 investment_screener/backend/py_services/verify_portfolio_invariants.py
```
