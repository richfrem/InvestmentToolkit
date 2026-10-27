# toolkit-manager

Operations for the Investment Toolkit itself, packaged as an APM-native package (`type: full`, primitives under `.apm/`).

## Skill

| Skill | Modes |
|---|---|
| `managing-the-toolkit` | `onboarding` (`/toolkit-onboarding`), `run-app` (`/start-screener`), `sqlite-admin` (`/sqlite-admin`), `maintenance-audits` |

## Layout

```
apm.yml                          manifest (includes: auto)
.apm/skills/managing-the-toolkit/
  SKILL.md                       hub (mode table, shared constraints)
  references/modes/              one file per mode
  references/                    agent quick reference, evolution log, data-architecture/sql (DDL)
  scripts/                       sqlite_admin, audit_file_dependencies, audit_sqlite_usage,
                                 app_smoke_test, archive_temp_json, extract_ecosystem_yaml
  tests/  evals/
docs/                            governance, attribution, lifecycle
```

`db_backup.py` is the backend's own module (`investment_screener/backend/py_services/domain_model/db_backup.py`), shared with `sqlite_admin.py` rather than copied.

## Data architecture

All portfolio data (holdings, targets, thesis state, trades, cash, price levels, alerts, valuations, thesis breakers) lives in `investment_screener/backend/data/domain_model.sqlite`; research and analysis live in `intelligence.sqlite`. See ADR-038 (`docs/architecture/ADRs/038-sqlite-single-source-of-truth.md`) and `INIT_AGENTS.md` for setup. The model and its DDL are documented in `docs/architecture/domain-data-model.md`, `docs/architecture/supplementary-domain-schemas.md` and `.apm/skills/managing-the-toolkit/references/data-architecture/sql/`.

## Install and test

`apm install ./plugins/toolkit-manager --target agent-skills` from the repository root deploys the skill to `.agents/skills/` (generated and gitignored; edit the sources under `.apm/`).

`python3 -m pytest plugins/toolkit-manager/.apm/skills/managing-the-toolkit/tests` (pytest skips dot-directories, so the path must be explicit).
