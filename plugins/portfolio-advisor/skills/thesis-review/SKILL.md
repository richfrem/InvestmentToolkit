---
name: thesis-review
plugin: portfolio-advisor
description: Interactive entry point for pitching a new investment thesis or challenging an existing one, delegating analysis to the thesis-review-agent.
---

# Thesis Review

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints
- Acts as a delegator; hands off execution to `thesis-review-agent`.
- Scripts and reference files must remain unexecuted until invoked by the agent.
- Target portfolio adjustments must preserve the 100.00% allocation invariant.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/update_targets.py --show
```

## Workflow
1. **Intake Pitch**: Receive the user's thesis pitch, macro theme, or proposed pillar adjustment.
2. **Delegate Agent**: Launch `thesis-review-agent` via sub-agent orchestration.
3. **Committee Review**: Agent conducts adversarial research, DCF valuations, and weight calibrations.
4. **Apply Blueprint**: Finalized target updates are written using canonical scripts and blueprint generators.

## Verification
```bash
python3 plugins/portfolio-advisor/scripts/validate_weights.py --target investment_screener/backend/data/theses/target-portfolio.json
```

## References
- [Investment Thesis](references/investment_thesis.md) - Canonical portfolio thesis and sub-strategy definitions.
