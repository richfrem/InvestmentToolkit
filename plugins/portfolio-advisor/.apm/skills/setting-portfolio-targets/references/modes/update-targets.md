# Mode: update-targets

Updates target portfolio weights by pillar and holding in the canonical thesis JSON file, validating 100% sum and running the refresh chain.

## Constraints
- **A target change is a stance change**: make it only from analysis saved this cycle (a valuation saved with `persist_valuation.py`, or the owner's decision), never from chat analysis that isn't in the record ([procedure](../recommendation-coherence.md) section 0).
- Target weights across all positions and cash must sum to exactly 100.00%.
- Single holding cap is 15%; pillar concentration cap is 40%.
- Always execute `update_targets.py` with `--write`. The thesis pages are live from the database, so there is nothing to regenerate.
- Complete the full post-update refresh chain after every target modification.

## Quick start
```bash
python3 investment_screener/backend/py_services/update_targets.py --set NVDA=6.5 META=4.5 --write
```

## Workflow
1. **Inspect Targets**: Load existing target allocations using `update_targets.py --show`.
2. **Apply Changes**: Execute `update_targets.py --set TICKER=WEIGHT --write` (or `--add` for new tickers).
3. **Re-Lock Holdings**: Re-apply fixed allocations for unchanged positions if proportional scaling caused drift.
4. **Review Gate**: `python3 investment_screener/backend/py_services/review_gate.py verify` must exit 0.
5. **Closing Refresh**: Run `python3 investment_screener/backend/py_services/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session (regenerates the review JSON and runs `verify_refresh.py`).

## Verification
```bash
python3 investment_screener/backend/py_services/verify_refresh.py
python3 investment_screener/backend/py_services/verify_screener_integrity.py
```

## References
- [Keeping Recommendations Coherent](../recommendation-coherence.md) - Review gate and canonical record.
- Investment Thesis (`investment_screener/backend/data/theses/investment_thesis.md`) - Target portfolio document and strategy definitions.
