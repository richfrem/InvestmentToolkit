---
name: ytd-return
plugin: portfolio-advisor
description: Calculates Simple and Time-Weighted YTD returns, adjusting for cash flows (deposits/withdrawals) to measure true investment performance.
---

# YTD Return Tracker

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints
- Performance calculations must adjust for deposits and withdrawals using Time-Weighted Return (TWR) linking.
- Historical cash flow records are sourced strictly from `investment_screener/backend/data/cash_flows.json`.
- Invariant: Simple return and TWR must be computed from inception date (Jan 1 of active year).

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/ytd_return.py
```

## Workflow
1. **Ingest Cash Flows**: Load cash transactions (deposits/withdrawals) from the `cash_flow` and `cash_flow_baseline` tables in `domain_model.sqlite`.
2. **Fetch Valuations**: Retrieve portfolio starting valuation and current total portfolio equity plus cash.
3. **Compute Returns**: Calculate simple return and time-weighted return linking all cash flow periods.
4. **Display Report**: Present YTD performance summary table including net deposits and period gains.

## Verification
```bash
python3 plugins/portfolio-advisor/scripts/ytd_return.py --json
```
