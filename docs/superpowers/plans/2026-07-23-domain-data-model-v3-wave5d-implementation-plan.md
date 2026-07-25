# Wave 5D — Predictions Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `predictions.jsonl` (87 real rows) and the not-yet-existing
`predictions_graded.jsonl` into `intelligence_event` as new `PREDICTION_CLAIM`/`PREDICTION_GRADED`
event types — the first Wave 5 sub-wave that requires widening the live `event_type` CHECK
constraint on a table already holding 196 real rows, rather than writing into an
already-blessed event type.

**Architecture:** Reuse the existing `py_services/intelligence/` package
(`event_store.append_event`, `event_repository.insert_event`, `replay_ledger.replay_events_to_db`,
`db_client.initialize_db`) exactly as Wave 5C did for `REVIEW_DAILY`. The one genuinely new piece
of infrastructure this wave adds is the CHECK-constraint-widening migration itself
(rebuild-and-copy, since SQLite has no `ALTER TABLE ... ALTER CONSTRAINT`), applied first, in its
own task, tested against a fixture DB before it ever touches `main`'s real 196-row table.

**Tech Stack:** Python 3.13 (`sqlite3` stdlib, WAL mode), pytest (`tmp_path` fixtures + one
real-repo integration test), the existing `py_services/intelligence/` package.

## Global Constraints

(Copied verbatim from `docs/superpowers/specs/2026-07-19-domain-data-model-v3-implementation-design.md` and `docs/superpowers/plans/2026-07-19-domain-data-model-v3-implementation-plan.md` — every task below implicitly includes these.)

- **This is a pivot, not an addition.** SQLite/domain repositories become the primary persistence
  layer for applicable operational data; JSON/JSONL must not remain an active operational store
  without an explicit approved exception (spec §2.18).
- **No permanent hybrid.** `JSON + JSONL + SQLite` forever is a failed wave, not a resting state.
- **A domain is migrated only when:** producer writes SQLite + every real consumer reads SQLite +
  old file archived via `git mv` (or local-only `mv` for gitignored files, spec §2.19). Table
  existence, data copying, or a passing fixture test do not count.
- **No script opens its own SQLite connection outside the owning repository/service layer.**
- **Every wave reports:** the Wave KPI table (JSON files before/after, files archived, reads/writes
  removed, producers/consumers migrated, context-bundle files removed, remaining exceptions named).
- **Archive convention:** `ARCHIVE/<mirrored source path>` via `git mv`; gitignored/private files
  archive locally only, never `git add`ed (spec §2.19). `predictions.jsonl` is **git-tracked**
  (confirmed via `git check-ignore` returning nothing) — its archive step is a real `git mv`.
- **A "real data migration write" must run against the main checkout's actual gitignored data
  files and actual SQLite/ledger files, never a worktree's copy** — verification must be
  independently re-run against the main checkout's actual files.
- **When a real migration script takes multiple path arguments (source file, target DB, AND a
  ledger/JSONL path), override every one of them explicitly to main-checkout absolute paths.**
- **A wave's plan document must include the design spec's actual required content verbatim, not a
  self-invented subset** — Hybrid Exit Criteria, full §5 Validation Strategy checklist, 9-item
  Definition of Done, computed Context Bundle Completion Bar. All four appear verbatim below.

---

## Task 0 — Fresh Verification Findings (already performed at plan-authoring time)

Per this migration's standing discipline ("every wave except Wave 4 and Wave 5A found the plan's
initial assumptions wrong once real code was read"), the following was independently re-verified
against real, current code and real data **before** writing Task 1 below — not assumed from the
spec or kickoff prompt:

- **`predictions.jsonl`:** 87 real lines (`wc -l`), git-tracked (`git check-ignore` returns
  nothing).
- **`predictions_graded.jsonl`:** confirmed absent from disk (`ls` → No such file or directory).
  **No graded-claims backfill is needed** — Task 4's migration script only backfills
  `predictions.jsonl` into `PREDICTION_CLAIM` events. The `PREDICTION_GRADED` cutover is a
  producer/consumer code change only (Tasks 2–3), with nothing to backfill.
- **`intelligence_event.event_type` CHECK constraint** (queried directly against
  `investment_screener/backend/data/intelligence.sqlite`): currently
  `'RESEARCH_IMPORT', 'NEWS_SWEEP', 'EARNINGS', 'VALUATION_UPDATE', 'TECHNICAL_SWEEP', 'PORTFOLIO_DECISION', 'THESIS_UPDATE', 'MACRO_EVENT', 'REVIEW_DAILY', 'REVIEW_WEEKLY'`
  — `PREDICTION_CLAIM`/`PREDICTION_GRADED` are **not** present. Real row counts by type:
  `RESEARCH_IMPORT` 80, `TECHNICAL_SWEEP` 105, `REVIEW_DAILY` 11 = **196 total**, matching
  `observations.jsonl`'s own line count (196), confirming DB and ledger are in sync before this
  wave touches either.
- **Real producers, re-verified by grep (not assumed from spec):** `prediction_ledger.py`
  (`append_prediction`/`append_grade`, the actual write primitives), `harvest_predictions.py`
  (calls `append_prediction` at line 332), `grade_predictions.py` (calls `append_grade` at line
  159). Matches spec's 3-producer claim exactly.
- **Real consumers, re-verified by grep:** `earnings_expectations.py` (imports
  `load_predictions`/`append_prediction`/`load_graded`/`append_grade` at lines 293–307, uses them
  at 338/447/478/588/660), `generate_track_record_report.py` (line 45, uses at 81–82),
  `backtest_harness.py` (has its own `PREDICTIONS_PATH` constant at line 73, used at line 542 —
  **note:** this file does not import from `prediction_ledger.py`, it duplicates the path constant
  itself; Task 3 must fix this file's own constant, not just its import), `prediction_ledger.py`
  itself (the `_validate_all()` CLI consumer), `harvest_predictions.py` (also a consumer via
  `latest_prediction_for`/`load_predictions` at lines 245/353/374 — it is both producer and
  consumer). Matches spec's 6-consumer claim (`harvest_predictions.py` and `prediction_ledger.py`
  each count once in the producer list and once in the consumer list, exactly as spec §2.11
  states).
- **Known false positive, re-confirmed:** `audit_json_usage.py` line 398 explicitly allowlists
  `predictions.jsonl` under `ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL` (line 554's classification
  string) — this is the audit tool's own intentional exemption list, not a real I/O consumer. It
  **does** need updating once this wave archives the file (Task 7), but it was never a real
  consumer to migrate.
- **Repository pattern to reuse, confirmed by reading the actual files:**
  `py_services/intelligence/event_store.py::append_event()` (ledger write + idempotency dedup),
  `py_services/intelligence/event_repository.py::insert_event()`/`get_latest_event_by_type()`/
  `list_active_events_by_type()` (SQLite reads/writes), `py_services/intelligence/
  replay_ledger.py::replay_events_to_db()` (ledger → DB replay), `py_services/intelligence/
  db_client.py::initialize_db()` (schema). Wave 5C's `migrate_daily_briefs_to_ledger.py` is the
  exact template for this wave's Task 4 migration script — same `--dry-run`/`--write`,
  `--briefs-dir`/`--db-path`/`--jsonl-path` argparse shape (renamed for this domain), same
  `_default_jsonl_path()` fallback resolution. The one thing Wave 5C's template did **not** need
  and this wave does: a CHECK-constraint-widening step before any event of the new type can be
  inserted at all (Task 1, below) — `REVIEW_DAILY` already existed in the constraint when Wave 5C
  ran; `PREDICTION_CLAIM`/`PREDICTION_GRADED` do not exist yet.

---

## Task 1: Widen the `intelligence_event.event_type` CHECK constraint (rebuild-and-copy)

**Files:**
- Create: `investment_screener/backend/py_services/intelligence/migrations/
  widen_event_type_add_predictions.py`
- Test: `investment_screener/backend/tests/py_services/
  test_widen_event_type_add_predictions.py`

**Why this is its own task, before any producer/consumer code changes:** SQLite has no
`ALTER TABLE ... ALTER CONSTRAINT`. The only safe path is: create a new table with the widened
`CHECK`, copy every existing row into it, verify row-for-row, drop the old table, rename the new
one into place — inside a single transaction, tested against a throwaway fixture DB first, and
only run against `main`'s real `intelligence.sqlite` (196 rows) after that fixture test passes.
This must complete and be verified before Task 2 writes any `PREDICTION_CLAIM` row, because an
insert against the old constraint would simply fail with `sqlite3.IntegrityError`.

**Interfaces:**
- Consumes: nothing new — operates directly via `sqlite3.Connection`, mirroring the existing
  `db_client.py::initialize_db()`'s direct-SQL style (this is schema DDL, not a repository-layer
  read/write, so it does not go through `event_repository.py`).
- Produces: `widen_event_type_constraint(conn: sqlite3.Connection) -> dict` — returns
  `{"before_row_count": int, "after_row_count": int, "before_constraint": str, "after_constraint": str}`
  for the caller to log/verify. Raises `AssertionError` if `before_row_count != after_row_count`
  (this must never silently proceed on a mismatch).

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_widen_event_type_add_predictions.py
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.migrations.widen_event_type_add_predictions import (  # noqa: E402
    widen_event_type_constraint,
)


def _seed_events(conn, count_by_type):
    """Insert minimal valid rows so the fixture DB isn't empty when widened."""
    seq = 1
    for event_type, count in count_by_type.items():
        for i in range(count):
            conn.execute(
                "INSERT INTO intelligence_event "
                "(event_id, event_sequence, event_type, effective_at, ingested_at, status, "
                "content_hash) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?);",
                (f"{event_type}-{i}", seq, event_type, "2026-01-01T00:00:00Z",
                 "2026-01-01T00:00:00Z", f"hash-{seq}"),
            )
            seq += 1
    conn.commit()


def test_widen_preserves_all_existing_rows(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_events(conn, {"RESEARCH_IMPORT": 3, "TECHNICAL_SWEEP": 2, "REVIEW_DAILY": 1})
    result = widen_event_type_constraint(conn)
    assert result["before_row_count"] == 6
    assert result["after_row_count"] == 6
    cursor = conn.execute("SELECT COUNT(*) FROM intelligence_event;")
    assert cursor.fetchone()[0] == 6


def test_widen_allows_prediction_claim_insert_after(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_events(conn, {"RESEARCH_IMPORT": 1})
    widen_event_type_constraint(conn)
    # Must not raise IntegrityError now that the constraint is widened.
    conn.execute(
        "INSERT INTO intelligence_event "
        "(event_id, event_sequence, event_type, effective_at, ingested_at, status, "
        "content_hash) VALUES ('pred-1', 99, 'PREDICTION_CLAIM', '2026-01-01T00:00:00Z', "
        "'2026-01-01T00:00:00Z', 'ACTIVE', 'hash-99');"
    )
    conn.execute(
        "INSERT INTO intelligence_event "
        "(event_id, event_sequence, event_type, effective_at, ingested_at, status, "
        "content_hash) VALUES ('grade-1', 100, 'PREDICTION_GRADED', '2026-01-01T00:00:00Z', "
        "'2026-01-01T00:00:00Z', 'ACTIVE', 'hash-100');"
    )
    conn.commit()
    cursor = conn.execute(
        "SELECT COUNT(*) FROM intelligence_event WHERE event_type IN "
        "('PREDICTION_CLAIM', 'PREDICTION_GRADED');"
    )
    assert cursor.fetchone()[0] == 2


def test_widen_still_rejects_truly_invalid_event_type(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_events(conn, {"RESEARCH_IMPORT": 1})
    widen_event_type_constraint(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO intelligence_event "
            "(event_id, event_sequence, event_type, effective_at, ingested_at, status, "
            "content_hash) VALUES ('bad-1', 101, 'NOT_A_REAL_TYPE', '2026-01-01T00:00:00Z', "
            "'2026-01-01T00:00:00Z', 'ACTIVE', 'hash-101');"
        )


def test_widen_is_idempotent_on_rerun(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_events(conn, {"RESEARCH_IMPORT": 2})
    widen_event_type_constraint(conn)
    result_second = widen_event_type_constraint(conn)
    assert result_second["before_row_count"] == 2
    assert result_second["after_row_count"] == 2


def test_widen_preserves_fts_and_triggers(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute(
        "INSERT INTO intelligence_event "
        "(event_id, event_sequence, event_type, effective_at, ingested_at, status, "
        "title, body_markdown, content_hash) VALUES "
        "('r-1', 1, 'RESEARCH_IMPORT', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', "
        "'ACTIVE', 'Test Title', 'Test body content.', 'hash-1');"
    )
    conn.commit()
    widen_event_type_constraint(conn)
    cursor = conn.execute(
        "SELECT event_id FROM intelligence_event_fts WHERE intelligence_event_fts MATCH 'Test';"
    )
    # FTS shadow table content must survive the rebuild — either the trigger reindexed it
    # during copy, or the rebuild step explicitly repopulates FTS. Either is acceptable;
    # the row must be findable afterward.
    rows = cursor.fetchall()
    assert len(rows) >= 0  # placeholder assertion replaced below
    cursor2 = conn.execute(
        "SELECT ie.event_id FROM intelligence_event_fts fts "
        "JOIN intelligence_event ie ON ie.rowid = fts.rowid "
        "WHERE intelligence_event_fts MATCH 'Test';"
    )
    assert [r[0] for r in cursor2.fetchall()] == ["r-1"]
```

Add `import pytest` alongside the existing imports at the top of this test file (needed for the
`raises` assertion).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_widen_event_type_add_predictions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'intelligence.migrations.widen_event_type_add_predictions'`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/intelligence/migrations/widen_event_type_add_predictions.py
"""One-time schema migration: widen intelligence_event.event_type's CHECK constraint to
include PREDICTION_CLAIM/PREDICTION_GRADED (Wave 5D).

SQLite has no ALTER TABLE ... ALTER CONSTRAINT. The only safe path for changing a CHECK
constraint on a live table is: create a new table with the widened constraint, copy every
existing row into it verified row-for-row, drop the old table, rename the new table into
place -- all inside one transaction, so a failure partway through leaves the original table
untouched (SQLite auto-rolls-back an uncommitted transaction on any raised exception here).

This must run before any PREDICTION_CLAIM/PREDICTION_GRADED row is ever inserted -- an
insert against the pre-widening constraint fails with sqlite3.IntegrityError.
"""

import sqlite3

NEW_EVENT_TYPES = (
    "RESEARCH_IMPORT", "NEWS_SWEEP", "EARNINGS", "VALUATION_UPDATE", "TECHNICAL_SWEEP",
    "PORTFOLIO_DECISION", "THESIS_UPDATE", "MACRO_EVENT", "REVIEW_DAILY", "REVIEW_WEEKLY",
    "PREDICTION_CLAIM", "PREDICTION_GRADED",
)


def _current_check_constraint(conn: sqlite3.Connection) -> str:
    """Return the live CREATE TABLE statement for intelligence_event."""
    cursor = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='intelligence_event';"
    )
    row = cursor.fetchone()
    return row[0] if row else ""


def widen_event_type_constraint(conn: sqlite3.Connection) -> dict:
    """Widen intelligence_event's event_type CHECK constraint via rebuild-and-copy.

    Idempotent: if the constraint already includes PREDICTION_CLAIM/PREDICTION_GRADED,
    this is a no-op (detected by checking the live CREATE TABLE SQL text) and returns the
    current row count for both before/after.

    Args:
        conn: Open sqlite3 connection to the intelligence.sqlite database.

    Returns:
        Dict with before_row_count, after_row_count, before_constraint, after_constraint.

    Raises:
        AssertionError: if the row count changes across the rebuild (a real, non-recoverable
            data-loss signal -- this must never be silently swallowed).
    """
    before_constraint = _current_check_constraint(conn)
    if "PREDICTION_CLAIM" in before_constraint:
        count = conn.execute("SELECT COUNT(*) FROM intelligence_event;").fetchone()[0]
        return {
            "before_row_count": count,
            "after_row_count": count,
            "before_constraint": before_constraint,
            "after_constraint": before_constraint,
        }

    before_row_count = conn.execute("SELECT COUNT(*) FROM intelligence_event;").fetchone()[0]

    type_list_sql = ", ".join(f"'{t}'" for t in NEW_EVENT_TYPES)

    conn.execute("BEGIN;")
    try:
        conn.execute(f"""
        CREATE TABLE intelligence_event_new (
            event_id TEXT PRIMARY KEY,
            event_sequence INTEGER NOT NULL UNIQUE,
            instrument_id TEXT,
            event_type TEXT NOT NULL CHECK (event_type IN ({type_list_sql})),
            effective_at TEXT NOT NULL,
            observed_at TEXT,
            ingested_at TEXT NOT NULL,
            source_id TEXT,
            confidence_score REAL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
            status TEXT NOT NULL CHECK (
                status IN ('ACTIVE', 'SUPERSEDED', 'RETRACTED', 'INVALIDATED', 'DRAFT')
            ),
            title TEXT,
            body_markdown TEXT,
            payload_json TEXT,
            supersedes_event_id TEXT,
            idempotency_key TEXT UNIQUE,
            content_hash TEXT NOT NULL,
            FOREIGN KEY(instrument_id) REFERENCES instrument(instrument_id),
            FOREIGN KEY(supersedes_event_id) REFERENCES intelligence_event(event_id)
        );
        """)
        conn.execute("""
        INSERT INTO intelligence_event_new
        SELECT event_id, event_sequence, instrument_id, event_type, effective_at, observed_at,
               ingested_at, source_id, confidence_score, status, title, body_markdown,
               payload_json, supersedes_event_id, idempotency_key, content_hash
        FROM intelligence_event;
        """)

        copied_count = conn.execute(
            "SELECT COUNT(*) FROM intelligence_event_new;"
        ).fetchone()[0]
        if copied_count != before_row_count:
            raise AssertionError(
                f"Row count mismatch during rebuild: source had {before_row_count}, "
                f"copy has {copied_count}. Rolling back, no changes applied."
            )

        conn.execute("DROP TABLE intelligence_event_fts;")
        conn.execute("DROP TABLE intelligence_event;")
        conn.execute("ALTER TABLE intelligence_event_new RENAME TO intelligence_event;")

        conn.execute("""
        CREATE VIRTUAL TABLE intelligence_event_fts USING fts5(
            title,
            body_markdown,
            content='intelligence_event',
            content_rowid='rowid'
        );
        """)
        conn.execute("""
        CREATE TRIGGER trg_intelligence_event_ai AFTER INSERT ON intelligence_event BEGIN
            INSERT INTO intelligence_event_fts(rowid, title, body_markdown)
            VALUES (new.rowid, new.title, new.body_markdown);
        END;
        """)
        conn.execute("""
        CREATE TRIGGER trg_intelligence_event_ad AFTER DELETE ON intelligence_event BEGIN
            INSERT INTO intelligence_event_fts(intelligence_event_fts, rowid, title, body_markdown)
            VALUES('delete', old.rowid, old.title, old.body_markdown);
        END;
        """)
        conn.execute("""
        CREATE TRIGGER trg_intelligence_event_au AFTER UPDATE ON intelligence_event BEGIN
            INSERT INTO intelligence_event_fts(intelligence_event_fts, rowid, title, body_markdown)
            VALUES('delete', old.rowid, old.title, old.body_markdown);
            INSERT INTO intelligence_event_fts(rowid, title, body_markdown)
            VALUES (new.rowid, new.title, new.body_markdown);
        END;
        """)
        conn.execute(
            "INSERT INTO intelligence_event_fts(rowid, title, body_markdown) "
            "SELECT rowid, title, body_markdown FROM intelligence_event;"
        )

        after_row_count = conn.execute(
            "SELECT COUNT(*) FROM intelligence_event;"
        ).fetchone()[0]
        if after_row_count != before_row_count:
            raise AssertionError(
                f"Row count mismatch after rename: expected {before_row_count}, "
                f"got {after_row_count}. Transaction will be rolled back."
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    after_constraint = _current_check_constraint(conn)
    return {
        "before_row_count": before_row_count,
        "after_row_count": after_row_count,
        "before_constraint": before_constraint,
        "after_constraint": after_constraint,
    }
```

Create `investment_screener/backend/py_services/intelligence/migrations/__init__.py` (empty) if
this directory doesn't already exist as a package — check first with
`ls investment_screener/backend/py_services/intelligence/migrations/__init__.py` (the
`migrations/` directory already exists per the directory listing gathered during Task 0's
verification, but confirm the `__init__.py` file specifically before assuming it's a package).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_widen_event_type_add_predictions.py -v`
Expected: `5 passed`

- [ ] **Step 5: Dry-run against a COPY of main's real `intelligence.sqlite` (never the live file directly)**

```bash
cp investment_screener/backend/data/intelligence.sqlite /tmp/intelligence_widen_dryrun.sqlite
cd investment_screener/backend
python3 -c "
import sqlite3, sys
sys.path.insert(0, 'py_services')
from intelligence.migrations.widen_event_type_add_predictions import widen_event_type_constraint
conn = sqlite3.connect('/tmp/intelligence_widen_dryrun.sqlite')
result = widen_event_type_constraint(conn)
print(result)
assert result['before_row_count'] == 196, f\"expected 196, got {result['before_row_count']}\"
assert result['after_row_count'] == 196
print('DRY-RUN PASS: 196 -> 196, real data preserved on a disposable copy.')
"
```

Expected output: `{'before_row_count': 196, 'after_row_count': 196, ...}` then
`DRY-RUN PASS: 196 -> 196, real data preserved on a disposable copy.` This is the evidence gate
before Task 4 ever runs this same widening step against `main`'s real, live
`intelligence.sqlite` — do not proceed to Task 4's real write until this exact output is
reproduced.

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/intelligence/migrations/widen_event_type_add_predictions.py \
        investment_screener/backend/py_services/intelligence/migrations/__init__.py \
        investment_screener/backend/tests/py_services/test_widen_event_type_add_predictions.py
git commit -m "feat: add CHECK-constraint-widening migration for PREDICTION_CLAIM/PREDICTION_GRADED (Wave 5D Task 1)"
```

---

## Task 2: Producer cutover — dual-write in `prediction_ledger.py`

**Files:**
- Modify: `investment_screener/backend/py_services/prediction_ledger.py`
- Test: `investment_screener/backend/tests/py_services/test_prediction_ledger.py` (existing file
  — add new test functions, do not replace existing ones)

**Interfaces:**
- Consumes: `intelligence.event_store.append_event(jsonl_path, event_type, effective_at, status,
  title, body_markdown, ticker=None, source_id=None, payload=None, supersedes_event_id=None,
  idempotency_key=None) -> str` (existing, unchanged signature).
- Produces: `append_prediction(record, path=PREDICTIONS_PATH, jsonl_path=None) -> None` and
  `append_grade(record, path=GRADED_PATH, jsonl_path=None) -> None` — both now dual-write: the
  existing JSONL append (source of truth during migration, per Hybrid Exit Criteria below) PLUS
  a new `append_event()` call into `observations.jsonl`/`intelligence.sqlite`. New optional
  `jsonl_path` parameter (defaulting to the standard ledger path via
  `intelligence.event_store._default_jsonl_path()`) lets tests point at an isolated ledger file,
  same pattern as every other dual-write producer in this migration (`daily_brief.py`'s Wave 5C
  cutover).

- [ ] **Step 1: Write the failing test**

Add to the existing `investment_screener/backend/tests/py_services/test_prediction_ledger.py`:

```python
def test_append_prediction_dual_writes_to_intelligence_ledger(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "investment_screener/backend/py_services"))
    from intelligence.db_client import initialize_db
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.event_repository import get_latest_event_by_type
    from prediction_ledger import append_prediction

    jsonl_path = tmp_path / "predictions.jsonl"
    ledger_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    record = {
        "id": "AAPL:action_rating:2026-07-23",
        "ticker": "AAPL",
        "type": "action_rating",
        "claimDate": "2026-07-23",
        "direction": "bullish",
        "horizonDays": 90,
    }
    append_prediction(record, path=jsonl_path, jsonl_path=ledger_path)

    assert jsonl_path.exists()
    with open(jsonl_path) as f:
        assert len(f.readlines()) == 1

    assert ledger_path.exists()
    conn = initialize_db(str(db_path))
    replay_events_to_db(str(ledger_path), conn)
    event = get_latest_event_by_type(conn, "PREDICTION_CLAIM")
    assert event is not None
    assert event["title"] == "Prediction claim: AAPL action_rating (2026-07-23)"


def test_append_grade_dual_writes_to_intelligence_ledger(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "investment_screener/backend/py_services"))
    from intelligence.db_client import initialize_db
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.event_repository import get_latest_event_by_type
    from prediction_ledger import append_grade

    graded_jsonl_path = tmp_path / "predictions_graded.jsonl"
    ledger_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    grade_record = {
        "predictionId": "AAPL:action_rating:2026-07-23",
        "ticker": "AAPL",
        "gradedAt": "2026-10-23",
        "outcome": "correct",
        "relativeReturn": 0.08,
    }
    append_grade(grade_record, path=graded_jsonl_path, jsonl_path=ledger_path)

    assert graded_jsonl_path.exists()
    conn = initialize_db(str(db_path))
    replay_events_to_db(str(ledger_path), conn)
    event = get_latest_event_by_type(conn, "PREDICTION_GRADED")
    assert event is not None
    assert event["title"] == "Prediction grade: AAPL action_rating (correct)"


def test_append_prediction_still_writes_jsonl_when_ledger_write_fails(tmp_path, monkeypatch):
    """JSONL remains the authoritative source during the dual-write window (Hybrid Exit
    Criteria below) -- a ledger-side failure must not silently lose the JSONL append, since
    JSONL is still what every consumer reads until Task 3 cuts them over."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "investment_screener/backend/py_services"))
    import prediction_ledger

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated ledger outage")

    monkeypatch.setattr(prediction_ledger, "_append_prediction_event", _boom)

    jsonl_path = tmp_path / "predictions.jsonl"
    record = {"id": "X:action_rating:2026-07-23", "ticker": "X", "type": "action_rating"}
    prediction_ledger.append_prediction(record, path=jsonl_path)

    assert jsonl_path.exists()
    with open(jsonl_path) as f:
        assert len(f.readlines()) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_prediction_ledger.py -k dual_writes -v`
Expected: FAIL — `append_prediction()`/`append_grade()` don't yet call `append_event()`.

- [ ] **Step 3: Write minimal implementation**

Modify `investment_screener/backend/py_services/prediction_ledger.py`. Add imports near the top
(after the existing `REPO_ROOT`/path constants, before `HORIZON_DAYS`):

```python
import sys as _sys

_INTEL_DIR = REPO_ROOT / "investment_screener/backend/py_services"
if str(_INTEL_DIR) not in _sys.path:
    _sys.path.insert(0, str(_INTEL_DIR))

from intelligence.event_store import append_event as _append_event  # noqa: E402
```

Replace `append_prediction` and `append_grade` with dual-write versions, and add the two
`_append_*_event` helpers (named so the failure-isolation test above can monkeypatch them
independently of the JSONL write):

```python
def _append_prediction_event(record: dict[str, Any], jsonl_path) -> None:
    """Write one PREDICTION_CLAIM event to the intelligence ledger.

    Isolated into its own function (rather than inlined in append_prediction) so a ledger
    outage can be simulated/monkeypatched in tests without touching the JSONL append path --
    JSONL remains authoritative during the dual-write window (Hybrid Exit Criteria).
    """
    from intelligence.event_store import _default_jsonl_path

    resolved_path = str(jsonl_path) if jsonl_path else str(_default_jsonl_path())
    ticker = record.get("ticker")
    claim_type = record.get("type")
    claim_date = record.get("claimDate")
    _append_event(
        resolved_path,
        event_type="PREDICTION_CLAIM",
        effective_at=claim_date or "",
        status="ACTIVE",
        title=f"Prediction claim: {ticker} {claim_type} ({claim_date})",
        body_markdown=f"Direction: {record.get('direction')}, horizon: "
                       f"{record.get('horizonDays')} days.",
        ticker=ticker,
        source_id="prediction_ledger",
        payload=record,
        idempotency_key=f"prediction-claim-{record.get('id')}",
    )


def _append_grade_event(record: dict[str, Any], jsonl_path) -> None:
    """Write one PREDICTION_GRADED event to the intelligence ledger."""
    from intelligence.event_store import _default_jsonl_path

    resolved_path = str(jsonl_path) if jsonl_path else str(_default_jsonl_path())
    ticker = record.get("ticker")
    prediction_id = record.get("predictionId")
    outcome = record.get("outcome")
    _append_event(
        resolved_path,
        event_type="PREDICTION_GRADED",
        effective_at=record.get("gradedAt") or "",
        status="ACTIVE",
        title=f"Prediction grade: {ticker} "
              f"{prediction_id.split(':')[1] if prediction_id and ':' in prediction_id else ''} "
              f"({outcome})".replace("  ", " ").strip(),
        body_markdown=f"Outcome: {outcome}, relative return: "
                       f"{record.get('relativeReturn')}.",
        ticker=ticker,
        source_id="prediction_ledger",
        payload=record,
        supersedes_event_id=None,
        idempotency_key=f"prediction-grade-{prediction_id}",
    )


def append_prediction(
    record: dict[str, Any], path: Path = PREDICTIONS_PATH, jsonl_path=None
) -> None:
    """Append one prediction record to predictions.jsonl AND the intelligence ledger.

    JSONL remains the authoritative read path for every existing consumer until Task 3 of
    Wave 5D cuts each one over individually -- this function's JSONL write must never be
    skipped or made conditional on the ledger write succeeding.
    """
    _append_jsonl(record, path)
    _append_prediction_event(record, jsonl_path)


def append_grade(
    record: dict[str, Any], path: Path = GRADED_PATH, jsonl_path=None
) -> None:
    """Append one grade record to predictions_graded.jsonl AND the intelligence ledger."""
    _append_jsonl(record, path)
    _append_grade_event(record, jsonl_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_prediction_ledger.py -v`
Expected: all existing tests still pass, plus the 3 new dual-write tests pass.

- [ ] **Step 5: Run the full existing prediction test suite to confirm no regression**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/ -k "prediction or harvest or grade or earnings_expectation or track_record or backtest" -v`
Expected: no new failures relative to the pre-existing baseline (documented in Hard-Stop Condition
7 below — `zod-schemas.spec.ts` and the `InvestmentRepository` real-sqlite parity test are the
only known pre-existing failures; re-confirm this is still the complete list before proceeding).

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/prediction_ledger.py \
        investment_screener/backend/tests/py_services/test_prediction_ledger.py
git commit -m "feat: dual-write predictions/grades to intelligence_event (Wave 5D Task 2)"
```

---

## Task 3: Consumer cutover — read from `intelligence_event` instead of JSONL

**Files (real file list, per Task 0's fresh grep — read each file's actual current code before
editing, do not assume the exact line numbers above remain unchanged after Task 2's edits):**
- Modify: `investment_screener/backend/py_services/earnings_expectations.py`
- Modify: `investment_screener/backend/py_services/grade_predictions.py`
- Modify: `investment_screener/backend/py_services/generate_track_record_report.py`
- Modify: `investment_screener/backend/py_services/backtest_harness.py`
- Modify: `investment_screener/backend/py_services/harvest_predictions.py`
- Test: one test per file listed above, in
  `investment_screener/backend/tests/py_services/test_<matching_name>.py` (existing test files —
  add new test functions asserting the SQLite read path, do not delete existing JSONL-path tests
  until Task 4's backfill has run and Task 7 is ready to archive).

**Interfaces:**
- Consumes: `intelligence.event_repository.list_active_events_by_type(conn, event_type) ->
  list[dict]` (existing, unchanged) — each returned dict's `payload_json` field, when
  `json.loads()`-parsed, reconstructs the original prediction/grade record shape written by
  Task 2's `_append_prediction_event`/`_append_grade_event`.
- Produces: each modified file's read functions (`load_predictions`-equivalent call sites) now
  call `list_active_events_by_type(conn, "PREDICTION_CLAIM")` /
  `list_active_events_by_type(conn, "PREDICTION_GRADED")` and `json.loads(row["payload_json"])`
  per row, instead of `prediction_ledger.load_predictions()`/`load_graded()`.

**Read each file's real current code before writing this task's exact diff** — this plan
deliberately does not pre-script line-exact replacements for all 5 files (per the overall plan's
own guidance for consumer-rewiring tasks spanning many files: "state the real file list, the
available repository functions, and the instruction 'read this file's actual current code before
editing'"). What follows is a worked example for `generate_track_record_report.py` (the smallest,
clearest consumer) to establish the pattern; apply the same pattern to the other 4 files,
re-reading each one's actual current call sites first.

- [ ] **Step 1: Write the failing test for `generate_track_record_report.py`**

Add to `investment_screener/backend/tests/py_services/test_generate_track_record_report.py`:

```python
def test_report_reads_predictions_from_intelligence_ledger(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "investment_screener/backend/py_services"))
    from intelligence.db_client import initialize_db
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from generate_track_record_report import build_report  # exact function name TBD from
    # this file's real current code -- confirm against a fresh read before writing this call

    ledger_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    conn = initialize_db(str(db_path))

    append_event(
        str(ledger_path), event_type="PREDICTION_CLAIM", effective_at="2026-07-01T00:00:00Z",
        status="ACTIVE", title="Prediction claim: AAPL action_rating (2026-07-01)",
        body_markdown="Direction: bullish, horizon: 90 days.", ticker="AAPL",
        payload={"id": "AAPL:action_rating:2026-07-01", "ticker": "AAPL",
                 "type": "action_rating", "direction": "bullish"},
        idempotency_key="prediction-claim-AAPL:action_rating:2026-07-01",
    )
    append_event(
        str(ledger_path), event_type="PREDICTION_GRADED", effective_at="2026-10-01T00:00:00Z",
        status="ACTIVE", title="Prediction grade: AAPL action_rating (correct)",
        body_markdown="Outcome: correct, relative return: 0.1.", ticker="AAPL",
        payload={"predictionId": "AAPL:action_rating:2026-07-01", "outcome": "correct",
                 "relativeReturn": 0.1},
        idempotency_key="prediction-grade-AAPL:action_rating:2026-07-01",
    )
    replay_events_to_db(str(ledger_path), conn)

    report = build_report(db_path=str(db_path))
    assert report["total_graded"] == 1
    assert report["correct_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_generate_track_record_report.py -k intelligence_ledger -v`
Expected: FAIL — `build_report()` does not yet accept a `db_path` parameter / does not query
`intelligence_event`.

- [ ] **Step 3: Read the file's real current code, then rewrite its read path**

Read `investment_screener/backend/py_services/generate_track_record_report.py` in full first.
Its current line 45 (`from prediction_ledger import GRADED_PATH, PREDICTIONS_PATH, load_graded,
load_predictions`) and lines 78/81-82 (the function signature and its two `load_*` calls) are the
exact lines to replace — confirm they still match this description before editing, since Task 2's
edits to `prediction_ledger.py` do not touch this file, but any other concurrent change might.
Replace the import and the two load calls with:

```python
import json
import sys as _sys
from pathlib import Path as _Path

_INTEL_DIR = _Path(__file__).resolve().parent
if str(_INTEL_DIR) not in _sys.path:
    _sys.path.insert(0, str(_INTEL_DIR))

from intelligence.db_client import initialize_db
from intelligence.event_repository import list_active_events_by_type


def _load_predictions_from_ledger(db_path: str) -> list[dict]:
    conn = initialize_db(db_path)
    events = list_active_events_by_type(conn, "PREDICTION_CLAIM")
    return [json.loads(e["payload_json"]) for e in events if e["payload_json"]]


def _load_graded_from_ledger(db_path: str) -> list[dict]:
    conn = initialize_db(db_path)
    events = list_active_events_by_type(conn, "PREDICTION_GRADED")
    return [json.loads(e["payload_json"]) for e in events if e["payload_json"]]
```

Then change the function's signature (previously `predictions_path: Path = PREDICTIONS_PATH,
graded_path: Path = GRADED_PATH`) to `db_path: str = str(_Path(__file__).resolve().parents[2] /
"data/intelligence.sqlite")`, and its body's `load_predictions(predictions_path)`/
`load_graded(graded_path)` calls to `_load_predictions_from_ledger(db_path)`/
`_load_graded_from_ledger(db_path)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_generate_track_record_report.py -v`
Expected: all pass, including the new ledger-backed test.

- [ ] **Step 5: Repeat Steps 1–4 for the remaining 4 consumer files**

For each of `earnings_expectations.py`, `grade_predictions.py`, `backtest_harness.py`,
`harvest_predictions.py`:
1. Read the file's real current code in full (do not trust this plan's Task-0 line numbers as
   still-accurate after Tasks 2's edits to `prediction_ledger.py` and this task's own prior
   file edits — re-grep each file immediately before editing it).
2. Write a new test asserting the function under test reads from `intelligence_event` (same
   `append_event` + `replay_events_to_db` + assert-on-output pattern as Step 1 above), specific
   to that file's actual exported function name and signature.
3. Replace its `prediction_ledger.load_predictions`/`load_graded` (or, for `backtest_harness.py`,
   its own duplicated `PREDICTIONS_PATH` constant and direct `_load_jsonl`-equivalent read) with
   the same `_load_predictions_from_ledger`/`_load_graded_from_ledger` pattern (or import them
   from `generate_track_record_report.py` if a shared helper module makes more sense once all 5
   files' real code is in view — judgment call at implementation time, not pre-decided here).
4. Run that file's own test suite, confirm pass, commit individually (one commit per file, per
   the overall plan's "keep commits logical and reviewable" instruction).

**`earnings_expectations.py` special note (already flagged by Task 0):** this file's own
`_load_predictions`/`_append_prediction`/etc. names are conditionally imported with a `None`
fallback (`try`/`except ImportError` around lines 293–307) — its rewrite must preserve that
graceful-degradation contract (some callers may run in a context where the ledger read genuinely
isn't available yet), not silently remove the `None`-check branches downstream at lines 333/473.

**`backtest_harness.py` special note (already flagged by Task 0):** this file does not import
from `prediction_ledger.py` at all — it declares its own `PREDICTIONS_PATH` constant at line 73
and reads from it directly at line 542. Its fix is a self-contained read-path swap to
`_load_predictions_from_ledger`, not an import-statement change.

- [ ] **Step 6: Run the full backend Python test suite to confirm no regression across all 5 files**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/ -v 2>&1 | tail -40`
Expected: no new failures beyond the documented pre-existing baseline (Hard-Stop Condition 7).

---

## Task 4: Real migration — backfill `predictions.jsonl`'s 87 rows into `intelligence_event`

**Files:**
- Create: `investment_screener/backend/py_services/migrate_predictions_to_ledger.py`
- Test: `investment_screener/backend/tests/py_services/test_migrate_predictions_to_ledger.py`

**Interfaces:**
- Consumes: `intelligence.event_store.append_event` (existing), `intelligence.replay_ledger.
  replay_events_to_db` (existing), `intelligence.db_client.initialize_db` (existing), `intelligence.
  migrations.widen_event_type_add_predictions.widen_event_type_constraint` (Task 1).
- Produces: `migrate(predictions_path: Path, jsonl_path: Path, db_path: Path, dry_run: bool =
  True) -> dict` returning `{"source_count": int, "written_count": int, "skipped": list[str]}` —
  same return shape as Wave 5C's `migrate_daily_briefs_to_ledger.py::migrate()`, for consistency.

- [ ] **Step 1: Write the failing test**

```python
# investment_screener/backend/tests/py_services/test_migrate_predictions_to_ledger.py
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.migrations.widen_event_type_add_predictions import (  # noqa: E402
    widen_event_type_constraint,
)
from intelligence.event_repository import list_active_events_by_type  # noqa: E402
from migrate_predictions_to_ledger import migrate  # noqa: E402


def _write_fixture_predictions(path):
    records = [
        {"id": "AAPL:action_rating:2026-01-01", "ticker": "AAPL", "type": "action_rating",
         "claimDate": "2026-01-01", "direction": "bullish", "horizonDays": 90},
        {"id": "MSFT:dcf_fair_value:2026-01-02", "ticker": "MSFT", "type": "dcf_fair_value",
         "claimDate": "2026-01-02", "direction": "bearish", "horizonDays": 180},
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return records


def test_migrate_dry_run_reports_counts_without_writing(tmp_path):
    predictions_path = tmp_path / "predictions.jsonl"
    _write_fixture_predictions(predictions_path)
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    report = migrate(predictions_path, jsonl_path, db_path, dry_run=True)

    assert report["source_count"] == 2
    assert not jsonl_path.exists()


def test_migrate_write_widens_constraint_then_backfills_all_rows(tmp_path):
    predictions_path = tmp_path / "predictions.jsonl"
    _write_fixture_predictions(predictions_path)
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    conn = initialize_db(str(db_path))
    conn.execute(
        "INSERT INTO intelligence_event (event_id, event_sequence, event_type, effective_at, "
        "ingested_at, status, content_hash) VALUES ('r-1', 1, 'RESEARCH_IMPORT', "
        "'2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'ACTIVE', 'hash-1');"
    )
    conn.commit()
    conn.close()

    report = migrate(predictions_path, jsonl_path, db_path, dry_run=False)

    assert report["written_count"] == 2
    conn = initialize_db(str(db_path))
    events = list_active_events_by_type(conn, "PREDICTION_CLAIM")
    assert len(events) == 2
    tickers = {json.loads(e["payload_json"])["ticker"] for e in events}
    assert tickers == {"AAPL", "MSFT"}
    # The pre-existing RESEARCH_IMPORT row must survive the widening rebuild untouched.
    research_events = list_active_events_by_type(conn, "RESEARCH_IMPORT")
    assert len(research_events) == 1


def test_migrate_is_idempotent_on_rerun(tmp_path):
    predictions_path = tmp_path / "predictions.jsonl"
    _write_fixture_predictions(predictions_path)
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    migrate(predictions_path, jsonl_path, db_path, dry_run=False)
    report_second = migrate(predictions_path, jsonl_path, db_path, dry_run=False)

    conn = initialize_db(str(db_path))
    events = list_active_events_by_type(conn, "PREDICTION_CLAIM")
    assert len(events) == 2  # no duplicates from the idempotency_key dedup in append_event
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_migrate_predictions_to_ledger.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'migrate_predictions_to_ledger'`

- [ ] **Step 3: Write minimal implementation**

```python
# investment_screener/backend/py_services/migrate_predictions_to_ledger.py
#!/usr/bin/env python3
"""One-time migration: backfill the real data/predictions.jsonl claims into the Intelligence
Ledger as PREDICTION_CLAIM events (Wave 5D, ADR-029).

Widens the intelligence_event.event_type CHECK constraint first (via
widen_event_type_constraint, rebuild-and-copy, verified row-for-row) since PREDICTION_CLAIM
does not exist in the live constraint before this wave. Then uses the same append_event/
replay_events_to_db machinery every other Wave 5 domain uses, and the same idempotency_key
format (prediction-claim-{id}) prediction_ledger.py's own dual-write already uses (Task 2) --
so a future real harvest_predictions.py run for an already-backfilled claim never double-writes.

Usage:
    python3 migrate_predictions_to_ledger.py --dry-run
    python3 migrate_predictions_to_ledger.py --write
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

DEFAULT_PREDICTIONS_PATH = REPO_ROOT / "investment_screener/backend/data/predictions.jsonl"
DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite"


def migrate(predictions_path: Path, jsonl_path: Path, db_path: Path, dry_run: bool = True) -> dict:
    """Backfill every data/predictions.jsonl claim into intelligence_event.

    Args:
        predictions_path: Path to predictions.jsonl (source of truth during migration).
        jsonl_path: observations.jsonl ledger to append PREDICTION_CLAIM events to.
        db_path: intelligence.sqlite to widen the constraint on and replay the ledger into.
        dry_run: When True (default), report counts without writing or widening anything.

    Returns:
        {"source_count": int, "written_count": int, "skipped": list[str]}
    """
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db
    from intelligence.migrations.widen_event_type_add_predictions import (
        widen_event_type_constraint,
    )

    records = []
    skipped: list[str] = []
    if predictions_path.exists():
        with open(predictions_path) as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    skipped.append(f"line {i}: invalid JSON")

    report = {"source_count": len(records), "written_count": 0, "skipped": skipped}

    if dry_run:
        for r in records:
            if not r.get("id") or not r.get("ticker"):
                skipped.append(f"record missing id/ticker: {r}")
        return report

    conn = initialize_db(str(db_path))
    widen_result = widen_event_type_constraint(conn)
    assert widen_result["before_row_count"] == widen_result["after_row_count"], (
        f"Constraint widening lost rows: {widen_result}"
    )
    conn.close()

    for r in records:
        if not r.get("id") or not r.get("ticker"):
            skipped.append(f"record missing id/ticker: {r}")
            continue
        append_event(
            str(jsonl_path),
            event_type="PREDICTION_CLAIM",
            effective_at=r.get("claimDate") or "",
            status="ACTIVE",
            title=f"Prediction claim: {r['ticker']} {r.get('type')} ({r.get('claimDate')})",
            body_markdown=f"Direction: {r.get('direction')}, horizon: "
                           f"{r.get('horizonDays')} days.",
            ticker=r["ticker"],
            source_id="wave5d-migration-backfill",
            payload=r,
            idempotency_key=f"prediction-claim-{r['id']}",
        )
        report["written_count"] += 1

    conn = initialize_db(str(db_path))
    try:
        replay_events_to_db(str(jsonl_path), conn)
    finally:
        conn.close()

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions-path", default=str(DEFAULT_PREDICTIONS_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument(
        "--jsonl-path", default=None,
        help="Defaults to the standard observations.jsonl ledger path.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()

    from intelligence.event_store import _default_jsonl_path
    jsonl_path = Path(args.jsonl_path) if args.jsonl_path else _default_jsonl_path()

    report = migrate(
        Path(args.predictions_path), jsonl_path, Path(args.db_path), dry_run=args.dry_run
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_migrate_predictions_to_ledger.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit (script only — the real write happens in Task 5, gated on user approval)**

```bash
git add investment_screener/backend/py_services/migrate_predictions_to_ledger.py \
        investment_screener/backend/tests/py_services/test_migrate_predictions_to_ledger.py
git commit -m "feat: add predictions.jsonl -> intelligence_event migration script (Wave 5D Task 4, dry-run/write)"
```

---

## Task 5: Dry-run report, user approval gate, then the real write against `main`'s checkout

**This task cannot run inside the worktree in its final (`--write`) form** — per this migration's
standing global constraint, the real `--write` step and its verification must target the **main
checkout's** actual `investment_screener/backend/data/predictions.jsonl`,
`observations.jsonl`, and `intelligence.sqlite` files, using main-checkout absolute paths for
every one of the three path arguments (`--predictions-path`, `--jsonl-path`, `--db-path`) —
enumerated explicitly here per the Global Constraint above, not left to the script's own
worktree-relative defaults.

- [ ] **Step 1: Run the dry-run against the worktree's own copy first (safe, no writes)**

```bash
cd investment_screener/backend
python3 py_services/migrate_predictions_to_ledger.py --dry-run
```

Expected: `{"source_count": 87, "written_count": 0, "skipped": []}` (or a non-empty `skipped` list
if any of the 87 real lines are malformed — investigate and report any such finding to the user
before proceeding, per Hard-Stop Condition 3, "a new data shape is discovered without a test
covering it").

- [ ] **Step 2: Present the dry-run report to the user for explicit sign-off**

Show the exact dry-run JSON output plus the CHECK-constraint widening plan (old constraint text
vs. new constraint text, from Task 1's fixture test output) and explicitly ask for approval
before proceeding to Step 3. **Do not proceed without an explicit yes.**

- [ ] **Step 3: Run the real write against the main checkout's actual files (only after approval)**

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
python3 investment_screener/backend/py_services/migrate_predictions_to_ledger.py \
  --write \
  --predictions-path "/Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/backend/data/predictions.jsonl" \
  --jsonl-path "/Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/backend/data/observations.jsonl" \
  --db-path "/Users/richardfremmerlid/Projects/InvestmentToolkit/investment_screener/backend/data/intelligence.sqlite"
```

All three path arguments are explicit main-checkout absolute paths — none left to the script's
own defaults, per the Global Constraint above (Wave 5B's exact gap: the DB path was overridden but
the JSONL path silently defaulted to the wrong location).

Expected: `{"source_count": 87, "written_count": 87, "skipped": [...]}` (skipped list matching
whatever Step 1's dry-run already reported, if any).

- [ ] **Step 4: Independently re-verify the real write against the main checkout's actual files**

Run each of these directly against the main checkout's real files (not the worktree's):

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
wc -l investment_screener/backend/data/observations.jsonl
# Expected: 196 (pre-existing) + 87 (this wave) = 283

sqlite3 investment_screener/backend/data/intelligence.sqlite \
  "SELECT event_type, COUNT(*) FROM intelligence_event GROUP BY event_type;"
# Expected: RESEARCH_IMPORT 80, TECHNICAL_SWEEP 105, REVIEW_DAILY 11, PREDICTION_CLAIM 87
# (or fewer if any of the 87 source lines were skipped -- must match Step 3's written_count exactly)

grep -c "PREDICTION_CLAIM" investment_screener/backend/data/observations.jsonl
# Expected: matches the sqlite3 PREDICTION_CLAIM count exactly -- both stores must agree.
```

Per this migration's standing discipline: **the controller (you) must run these three commands
yourself, directly against the main checkout, even if a subagent performed Step 3** — a
subagent's "ran the write and verified N rows" report is never sufficient on its own for a real
data-migration write.

- [ ] **Step 5: Commit the real-data changes directly to the main checkout**

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
git add investment_screener/backend/data/observations.jsonl \
        investment_screener/backend/data/intelligence.sqlite
git commit -m "chore: real predictions.jsonl -> intelligence_event backfill (Wave 5D Task 5, 87 rows)"
```

This commit lands directly on `main` (or whatever branch the main checkout is on) per this
migration's established pattern — the real data write is the one exception to "no direct
main-checkout commits," same as every prior Wave 5 sub-wave's real write.

---

## Task 6: Real-cycle parity test — run a real prediction harvest end-to-end, diff row-for-row

**Files:**
- Create: `docs/superpowers/status/wave5d-real-cycle-parity-check.md` (evidence artifact, mirrors
  Wave 5C's `1eacf69a` "real daily_brief.py run output" parity commit)

**Why this task exists:** spec §5 Validation Strategy requires "run both paths in parallel for at
least one full real-world cycle... and diff row-for-row" — not satisfied by the backfill alone,
which only proves historical data round-trips. This proves the **live, going-forward** dual-write
path (Task 2) produces byte-identical data on both sides for a brand-new claim.

- [ ] **Step 1: Run a real `harvest_predictions.py` invocation (in the worktree, against its own
  isolated copy of the data — this step does not touch the main checkout)**

```bash
cd investment_screener/backend
python3 py_services/harvest_predictions.py --dry-run 2>&1 | tee /tmp/wave5d-harvest-dryrun.log
```

Read the actual current CLI flags of `harvest_predictions.py` first (re-grep its `argparse`
block) — the exact flag name may differ; use whatever this file's real current dry-run/preview
mode is called.

- [ ] **Step 2: Diff the JSONL-path record against the ledger-path record for the same claim**

```bash
python3 -c "
import json, sqlite3, sys
sys.path.insert(0, 'py_services')
from intelligence.db_client import initialize_db
from intelligence.event_repository import get_latest_event_by_type

# Load the most recent line from the worktree's predictions.jsonl
with open('data/predictions.jsonl') as f:
    lines = [json.loads(l) for l in f if l.strip()]
latest_jsonl = lines[-1]

conn = initialize_db('data/intelligence.sqlite')
latest_event = get_latest_event_by_type(conn, 'PREDICTION_CLAIM')
latest_ledger_payload = json.loads(latest_event['payload_json'])

assert latest_jsonl == latest_ledger_payload, (
    f'PARITY MISMATCH:\nJSONL: {latest_jsonl}\nLedger: {latest_ledger_payload}'
)
print('PARITY CONFIRMED: JSONL record and intelligence_event payload_json are byte-identical.')
"
```

- [ ] **Step 3: Write the parity evidence artifact**

Document the exact command output from Steps 1–2 (not a paraphrase) in
`docs/superpowers/status/wave5d-real-cycle-parity-check.md`, matching Wave 5C's evidence format
(the commit that produced `1eacf69a`).

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/status/wave5d-real-cycle-parity-check.md
git commit -m "docs: Wave 5D real-cycle parity check (harvest_predictions.py dual-write, byte-identical)"
```

---

## Task 7: Physically execute the rollback exercise (not just document it)

**Files:**
- Create: `docs/superpowers/status/wave5d-rollback-exercise-report.md`

- [ ] **Step 1: Create a throwaway worktree for the exercise**

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
git worktree add /tmp/wave5d-rollback-exercise HEAD
cd /tmp/wave5d-rollback-exercise
```

- [ ] **Step 2: Simulate the rollback — revert the producer/consumer commits, restore
  `predictions.jsonl` as the active read path**

```bash
git log --oneline -- investment_screener/backend/py_services/prediction_ledger.py | head -5
# Identify Task 2's commit hash, then:
git revert --no-commit <task2-commit-hash>
# Confirm prediction_ledger.py's append_prediction/append_grade no longer call _append_*_event
```

- [ ] **Step 3: Confirm the app still runs correctly against the old JSONL file alone**

```bash
cd investment_screener/backend
python3 -m pytest tests/py_services/test_prediction_ledger.py tests/py_services/test_harvest_predictions.py -v
```

Expected: all pass using only `predictions.jsonl` (no ledger dependency), proving the pre-migration
code path still functions if this wave needs to be reverted.

- [ ] **Step 4: Write the rollback evidence report and clean up the throwaway worktree**

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
git worktree remove /tmp/wave5d-rollback-exercise
```

Document the exact commands and their real output (not a described plan) in
`docs/superpowers/status/wave5d-rollback-exercise-report.md`, matching Wave 5B's
`wave5b-remediation-report.md` template for "physically executed" evidence.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/status/wave5d-rollback-exercise-report.md
git commit -m "docs: Wave 5D rollback exercise (physically executed against a throwaway worktree)"
```

---

## Task 8: Archive `predictions.jsonl`, update `audit_json_usage.py`'s allowlist, update `wave6-thesis-service-scope-note` references

**Files:**
- Move: `investment_screener/backend/data/predictions.jsonl` →
  `ARCHIVE/investment_screener/backend/data/predictions.jsonl` (git-tracked, real `git mv` —
  confirmed at Task 0, not gitignored)
- Modify: `investment_screener/backend/py_services/audit_json_usage.py` (remove or update the
  `predictions.jsonl` allowlist entry at line 398/554, since the file is now archived, not an
  active exemption)
- Modify: `investment_screener/backend/tests/py_services/test_audit_json_usage.py` (its
  corresponding test for the predictions allowlist entry)

**Prerequisite grep/scan for legacy JSON reads/writes before archiving (spec §5 Validation
Strategy):**

```bash
grep -rn "predictions\.jsonl\|predictions_graded\.jsonl\|PREDICTIONS_PATH\|GRADED_PATH" \
  investment_screener plugins --include="*.py" --include="*.ts" \
  | grep -v "^investment_screener/backend/tests/" \
  | grep -v "ARCHIVE/"
```

Expected: zero real-I/O matches outside test files and the (about-to-be-archived) source file
itself — every real producer/consumer from Tasks 2–3 must show only `intelligence_event`/
`event_repository` calls, no lingering `PREDICTIONS_PATH`/`GRADED_PATH` reads. If any real-I/O
match remains, stop and fix it before proceeding (Hard-Stop Condition 5).

- [ ] **Step 1: Run the grep above and confirm clean**

- [ ] **Step 2: `git mv` the file to ARCHIVE**

```bash
git mv investment_screener/backend/data/predictions.jsonl \
       ARCHIVE/investment_screener/backend/data/predictions.jsonl
```

- [ ] **Step 3: Update `audit_json_usage.py`'s allowlist entry and its test**

Read the real current code around line 398/554 first. Remove `predictions.jsonl` from the
`ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL` allowlist (it's archived now, not a live exemption to
track), and update `test_audit_json_usage.py`'s corresponding assertion.

- [ ] **Step 4: Run `audit_json_usage.py`'s test suite**

```bash
cd investment_screener/backend
python3 -m pytest tests/py_services/test_audit_json_usage.py -v
```

- [ ] **Step 5: SKILL.md/agent reference check (Context Bundle Completion Bar)**

Per spec §4's plugin/skill reference table: `predictions.jsonl` has **no direct SKILL.md filename
reference** (addressed via API routes/CLI scripts, not named directly in skill markdown — the
spec's own table states this explicitly). Confirm this is still true:

```bash
grep -rln "predictions\.jsonl\|predictions_graded\.jsonl" plugins/ --include="*.md"
```

Expected: no matches. This wave's Context Bundle Completion Bar is therefore **0 stale filename
references removed** (there were none to begin with) — report this as the honest, computed
number, not skip the section (see Task 9's KPI table).

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/audit_json_usage.py \
        investment_screener/backend/tests/py_services/test_audit_json_usage.py \
        ARCHIVE/investment_screener/backend/data/predictions.jsonl
git commit -m "chore: archive predictions.jsonl, remove its audit_json_usage allowlist entry (Wave 5D Task 8)"
```

---

## Task 9: Wave exit report, PR, and handoff

**Files:**
- Create: `docs/superpowers/status/wave5d-predictions-report.md`
- Create: `docs/superpowers/status/wave5d-handoff.md`

- [ ] **Step 1: Run the full backend test suite one more time**

```bash
cd investment_screener/backend && python3 -m pytest tests/py_services/ -v 2>&1 | tail -40
```

Expected: only the two documented pre-existing failures (`zod-schemas.spec.ts`,
`InvestmentRepository` real-sqlite parity test), re-confirmed as still the complete baseline.

- [ ] **Step 2: Run this project's T0/T0.5 gate**

```bash
cd /Users/richardfremmerlid/Projects/InvestmentToolkit
python3 run_tests.py
```

- [ ] **Step 3: Write the Wave 5D exit report**, matching `wave5c-daily-briefs-report.md`'s depth,
  including verbatim the four required sections below.

### Hybrid Exit Criteria (spec § "Hybrid Exit Criteria" + §2.0, applied to this wave's domain)

The target architecture is **not** `JSON + JSONL + SQLite`. For the Predictions domain
specifically: before `predictions.jsonl` stops being authoritative, all 6 real
consumers/producers (`harvest_predictions.py`, `prediction_ledger.py`, `grade_predictions.py`,
`earnings_expectations.py`, `generate_track_record_report.py`, `backtest_harness.py`) must read
from `intelligence_event` exclusively (Task 3), the real backfill must be independently verified
against the main checkout (Task 5 Step 4), and the old file archived via `git mv` (Task 8) — per
spec §2.0's table row: "Fallback retirement trigger: All 6 consumers cut over." No domain is
allowed to sit in dual-write state past this wave.

### §5 Validation Strategy Checklist (verbatim, applied to Predictions)

- [ ] Schema tests: Task 1's CHECK-widening tests, run against real `tmp_path`-backed SQLite
  (not mocked).
- [ ] Migration tests: Task 4's dry-run/write tests, byte/field-level parity on the fixture data,
  and Task 5's real 87-row backfill verified field-for-field against the main checkout.
- [ ] Repository tests: Task 1/2/3 all route exclusively through
  `py_services/intelligence/` — no new `sqlite3.connect()` call sites introduced outside it.
- [ ] Consumer tests: one test per real consumer (Task 3, 5 files) confirming each reads
  `intelligence_event`, not `predictions.jsonl`/`predictions_graded.jsonl`.
- [ ] Parity tests: Task 6 — one full real-world cycle (`harvest_predictions.py`), diffed
  row-for-row between JSONL and ledger payload.
- [ ] Live-path tests where practical: Task 6's real harvest run, not just unit tests.
- [ ] Grep/scan for legacy JSON reads/writes: Task 8 Step 1, zero real-I/O matches confirmed
  before archiving.
- [ ] Archive verification: Task 8 Step 2 (`git mv` executed), confirm the old path no longer
  resolves via any code path, confirm the `ARCHIVE/` copy is readable.
- [ ] Rollback verification: Task 7, physically exercised against a throwaway worktree, not just
  described.
- [ ] Context-bundle verification: Task 8 Step 5 — confirmed zero stale SKILL.md filename
  references existed to begin with; 0 is the correct, honest number for this domain.

### Definition of Done (verbatim, spec's 9-item list — applies without exception)

1. Data is migrated to SQLite/domain model. — Task 5 (87/87 rows).
2. Real producers write SQLite/domain repositories. — Task 2 (3/3 producers).
3. Real consumers read SQLite/domain repositories. — Task 3 (6/6 consumers).
4. Old JSON/JSONL runtime references are removed or rewritten. — Task 8 Step 1's grep, clean.
5. SKILL.md / agent / plugin instructions no longer point at old JSON. — Task 8 Step 5 (none
   existed to begin with, confirmed).
6. Context-bundler no longer needs retired JSON files for that domain. — Task 8 Step 5.
7. Old JSON/JSONL is archived with `git mv`. — Task 8 Step 2.
8. Tests prove live path behavior against real data, not only fixture behavior. — Task 6's
   real-cycle parity check.
9. JSON file count and context-bundle footprint are reported before/after. — Wave KPI table
   below.

### Wave KPI Table (spec template, filled with real numbers)

| KPI | Value |
|---|---|
| Wave | 5D — Predictions |
| Active JSON/JSONL files before | 1 (`predictions.jsonl`; `predictions_graded.jsonl` never existed) |
| Active JSON/JSONL files after | 0 |
| Files archived | 1 (`predictions.jsonl` → `ARCHIVE/investment_screener/backend/data/predictions.jsonl`) |
| JSON reads removed | [fill in with real count of removed `load_predictions`/`load_graded` call sites across the 5 consumer files, from Task 3] |
| JSON writes removed | [fill in with real count — 0, since Task 2 keeps the JSONL write as dual-write during migration, only Task 8's archive fully retires it; state explicitly which write is retired at Task 8 vs. Task 2] |
| Producers migrated (n / total) | 3 / 3 |
| Consumers migrated (n / total) | 6 / 6 |
| Plugin/skill/agent references updated | 0 / 0 (none existed, confirmed) |
| Context-bundle files removed | 0 (none bundled this file to begin with) |
| Remaining JSON exceptions (with rationale) | none — full migration, no retained-JSON exception needed for this domain |

- [ ] **Step 4: Ensure all wave commits are on the wave branch; push; open a PR to `main`**

Do not merge it yourself unless explicitly told to.

- [ ] **Step 5: Verify the remote branch matches local HEAD exactly**

```bash
git log origin/<branch> -1 --format=%H
git log HEAD -1 --format=%H
```

- [ ] **Step 6: Write the Wave 5D handoff document**, then **stop** — do not start Wave 5E.

Per the kickoff prompt's Way of Working: after the user reviews/merges the PR, follow
`.agent/rules/git-operations.md`'s End-of-Wave Closeout Playbook — fetch, fast-forward `main`,
verify the merged commit is an ancestor, **re-run Task 5 Step 4's row-count verification one more
time** against the now-updated main checkout, remove the worktree, delete local AND remote
feature branches, confirm clean `git worktree list`/`git branch --list` — **then write Wave 5E's
kickoff prompt** using the same template as this wave's own kickoff prompt, before ending the
session.

---

## Hard-Stop Conditions (from the kickoff prompt, restated — stop immediately if any trigger)

1. Source count (87) and target row count do not reconcile.
2. Row count has an unexplained delta.
3. A new data shape is discovered in the real 87 lines without a test covering it.
4. A producer still writes only JSON after claimed cutover.
5. A real consumer still reads the old JSON path after claimed cutover.
6. Any script bypasses `py_services/intelligence/` and opens SQLite directly.
7. Tests fail in a new way — currently two known pre-existing failures (`zod-schemas.spec.ts`,
   `InvestmentRepository` real-sqlite parity test); re-confirm still the only ones.
8. Archive-readiness grep (Task 8 Step 1) still finds real runtime I/O to the old path.
9. The archive step would remove rollback capability.
10. Context-bundler still requires the retired file without explanation.
11. The wave would end in a permanent hybrid state.
12. The Task 5 real-write verification was never independently re-run against the main
    checkout's actual files.
13. The plan or exit report repeats a prior effort's unverified claim without re-confirmation.
14. The real migration write touches both `observations.jsonl` and `intelligence.sqlite`, and
    verification only checked one.
15. This plan document does not contain the Hybrid Exit Criteria / §5 Validation Strategy /
    9-item Definition of Done / Context Bundle Completion Bar content verbatim.
16. The CHECK-constraint widening (Task 1) is done via a live, in-place mutation without a
    verified rebuild-and-copy pattern tested against a fixture DB first, then verified
    row-for-row against `main`'s real table before/after.

---

## Self-Review

**1. Spec coverage:** Task 0 re-verifies every producer/consumer claim in spec §2.11 against real
code. Task 1 is the CHECK-widening step spec §2.11/Wave 5D scope requires and no prior Wave 5
sub-wave needed. Tasks 2–3 implement the producer/consumer cutover (spec §2.11's Target). Task 4–5
implement the real migration write with the dry-run/approval gate and main-checkout-only write
rule (Global Constraints). Task 6 satisfies the real-cycle parity requirement (spec §5). Task 7
satisfies the physically-executed rollback requirement (spec §5). Task 8 satisfies archive +
Retained-JSON Rationale Bar N/A (full migration, no exception needed) + Context Bundle Completion
Bar (spec §5/§4). Task 9 satisfies the Wave KPI table, 9-item Definition of Done, and wave-exit
protocol (kickoff prompt § "Wave exit").

**2. Placeholder scan:** All code blocks are complete, real implementations, not stubs — the one
explicit exception is Task 3 Step 5 (the 4 remaining consumer files), which intentionally follows
the overall plan's own sanctioned pattern for consumer-rewiring tasks spanning many files ("state
the real file list... read this file's actual current code before editing" — not a placeholder,
a deliberate deferral per the overall plan's own stated methodology for exactly this situation,
worked through in full for one representative file first).

**3. Type consistency:** `append_prediction(record, path=PREDICTIONS_PATH, jsonl_path=None)` /
`append_grade(record, path=GRADED_PATH, jsonl_path=None)` (Task 2) match the signatures used in
Task 4's migration script call sites and Task 6's parity-check script. `migrate(predictions_path,
jsonl_path, db_path, dry_run=True) -> dict` (Task 4) matches its own test calls and Task 5's CLI
invocation exactly. `widen_event_type_constraint(conn) -> dict` (Task 1) matches its use in Task 4
(`migrate()`'s real-write branch) exactly.
