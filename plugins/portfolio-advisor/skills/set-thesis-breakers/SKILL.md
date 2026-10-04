---
name: set-thesis-breakers
plugin: portfolio-advisor
description: Interactive session to define a holding's thesis breakers, proposing 2-3 candidate conditions classified as auto-evaluated or manual for user confirmation.
---

# Set Thesis Breakers

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints
- Every breaker must be explicitly reviewed and confirmed in plain language by the user before writing.
- Never save inferred default breakers without human approval.
- Classify each breaker clearly as auto-evaluated (daily programmatic check) or manual (qualitative review).
- Breakers must define objective, measurable invalidation thresholds.

## Quick start
```bash
python3 -c "import sqlite3; conn = sqlite3.connect('investment_screener/backend/data/domain_model.sqlite'); print(conn.execute('SELECT symbol, thesis_breaker_summary FROM investment WHERE symbol="NVDA"').fetchall())"
```

## Workflow
1. **Pre-Read**: Ingest ticker rationale, DCF parameters, and framework score from `target-portfolio.json` and projections.
2. **Draft Candidates**: Formulate 2-3 specific, measurable breaker proposals (e.g. margin floor, revenue growth hurdle).
3. **Interview User**: Present proposals in plain English, explaining trade-offs and monitoring frequency.
4. **Refine**: Incorporate user feedback or adjustments to thresholds and evaluation types.
5. **Persist**: Update breaker definitions via `update_thesis.py` or domain model repositories.
6. **Closing Refresh**: Run `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Verification
```bash
python3 plugins/portfolio-advisor/scripts/verify_refresh.py
```
