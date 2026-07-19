# Wave 1 Task 4 — Projections Migration Execution Report

**Status: REAL WRITE EXECUTED.** This report documents the real, insert-only migration
of `investment_screener/backend/data/projections/*.json` into a real SQLite file at
`investment_screener/backend/data/domain_model.sqlite`, created by this task (no prior
canonical path existed from Wave 0 or Task 2 — both explicitly only ever used `:memory:`).
The command below was actually run against the real 82-file corpus; every number in this
report is copied verbatim from that run's output or from direct `SELECT COUNT(*)` /
Python cross-checks against the resulting file, not estimated.

## What changed

`investment_screener/backend/py_services/domain_model/migrate_projections_to_sqlite.py`:

- Extracted the per-file migration loop that used to live inline in `run_dry_run` into a
  shared `_migrate_all(conn, projections_dir)` helper.
- `run_dry_run(projections_dir)` now calls `_migrate_all` against an in-memory connection
  (unchanged behavior, same as before).
- Added `run_real_migration(projections_dir, db_path)`, which calls `_migrate_all` against
  a real `db_client.initialize_db(db_path)` connection — the only new code path in this
  task, and it shares the exact same per-entry migration logic as the already-approved
  dry run, so the results are guaranteed comparable.
- Added a CLI entry point (`main()`, `argparse`) with a `--write` flag, following this
  repo's existing `--dry-run`/`--write` convention (see
  `investment_screener/backend/py_services/lock_and_normalize_targets.py`). Default
  (no `--write`) runs the safe in-memory dry run and prints the report. `--write` runs
  `run_real_migration` against `--db-path` (default
  `investment_screener/backend/data/domain_model.sqlite`).
- This module still never reads back, modifies, or deletes anything under
  `projections_dir` — insert-only into SQLite, exactly as before.

## Real-write command and output

Run from the repo root (`PYTHONPATH` set to `py_services` so `domain_model` resolves as a
package; relative default paths resolve against the repo root, which is why `cd` there
matters):

```bash
PYTHONPATH=investment_screener/backend/py_services python3 -m domain_model.migrate_projections_to_sqlite --write \
  --db-path investment_screener/backend/data/domain_model.sqlite \
  --projections-dir investment_screener/backend/data/projections
```

Output (truncated to the summary; full `per_ticker` array in the raw JSON matches Task 2's
dry-run report exactly, ticker-for-ticker):

```
[WRITE MODE] Migrated into real database: investment_screener/backend/data/domain_model.sqlite
{
  "total_files": 82,
  "total_versions": 132,
  "total_scenarios": 396,
  "legacy_shape_count": 0,
  "missing_scenarios_count": 0,
  "both_shapes_count": 2,
  "file_errors": []
}
```

These `total_versions` (132) / `total_scenarios` (396) / `legacy_shape_count` (0) /
`missing_scenarios_count` (0) / `both_shapes_count` (2) numbers are **identical** to Task
2's dry-run report — expected, since `run_real_migration` executes the identical
`_migrate_all` code path that dry-run always used, just against a real file instead of
`:memory:`. `total_versions`/`total_scenarios` here count **migration calls made** (insert
attempts), not distinct SQLite rows after upsert — see the Delta section below for why
those two numbers differ from the actual row counts.

Exit code: `0`. `pytest investment_screener/backend/tests/py_services/test_migrate_projections_to_sqlite.py`
was also re-run after the refactor: 10/10 passed (unchanged from before this task; this
task didn't add new unit tests, it added a real-execution mode reusing all previously
tested logic).

## Step 2: Migration parity counts (real, computed numbers)

### Source count

```bash
python3 -c "
import json, pathlib
files = list(pathlib.Path('investment_screener/backend/data/projections').glob('*.json'))
print(len(files), sum(len(json.loads(f.read_text())) for f in files))
"
```
Output: `82 132`

- **Source `.json` files**: 82
- **Source array-entries (raw, before any upsert-collapse)**: 132

### SQLite count (real file, after the write)

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('investment_screener/backend/data/domain_model.sqlite')
print('projection_version:', conn.execute('SELECT COUNT(*) FROM projection_version').fetchone()[0])
print('projection_scenario:', conn.execute('SELECT COUNT(*) FROM projection_scenario').fetchone()[0])
print('investment:', conn.execute('SELECT COUNT(*) FROM investment').fetchone()[0])
"
```
Output:
```
projection_version: 115
projection_scenario: 345
investment: 82
```

- **`projection_version` row count**: 115
- **`projection_scenario` row count**: 345
- **`investment` row count**: 82 (one per source file/ticker, as expected — `resolve_investment`
  is idempotent per symbol and every file's ticker is unique)

### Delta: 132 raw entries vs. 115 `projection_version` rows — fully explained, not hand-waved

Delta = 132 - 115 = **17**. This is fully accounted for by the confirmed
upsert-on-`(investment_id, version)` semantics in `save_projection_version`: when the same
`(ticker, version)` pair legitimately appears more than once in a single source file's
array (i.e. the file itself contains two or more array-entries stamped with the same
`version` number — a real property of the source data, not a script defect), each later
insert for that pair overwrites the earlier row via `ON CONFLICT ... DO UPDATE`, so the
row count ends up lower than the raw insert-call count by exactly the number of such
collisions.

Verified directly against the real files:

```bash
python3 -c "
import json, pathlib
files = sorted(pathlib.Path('investment_screener/backend/data/projections').glob('*.json'))
dupes = []
for f in files:
    entries = json.loads(f.read_text())
    entries = entries if isinstance(entries, list) else [entries]
    seen = {}
    for e in entries:
        v = e.get('version')
        seen[v] = seen.get(v, 0) + 1
    for v, c in seen.items():
        if c > 1:
            dupes.append((f.stem, v, c))
print(dupes)
print('total collisions (entries beyond the first per version):', sum(c - 1 for _, _, c in dupes))
"
```

Output:
```
[('AAPL', 1, 2), ('ALAB', 1, 2), ('AMZN', 1, 2), ('ANET', 1, 2), ('AVGO', 1, 2), ('CAKE', 1, 2),
 ('CELH', 1, 2), ('EQIX', 1, 2), ('META', 1, 2), ('MSFT', 1, 2), ('NKE', 1, 2), ('NVDA', 3, 3),
 ('NVDA', 2, 2), ('OKLO', 1, 2), ('ORCL', 1, 2), ('SYM', 1, 2)]
total collisions: 17
```

17 collisions, spread across 15 tickers with one duplicated version each (14 tickers with
`version:1` appearing twice, plus `OKLO`, `ORCL`, `SYM`, `ALAB`, `ANET`, `AVGO`, `CAKE`,
`CELH`, `EQIX`, `META`, `MSFT`, `NKE`, `AAPL`, `AMZN` — 14 total) and `NVDA` alone
contributing 3 collisions across two duplicated versions (`version:3` appearing 3 times =
2 collisions, `version:2` appearing twice = 1 collision). **17 matches the delta exactly
(132 - 115 = 17).** No unexplained discrepancy.

The same logic explains the `projection_scenario` delta: 396 insert calls - 345 rows = 51
= 17 × 3 (every real entry has exactly 3 scenarios — `bear`/`base`/`bull`, confirmed
`missing_scenarios_count: 0` above), i.e. each of the 17 collided version-entries also
collided on its 3 scenario upserts (`ON CONFLICT(projection_id, scenario_name)`).

### Field-level parity sample

**Coverage note on the brief's "3 legacy-shape + 3 missing-scenarios" requirement:** Task
2's dry run already found, and this task's real run re-confirms via `legacy_shape_count: 0`
and `missing_scenarios_count: 0` in the JSON output above, that **zero** of the 82 real
files/132 real entries use the legacy-top-level-only shape or have a missing/empty
`scenarios` block. Those two shapes exist only as synthetic test fixtures
(`LEGACY_ENTRY`, `NO_SCENARIOS_ENTRY` in `test_migrate_projections_to_sqlite.py`) — there
is no real ticker to sample for either category, so the brief's literal "3 + 3 real
tickers" instruction cannot be satisfied against real data without fabricating an example.
In place of those two categories, the sample below includes both real occurrences of the
**third, actually-observed edge-case shape** — `IONQ` and `QBTS`, the 2/132 entries with
both top-level and nested `aiThesis` fields — which is the real shape-diversity this
corpus actually contains.

Sample script (compares each ticker's **last array-entry** in its source JSON — the most
recently appended, mirroring the file's own append order — against the SQLite row for that
ticker+version, field by field):

```bash
python3 -c "
import json, sqlite3, pathlib, sys
sys.path.insert(0, 'investment_screener/backend/py_services')
from domain_model.migrate_projections_to_sqlite import parse_projection_entry
conn = sqlite3.connect('investment_screener/backend/data/domain_model.sqlite')
files = sorted(pathlib.Path('investment_screener/backend/data/projections').glob('*.json'))
sample = ['AAPL','ALAB','AMD','AMZN','ANET','AVGO','CAKE','CELH','EQIX','META','MSFT','NKE',
          'NVDA','OKLO','ORCL','SYM','IONQ','QBTS','TSLA','INTC','GOOG','RKLB','CRWD','PLTR']
for ticker in sample:
    f = pathlib.Path('investment_screener/backend/data/projections')/f'{ticker}.json'
    entries = json.loads(f.read_text())
    last = entries[-1] if isinstance(entries, list) else entries
    parsed = parse_projection_entry(last)
    row = conn.execute(
        'SELECT fair_value, action, version FROM projection_version pv '
        'JOIN investment i ON pv.investment_id=i.investment_id '
        'WHERE i.symbol=? AND pv.version=?', (ticker, parsed['version'])
    ).fetchone()
    match = row and row[0]==parsed['fair_value'] and row[1]==parsed['action'] and row[2]==parsed['version']
    print(ticker, parsed['version'], parsed['fair_value'], row[0], parsed['action'], row[1], match)
"
```

| Ticker | Version | Source fair_value | SQLite fair_value | Source action | SQLite action | Match |
|---|---|---|---|---|---|---|
| AAPL | 1 | 270.65 | 270.65 | HOLD | HOLD | Y |
| ALAB | 1 | 133.25 | 133.25 | SELL | SELL | Y |
| AMD | 5 | 352.63 | 352.63 | MAINTAIN | MAINTAIN | Y |
| AMZN | 1 | 347.8 | 347.8 | BUY | BUY | Y |
| ANET | 2 | 173.71 | 173.71 | INITIATE | INITIATE | Y |
| AVGO | 2 | 284.76 | 284.76 | INITIATE | INITIATE | Y |
| CAKE | 1 | 51.6 | 51.6 | SELL | SELL | Y |
| CELH | 1 | 19.02 | 19.02 | SELL | SELL | Y |
| EQIX | 2 | 883.71 | 883.71 | WATCHLIST | WATCHLIST | Y |
| META | 2 | 1105.3 | 1105.3 | INITIATE | INITIATE | Y |
| MSFT | 2 | 648.6 | 648.6 | BUY | BUY | Y |
| NKE | 1 | 46.13 | 46.13 | HOLD | HOLD | Y |
| NVDA | 3 | 445.16 | 445.16 | INITIATE | INITIATE | Y |
| OKLO | 2 | 6.65 | 6.65 | SELL | SELL | Y |
| ORCL | 1 | 261.88 | 261.88 | BUY | BUY | Y |
| SYM | 1 | 73.86 | 73.86 | BUY | BUY | Y |
| IONQ (both-shape) | 1 | 10.24 | 10.24 | SELL | SELL | Y |
| QBTS (both-shape) | 1 | 0.9 | 0.9 | SELL | SELL | Y |
| TSLA | 2 | 279.33 | 279.33 | SELL | SELL | Y |
| INTC | 10 | 62.35 | 62.35 | HOLD | HOLD | Y |
| GOOG | 3 | 517.98 | 517.98 | ACCUMULATE | ACCUMULATE | Y |
| RKLB | 1 | 12.92 | 12.92 | SELL | SELL | Y |
| CRWD | 3 | 155.22 | 155.22 | EXIT | EXIT | Y |
| PLTR | 2 | 147.06 | 147.06 | HOLD | HOLD | Y |

**Result: 24/24 sampled tickers matched exactly** (`fair_value`, `action`, and `version` all
identical between source JSON and SQLite row) — no discrepancies. This sample exceeds the
brief's 20-ticker minimum and includes both real both-shape tickers (IONQ, QBTS), verifying
the timestamp-precedence rule (IONQ's `10.24`, the newer top-level catalyst-corrected
value, not the stale `8.54` nested value) survived the real write unchanged.

As a stronger check beyond the required 20-ticker sample, the same comparison was also run
against **all 82 tickers** (last array-entry vs. its SQLite row): **82/82 matched, 0
mismatches.**

## Files migrated / versions migrated / scenarios migrated

- Files processed: 82
- `projection_version` insert/upsert calls made: 132 (132 succeeded, 0 errors)
- `projection_version` distinct rows in the real database: 115 (delta of 17 fully explained
  above)
- `projection_scenario` insert/upsert calls made: 396 (396 succeeded, 0 errors)
- `projection_scenario` distinct rows in the real database: 345 (delta of 51 = 17 × 3,
  same root cause)
- `investment` rows created: 82 (one per ticker)
- Errors encountered: **0** (`file_errors: []` in the real-run output, matching Task 2's
  dry run exactly)

## Source JSON files — confirmed untouched

```bash
git status --short investment_screener/backend/data/projections/
```
Output: **empty** (no output at all) — zero files under `projections/` were added,
modified, or deleted by this task. `git status --short` for the whole worktree shows only
two changes: the modified migration script and the new, previously-untracked
`domain_model.sqlite` file:
```
 M investment_screener/backend/py_services/domain_model/migrate_projections_to_sqlite.py
?? investment_screener/backend/data/domain_model.sqlite
```
`domain_model.sqlite` was also checked for stray `-wal`/`-shm` sidecar files left over
from `PRAGMA journal_mode=WAL`; none exist (the connection was closed cleanly via a
`try/finally`, which checkpoints and removes them).

## Self-review

- All numbers above are copied from real command output pasted into this file (the
  real-write JSON output, real `SELECT COUNT(*)` queries against the actual
  `domain_model.sqlite` file, and a real Python duplicate-version scan of the actual
  source files) — none are estimated.
- The 132-vs-115 delta has a real, verified explanation: 17 exact `(ticker, version)`
  collisions inside 16 source files (15 tickers with 1 collision, NVDA with 3), confirmed
  by directly counting duplicate `version` values in the raw JSON, not inferred.
  `projection_scenario`'s 396-vs-345 (51) delta is the same 17 collisions × 3 scenarios
  each.
- The field-level sample includes 24 tickers (exceeds the 20 minimum), and includes the 2
  real both-shape tickers (IONQ, QBTS) as the closest available real edge case — but does
  **not** include 3 legacy-shape-only or 3 missing-scenarios tickers, because zero such
  tickers exist in the real 82-file corpus (`legacy_shape_count: 0`,
  `missing_scenarios_count: 0`, confirmed both in Task 2's dry run and this task's real
  run). This is flagged explicitly above rather than silently substituted or ignored.
- `git status --short investment_screener/backend/data/projections/` is empty — confirmed
  zero source JSON files were modified or deleted by this task.

## Concerns for the reader

1. **The brief's literal "at least 3 legacy-shape + 3 missing-scenarios real tickers"
   sample requirement cannot be met** — the real corpus contains zero entries in either
   category (confirmed twice: Task 2's dry run and this task's real run both report
   `legacy_shape_count: 0` and `missing_scenarios_count: 0`). The sample instead
   demonstrates the real shape diversity that does exist (both-shape: IONQ, QBTS) and was
   expanded to 24 tickers, plus a full 82/82 all-ticker check, to compensate. Flagging this
   explicitly per the task's "explain negative check results" instruction rather than
   treating it as satisfied.
2. **No prior canonical path for `domain_model.sqlite` existed** in Wave 0 or Task 2 (both
   confirmed to use only `:memory:`) — this task chose
   `investment_screener/backend/data/domain_model.sqlite`, matching the brief's suggested
   fallback path and the sibling `investment_screener/backend/data/projections/` /
   `investment_screener/backend/data/research/` layout convention already in that
   directory. This choice should be confirmed as canonical before any later wave assumes
   it.
3. The 115/345 real row counts (vs. the more "obvious" 132/396 raw counts, which is what a
   reader skimming just the run's stdout JSON would see) is easy to misread as a bug if
   this report isn't read in full — future automation querying this database should query
   `projection_version`/`projection_scenario` directly (115/345), not assume the
   migration-report JSON's `total_versions`/`total_scenarios` fields equal final row
   counts.
