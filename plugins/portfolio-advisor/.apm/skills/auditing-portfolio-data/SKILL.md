---
name: auditing-portfolio-data
plugin: portfolio-advisor
description: Audits the integrity and coverage of the portfolio data. Covers database and freshness checks across domain_model.sqlite and intelligence.sqlite, analysis coverage of every holding and watchlist name (missing DCF or technical models), and the pre-flight screener invariants (target sum, action logic, cash totals, taxonomy, valuation freshness). Trigger on "run a data quality audit", "check data integrity", "which tickers are unanalyzed", "coverage audit", "screener integrity", "verify the screener invariants" or before a major review.
allowed-tools: Bash, Read
---

# Auditing Portfolio Data

Read-only audits. They report; they do not repair, and nothing here changes a database record unless the owner explicitly asks.

## Contents

- [Quick start](#quick-start) · [Workflow](#workflow) · [Constraints](#constraints) · [Modes](#modes) · [Scripts](#scripts) · [Verification](#verification) · [References](#references)

## Quick start

From the repository root (paths starting with `scripts/` are relative to this skill's folder):

```bash
python3 scripts/audit_coverage.py
python3 investment_screener/backend/py_services/verify_screener_integrity.py
```

## Workflow

1. Match the request to a mode and read its mode file.
2. Run the audit and read the categorized result.
3. Report findings with the exact ticker or table; route fixes to the right skill (`stock-intake` or `update-analysis` for missing analysis, the sync modes for stale prices).

## Constraints

- **Read-only by default**: no database record is modified unless explicitly instructed.
- **SQLite only**: query `domain_model.sqlite` (and `intelligence.sqlite`); cash-equivalent positions (`PSU-U.TO`, `CASH_USD`) are excluded from missing-valuation alerts.
- **Staleness** means a price older than 24 hours on a trading day, judged from stored timestamps, never a file modification time.

## Modes

| Mode | Trigger | What it does |
|---|---|---|
| [data-quality](references/modes/data-quality.md) | "data quality audit" | Schema, foreign keys, orphan positions, broken account links, stale prices |
| [coverage](references/modes/coverage.md) | "coverage audit" | Fully analyzed / partial / needs analysis for holdings and watchlist; queue for batch intake |
| [screener-integrity](references/modes/screener-integrity.md) | "screener integrity" | The six non-negotiable invariants across the database and screener tables |

## Scripts

- `scripts/audit_coverage.py` (also `--gaps-only`); tests in `tests/`.
- Shared engine (`py_services/`): `verify_screener_integrity.py`, `verify_portfolio_invariants.py`, `align_all_strategies.py`.

## Verification

- `audit_coverage.py --gaps-only` lists only the gaps; `verify_screener_integrity.py` exits 0 when every invariant holds.
- Routing cases for every mode are in `evals/evals.json`.

## References

- The `valuing-investments` skill (fix missing analyses) and `setting-portfolio-targets` (fix target and action inconsistencies).
