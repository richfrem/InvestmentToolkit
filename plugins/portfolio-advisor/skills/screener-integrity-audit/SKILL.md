---
name: screener-integrity-audit
plugin: portfolio-advisor
description: Pre-flight audit verifying all 6 core portfolio and table invariants across Investment Screener, Portfolio Table, and Intelligence Feed dashboards.
---

# Screener Integrity Audit

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints
- Enforce all 6 non-negotiable screener invariants across database and table components.
- Invariant 1: Total target portfolio weights must sum to exactly 100.00%.
- Invariant 2: Unheld tickers cannot carry TRIM/ACCUMULATE/EXIT; 0% held tickers must be EXIT.
- Invariant 3: Portfolio total USD strictly equals sum of equity values plus account cash.
- Invariant 4: Every ticker must belong to a registered pillar and sub-strategy.
- Invariant 5: 100% of target holdings must have active valuation models.

## Quick start
```bash
python3 investment_screener/backend/py_services/verify_screener_integrity.py
```

## Workflow
1. **Target Sum**: Verify target weights sum to 100.00% using `verify_screener_integrity.py`.
2. **Action Logic**: Validate holding state consistency between share count and action labels.
3. **Cash Totals**: Validate portfolio cash invariant and cash pillar categorization.
4. **Taxonomy**: Confirm ticker-to-strategy alignments via `align_all_strategies.py`.
5. **Valuation Freshness**: Check that active target holdings have valid DCF or ETF projections.

## Verification
```bash
python3 investment_screener/backend/py_services/verify_screener_integrity.py
```
