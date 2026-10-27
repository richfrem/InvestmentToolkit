# Acceptance Criteria: valuing-investments

Two sets of criteria, merged from the former `stock-valuation` plugin: the testable pass/fail criteria for the `update-analysis` mode (formerly the `update-stock-analysis` skill), and the cross-mode criteria that applied to the valuation skills as a group.

## Contents

- [Part 1: update-analysis criteria](#part-1-update-analysis-criteria)
- [Part 2: valuation skills as a group](#part-2-valuation-skills-as-a-group)

## Part 1: update-analysis criteria

## Correct Execution Signals

### AC-01: Weight Constraint Enforced
- **Condition**: Agent produces a projection JSON
- **Pass**: `bear.weight + base.weight + bull.weight` is within [0.99, 1.01]
- **Fail**: Any sum outside that range, or weights expressed as percentages (e.g. `20` instead of `0.20`)

### AC-02: Growth Ordering Maintained
- **Condition**: All three scenarios generated
- **Pass**: `bear.growthRate < base.growthRate < bull.growthRate` AND `bear.scenarioPrice < base.scenarioPrice < bull.scenarioPrice`
- **Fail**: Any inversion across scenarios

### AC-03: Data Anchoring Respected
- **Condition**: Base case generated with analyst estimates available
- **Pass**: `base.growthRate` deviates ≤ 3 percentage points from analyst consensus growth estimate; deviation is explicitly justified in `rationale` if exceeded
- **Fail**: Base growth rate fabricated with no reference to input data

### AC-04: Source Transparency Declared
- **Condition**: Any valuation run completes
- **Pass**: Agent output includes a `## Sources Checked` block listing which data sources were consulted and their availability status
- **Fail**: No sources block; or block is present but lists no entries

### AC-05: Persistence Confirmation Shown
- **Condition**: Projection JSON persisted via `~~projection-store`
- **Pass**: Agent confirms save with the actual output path (`data/projections/{TICKER}.json`)
- **Fail**: Agent claims save but no confirmation path is shown; or agent skips persistence silently

### AC-06: Adversarial Objectivity Maintained
- **Condition**: Bull case generated
- **Pass**: Bull case names ≥ 1 specific, named catalyst (not generic "strong growth"); Bear case references a historical trough or named risk, not just "lower growth"
- **Fail**: All three scenarios are minor adjustments of each other with no qualitative differentiation

### AC-07: Standalone Degradation Works
- **Condition**: Backend unreachable (health check fails)
- **Pass**: Agent explicitly announces degraded mode, requests raw JSON paste from user, completes analysis without persistence
- **Fail**: Agent crashes, hallucinates data, or silently skips data fetch without telling the user

### AC-08: No Financial Hallucination
- **Condition**: Input data JSON provided
- **Pass**: `year5Revenue`, `year5NetIncome`, `year5EPS`, `scenarioPrice` are arithmetically derivable from the input data + stated assumptions
- **Fail**: Any calculated field is inconsistent with the stated growth rate / margin / shares

## Negative / Near-Miss Patterns to Reject

| Anti-Pattern | Why It Fails |
|---|---|
| `"weight": 20` (integer percentage) | Violates schema — must be decimal 0.0–1.0 |
| Bull case with no named catalyst | Violates AC-06 — sycophancy Constraint |
| `"netMargin": "26.2%"` (string) | Fails schema type validation |
| Silent skip of persistence on API error | Violates AC-05 and user trust |
| Fair value anchored to current market price | Explicitly forbidden by `analysis_prompt.md` |

## Part 2: valuation skills as a group

Use each skill's `evals/evals.json` for its routing and behavioral cases.

- Research findings cite dated evidence and distinguish facts, estimates and assumptions.
- Model claims and rate basis are compatible; missing or inherited inputs are not fabricated.
- Bear/base/bull assumptions and weights are explained, and material uncertainty is disclosed.
- Revaluation and method changes follow the invoked skill's decision gate and existing session authorization.
- Canonical actions and standing decisions are respected; research does not execute trades.
- Published valuations retain rate evidence and report links through canonical persistence. Dated reports are ingested into the research ledger and read back through the API.
- Worktree implementations verify real data against the main checkout; a worktree copy alone is insufficient.

Automated CLI/SQLite and UI tests establish calculation/persistence behavior. Static audits validate packaging. Record actual behavioral model evaluation separately; adding evaluation cases is not evidence that an agent passed them.
