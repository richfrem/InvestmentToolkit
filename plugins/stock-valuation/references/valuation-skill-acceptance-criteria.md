# Valuation skill acceptance criteria

Use each skill's `evals/evals.json` for its routing and behavioral cases.

- Research findings cite dated evidence and distinguish facts, estimates and assumptions.
- Model claims and rate basis are compatible; missing or inherited inputs are not fabricated.
- Bear/base/bull assumptions and weights are explained, and material uncertainty is disclosed.
- Revaluation and method changes follow the invoked skill's decision gate and existing session authorization.
- Canonical actions and standing decisions are respected; research does not execute trades.
- Published valuations retain rate evidence and report links through canonical persistence. Dated reports are ingested into the research ledger and read back through the API.
- Worktree implementations verify real data against the main checkout; a worktree copy alone is insufficient.

Automated CLI/SQLite and UI tests establish calculation/persistence behavior. Static audits validate packaging. Record actual behavioral model evaluation separately; adding evaluation cases is not evidence that an agent passed them.
