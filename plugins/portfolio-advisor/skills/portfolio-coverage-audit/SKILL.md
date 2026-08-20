---
name: portfolio_coverage_audit
plugin: portfolio-advisor
description: >
  Audits analysis coverage across all portfolio holdings and watchlist tickers.
  Identifies unanalyzed tickers ($0.00 price, missing DCF projections, missing TA levels),
  ranks them by priority, and queues them for automated intake via /stock-intake.
  Trigger with /portfolio-coverage-audit or "audit screener coverage".
allowed-tools: Bash, Read, Write
---

# Portfolio Coverage Audit Skill

**Trigger:** `/portfolio-coverage-audit` or `audit screener coverage`

---

## Purpose
Scans `domain_model.sqlite` to identify:
1. **Fully Analyzed**: Live price + DCF Scenario Model + Technical levels.
2. **Partial**: Price available but lacking AI scenario projections.
3. **Gaps / Needs Analysis**: Zero/stale price, no DCF projections, unanalyzed watchlist tickers.

---

## Execution Instructions

Run the coverage auditor script:
```bash
python3 scripts/audit_coverage.py
```

To list only the gap tickers for batch intake:
```bash
python3 scripts/audit_coverage.py --gaps-only
```
