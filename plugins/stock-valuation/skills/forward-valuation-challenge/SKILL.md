---
name: forward-valuation-challenge
plugin: stock-valuation
description: Challenge and stress-test AI-generated investment thesis valuations that are overly anchored on historical financials. Enforces forward-looking contract pipelines, hyperscaler capex cycles, and backlog-based revenue floors. Trigger on /forward-valuation-challenge or "challenge [TICKER] forward valuation".
allowed-tools: Bash, Read, Write
---

# Forward Valuation Challenge

Stress-tests equity valuations against forward-looking contract backlogs, hyperscaler capex, and secular demand drivers.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- **Backlog revenue floor**: Bear cases must never assume revenue collapses below verified contracted backlog and non-cancellable LOIs.
- **Hyperscaler capex context**: Valuations for power, cooling, compute, and grid infrastructure must incorporate public hyperscaler capex commitments (2025–2030).
- **Multiple repricing**: Exit multiples must reflect structural sector re-ratings rather than legacy pre-AI cycle trough averages.
- **Scenario spread sanity**: Flag and reject scenarios where Bull is $>50\times$ Bear unless explicitly modeling pre-revenue biotechnology or early exploration.

## Quick start

Activate when evaluating infrastructure, power, cooling, or compute providers with substantial forward backlogs:

```bash
python3 plugins/stock-valuation/scripts/dcf_scenarios.py --help
```

Key inputs: signed contract backlog, multi-year delivery timelines, hyperscaler capex guidance.

## Workflow

1. **Verify Applicability**:
   Confirm asset belongs to AI power, data center infrastructure, compute hardware, or utility transmission.
2. **Audit Backlog Visibility**:
   - Extract firm contracted backlog and commercial pipeline from latest SEC 10-K/10-Q.
   - Calculate backlog coverage ratio: `Backlog / TTM Revenue`.
3. **Formulate Scenario Bounds**:
   - `Bear Case Floor`: $\text{Contracted Backlog} \times \text{Delivery Probability} \times \text{Trough Margin} / \text{Shares}$.
   - `Base Case`: Operating leverage ramp aligned with confirmed hyperscaler deployment schedules.
   - `Bull Case`: Market share expansion plus pricing power in supply-constrained categories.
4. **Recalibrate Valuation Output**:
   Recompute DCF scenario weights and ensure probability-weighted fair value reflects structural demand reality.

## Verification

- Confirm Bear case target does not breach calculated backlog floor.
- Verify scenario spread ratio is $<50\times$.
- Test routing cases against `evals/evals.json`.
