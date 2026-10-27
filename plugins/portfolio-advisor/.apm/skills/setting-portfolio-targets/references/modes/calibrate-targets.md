# Mode: calibrate-targets

Interactive target-weight calibration session. Evaluates each holding sequentially, presenting current, target, and recommended weights with rigorous DCF reasoning.

## Constraints
- **Targets follow saved analysis**: calibrate only from valuations and decisions saved this cycle; `python3 investment_screener/backend/py_services/review_gate.py verify` must exit 0 before persisting (procedure: `references/recommendation-coherence.md` section 0).
- Act as an opinionated calibrator; challenge contradictions against DCF signals or concentration limits.
- The human investor retains final authority; record explicit overrides and proceed.
- Total portfolio target weights must sum to exactly 100.00% (+-0.05% tolerance).
- Present holdings sequentially; never batch-skip without user authorization.

## Quick start
```bash
python3 investment_screener/backend/py_services/update_targets.py --show
```

## Workflow
1. **Load Ledger**: Ingest current positions, target weights, and DCF fair-value projections into an in-memory ledger.
2. **Open Session**: Present session scope, total target sum, and current pillar allocations.
3. **Sequential Review**: For each holding, present current %, target %, DCF upside, and rationale. Solicit user agreement or adjusted target.
4. **Rebalance Sum**: If calibrated weights do not sum to 100.00%, offer proportional normalization or specific adjustments.
5. **Persist**: Write finalized targets via `update_targets.py --write` (the thesis pages are live from the database).
6. **Review Gate**: `python3 investment_screener/backend/py_services/review_gate.py verify` must exit 0.
7. **Closing Refresh**: Run `python3 investment_screener/backend/py_services/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Verification
```bash
python3 investment_screener/backend/py_services/validate_weights.py --mode target
python3 investment_screener/backend/py_services/verify_refresh.py
```
