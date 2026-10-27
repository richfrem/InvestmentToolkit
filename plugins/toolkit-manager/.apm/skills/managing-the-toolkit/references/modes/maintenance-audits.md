# Mode: maintenance-audits

Code and data hygiene for the toolkit: audits that guard the "SQLite only" data rule and regenerate the architecture registers, a smoke test of the running app, scratch-file archiving and an ecosystem summary. Not triggered by a slash command; run on request or after changing storage, migrations or where files live.
Allowed tools: Bash, Read, Write. Paths starting with `scripts/` are relative to this skill's folder; `--root` is the repository root.

## Constraints

- **The audits are read-only.** `audit_file_dependencies.py` and `audit_sqlite_usage.py` never modify a scanned file; `--write-register` only edits the register file named below.
- **The data rule**: portfolio data lives only in `domain_model.sqlite`. No `.py`, `.ts`, `.tsx` or `.js` file may read or write a JSON, JSONL, CSV or spreadsheet file, or a retired data directory (`research/`, `daily-briefs/`, `etf_analysis/`, `13f/`, `projections/`), except the tooling and migration entries the register lists.
- **Never delete.** `archive_temp_json.py` moves files into `temp/archive/<date>/`, dry-run by default; nothing in this mode deletes data.
- **Real databases are never written.** `app_smoke_test.py` works on a copy inside a git worktree and never touches the main checkout's databases.
- **Review `unreviewed` register entries by hand.** `--write-register` adds new dependencies as `unreviewed`; a person (or the owner's decision) assigns the disposition and the step that removes it.

## Scripts

| Script | What it does | Typical command |
|---|---|---|
| `audit_file_dependencies.py` | Inventories every place code reads or writes a data file and compares it with `docs/architecture/file-dependency-register.json` | `python3 scripts/audit_file_dependencies.py --root <repo> --check` (`--strict` is the end state; `--write-register` adds unlisted dependencies as `unreviewed` and drops stale ones) |
| `audit_sqlite_usage.py` | Follows legacy portfolio data file names through constants, defaults and wrappers in every non-symlink `.py` under `plugins/` and `investment_screener/` and classifies each use (`READ_CONTENT`, `STAT_ONLY`, `WRITE`, `VESTIGIAL`, `UNUSED`, ...) | `python3 scripts/audit_sqlite_usage.py --root <repo> --check` (also `--json out.json --artifacts`, `--self-test`) |
| `app_smoke_test.py` | Copies the real databases into a worktree's data folder, starts the backend there on a spare port and checks every read route the web app uses | `python3 scripts/app_smoke_test.py` (`--source-data <dir>`, `--port 3199`, `--routes-only`) |
| `archive_temp_json.py` | Moves old scratch JSON in `temp/` and `temp/evaluations/` (older than 7 days by default) into `temp/archive/<date>/` | `python3 scripts/archive_temp_json.py` lists; add `--move` to move; `--older-than-days N` |
| `extract_ecosystem_yaml.py` | Writes `ecosystem_yaml_summary.md` at the repository root from the deployed skills and agents | `python3 scripts/extract_ecosystem_yaml.py` |

## Workflow

1. After a change to storage, migrations or file locations, run `audit_sqlite_usage.py --check` and `audit_file_dependencies.py --check`. Fix real violations; for a legitimately moved or removed file, update the register entry (the register is keyed by file path).
2. To refresh the generated architecture reports (`docs/architecture/json-discovery-audit.*` and `allowed-json-register.*`), run `python3 investment_screener/backend/py_services/audit_json_usage.py --root . --out docs/architecture`. They are generated; never edit them by hand.
3. After storage changes that the unit tests cannot cover, run `app_smoke_test.py` and read the PASS/FAIL table.
4. Run `archive_temp_json.py` (dry run first) when `temp/` has grown.

## Verification

- `audit_file_dependencies.py --check` and `audit_sqlite_usage.py --check` exit 0 (note: the repository register may already list known mismatches; compare with the last recorded baseline rather than assuming zero).
- `app_smoke_test.py` prints PASS for every route and exits 0.
- The tests in `tests/` cover each script; pass the path explicitly because pytest skips dot-directories.
