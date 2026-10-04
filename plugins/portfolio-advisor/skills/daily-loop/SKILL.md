---
name: daily-loop
plugin: portfolio-advisor
description: The single master daily command. Provides fast non-interactive morning briefs or guides the interactive daily portfolio loop through freshness, brief, triage, and action cards.
---

# Daily Investment Loop

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints
- Fast scan (`--scan`) runs non-interactively; full loop guides step-by-step triage.
- Check database freshness against `domain_model.sqlite` (never retired `portfolio.json`).
- Adhere to the single-decision pacing rule; never prompt multiple conflicting choices at once.
- Enforce the macro gate and binary-event protocol from the methodology reference.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/run_daily.py --scan
```

## Workflow
1. **Readiness (Step 0)**: Verify backend API health, `domain_model.sqlite` sync timestamps, and TradingView CDP connectivity.
2. **Morning Brief (Step 1)**: Ingest macro regime, conviction-scored REDUCE/ACCUMULATE lists, and binary event flags from `daily_brief.py`.
3. **Triage (Step 2)**: Present urgent holding alerts, thesis breaker breaches, and price catalysts one ticker at a time.
4. **Action Cards (Step 3)**: Formulate actionable trade proposals with tranche sizing and PSU-U.TO capital sourcing.
5. **Evolution & Summary (Steps 4-5)**: Log operational friction, record execution receipts, and display final session status.
6. **Closing Refresh**: Run `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Verification
```bash
python3 plugins/portfolio-advisor/scripts/verify_daily_run.py --latest
python3 investment_screener/backend/py_services/verify_portfolio_invariants.py
```

## References
- [Daily Brief Methodology](references/daily-brief-methodology.md) - Macro regime definitions, conviction scoring formulas, and triage protocol.
