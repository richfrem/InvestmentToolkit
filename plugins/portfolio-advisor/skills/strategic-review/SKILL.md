---
name: strategic-review
plugin: portfolio-advisor
description: Challenges and stress-tests the investment thesis against AI valuation evidence, pillar performance, and market reality, producing formula improvement proposals.
---

# Strategic Review

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints
- Targets must always sum to 100.00% (+-0.05%); normalize after any weight adjustment.
- Sizing constraints: no holding may exceed 15% and no pillar may exceed 40% of total portfolio.
- Standing decisions anchor allocations; require >15% Fair Value change or material catalysts to revisit.
- Run the full refresh chain after applying changes (`update_targets.py --blueprint`, `generate_review_json.py`, `verify_refresh.py`).

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/update_targets.py --show
```

## Workflow
1. **Gap Analysis**: Scan portfolio state, identifying untracked holdings, unallocated targets, and DCF conflicts.
2. **Foundation Scan**: Ingest DCF projections from `data/projections/` and recent review notes.
3. **Adversarial Evaluation**: Apply `references/strategic_review_prompt.md` criteria to stress-test pillar logic and assumptions.
4. **Propose Calibrations**: Formulate explicit target weight adjustments and present recommendations to user.
5. **Apply & Refresh**: Write approved changes via `update_targets.py --write --blueprint` and run full refresh chain.

## Verification
```bash
python3 plugins/portfolio-advisor/scripts/verify_refresh.py
python3 investment_screener/backend/py_services/verify_thesis_sync.py
```

## References
- [Investment Thesis](references/investment_thesis.md) - Canonical portfolio thesis and sub-strategy definitions.
- [Fallback Tree](references/fallback-tree.md) - Operational fallback procedures for backend disruptions.
- [Strategic Review Prompt](references/strategic_review_prompt.md) - Comprehensive strategic analysis prompt instructions.
