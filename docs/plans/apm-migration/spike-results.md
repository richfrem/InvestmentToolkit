# APM spike results (apm 0.33.0, throwaway project outside the repo)

Package under test: two hubs (`hub-a` with `references/modes/` and `scripts/`, `hub-b` with a shared reference), one `*.agent.md`, `apm.yml` with `includes: auto`, `metadata.packaging_mode: full`, `metadata.governance_lane: team`.

| Question | Result |
|---|---|
| Does the validator check structure once `packaging_mode: full` is set? | Yes. It passes with the full-mode checks active (no duplicate root primitives). Without that field it skips them. |
| Local dependency syntax for a project install | `apm install ./plugins/<name> --target agent-skills,claude` works with a **relative** path. It creates the project `apm.yml` if missing and records `dependencies.apm: [./plugins/<name>]`, plus `apm.lock.yaml` and a gitignored `apm_modules/`. (An absolute path also works but is recorded as absolute, which is not portable.) |
| Where do hubs land? | `.agents/skills/<hub>/` and `.claude/skills/<hub>/`, with every subfolder (`references/modes/`, `scripts/`, `assets/`). Agents land in `.claude/agents/<name>.md` (the `.agent` suffix is dropped). |
| Are cross-hub markdown links rewritten? | Yes: `[x](../hub-b/references/shared.md)` became a link into `apm_modules/_local/<pkg>/.apm/skills/hub-b/...`, which resolves in the deployed copy. The mode-file link was rewritten the same way. So **same-plugin cross-hub links work**, but only after an install (the target is the gitignored cache). |
| Are paths in code text rewritten? | No. `python3 scripts/tool.py` stayed as written, relative to the skill folder (SF-8 confirmed). |
| Uninstall | `apm uninstall ./plugins/<name>` removed all deployed files and the `apm.yml` entry. The earlier etf-analysis uninstall failure came from a test fixture with no `apm.yml`, not from the package. |
| `apm pack` (marketplace option) | Emits `build/<name>-<version>/` with `plugin.json`, `skills/`, `agents/` in plugin-native layout. It also **writes a generated `.claude-plugin/plugin.json` into the package folder**, so that path must be gitignored in each plugin. |
| Not yet tested | `dependencies.mcp` for the Questrade HTTP server (tested in wave 1), installing four plugins from one root `apm.yml`. |

Consequences for the plan:
- Decision 5 (deploy with APM) is viable: a root `apm.yml` listing `./plugins/<name>` replaces the legacy sync, and `.agents/` and `.claude/` are generated (already gitignored).
- Decision 2 (same-plugin cross-hub links) works as designed; cross-plugin references stay by skill name.
- Each plugin needs `.claude-plugin/plugin.json` in its `.gitignore` (written by `apm pack`).
