---
name: data-quality-audit
plugin: portfolio-advisor
description: Runs data integrity audits across domain_model.sqlite and intelligence.sqlite, checking price staleness, missing DCF projections, unlinked accounts, and table schema health.
---

# Data Quality Audit

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints
- Validate schema constraints against `domain_model.sqlite` and `intelligence.sqlite`.
- Detect orphan positions, broken account linkages, and stale market prices (>24h during trading days).
- Audit without modifying database records unless explicitly instructed.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/audit_coverage.py
```

## Workflow
1. **Schema Check**: Inspect database tables, foreign keys, and column constraints for structural integrity.
2. **Freshness Audit**: Scan `account_investment.last_synced_at` and quote timestamps to flag outdated valuations.
3. **Coverage Check**: Cross-reference active holdings against available DCF projections in `investment_screener/backend/data/projections/`.
4. **Report Findings**: Output a categorized summary of health checks, warnings, and missing data items.

## Verification
```bash
pytest investment_screener/backend/tests/
```
