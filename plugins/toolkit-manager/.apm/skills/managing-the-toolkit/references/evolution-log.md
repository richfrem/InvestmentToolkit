# Evolution Log — toolkit-manager

Append-only record of every self-evolution event. Written by the `self-evolution` skill.
Do not edit manually except to correct a factual error.

| Date | Tier | Friction / Failure | Patch | Edit Type | Outcome |
|------|------|-------------------|-------|-----------|---------|
| 2026-10-04 | Tier 1 | toolkit-manager skills had non-canonical sections, real-file references, and missing evals | Removed unused real file, retrofitted run-screener and toolkit-onboarding to 6 canonical sections, created evals.json | fix | PASS |
| 2026-10-08 | Tier 1 (Gap) | Onboarding never asked whether the owner uses Questrade, so nothing recorded which broker connections refreshes may use. | Onboarding asks once and leaves `QUESTRADE_ENABLED=false` (TradingView only) unless the owner completes `/questrade-setup` (ADR-036). | Skill workflow | Setting read by `broker_sources.py`. |
| 2026-10-26 | Tier 1 (Structure) | Three skills shared two scripts through symlinks, five maintenance scripts belonged to no skill, and `db_backup.py` was a plugin file the backend reached through a symlink. | One hub `managing-the-toolkit` (onboarding, run-app, sqlite-admin, maintenance-audits); `db_backup.py` became a real file in the backend (`py_services/domain_model/`) shared with `sqlite_admin.py`; scripts and tests find the repo by marker; manifests retired; `file-dependency-register.json` paths updated. | refactor | PASS (76 tests = baseline, validator, auditor, real `apm install`) |
