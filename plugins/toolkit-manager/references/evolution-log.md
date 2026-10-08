# Evolution Log — toolkit-manager

Append-only record of every self-evolution event. Written by the `self-evolution` skill.
Do not edit manually except to correct a factual error.

| Date | Tier | Friction / Failure | Patch | Edit Type | Outcome |
|------|------|-------------------|-------|-----------|---------|
| 2026-10-04 | Tier 1 | toolkit-manager skills had non-canonical sections, real-file references, and missing evals | Removed unused real file, retrofitted run-screener and toolkit-onboarding to 6 canonical sections, created evals.json | fix | PASS |
| 2026-10-08 | Tier 1 (Gap) | Onboarding never asked whether the owner uses Questrade, so nothing recorded which broker connections refreshes may use. | Onboarding asks once and leaves `QUESTRADE_ENABLED=false` (TradingView only) unless the owner completes `/questrade-setup` (ADR-036). | Skill workflow | Setting read by `broker_sources.py`. |
