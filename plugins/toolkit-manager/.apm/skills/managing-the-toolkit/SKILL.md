---
name: managing-the-toolkit
plugin: toolkit-manager
description: Runs and maintains the Investment Toolkit itself. Covers first-time onboarding of a fresh clone (runtimes, database, accounts, broker sync, valuation baselines), launching the Investment Screener suite (backend and frontend), backing up, exporting, rebuilding and restoring the SQLite databases, and the maintenance audits that guard the "SQLite only" data rule. Trigger on /toolkit-onboarding, /start-screener, /sqlite-admin, "help me set up the toolkit", "run the screener", "start the app", "launch investment toolkit", "start servers", "back up the database", "restore the database", "export the schema and data", "rebuild the database from an export", "is the database healthy", or before any migration or bulk data write.
allowed-tools: Bash, Read, Write
---

# Managing the Toolkit

One skill for the toolkit's own operations: getting a fresh clone running, starting the app, protecting the databases, and auditing the code against the data rules.

## Contents

- [Quick start](#quick-start) · [Workflow](#workflow) · [Constraints](#constraints) · [Modes](#modes) · [Scripts](#scripts) · [Verification](#verification) · [References](#references)

## Quick start

From the repository root:

```bash
python3 run_investment_toolkit.py                              # start the suite (run-app mode)
python3 investment_screener/backend/py_services/domain_model/db_backup.py backup --db domain_model   # snapshot before any write
```

Paths starting with `scripts/` below are relative to this skill's folder; the backup tool is the backend's own module and is called by its repository path.

## Workflow

1. Match the request to a mode in the table below and read its mode file.
2. For anything that writes to a real database, take a binary snapshot first (the [sqlite-admin mode](references/modes/sqlite-admin.md)).
3. Follow the mode's workflow; confirm with the owner before restoring, syncing broker positions or placing orders.
4. Finish with the mode's verification.

## Constraints

- **Single source of truth**: all portfolio holdings, cash balances and target allocations live in `domain_model.sqlite`; never write to retired JSON files.
- **Cash invariant**: `Total USD = sum(Equities Market Value) + sum(Account Cash USD)`.
- **Human confirmation**: never apply broker position syncs, restore a database or place orders without the owner's explicit go-ahead.
- **Migration authority**: schema changes go through `schema_migrator.py`, never raw SQL against the tables.
- **Never create orphan processes**: identify who owns ports 3001 and 5173 before restarting anything.

## Modes

| Mode | Trigger | What it does |
|---|---|---|
| [onboarding](references/modes/onboarding.md) | `/toolkit-onboarding` | Fresh-clone bootstrap: runtimes, backup, accounts, holdings sync, DCF baselines, export, launch |
| [run-app](references/modes/run-app.md) | `/start-screener` | Starts backend (3001) and frontend (5173) with the unified runner and confirms both are listening |
| [sqlite-admin](references/modes/sqlite-admin.md) | `/sqlite-admin` | Health check, binary backup, portable export, verified rebuild, restore |
| [maintenance-audits](references/modes/maintenance-audits.md) | none (run on request) | Data-rule audits and their registers, app smoke test, temp-file archiving, ecosystem summary |

## Scripts

- `scripts/sqlite_admin.py`: `status`, `export`, `verify-export`, `rebuild` (imports the backend's `db_backup` module).
- `scripts/audit_file_dependencies.py`, `scripts/audit_sqlite_usage.py`: read-only guards for the SQLite-only data rule.
- `scripts/app_smoke_test.py`, `scripts/archive_temp_json.py`, `scripts/extract_ecosystem_yaml.py`: maintenance utilities.
- Tests: `tests/` (pass the path explicitly: `python3 -m pytest plugins/toolkit-manager/.apm/skills/managing-the-toolkit/tests`).

## Verification

- `python3 scripts/sqlite_admin.py status --db domain_model` lists tables, row counts and the schema `user_version`.
- `python3 scripts/sqlite_admin.py verify-export <folder>` prints `export ok` with matching counts.
- With the suite running: HTTP 200 from `http://localhost:5173` and `http://localhost:3001/api/health`.
- Routing cases for every mode are in `evals/evals.json`.

## References

- [Agent quick reference](references/agent-quick-reference.md): commands and conventions for agents working in the repo.
- [Database DDL](references/data-architecture/sql/): `01_intelligence_ledger_schema.sql`, `02_portfolio_operations_schema.sql`, `03_domain_data_model_schema.sql`.
- Data-architecture documents live in `docs/architecture/` (`domain-data-model.md`, `migration-inventory-and-strategy.md`, `supplementary-domain-schemas.md`).
- [Evolution log](references/evolution-log.md): append-only history of changes to this skill.
