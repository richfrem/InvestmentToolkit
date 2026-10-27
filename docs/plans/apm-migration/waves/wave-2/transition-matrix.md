# Wave 2: transition matrix

Old skill names are retired; slash commands are unchanged. Each old skill is now a mode file under `references/modes/` of its hub.

| Legacy skill | Hub skill | Mode | Slash command | What changed |
|:---|:---|:---|:---|:---|
| `toolkit-onboarding` | `managing-the-toolkit` | `onboarding` | `/toolkit-onboarding` | Backup command is now the backend's db_backup module path; run-screener and Questrade steps point at modes. |
| `run-screener` | `managing-the-toolkit` | `run-app` | `-` | Content carried over; paths made relative to the hub. |
| `sqlite-admin` | `managing-the-toolkit` | `sqlite-admin` | `-` | Backup, list, verify and restore call the backend's own db_backup module by repo path; sqlite_admin.py shares it. |

## Other changes
- New mode `maintenance-audits` for the five scripts no skill used (`audit_file_dependencies`, `audit_sqlite_usage`, `app_smoke_test`, `archive_temp_json`, `extract_ecosystem_yaml`); settled as "keep in the hub" (not archived).
- `db_backup.py` is now a real file at `investment_screener/backend/py_services/domain_model/db_backup.py` (it replaced the backend's symlink); schema_migrator, the launcher, `sqlite_admin.py` and the backend test `test_db_backup.py` all use it from there.
- Scripts and tests find the repo root by the `investment_screener/` marker; `sqlite_admin.py` exits with a clear message if run outside the repo.
- The data-architecture `.md` symlinks were retired (canonical copies stay in `docs/architecture/`); references to them were rewritten.
- Updated elsewhere: `run_tests.py`, backend `paths.ts` (agent guide path), `INIT_AGENTS.md`, `README.md`, `architecture.md`, `docs/architecture/file-dependency-register.json` (paths only; dispositions preserved), one stock-valuation eval; marketplace entry removed.
