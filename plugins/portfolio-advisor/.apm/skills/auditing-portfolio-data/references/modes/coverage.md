# Mode: coverage

Audits analysis coverage across all portfolio holdings and watchlist tickers, identifying unanalyzed tickers and missing DCF or technical models.

## Constraints
- Query coverage exclusively from `domain_model.sqlite` and local projection JSON files.
- Categorize holdings into Fully Analyzed, Partial, and Needs Analysis.
- Exclude cash-equivalent positions (`PSU-U.TO`, `CASH_USD`) from missing valuation alerts.

## Quick start
```bash
python3 scripts/audit_coverage.py
```

## Workflow
1. **Scan Holdings**: Retrieve all active portfolio holdings and watchlist tickers from SQLite.
2. **Evaluate Valuations**: Verify existence of valid 5-year DCF scenario projections in `data/projections/`.
3. **Evaluate Technicals**: Check availability of current support/resistance levels and EMA regimes.
4. **Generate Queue**: Output prioritized gap list ready for batch onboarding via `/stock-intake`.

## Verification
```bash
python3 scripts/audit_coverage.py --gaps-only
```
