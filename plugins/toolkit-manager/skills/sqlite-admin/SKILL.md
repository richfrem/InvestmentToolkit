---
name: sqlite-admin
plugin: toolkit-manager
description: Back up, restore, export and rebuild the toolkit's SQLite databases (domain_model.sqlite portfolio data, intelligence.sqlite research ledger). Use when the user says "back up the database", "restore the database", "export the schema and data", "rebuild the database from an export", "is the database healthy", or before any migration or bulk data write.
allowed-tools: Bash, Read
---

# SQLite Admin

Two independent safety nets for `domain_model` (all portfolio data) and `intelligence` (research ledger). Both databases are gitignored personal data; nothing here deletes or overwrites one without an explicit flag.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- **Real data lives in the main checkout.** Worktrees hold their own empty copies of the gitignored databases; a backup or export taken in a worktree protects nothing. The scripts look for `investment_screener/backend/data` upward from the skill, then from the current directory; set `SQLITE_ADMIN_DATA_DIR` to point at the main checkout's data folder, or pass a full path to `--db`.
- **Back up before any write** to a real database (migration, import, sync, bulk edit). `schema_migrator` and `run_investment_toolkit.py` already do this automatically; do it by hand for anything else.
- **Never restore or rebuild over a live database on your own.** `restore` needs `--yes` and the owner's go-ahead; stop the backend first. `rebuild` refuses to overwrite and only creates a new file.
- **Write exports to a gitignored folder** (for example under `temp/`), never into a tracked folder.

## Quick start

Run from this skill's folder:

```bash
python3 scripts/sqlite_admin.py status --db domain_model
python3 scripts/db_backup.py backup --db domain_model
```

## Workflow

1. **Check health:** `python3 scripts/sqlite_admin.py status --db <domain_model|intelligence|path>` prints tables, row counts, `user_version`, journal mode.
2. **Binary snapshot (fast, exact):** `python3 scripts/db_backup.py backup --db <name>` writes a verified copy to `backups/` beside the database (keeps 14; WAL rows included). List with `python3 scripts/db_backup.py list --db <name>`, check one with `python3 scripts/db_backup.py verify <file>`.
3. **Portable export (rebuild from anything):** `python3 scripts/sqlite_admin.py export --db <name> --out <empty folder>` writes `schema.sql`, `data/<table>.sql` (one `INSERT` per row) and `manifest.json` (row counts, `user_version`). Plain text: readable, diffable, loadable by any SQLite. Write exports to a gitignored folder, never a tracked one.
4. **Prove the export:** `python3 scripts/sqlite_admin.py verify-export <folder>` rebuilds in memory and compares every table's row count and integrity with the manifest. Do this right after every export.
5. **Rebuild** into a NEW file: `python3 scripts/sqlite_admin.py rebuild <folder> --db <new-file>`. It loads data before indexes and triggers (so triggers do not re-fire), checks counts, `integrity_check` and foreign-key violations, and leaves no file on failure. It refuses to overwrite. To put it live, the owner stops the backend and moves it into place.
6. **Restore a snapshot** (owner approval required): stop the backend, then `python3 scripts/db_backup.py restore <backup-file> --db <name> --yes`. A `pre-restore` backup of the current state is taken first.

## Verification

- `verify-export` prints `export ok: N tables, M rows, matches manifest`.
- After a rebuild, run `sqlite_admin.py status --db <new file>` and compare with the source.
- Routing cases: `evals/evals.json`.
