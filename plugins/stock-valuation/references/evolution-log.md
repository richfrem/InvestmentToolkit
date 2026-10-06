# Evolution Log — Stock Valuation Plugin

Append-only record of every self-evolution event. Written by the `self-evolution` skill.
Do not edit manually except to correct a factual error.

| Date | Tier | Failure | Patch | Edit Type | Outcome |
|------|------|---------|-------|-----------|---------|
| 2026-09-02 | Tier 1 (Gap) | Valuation projections and price levels required ad-hoc Python snippets for SQLite persistence, leading to potential version collisions and lack of atomicity. | Created canonical `persist_valuation.py` script in `plugins/stock-valuation/scripts/` and symlinked to `skills/update-stock-analysis/scripts/` via `symlink_manager.py`. Script automatically inspects existing versions and assigns `MAX(version) + 1`, atomic multi-table transaction, and updates SKILL.md. | New script + symlink + documentation + test | Projections, scenarios, and TV price levels now persist atomically via clean CLI command with 100% test coverage. |
| 2026-10-02 | Tier 1 (Friction) | Step 4.5 mandated autonomous subagent dispatch (red-team-agent) which broke unattended execution and triggered intrusive approval prompts in CLI runners. | Revised SKILL.md Step 4.5 to make inline review the default and gate subagent dispatch behind explicit user confirmation. | Update SKILL.md | Inline adversarial check default; subagents strictly opt-in per user request. |
| 2026-10-04 | Tier 1 | stock-valuation skills had oversized bodies, non-canonical headings, unmanaged real files in references, and missing links | Migrated real files to canonical references with symlink_manager, aligned all 4 skills to 6 canonical sections within lean budget, fixed evals | fix | PASS |


| 2026-10-05 | Tier 1 (Gap) | AI valuations could omit forward guidance, conventional memory/storage and speed-to-power demand; backlog floor instructions could overstate guaranteed value. | Added shared AI forward-evidence guide to three valuation skills and five review/intake skills, corrected backlog bounds and model-method labeling, and added MU/BE evaluation cases. | Skill guidance + managed references + contract tests | Requires dated forward revenue/EPS, capacity and annual cash conversion, separates firm orders from frameworks, and flags NEEDS_REVALUATION without changing canonical actions. Static audits and focused tests verified; behavioral model evals not run. |
