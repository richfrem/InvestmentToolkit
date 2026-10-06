---
name: forward-valuation-challenge
plugin: stock-valuation
description: Challenge and stress-test AI-generated investment thesis valuations that are overly anchored on historical financials. Tests forward estimates, contract delivery schedules, memory/storage demand, and hyperscaler capex cycles. Trigger on /forward-valuation-challenge or "challenge [TICKER] forward valuation".
allowed-tools: Bash, Read, Write
---

# Forward Valuation Challenge

Stress-tests equity valuations against forward-looking contract backlogs, hyperscaler capex, and secular demand drivers.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints
- **AI forward-evidence gate**: Before valuation or action proposals for AI-exposed names, apply [AI-sector forward valuation evidence](references/ai-forward-valuation.md). Reconcile dated forward estimates, memory/storage or power demand, executable capacity and cash conversion; flag `NEEDS_REVALUATION` when material drivers are missing. This review flag does not replace the canonical action or standing decision.

- **Backlog delivery bounds**: Bear cases must account for verified non-cancellable contracts and their delivery schedules; framework capacity and LOIs are not guaranteed revenue, and multi-year backlog is not an annual floor.
- **Hyperscaler capex context**: Use the latest dated hyperscaler capex guidance and distinguish announced budgets from contracted supplier revenue.
- **Multiple repricing**: Test whether evidenced structural changes justify different multiples; neither legacy trough averages nor an automatic AI premium is sufficient.
- **Scenario spread sanity**: Flag and reject scenarios where Bull is $>50\times$ Bear unless explicitly modeling pre-revenue biotechnology or early exploration.

## Quick start

Activate when evaluating AI-exposed infrastructure, power, cooling, compute, memory or storage providers:

```bash
python3 plugins/stock-valuation/scripts/dcf_scenarios.py --help
```

Key inputs: dated forward revenue/EPS estimates, firm orders versus pipeline, delivery timelines, capacity, capex and cash conversion.

## Workflow

1. **Verify Applicability**:
   Confirm asset belongs to AI power, data center infrastructure, compute hardware, memory/storage, or utility transmission.
2. **Audit Backlog Visibility**:
   - Extract firm contracted backlog and commercial pipeline from latest SEC 10-K/10-Q.
   - Calculate backlog coverage ratio: `Backlog / TTM Revenue`.
3. **Formulate Scenario Bounds**:
   - `Bear Case Bound`: Model enforceable contracted deliveries by year, including cancellation, commissioning and cash-conversion risks; do not treat the entire backlog as annual revenue or equity value.
   - `Base Case`: Operating leverage ramp aligned with confirmed hyperscaler deployment schedules.
   - `Bull Case`: Market share expansion plus pricing power in supply-constrained categories.
4. **Recalibrate Valuation Output**:
   Recompute DCF scenario weights and ensure probability-weighted fair value reflects structural demand reality.

## Verification

- For AI-exposed names, verify the forward-evidence cases in `evals/evals.json`; record source dates, modeled changes and unresolved gaps before relying on a valuation signal.

- Confirm scenarios reconcile forward guidance and executable deliveries without treating backlog as guaranteed equity value.
- Verify scenario spread ratio is $<50\times$.
- Test routing cases against `evals/evals.json`.

## References
- [AI-sector Forward Valuation Evidence](references/ai-forward-valuation.md) - Forward estimates, memory/storage and power drivers, cash-flow bridge, and recommendation readiness.
