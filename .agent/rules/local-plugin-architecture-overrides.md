---
description: InvestmentToolkit's plugin layout. Overrides the generic symlink and symlinks.json rules in plugin-architecture-policy.md and git-operations.md.
globs: ["plugins/**", "apm.yml", "apm.lock.yaml"]
---

# Local Plugin Architecture Overrides (InvestmentToolkit)

`plugin-architecture-policy.md` and `git-operations.md` come from `agent-plugins-skills` and are overwritten on every sync, so the toolkit's own rules live here (`local-` rules are never synced).

## Overrides

- **No symlinks, no `symlinks.json`.** The four project plugins (`portfolio-advisor`, `tradingview`, `toolkit-manager`, `questrade`) are APM packages. Each skill hub keeps its scripts, references, assets and tests as real files; `symlink_manager.py` and the hub-and-spoke symlink pattern do not apply here.
- **Shared code lives in the backend.** A script the backend imports, or that two or more hubs use, is a real file in `investment_screener/backend/py_services/`.
- **Install with APM**: `apm install --target agent-skills` from the repository root (root `apm.yml`). Never edit the deployed copies in `.agents/skills/`; change the plugin source and reinstall. Commit `apm.lock.yaml` with the change.
- **Library plugins** from `agent-plugins-skills` still install through the legacy sync (`plugin-sources.json`, `plugin-retention.json`); never install the same plugin with both installers.
- **Ledger**: old-to-new paths are recorded in `docs/plans/apm-migration/`.
