# Package Lifecycle

1. Author or change primitives in `.apm/` (never in the deployed `.agents/` or `.claude/` copies).
2. Validate: `python3 <packaging-with-apm>/scripts/validate_apm_package.py --path plugins/questrade`.
3. Run the tests under `.apm/skills/*/tests`.
4. Deploy into a project with `apm install ./plugins/questrade --target agent-skills,claude`.
5. Commit `apm.yml` and the project's `apm.lock.yaml` together.
