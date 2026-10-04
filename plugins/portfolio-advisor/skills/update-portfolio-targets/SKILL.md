---
name: update-portfolio-targets
plugin: portfolio-advisor
description: Updates target portfolio weights by pillar and holding in the canonical thesis JSON file, validating 100% sum and running the refresh chain.
---

# Update Portfolio Targets

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints
- Target weights across all positions and cash must sum to exactly 100.00%.
- Single holding cap is 15%; pillar concentration cap is 40%.
- Always execute `update_targets.py` with `--write --blueprint` to synchronize `investment_thesis.md`.
- Complete the full post-update refresh chain after every target modification.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/update_targets.py --set NVDA=6.5 META=4.5 --write --blueprint
```

## Workflow
1. **Inspect Targets**: Load existing target allocations using `update_targets.py --show`.
2. **Apply Changes**: Execute `update_targets.py --set TICKER=WEIGHT --write --blueprint` (or `--add` for new tickers).
3. **Re-Lock Holdings**: Re-apply fixed allocations for unchanged positions if proportional scaling caused drift.
4. **Closing Refresh**: Run `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session (regenerates the review JSON and runs `verify_refresh.py`).

## Verification
```bash
python3 plugins/portfolio-advisor/scripts/verify_refresh.py
python3 investment_screener/backend/py_services/verify_screener_integrity.py
```

## References
- [Investment Thesis](references/investment_thesis.md) - Target portfolio document and strategy definitions.
