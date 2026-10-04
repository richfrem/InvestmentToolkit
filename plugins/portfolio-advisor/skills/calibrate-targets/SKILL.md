---
name: calibrate-targets
plugin: portfolio-advisor
description: Interactive target-weight calibration session. Evaluates each holding sequentially, presenting current, target, and recommended weights with rigorous DCF reasoning.
---

# Calibrate Targets

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints
- Act as an opinionated calibrator; challenge contradictions against DCF signals or concentration limits.
- The human investor retains final authority; record explicit overrides and proceed.
- Total portfolio target weights must sum to exactly 100.00% (+-0.05% tolerance).
- Present holdings sequentially; never batch-skip without user authorization.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/update_targets.py --show
```

## Workflow
1. **Load Ledger**: Ingest current positions, target weights, and DCF fair-value projections into an in-memory ledger.
2. **Open Session**: Present session scope, total target sum, and current pillar allocations.
3. **Sequential Review**: For each holding, present current %, target %, DCF upside, and rationale. Solicit user agreement or adjusted target.
4. **Rebalance Sum**: If calibrated weights do not sum to 100.00%, offer proportional normalization or specific adjustments.
5. **Persist**: Write finalized targets via `update_targets.py --write --blueprint` to update JSON and thesis documentation.
6. **Closing Refresh**: Run `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Verification
```bash
python3 plugins/portfolio-advisor/scripts/validate_weights.py --target investment_screener/backend/data/theses/target-portfolio.json
python3 plugins/portfolio-advisor/scripts/verify_refresh.py
```
