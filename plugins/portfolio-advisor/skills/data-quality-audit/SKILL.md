---
name: data-quality-audit
plugin: portfolio-advisor
description: >
  Runs data integrity audits across domain_model.sqlite and intelligence.sqlite.
  Checks price staleness, missing DCF projections, unlinked accounts, and table schema health.
  Trigger on /data-quality-audit, "audit data quality", or "check db integrity".
allowed-tools: Bash, Read
---

# Data Quality Audit Skill

**Trigger:** `/data-quality-audit` or `audit data quality`

---

## Purpose
Validates database schema constraints, verifies price staleness across holdings, and detects orphan records in `domain_model.sqlite`.

---

## Execution
Run the data quality audit suite:
```bash
python3 plugins/portfolio-advisor/scripts/audit_coverage.py
```

To run full backend test suite verification:
```bash
pytest investment_screener/backend/tests/
```
