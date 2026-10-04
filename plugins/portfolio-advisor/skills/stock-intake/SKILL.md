---
name: stock-intake
plugin: portfolio-advisor
description: Autonomous end-to-end stock intake wizard pulling live financials, technical levels, running scenario DCF models, and registering tickers into strategy pillars.
---

# Stock Intake

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints
- Guide one conversational decision at a time using plain-English analogies for technical metrics.
- Respect existing standing decisions unless Fair Value delta exceeds 15%.
- Capital sourcing must compute advisory share counts funded by selling PSU-U.TO in the same account.
- Always require user confirmation before writing new tickers to SQLite or injecting chart overlays.

## Quick start
```bash
python3 investment_screener/backend/py_services/fetch_financials.py NVDA
```

## Workflow
1. **Intent & Checks**: Confirm ticker symbol, existing standing decisions, and target strategy pillar.
2. **News & Catalysts**: Ingest recent news and earnings context (optional Grok sweep).
3. **Technical Tiers**: Read TradingView CDP technical indicators (200 EMA, ADX, RSI) for entry and trim shelves.
4. **Valuation Modeling**: Execute 5-year scenario DCF model via `dcf_scenarios.py` to establish fair value.
5. **Capital Sourcing**: Calculate target weight, share tranche sizing, and account allocation (TFSA/RRSP).
6. **Persist & Overlay**: Present summary card, obtain approval, persist to database, and inject chart levels.
7. **Closing Refresh**: Run `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Verification
```bash
python3 investment_screener/backend/py_services/verify_screener_integrity.py
```

## References
- [Stock Analysis Surface Checklist](references/stock-analysis-surface-checklist.md) - Canonical metric mappings, sources, and persistence verification rules.
