---
name: valuation-math-validation
plugin: stock-valuation
description: Detect and prevent computational bugs in the DCF and scenario valuation engine that produce nonsensical target prices. Enforces unit normalization, monotonicity checks, scenario spread bounds, and dilution math. Trigger on /valuation-math-validation or "validate valuation math".
allowed-tools: Bash, Read, Write
---

# Valuation Math Validation

Deterministic mathematical gatekeeper preventing computational bugs and distorted target prices in scenario DCF models.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- **Input decimal normalization**: All percentage inputs must be in decimal form (`0.10` for $10\%$, not `10.0`).
- **Strict monotonicity**: Increasing revenue CAGR or operating margin must strictly increase or preserve target price; negative sensitivity derivatives are fatal errors.
- **Scenario ordering**: Bear price $<$ Base price $<$ Bull price.
- **Spread ratio limit**: Bull target price must not exceed $50\times$ Bear target price unless modeling binary biotechnology or pre-revenue assets.
- **Zero negative residual**: If computed equity value is negative, target price must clamp to `$0.00` and label as restructuring/wipeout.

## Quick start

Execute mathematical validation on any scenario valuation payload:

```bash
python3 plugins/stock-valuation/scripts/validate_projection.py --input temp/evaluations/{TICKER}_projection.json
```

Key inputs: scenario revenue growth, margins, discount rate, exit multiple, share count.

## Workflow

1. **Input Range Audit**:
   - `revCAGR`: $-0.50$ to $3.00$
   - `netMargin`: $-1.00$ to $1.00$
   - `discountRate`: $0.01$ to $0.50$
   - `exitPE`: $1$ to $100$
   - `probabilityWeight`: sum to $1.00 \pm 0.01$
2. **Unit Consistency Check**:
   Confirm revenue, net income, cash, and debt are in identical units (e.g. millions vs billions) across all steps.
3. **Discount Factor Validation**:
   Ensure discount factor is calculated as $(1 + r)^t$, not double-discounted against cash flow intervals.
4. **Monotonicity & Sensitivity Perturbation**:
   Verify that a $+1\%$ shift in growth produces $\Delta \text{Price} \ge 0$.
5. **Reconciliation Audit**:
   Verify probability-weighted fair value: $\text{FV} = w_{\text{bear}} P_{\text{bear}} + w_{\text{base}} P_{\text{base}} + w_{\text{bull}} P_{\text{bull}}$.

## Verification

- Confirm zero assertion failures from `validate_projection.py`.
- Verify monotonicity test output.
- Validate test cases against `evals/evals.json`.
