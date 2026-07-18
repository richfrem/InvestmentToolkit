# Canonical Research Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the workstation intelligence folder system to consolidate research observations into a SQLite database read-model mapped from a JSONL event stream, with generated split Markdown views.

**Architecture:** Use a hybrid event sourcing model where observations are written to an append-only JSONL master log, SQLite acts as a query index (replayed from JSONL), and Markdown views are generated summaries.

**Tech Stack:** SQLite, Python, Node.js/Express, JSONL.

## Global Constraints
* No production code without a failing test first.
* All SQLite writes must utilize Write-Ahead Logging (WAL) mode for concurrency.
* SQLite concurrency model: Single writer, many readers. Ensure transactions are kept short to avoid busy lockouts.
* Strict event type taxonomy and status constraints must be enforced at the database level.
* Replay-first authority flow: All updates MUST append to the JSONL event ledger first, then replay into the SQLite database.
* No raw dated research markdown files are to be deleted until the deterministic migration verification gate passes.

---

## Phase 2 Scope Note (added 2026-07-18, post-audit)

An audit of every `.py` script, `SKILL.md`, Express route, and frontend component that reads
or writes the files this migration touches found real, previously-undocumented coupling:

- `plugins/portfolio-advisor/scripts/consolidate_research.py` already merges dated
  `{TICKER}_{DATE}.md` files into a canonical `{TICKER}.md` (72 of 152 research files on disk
  already have both forms — the dated originals were never deleted). Phase 2 refactors this
  script's proven scan/group/parse logic into the ledger migrator rather than discarding it.
- `investment_screener/backend/src/routes/docs.ts`'s `GET /research/:filename` regex
  (`^[A-Z0-9.-]{1,10}_\d{4}-\d{2}-\d{2}\.md$`) structurally rejects canonical filenames — none
  of the 72 already-consolidated files are servable today. This is a pre-existing bug, not
  something the ledger migration introduces, but Phase 2 fixes it since generated views make
  it worse.
- Every historical `projections/{TICKER}.json` version has a `researchReport` field
  hard-pointing at a dated filename, consumed directly by `DeepDiveModal.tsx`. Phase 2
  rewrites these to point at the canonical generated file (confirmed with user: losing
  point-in-time historical linkage is acceptable — the modal will always show current state).
- `predictions.jsonl` (`py_services/prediction_ledger.py`) and `evolution_events.jsonl`
  (`py_services/evolution_events.py`) are two pre-existing, independently-implemented
  append-only JSONL ledgers with the same `_append_jsonl`/`_load_jsonl` idiom. They are
  **domain-separate from `observations.jsonl`** (quantitative backtesting claims and agent
  self-evolution telemetry, respectively, vs. qualitative research/thesis/valuation events) —
  Phase 2 does not merge them, only notes them as prior art.
- `context/events.jsonl` at the repo root is a **false lead** — it's the unrelated
  `agent-agentic-os` plugin's generic session/lock event bus (`kernel.py`), not an
  investment-domain ledger. No overlap, no action needed. (Its rotate-on-size-threshold and
  per-consumer cursor-file pattern is useful prior art for `replay_ledger.py`'s own checkpoint
  design, already covered in Phase 1.)
- `ta-sweep-results.json` is written by two independent code paths
  (`ta_sweep_batch.py:save_sweep_results()` and a re-implementation inlined in
  `daily_brief.py`) that build the identical payload shape — a duplicate-write hazard flagged
  during the audit. Phase 2 includes a small, independent fix (Task 11) since it surfaced from
  the same audit, but it does not depend on or block the ledger work.
- `theses/investment_thesis.md`, `theses/sub_strategies/*.md`, and `target-portfolio.json`
  remain **explicitly out of scope** — unchanged per the design spec. They already have their
  own generated-view mechanism (`AUTO_UPDATE` block regeneration) and drift-checker
  (`verify_thesis_sync.py`); folding them into this ledger is a candidate for a future,
  separate plan, not this one.

---

## Phase 1: Read-Model Infrastructure (Tasks 0-4)

Builds the SQLite read-model plumbing only: schema, FTS5 index, JSONL replay, rebuild/backup
verification. Assumes `observations.jsonl` exists; does not yet write to it. Tasks 0-4 below.

---

### Task 0: Lock Node.js Backend Dependencies

**Files:**
- Modify: `investment_screener/backend/package.json`
- Modify: `package-lock.json`

**Interfaces:**
- Consumes: npm registry.
- Produces: `better-sqlite3` module node dependency.

- [ ] **Step 1: Check existing dependencies**

Run: `node -e "require('better-sqlite3')"`
Expected: FAIL with `Cannot find module 'better-sqlite3'`

- [ ] **Step 2: Install better-sqlite3 workspace package**

Run: `npm install better-sqlite3 -w backend`
Expected: Installation completes, lockfile updates.

- [ ] **Step 3: Verify module load**

Run: `node -e "require('better-sqlite3')"`
Expected: PASS with exit code 0.

- [ ] **Step 4: Commit**

```bash
git add investment_screener/backend/package.json package-lock.json
git commit -m "chore: add better-sqlite3 package dependency to backend workspace"
```

---

### Task 1: Setup SQLite DB Schema, Triggers, and Tests

**Files:**
- Create: `investment_screener/backend/data/cache/.gitkeep`
- Modify: `investment_screener/backend/py_services/db_client.py`
- Test: `investment_screener/backend/tests/py_services/test_db_client.py`

**Interfaces:**
- Consumes: Standard `sqlite3` library in Python.
- Produces: `initialize_db()` and `db_connection` reference.

- [ ] **Step 1: Write the failing test**

```python
# test_db_client.py
from db_client import initialize_db

def test_db_initialization(tmp_path):
    db_path = tmp_path / "test_intelligence.sqlite"
    conn = initialize_db(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='instrument';")
    assert cursor.fetchone() is not None
```

> **Plan correction (pre-flight review, 2026-07-18):** `test_sequence_uniqueness_constraint`
> was originally listed here, but it inserts into `intelligence_event`, which this task's
> minimal implementation does not create (that table is introduced in Task 2). The test has
> been moved to Task 2 Step 1 so each task's failing test matches what that task actually
> builds. User-confirmed resolution — see Task 2 Step 1 below.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest investment_screener/backend/tests/py_services/test_db_client.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Create `investment_screener/backend/py_services/db_client.py`:
```python
import sqlite3

def initialize_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    
    # Create tables
    conn.execute("""
    CREATE TABLE IF NOT EXISTS instrument (
        instrument_id TEXT PRIMARY KEY,
        ticker TEXT NOT NULL,
        exchange TEXT,
        name TEXT NOT NULL,
        active_from TEXT,
        active_to TEXT,
        UNIQUE(ticker, exchange, active_from)
    );
    """)
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS ledger_checkpoint (
        checkpoint_id TEXT PRIMARY KEY,
        last_event_sequence INTEGER NOT NULL,
        last_event_id TEXT NOT NULL,
        schema_version INTEGER NOT NULL,
        processed_at TEXT NOT NULL,
        ledger_file_hash TEXT NOT NULL
    );
    """)
    
    conn.commit()
    return conn
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest investment_screener/backend/tests/py_services/test_db_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/tests/py_services/test_db_client.py investment_screener/backend/py_services/db_client.py
git commit -m "feat: setup SQLite database initialization schema and tests"
```

---

### Task 2: Implement FTS5 Table and Triggers (INSERT, UPDATE, DELETE)

**Files:**
- Modify: `investment_screener/backend/py_services/db_client.py`
- Test: `investment_screener/backend/tests/py_services/test_db_client.py`

- [ ] **Step 1: Write failing test for FTS sync**

Add to `test_db_client.py`:
```python
import pytest
import sqlite3

def test_fts_search_sync(tmp_path):
    db_path = tmp_path / "test_intelligence.sqlite"
    conn = initialize_db(str(db_path))
    
    # Insert mock instrument & event
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.execute("""
        INSERT INTO intelligence_event (event_id, event_sequence, instrument_id, event_type, effective_at, ingested_at, status, title, body_markdown, content_hash)
        VALUES ('evt_1', 1, 'us-pltr', 'NEWS_SWEEP', '2026-07-18', '2026-07-18', 'ACTIVE', 'Nvidia AI Partnership', 'Palantir ontology builds secure node.', 'hash_1');
    """)
    conn.commit()
    
    cursor = conn.cursor()
    cursor.execute("SELECT rowid FROM intelligence_event_fts WHERE intelligence_event_fts MATCH 'Nvidia';")
    assert cursor.fetchone() is not None

def test_sequence_uniqueness_constraint(tmp_path):
    db_path = tmp_path / "test_intelligence.sqlite"
    conn = initialize_db(str(db_path))
    
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.execute("""
        INSERT INTO intelligence_event (event_id, event_sequence, instrument_id, event_type, effective_at, ingested_at, status, title, body_markdown, content_hash)
        VALUES ('evt_1', 1, 'us-pltr', 'NEWS_SWEEP', '2026-07-18', '2026-07-18', 'ACTIVE', 'Title 1', 'Body 1', 'hash_1');
    """)
    conn.commit()
    
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("""
            INSERT INTO intelligence_event (event_id, event_sequence, instrument_id, event_type, effective_at, ingested_at, status, title, body_markdown, content_hash)
            VALUES ('evt_2', 1, 'us-pltr', 'NEWS_SWEEP', '2026-07-18', '2026-07-18', 'ACTIVE', 'Title 2', 'Body 2', 'hash_2');
        """)
        conn.commit()
```

> **Plan correction (pre-flight review, 2026-07-18):** `test_sequence_uniqueness_constraint`
> moved here from Task 1 — it depends on `intelligence_event`, which is this task's table, not
> Task 1's.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest investment_screener/backend/tests/py_services/test_db_client.py -k "test_fts_search_sync or test_sequence_uniqueness_constraint" -v`
Expected: FAIL due to missing `intelligence_event` tables and triggers.

- [ ] **Step 3: Write minimal implementation**

Add full database schema (including `intelligence_event` and Triggers) in `db_client.py`:
```python
    conn.execute("""
    CREATE TABLE IF NOT EXISTS intelligence_event (
        event_id TEXT PRIMARY KEY,
        event_sequence INTEGER NOT NULL UNIQUE,
        instrument_id TEXT,
        event_type TEXT NOT NULL CHECK (
            event_type IN ('RESEARCH_IMPORT', 'NEWS_SWEEP', 'EARNINGS', 'VALUATION_UPDATE', 'TECHNICAL_SWEEP', 'PORTFOLIO_DECISION', 'THESIS_UPDATE', 'MACRO_EVENT', 'REVIEW_DAILY', 'REVIEW_WEEKLY')
        ),
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
    CREATE VIRTUAL TABLE IF NOT EXISTS intelligence_event_fts USING fts5(
        title,
        body_markdown,
        content='intelligence_event',
        content_rowid='rowid'
    );
    """)

    # Setup INSERT, UPDATE, DELETE triggers
    conn.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_intelligence_event_ai AFTER INSERT ON intelligence_event BEGIN
        INSERT INTO intelligence_event_fts(rowid, title, body_markdown)
        VALUES (new.rowid, new.title, new.body_markdown);
    END;
    """)

    conn.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_intelligence_event_ad AFTER DELETE ON intelligence_event BEGIN
        INSERT INTO intelligence_event_fts(intelligence_event_fts, rowid, title, body_markdown)
        VALUES('delete', old.rowid, old.title, old.body_markdown);
    END;
    """)

    conn.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_intelligence_event_au AFTER UPDATE ON intelligence_event BEGIN
        INSERT INTO intelligence_event_fts(intelligence_event_fts, rowid, title, body_markdown)
        VALUES('delete', old.rowid, old.title, old.body_markdown);
        INSERT INTO intelligence_event_fts(rowid, title, body_markdown)
        VALUES (new.rowid, new.title, new.body_markdown);
    END;
    """)
    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest investment_screener/backend/tests/py_services/test_db_client.py -v`
Expected: PASS (all tests in the file, including the Task 1 tests and both tests added in this task)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/db_client.py
git commit -m "feat: implement FTS5 virtual search index table and sync triggers"
```

---

### Task 3: JSONL Import Replay and Checkpoint Tracker

**Files:**
- Create: `investment_screener/backend/py_services/replay_ledger.py`
- Test: `investment_screener/backend/tests/py_services/test_replay_ledger.py`

- [ ] **Step 1: Write failing test for Replay Loop**

Create `test_replay_ledger.py`:
```python
import json
from replay_ledger import replay_events_to_db
from db_client import initialize_db

def test_replay_loop(tmp_path):
    jsonl_file = tmp_path / "test_observations.jsonl"
    db_path = tmp_path / "test_intelligence.sqlite"
    
    event = {
        "event_id": "evt_1",
        "event_sequence": 1,
        "ticker": "PLTR",
        "event_type": "NEWS_SWEEP",
        "effective_at": "2026-07-18",
        "ingested_at": "2026-07-18",
        "status": "ACTIVE",
        "title": "PLTR Contract",
        "body_markdown": "Palantir deal",
        "content_hash": "hash_1"
    }
    jsonl_file.write_text(json.dumps(event) + "\n")
    
    conn = initialize_db(str(db_path))
    replay_events_to_db(str(jsonl_file), conn)
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM intelligence_event;")
    assert cursor.fetchone()[0] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest investment_screener/backend/tests/py_services/test_replay_ledger.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `investment_screener/backend/py_services/replay_ledger.py`:
```python
import json
import hashlib
from datetime import datetime

def replay_events_to_db(jsonl_path, conn):
    # Load last sequence offset from checkpoint
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(last_event_sequence) FROM ledger_checkpoint;")
    row = cursor.fetchone()
    last_seq = row[0] if row and row[0] is not None else 0
    
    max_processed_sequence = last_seq
    last_event_id = "none"
    
    # Calculate file hash for checkpoint safety
    hasher = hashlib.sha256()
    
    try:
        with open(jsonl_path, 'rb') as f:
            hasher.update(f.read())
        file_hash = hasher.hexdigest()
    except FileNotFoundError:
        file_hash = "missing"
    
    try:
        with open(jsonl_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                event = json.loads(line)
                seq = event["event_sequence"]
                if seq <= last_seq:
                    continue
                
                # Insert into database
                conn.execute("""
                    INSERT OR IGNORE INTO intelligence_event (event_id, event_sequence, event_type, effective_at, ingested_at, status, title, body_markdown, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    event["event_id"], event["event_sequence"], event["event_type"],
                    event["effective_at"], event["ingested_at"], event["status"],
                    event["title"], event["body_markdown"], event["content_hash"]
                ))
                
                if seq > max_processed_sequence:
                    max_processed_sequence = seq
                    last_event_id = event["event_id"]
    except FileNotFoundError:
        pass
            
    # Update checkpoint only if new events processed
    if max_processed_sequence > last_seq:
        iso_now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute("INSERT OR REPLACE INTO ledger_checkpoint VALUES ('global', ?, ?, 1, ?, ?);", (
            max_processed_sequence, last_event_id, iso_now, file_hash
        ))
        conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest investment_screener/backend/tests/py_services/test_replay_ledger.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/replay_ledger.py investment_screener/backend/tests/py_services/test_replay_ledger.py
git commit -m "feat: implement JSONL event ledger replay loop and checkpoints"
```

---

## Plan Amendment (added 2026-07-18, post-Task-3): Shared Intelligence Data Layer

Per ADR-026 (`ADRs/026_canonical_research_consolidation_and_unified_ingest.md`, hybrid ledger
architecture), ADR-027 (`ADRs/027_sqlite_database_selection.md`, SQLite engine selection), and
ADR-028 (`ADRs/028_shared_intelligence_data_access_layer.md`, repository/service layer + the
event-modeling and anti-duplication rules below), this plan is a **full shared data-layer
refactor**, not a one-off SQLite migration. The failure mode being prevented: every future
plugin/skill/route growing its own ad hoc SQLite or JSONL access, recreating the exact
file-sprawl problem this migration exists to fix.

**Package convention (binds Task 1A onward):** `db_client.py`, `event_store.py`,
`replay_ledger.py`, `event_repository.py`, `instrument_repository.py`, `view_generator.py`,
and `models.py` live under `investment_screener/backend/py_services/intelligence/` (a proper
package with `__init__.py`, not flat modules in `py_services/` root). Tests `sys.path.insert`
at `investment_screener/backend/py_services` (the package's parent, not the package itself) and
import as `from intelligence.db_client import initialize_db`,
`from intelligence.event_store import append_event`, etc. — matching how a real package import
resolves, not a repeat of the flat-module `sys.path` hack.

**Anti-duplication rule (binds every task from here on, including Phase 2):** No new direct
SQLite access or JSONL event parsing outside `py_services/intelligence/`, unless explicitly
documented as an exception. A script that needs intelligence data calls the repository/service
layer — it does not open its own SQLite connection or write its own JSONL line.

**Event modeling rule (already satisfied by Tasks 1-2's schema, stated here for enforcement
going forward):** `event_type` is classification metadata on `intelligence_event` rows, not a
table-selection mechanism. `NEWS_SWEEP`, `EARNINGS`, `TECHNICAL_SWEEP`, `MACRO_EVENT`,
`THESIS_UPDATE`, `RESEARCH_IMPORT`, `REVIEW_DAILY`, `REVIEW_WEEKLY` all write to
`intelligence_event`. Do not create `news_sweep`/`earnings`/etc. tables. A new table is only
justified for a domain object with a materially different shape/lifecycle (e.g.
`research_thesis`, `valuation_version`, `portfolio_decision` — none exist yet in this plan;
adding one requires a documented ADR-level exception, not a quiet per-task decision).

**Deferred, not built in this pass (see ADR-028's "Deferred" section for the full rationale):**
Node/Express service layer (`src/services/intelligence/`) — nothing in this plan has Node
querying SQLite directly yet, only reading generated Markdown files (Task 8); full
`architecture.md`/`AGENTS.md`/`GEMINI.md` ecosystem rewrite — ADR-028 is the durable record in
the interim; a `generated_research_view` provenance table — noted as a legitimate future
addition, not required for the first working version.

**Retrofit of already-completed work:** Tasks 1-3 built `db_client.py` and `replay_ledger.py`
flat in `py_services/`, already reviewed and approved before this amendment landed. Task 1A
below moves them into the package (cheap now — ~150 lines, not merged anywhere durable yet — vs.
expensive after Phase 2 builds 7 more tasks on the flat structure) and folds in a required bug
fix.

---

### Task 1A: Establish Shared Intelligence Data Access Layer

**Files:**
- Create: `investment_screener/backend/py_services/intelligence/__init__.py` (empty)
- Move + modify: `investment_screener/backend/py_services/db_client.py` →
  `investment_screener/backend/py_services/intelligence/db_client.py` (content unchanged from
  Task 1-2's implementation)
- Move + modify: `investment_screener/backend/py_services/replay_ledger.py` →
  `investment_screener/backend/py_services/intelligence/replay_ledger.py` (content from Task 3,
  PLUS the bug fix described below)
- Create: `investment_screener/backend/py_services/intelligence/event_store.py`
- Create: `investment_screener/backend/py_services/intelligence/event_repository.py`
- Create: `investment_screener/backend/py_services/intelligence/instrument_repository.py`
- Create: `investment_screener/backend/py_services/intelligence/models.py`
- Move + modify: `investment_screener/backend/tests/py_services/test_db_client.py` (update
  imports to package form)
- Move + modify: `investment_screener/backend/tests/py_services/test_replay_ledger.py` (update
  imports to package form; add the incremental-resume test described below)
- Create: `investment_screener/backend/tests/py_services/test_event_store.py`
- Create: `investment_screener/backend/tests/py_services/test_event_repository.py`
- Create: `investment_screener/backend/tests/py_services/test_instrument_repository.py`

**Interfaces:**
- `models.py`: `@dataclass IntelligenceEvent` (mirrors `intelligence_event` columns) and
  `@dataclass Instrument` (mirrors `instrument` columns). No `SourceRecord`/`ValuationVersion`/
  `PortfolioDecision`/`ResearchThesis` dataclasses yet — those tables don't exist in this plan.
- `event_store.py`: `append_event(jsonl_path, event_type, effective_at, status, title,
  body_markdown, ticker=None, source_id=None, payload=None, supersedes_event_id=None,
  idempotency_key=None) -> str` — same contract originally specified for the now-superseded
  Phase 2 Task 5, relocated here since it's foundational, not writer-migration work.
- `event_repository.py`: `insert_event(conn, event: dict) -> bool` (returns whether a row was
  actually inserted, i.e. `cursor.rowcount == 1` — the caller, `replay_ledger.py`, uses this to
  decide whether to advance the checkpoint); `search_fts(conn, query: str) -> list[dict]`
  (wraps the `intelligence_event_fts MATCH` query so callers never write raw FTS5 SQL); and
  `list_active_events_for_ticker(conn, ticker: str) -> list[dict]` (ACTIVE events for a ticker,
  newest first — Task 7's `view_generator.py` calls this instead of its own `SELECT`, keeping
  every `intelligence_event` query in one file per ADR-028).
- `instrument_repository.py`: `resolve_instrument(conn, ticker: str, exchange: str | None =
  None, name: str | None = None) -> str` — returns `instrument_id`, inserting a new `instrument`
  row if the ticker isn't already known (idempotent: calling it twice for the same ticker
  returns the same `instrument_id`, does not insert twice).
- `replay_ledger.py`'s `replay_events_to_db(jsonl_path, conn) -> dict` — same as Task 3, but now
  (a) calls `event_repository.insert_event()` instead of raw `INSERT OR IGNORE` SQL directly,
  (b) only advances checkpoint bookkeeping (`max_processed_sequence`, `last_event_id`) for
  events `insert_event()` reports as actually inserted, (c) returns
  `{"processed": N, "skipped": [...]}` where `skipped` lists any event dicts that were rejected
  (duplicate sequence, taxonomy violation) so they are never silently lost.

This closes the Task 3 reviewer's Important finding (silent checkpoint advancement past
rejected events) as a natural consequence of routing inserts through `event_repository.py`
instead of duplicating the same `INSERT OR IGNORE` call site.

- [ ] **Step 1: Write the failing tests**

For `event_store.py` — reuse the exact two tests originally written for the now-superseded
Phase 2 Task 5 (`test_append_event_assigns_incrementing_sequence`,
`test_append_event_idempotency_key_dedups`), placed in
`investment_screener/backend/tests/py_services/test_event_store.py`, importing as
`from intelligence.event_store import append_event`.

For `event_repository.py`:
```python
# test_event_repository.py
from intelligence.db_client import initialize_db
from intelligence.event_repository import insert_event, search_fts

def test_insert_event_returns_true_when_row_inserted(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.commit()
    result = insert_event(conn, {
        "event_id": "evt_1", "event_sequence": 1, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-18", "ingested_at": "2026-07-18",
        "status": "ACTIVE", "title": "T1", "body_markdown": "B1", "content_hash": "h1",
    })
    assert result is True

def test_insert_event_returns_false_when_sequence_duplicate(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.commit()
    base = {
        "event_sequence": 1, "instrument_id": "us-pltr", "event_type": "NEWS_SWEEP",
        "effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE",
        "title": "T1", "body_markdown": "B1",
    }
    assert insert_event(conn, {**base, "event_id": "evt_1", "content_hash": "h1"}) is True
    assert insert_event(conn, {**base, "event_id": "evt_2", "content_hash": "h2"}) is False

def test_search_fts_returns_matching_events(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.commit()
    insert_event(conn, {
        "event_id": "evt_1", "event_sequence": 1, "instrument_id": "us-pltr",
        "event_type": "NEWS_SWEEP", "effective_at": "2026-07-18", "ingested_at": "2026-07-18",
        "status": "ACTIVE", "title": "Nvidia Partnership", "body_markdown": "Palantir and Nvidia.",
        "content_hash": "h1",
    })
    results = search_fts(conn, "Nvidia")
    assert len(results) == 1
    assert results[0]["title"] == "Nvidia Partnership"
```

For `instrument_repository.py`:
```python
# test_instrument_repository.py
from intelligence.db_client import initialize_db
from intelligence.instrument_repository import resolve_instrument

def test_resolve_instrument_creates_new_and_is_idempotent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    id_1 = resolve_instrument(conn, "PLTR", exchange="NASDAQ", name="Palantir Technologies")
    id_2 = resolve_instrument(conn, "PLTR", exchange="NASDAQ", name="Palantir Technologies")
    assert id_1 == id_2
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM instrument WHERE ticker = 'PLTR';")
    assert cursor.fetchone()[0] == 1
```

For the retrofitted `replay_ledger.py` (Task 3 bug fix, incorporated here) — add to
`test_replay_ledger.py`:
```python
def test_replay_skips_and_reports_taxonomy_violation_without_advancing_checkpoint(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    jsonl_path.write_text(
        '{"event_id": "evt_1", "event_sequence": 1, "event_type": "BOGUS_NOT_IN_TAXONOMY", '
        '"effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", '
        '"title": "T", "body_markdown": "B", "content_hash": "h1"}\n'
    )
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    result = replay_events_to_db(str(jsonl_path), conn)
    assert result["processed"] == 0
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["event_id"] == "evt_1"
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ledger_checkpoint;")
    assert cursor.fetchone()[0] == 0  # checkpoint must not advance past a rejected event

def test_replay_incremental_resume_picks_up_newly_appended_events(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    jsonl_path.write_text(
        '{"event_id": "evt_1", "event_sequence": 1, "event_type": "NEWS_SWEEP", '
        '"effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", '
        '"title": "T1", "body_markdown": "B1", "content_hash": "h1"}\n'
    )
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    replay_events_to_db(str(jsonl_path), conn)

    with open(jsonl_path, "a") as f:
        f.write(
            '{"event_id": "evt_2", "event_sequence": 2, "event_type": "NEWS_SWEEP", '
            '"effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", '
            '"title": "T2", "body_markdown": "B2", "content_hash": "h2"}\n'
        )
    replay_events_to_db(str(jsonl_path), conn)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM intelligence_event;")
    assert cursor.fetchone()[0] == 2
    cursor.execute("SELECT last_event_sequence FROM ledger_checkpoint WHERE checkpoint_id = 'global';")
    assert cursor.fetchone()[0] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest investment_screener/backend/tests/py_services/test_event_store.py investment_screener/backend/tests/py_services/test_event_repository.py investment_screener/backend/tests/py_services/test_instrument_repository.py -v`
Expected: FAIL with `ModuleNotFoundError` (package doesn't exist yet).

Run: `pytest investment_screener/backend/tests/py_services/test_replay_ledger.py -v -k "taxonomy_violation or incremental_resume"`
Expected: FAIL — either `ModuleNotFoundError` (imports not yet updated to package form) or, once
imports are fixed, `KeyError`/`AssertionError` against the current flat implementation's
unconditional-checkpoint-advance behavior.

- [ ] **Step 3: Move existing modules, then implement the new ones**

1. `git mv` (preserves history) `db_client.py` and `replay_ledger.py` into
   `py_services/intelligence/`; same for their two existing test files. Add empty
   `__init__.py`. Update the `sys.path.insert` line in both test files to point at
   `investment_screener/backend/py_services` (one level up from `intelligence/`), and change
   their imports to `from intelligence.db_client import initialize_db` /
   `from intelligence.replay_ledger import replay_events_to_db`.
2. Create `event_store.py` — same implementation the plan originally specified for Task 5
   (sequence assignment, content hash, idempotency-key dedup via linear scan of the JSONL
   file), just relocated and import-adjusted.
3. Create `event_repository.py`:
```python
def insert_event(conn, event: dict) -> bool:
    cursor = conn.execute("""
        INSERT OR IGNORE INTO intelligence_event
        (event_id, event_sequence, instrument_id, event_type, effective_at, ingested_at,
         status, title, body_markdown, content_hash)
        VALUES (:event_id, :event_sequence, :instrument_id, :event_type, :effective_at,
                :ingested_at, :status, :title, :body_markdown, :content_hash);
    """, {**event, "instrument_id": event.get("instrument_id")})
    conn.commit()
    return cursor.rowcount == 1


def search_fts(conn, query: str) -> list[dict]:
    cursor = conn.execute("""
        SELECT ie.event_id, ie.title, ie.body_markdown, ie.effective_at
        FROM intelligence_event_fts fts
        JOIN intelligence_event ie ON ie.rowid = fts.rowid
        WHERE intelligence_event_fts MATCH ?;
    """, (query,))
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
```
4. Create `instrument_repository.py`:
```python
def resolve_instrument(conn, ticker: str, exchange: str | None = None, name: str | None = None) -> str:
    cursor = conn.execute("SELECT instrument_id FROM instrument WHERE ticker = ?;", (ticker,))
    row = cursor.fetchone()
    if row:
        return row[0]
    instrument_id = f"{(exchange or 'na').lower()}-{ticker.lower()}"
    conn.execute(
        "INSERT INTO instrument (instrument_id, ticker, exchange, name, active_from, active_to) "
        "VALUES (?, ?, ?, ?, date('now'), NULL);",
        (instrument_id, ticker, exchange, name or ticker),
    )
    conn.commit()
    return instrument_id
```
5. Rewrite `replay_ledger.py`'s `replay_events_to_db` to call `event_repository.insert_event()`
   per row (instead of its own inline `INSERT OR IGNORE`), only advance
   `max_processed_sequence`/`last_event_id` when `insert_event()` returns `True`, collect
   rejected events into a `skipped` list, and return `{"processed": N, "skipped": [...]}`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest investment_screener/backend/tests/py_services/test_db_client.py investment_screener/backend/tests/py_services/test_replay_ledger.py investment_screener/backend/tests/py_services/test_event_store.py investment_screener/backend/tests/py_services/test_event_repository.py investment_screener/backend/tests/py_services/test_instrument_repository.py -v`
Expected: PASS, all tests, pristine output.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/intelligence/ investment_screener/backend/tests/py_services/test_db_client.py investment_screener/backend/tests/py_services/test_replay_ledger.py investment_screener/backend/tests/py_services/test_event_store.py investment_screener/backend/tests/py_services/test_event_repository.py investment_screener/backend/tests/py_services/test_instrument_repository.py
git rm investment_screener/backend/py_services/db_client.py investment_screener/backend/py_services/replay_ledger.py 2>/dev/null || true
git commit -m "refactor: establish py_services/intelligence/ shared data layer (ADR-028)

Retrofits Tasks 1-3's flat db_client.py/replay_ledger.py into a proper
package. Adds event_store.py, event_repository.py, instrument_repository.py.
Fixes Task 3 review finding: replay now only advances the checkpoint for
events actually inserted, never for silently-rejected ones."
```

---

### Task 4: Rebuild DB & Backup Verification Script

**Path update (per Task 1A):** all file paths below resolve under
`investment_screener/backend/py_services/intelligence/`, not bare `py_services/`. Imports use
`from intelligence.db_client import initialize_db` and
`from intelligence.replay_ledger import replay_events_to_db`.

**Files:**
- Create: `investment_screener/backend/py_services/rebuild_db.py`
- Test: `investment_screener/backend/tests/py_services/test_rebuild_db.py`

**Interfaces:**
- Consumes: `observations.jsonl` from history ledger.
- Produces: SQLite binary recreation script.

- [ ] **Step 1: Write failing test for Rebuild DB**

Create `test_rebuild_db.py`:
```python
import os
from rebuild_db import run_rebuild

def test_run_rebuild(tmp_path):
    db_path = tmp_path / "rebuilt_intelligence.sqlite"
    jsonl_path = tmp_path / "observations.jsonl"
    jsonl_path.write_text('{"event_id": "evt_test", "event_sequence": 1, "event_type": "MACRO_EVENT", "effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", "title": "Test event", "body_markdown": "Test body", "content_hash": "hash_val"}\n')
    
    run_rebuild(str(jsonl_path), str(db_path))
    assert db_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest investment_screener/backend/tests/py_services/test_rebuild_db.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `investment_screener/backend/py_services/rebuild_db.py`:
```python
import os
from db_client import initialize_db
from replay_ledger import replay_events_to_db

def run_rebuild(jsonl_path, db_path):
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = initialize_db(db_path)
    replay_events_to_db(jsonl_path, conn)
    conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest investment_screener/backend/tests/py_services/test_rebuild_db.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/rebuild_db.py investment_screener/backend/tests/py_services/test_rebuild_db.py
git commit -m "feat: implement SQLite database rebuild from plain text JSONL ledger backup"
```

---

## Phase 2: Writer & Reader Migration (Tasks 5-11)

Wires actual producers/consumers to the ledger built in Phase 1: a shared append helper,
migration of the 152 existing dated research files, generated-view rendering, the backend
route fix, projection pointer rewrite, `SKILL.md` updates, and the `ta-sweep-results.json`
duplicate-write fix. Depends on Phase 1 (`db_client.py`, `replay_ledger.py`) being complete.

---

### Task 5: SUPERSEDED — see Task 1A

This task's original scope (a shared event-append helper: `event_sequence` assignment,
`content_hash` computation, idempotency-key dedup) was pulled forward into Task 1A's
`event_store.py`, per ADR-028 — it's foundational data-layer work, not writer migration, so it
belongs before Phase 2's broader migration work, not inside it. **Do not implement a separate
`append_event.py`.** Every task below that needs to append an event imports
`from intelligence.event_store import append_event`.

---

### Task 6: Migrate Existing Dated Research Files into the Ledger

**Files:**
- Create: `investment_screener/backend/py_services/migrate_research_to_ledger.py`
- Test: `investment_screener/backend/tests/py_services/test_migrate_research_to_ledger.py`
- Reference (do not delete): `plugins/portfolio-advisor/scripts/consolidate_research.py`

**Interfaces:**
- Consumes: `investment_screener/backend/data/research/{TICKER}_{YYYY-MM-DD}.md` (152 files:
  80 dated-only, 72 with an existing but now-superseded canonical `{TICKER}.md` alongside).
- Produces: one `RESEARCH_IMPORT` event per dated file appended to `observations.jsonl` via
  `append_event()` (`intelligence.event_store`, Task 1A); a migration manifest; archived
  originals moved to `investment_screener/backend/data/history/archive/research/`.

**Package convention:** this script imports `from intelligence.event_store import
append_event` (per ADR-028 — no ad hoc JSONL writing outside the shared data layer). Its test
file's `sys.path.insert` points at `investment_screener/backend/py_services` (the `intelligence/`
package's parent), same as Task 1A's tests.

Implements Design Spec §5's 6-phase protocol (Scan → Classify → Manifest → Stage → Validate →
Publish & Archive), reusing `consolidate_research.py`'s existing file-discovery glob
(`*_202[0-9]-[0-9][0-9]-[0-9][0-9].md`) and ticker/date parsing instead of re-deriving them.
Global Constraint: **no raw dated research markdown files are deleted** — `Publish & Archive`
moves them, it never removes them, until the deterministic migration verification gate passes.

- [ ] **Step 1: Write the failing test**

```python
# test_migrate_research_to_ledger.py
import json
from migrate_research_to_ledger import scan_dated_files, migrate_to_ledger

def test_scan_dated_files_parses_ticker_and_date(tmp_path):
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    (research_dir / "PLTR_2026-07-02.md").write_text("# PLTR notes\nSome research.")
    (research_dir / "PLTR_2026-05-01.md").write_text("# PLTR notes\nOlder research.")
    (research_dir / "PLTR.md").write_text("# canonical, not dated - should be skipped")

    found = scan_dated_files(str(research_dir))
    assert len(found) == 2
    assert {f["ticker"] for f in found} == {"PLTR"}
    assert sorted(f["effective_at"] for f in found) == ["2026-05-01", "2026-07-02"]

def test_migrate_to_ledger_appends_one_event_per_file_and_archives_originals(tmp_path):
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    (research_dir / "PLTR_2026-07-02.md").write_text("# PLTR notes\nSome research.")
    jsonl_path = tmp_path / "observations.jsonl"
    archive_dir = tmp_path / "archive"

    manifest = migrate_to_ledger(str(research_dir), str(jsonl_path), str(archive_dir))

    events = [json.loads(l) for l in jsonl_path.read_text().splitlines()]
    assert len(events) == 1
    assert events[0]["event_type"] == "RESEARCH_IMPORT"
    assert events[0]["ticker"] == "PLTR"
    assert manifest["migrated_count"] == 1

    # Non-destructive: original still readable at its archived location, not deleted outright
    assert (archive_dir / "PLTR_2026-07-02.md").exists()
    assert not (research_dir / "PLTR_2026-07-02.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest investment_screener/backend/tests/py_services/test_migrate_research_to_ledger.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `investment_screener/backend/py_services/migrate_research_to_ledger.py`. Reuse the glob
pattern and ticker/date split from `consolidate_research.py` for `scan_dated_files()`. Then:

```python
import json
import re
import shutil
from pathlib import Path
from intelligence.event_store import append_event

DATED_FILE_RE = re.compile(r"^([A-Z0-9.\-]+)_(\d{4}-\d{2}-\d{2})\.md$")


def scan_dated_files(research_dir: str) -> list[dict]:
    found = []
    for path in Path(research_dir).glob("*.md"):
        match = DATED_FILE_RE.match(path.name)
        if not match:
            continue
        found.append({
            "ticker": match.group(1),
            "effective_at": match.group(2),
            "path": str(path),
        })
    return found


def migrate_to_ledger(research_dir: str, jsonl_path: str, archive_dir: str) -> dict:
    files = scan_dated_files(research_dir)
    Path(archive_dir).mkdir(parents=True, exist_ok=True)
    migrated = 0
    for entry in files:
        source_path = Path(entry["path"])
        body = source_path.read_text()
        append_event(
            jsonl_path,
            event_type="RESEARCH_IMPORT",
            effective_at=entry["effective_at"],
            status="ACTIVE",
            title=f"{entry['ticker']} research import ({entry['effective_at']})",
            body_markdown=body,
            ticker=entry["ticker"],
            idempotency_key=f"research-import-{source_path.name}",
        )
        shutil.move(str(source_path), str(Path(archive_dir) / source_path.name))
        migrated += 1
    return {"migrated_count": migrated}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest investment_screener/backend/tests/py_services/test_migrate_research_to_ledger.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/migrate_research_to_ledger.py investment_screener/backend/tests/py_services/test_migrate_research_to_ledger.py
git commit -m "feat: migrate dated research files into observations.jsonl ledger (non-destructive)"
```

---

### Task 7: Generated Research View Renderer

**Files:**
- Create: `investment_screener/backend/py_services/intelligence/view_generator.py` (part of the
  Task 1A package, per ADR-028 module list — not a standalone `py_services/` script)
- Test: `investment_screener/backend/tests/py_services/test_view_generator.py`

**Interfaces:**
- Consumes: `intelligence.sqlite` via `event_repository.list_active_events_for_ticker()` (Task
  1A) — this module does not write its own `SELECT` against `intelligence_event`; that would
  duplicate the one place ADR-028 designates for `intelligence_event` SQL.
- Produces: `investment_screener/backend/data/research/{TICKER}.summary.md` and
  `{TICKER}.timeline.md` per Design Spec §4's YAML frontmatter envelope.

- [ ] **Step 1: Write the failing test**

```python
# test_view_generator.py
from intelligence.db_client import initialize_db
from intelligence.view_generator import render_ticker_views

def test_render_ticker_views_writes_summary_and_timeline(tmp_path):
    db_path = tmp_path / "test_intelligence.sqlite"
    conn = initialize_db(str(db_path))
    conn.execute("INSERT INTO instrument VALUES ('us-pltr', 'PLTR', 'NASDAQ', 'Palantir', '2026-07-18', NULL);")
    conn.execute("""
        INSERT INTO intelligence_event (event_id, event_sequence, instrument_id, event_type, effective_at, ingested_at, status, title, body_markdown, content_hash)
        VALUES ('evt_1', 1, 'us-pltr', 'RESEARCH_IMPORT', '2026-07-18', '2026-07-18', 'ACTIVE', 'PLTR research import', 'Palantir ontology builds secure node.', 'hash_1');
    """)
    conn.commit()

    output_dir = tmp_path / "research"
    output_dir.mkdir()
    render_ticker_views("PLTR", conn, str(output_dir))

    summary = (output_dir / "PLTR.summary.md").read_text()
    timeline = (output_dir / "PLTR.timeline.md").read_text()
    assert "ticker: \"PLTR\"" in summary
    assert "documentType: generated-research-summary" in summary
    assert "Palantir ontology builds secure node." in timeline
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest investment_screener/backend/tests/py_services/test_view_generator.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Add to Task 1A's `event_repository.py` (in the same package, this task extends it rather than
creating a competing query path):
```python
def list_active_events_for_ticker(conn, ticker: str) -> list[dict]:
    cursor = conn.execute("""
        SELECT ie.effective_at, ie.title, ie.body_markdown
        FROM intelligence_event ie
        JOIN instrument i ON ie.instrument_id = i.instrument_id
        WHERE i.ticker = ? AND ie.status = 'ACTIVE'
        ORDER BY ie.effective_at DESC, ie.event_sequence DESC;
    """, (ticker,))
    return [
        {"effective_at": r[0], "title": r[1], "body_markdown": r[2]}
        for r in cursor.fetchall()
    ]
```

Create `investment_screener/backend/py_services/intelligence/view_generator.py`:
```python
from datetime import datetime, timezone
from pathlib import Path
from intelligence.event_repository import list_active_events_for_ticker


def render_ticker_views(ticker: str, conn, output_dir: str) -> None:
    events = list_active_events_for_ticker(conn, ticker)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = Path(output_dir)

    summary = (
        "---\n"
        "schemaVersion: 1\n"
        "documentType: generated-research-summary\n"
        f"ticker: \"{ticker}\"\n"
        f"generatedAt: \"{generated_at}\"\n"
        "---\n\n"
        f"# {ticker} Canonical Research Summary\n\n"
        "*This file is a generated view. Do not edit directly. Authoritative observations are "
        "stored in the JSONL event ledger and indexed in `intelligence.sqlite`.*\n\n"
        f"{events[0]['body_markdown'] if events else '_No active research events yet._'}\n"
    )
    (out / f"{ticker}.summary.md").write_text(summary)

    timeline_lines = [f"# {ticker} Research Timeline\n"]
    for event in events:
        timeline_lines.append(f"\n## {event['effective_at']} — {event['title']}\n\n{event['body_markdown']}\n")
    (out / f"{ticker}.timeline.md").write_text("".join(timeline_lines))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest investment_screener/backend/tests/py_services/test_view_generator.py investment_screener/backend/tests/py_services/test_event_repository.py -v`
Expected: PASS (both — this task added a method to `event_repository.py`, so its existing
tests must still pass alongside the new `view_generator.py` test).

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/intelligence/view_generator.py investment_screener/backend/py_services/intelligence/event_repository.py investment_screener/backend/tests/py_services/test_view_generator.py
git commit -m "feat: render generated research summary/timeline views from intelligence.sqlite"
```

---

### Task 8: Fix Backend Research Route for Canonical Filenames

**Files:**
- Modify: `investment_screener/backend/src/routes/docs.ts`
- Test: `investment_screener/backend/tests/api/docs.research.spec.ts`

**Interfaces:**
- `GET /research/:filename` — currently rejects any filename without a `_YYYY-MM-DD` suffix
  (regex `^[A-Z0-9.-]{1,10}_\d{4}-\d{2}-\d{2}\.md$`, `docs.ts` line ~40-59). Must also accept
  `{TICKER}.summary.md` and `{TICKER}.timeline.md` (Task 7's output).
- `GET /research` — currently derives `ticker`/`date` by splitting the filename on `_`
  (`docs.ts` line ~61-74), producing `undefined` dates for canonical filenames. Must branch on
  filename shape instead of assuming one.

- [ ] **Step 1: Write the failing test**

```typescript
// docs.research.spec.ts
import request from 'supertest';
import { app } from '../../src/index'; // adjust import to this project's actual app export

describe('GET /api/research/:filename', () => {
  it('serves a canonical {TICKER}.summary.md filename', async () => {
    const res = await request(app).get('/api/research/PLTR.summary.md');
    expect(res.status).not.toBe(400);
  });
});

describe('GET /api/research', () => {
  it('lists canonical files with a non-undefined ticker and a null (not undefined) date', async () => {
    const res = await request(app).get('/api/research');
    const canonical = res.body.find((f: any) => f.filename === 'PLTR.summary.md');
    expect(canonical).toBeDefined();
    expect(canonical.ticker).toBe('PLTR');
    expect(canonical.date).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -w backend -- docs.research.spec.ts`
Expected: FAIL — canonical filename rejected with 400, or `date` is `undefined` not `null`.

- [ ] **Step 3: Write minimal implementation**

In `docs.ts`, replace the single dated-only regex with two patterns and branch the listing
logic on which one matches:
```typescript
const DATED_FILENAME_RE = /^[A-Z0-9.-]{1,10}_\d{4}-\d{2}-\d{2}\.md$/;
const CANONICAL_FILENAME_RE = /^[A-Z0-9.-]{1,10}\.(summary|timeline)\.md$/;

// GET /research/:filename validation:
if (!DATED_FILENAME_RE.test(filename) && !CANONICAL_FILENAME_RE.test(filename)) {
  return res.status(400).json({ error: 'Invalid research filename' });
}

// GET /research listing — replace naive split('_') with:
function parseResearchFilename(filename: string): { ticker: string; date: string | null } {
  const datedMatch = filename.match(/^([A-Z0-9.-]{1,10})_(\d{4}-\d{2}-\d{2})\.md$/);
  if (datedMatch) return { ticker: datedMatch[1], date: datedMatch[2] };
  const canonicalMatch = filename.match(/^([A-Z0-9.-]{1,10})\.(summary|timeline)\.md$/);
  if (canonicalMatch) return { ticker: canonicalMatch[1], date: null };
  return { ticker: filename, date: null };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test -w backend -- docs.research.spec.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/src/routes/docs.ts investment_screener/backend/tests/api/docs.research.spec.ts
git commit -m "fix: serve canonical {TICKER}.summary/timeline.md research filenames"
```

---

### Task 9: Rewrite `researchReport` Pointers to Canonical Filenames

**Files:**
- Create: `investment_screener/backend/py_services/migrate_research_report_pointers.py`
- Test: `investment_screener/backend/tests/py_services/test_migrate_research_report_pointers.py`

**Interfaces:**
- Consumes/Produces: every version entry's `researchReport` field across
  `investment_screener/backend/data/projections/{TICKER}.json`.
- User-confirmed resolution: every historical projection version is rewritten to point at the
  ticker's single canonical `{TICKER}.summary.md` — point-in-time linkage to the specific
  dated file a projection was written against is intentionally not preserved.

- [ ] **Step 1: Write the failing test**

```python
# test_migrate_research_report_pointers.py
import json
from migrate_research_report_pointers import migrate_pointers

def test_migrate_pointers_rewrites_all_versions_to_canonical(tmp_path):
    projections_dir = tmp_path / "projections"
    projections_dir.mkdir()
    (projections_dir / "PLTR.json").write_text(json.dumps([
        {"version": 1, "researchReport": "PLTR_2026-05-01.md"},
        {"version": 2, "researchReport": "PLTR_2026-07-02.md"},
        {"version": 3},  # no researchReport field — must be left untouched
    ]))

    result = migrate_pointers(str(projections_dir))

    updated = json.loads((projections_dir / "PLTR.json").read_text())
    assert updated[0]["researchReport"] == "PLTR.summary.md"
    assert updated[1]["researchReport"] == "PLTR.summary.md"
    assert "researchReport" not in updated[2]
    assert result["rewritten_count"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest investment_screener/backend/tests/py_services/test_migrate_research_report_pointers.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `investment_screener/backend/py_services/migrate_research_report_pointers.py`. Use an
atomic write (temp file + rename, matching `update_thesis.py`'s existing pattern) to avoid
partial writes on a crash mid-migration:
```python
import json
import re
from pathlib import Path

DATED_RE = re.compile(r"^([A-Z0-9.\-]+)_\d{4}-\d{2}-\d{2}\.md$")


def migrate_pointers(projections_dir: str) -> dict:
    rewritten = 0
    for path in Path(projections_dir).glob("*.json"):
        versions = json.loads(path.read_text())
        changed = False
        for version in versions:
            report = version.get("researchReport")
            if not report:
                continue
            match = DATED_RE.match(report)
            if not match:
                continue
            version["researchReport"] = f"{match.group(1)}.summary.md"
            changed = True
            rewritten += 1
        if changed:
            tmp_path = path.with_suffix(".json.tmp")
            tmp_path.write_text(json.dumps(versions, indent=2))
            tmp_path.replace(path)
    return {"rewritten_count": rewritten}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest investment_screener/backend/tests/py_services/test_migrate_research_report_pointers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/migrate_research_report_pointers.py investment_screener/backend/tests/py_services/test_migrate_research_report_pointers.py
git commit -m "feat: rewrite historical researchReport pointers to canonical research views"
```

---

### Task 10: Wire Research-Writing Skills to the Event Ledger

**Files:**
- Modify: `plugins/stock-valuation/skills/stock_valuation/SKILL.md` (Step 7, currently
  `cat > research/{TICKER}_{YYYY-MM-DD}.md`)
- Modify: `plugins/stock-valuation/skills/stock-research/SKILL.md` (currently
  `cat >> research/{TICKER}_{DATE}.md`)

**Interfaces:**
- Replaces direct markdown writes with a `python3 -m intelligence.event_store` CLI call (Task
  1A's `event_store.py`), followed by `python3 -m intelligence.view_generator {TICKER}` (Task 7)
  to regenerate the canonical views. This is the orchestration/prompt-change case in
  `.agent/rules/test-driven-development.md` — TDD's Iron Law does not apply verbatim to prose
  instructions, but a success contract is still required per that rule's TDO section.

This task edits `SKILL.md` files only (no executable code) — per
`.agent/rules/worktree-subagent-isolation.md`, pure documentation/markdown edits are exempt
from the worktree requirement, but stay in this plan/worktree for ledger consistency with the
rest of Phase 2's shared context.

- [ ] **Step 1: Write the success contract (TDO, not TDD — no test framework applies to prose)**

Before editing, define the pass/fail check:
```bash
# Must find zero remaining direct dated-markdown writes in either skill:
grep -rn 'cat > research/\|cat >> research/' \
  plugins/stock-valuation/skills/stock_valuation/SKILL.md \
  plugins/stock-valuation/skills/stock-research/SKILL.md
# Expected before the edit: 2 matches (one per file).
# Expected after the edit: 0 matches, replaced by intelligence.event_store + intelligence.view_generator calls.
```

- [ ] **Step 2: Run the check to confirm the "before" state**

Run the `grep` above. Expected: 2 matches (proves the old pattern exists before the edit).

- [ ] **Step 3: Edit both `SKILL.md` files**

Replace the `cat > research/{TICKER}_{YYYY-MM-DD}.md` / `cat >> research/{TICKER}_{DATE}.md`
instructions with:
```bash
python3 -m intelligence.event_store \
  --event-type RESEARCH_IMPORT --ticker {TICKER} --effective-at "$(date +%F)" \
  --status ACTIVE --title "{TICKER} research update" --body-file /tmp/research_body.md
python3 -m intelligence.view_generator {TICKER}
```
(both invoked with cwd `investment_screener/backend/py_services/` so `-m intelligence.X`
resolves the package. `event_store.py`'s Task 1A implementation is a Python function; add a
thin `if __name__ == "__main__":` CLI wrapper with `argparse` mirroring the flags above as part
of this task, since Task 1A only specifies the importable function signature. Same for
`view_generator.py` — add a CLI wrapper taking `{TICKER}` as a positional arg.)

Preserve every other instruction in both files unmodified — this task touches only the
research-file-write steps, per the coding-conventions "Index & Preservation Directive."

- [ ] **Step 4: Run the check to confirm the "after" state**

Run the `grep` from Step 1 again. Expected: 0 matches.

- [ ] **Step 5: Commit**

```bash
git add plugins/stock-valuation/skills/stock_valuation/SKILL.md plugins/stock-valuation/skills/stock-research/SKILL.md investment_screener/backend/py_services/intelligence/event_store.py investment_screener/backend/py_services/intelligence/view_generator.py
git commit -m "docs: wire stock_valuation/stock-research skills to append_event ledger writer"
```

---

### Task 11: Deduplicate `ta-sweep-results.json` Writers (independent cleanup)

**Files:**
- Modify: `plugins/portfolio-advisor/scripts/daily_brief.py`
- Test: `investment_screener/backend/tests/py_services/test_daily_brief_ta_sweep_delegates.py`

**Interfaces:**
- `daily_brief.py` currently runs `ta_sweep_batch.py --no-save`, parses its stdout, and
  re-implements the exact `{timestamp, scan_date, count, results}` write that
  `ta_sweep_batch.py:save_sweep_results()` already performs (lines ~403-411 vs. ~279-298) — two
  independent code paths writing the same file shape is a drift hazard, not a ledger-design
  issue. This task is **independent of Phase 2's ledger work** — it can be done in any order
  relative to Tasks 5-10, included here because it surfaced from the same audit.

- [ ] **Step 1: Write the failing test**

```python
# test_daily_brief_ta_sweep_delegates.py
import ast
from pathlib import Path

def test_daily_brief_does_not_reimplement_ta_sweep_json_dump():
    source = Path("plugins/portfolio-advisor/scripts/daily_brief.py").read_text()
    tree = ast.parse(source)
    # No direct `json.dump(..., f)` call against a payload dict built inline in daily_brief.py —
    # the file must call ta_sweep_batch.save_sweep_results() instead.
    dump_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "dump"
    ]
    assert len(dump_calls) == 0, "daily_brief.py must delegate to ta_sweep_batch.save_sweep_results(), not reimplement json.dump"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest investment_screener/backend/tests/py_services/test_daily_brief_ta_sweep_delegates.py -v`
Expected: FAIL — the existing inline `json.dump(payload, f, indent=2)` call is found.

- [ ] **Step 3: Refactor `daily_brief.py`**

Remove `--no-save` from the `ta_sweep_batch.py` subprocess invocation (let it write
`ta-sweep-results.json` itself via its own `save_sweep_results()`), delete `daily_brief.py`'s
inlined payload-construction and `json.dump` block, and read the file back in after the
subprocess completes instead of holding the parsed stdout as the write source.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest investment_screener/backend/tests/py_services/test_daily_brief_ta_sweep_delegates.py -v`
Expected: PASS. Also re-run any existing `daily_brief.py` tests
(`test_daily_brief_rebalance_event_emission.py`, `test_daily_brief_thesis_breakers.py`,
`test_daily_brief_prediction_harvest.py`) to confirm no regression from removing `--no-save`.

- [ ] **Step 5: Commit**

```bash
git add plugins/portfolio-advisor/scripts/daily_brief.py investment_screener/backend/tests/py_services/test_daily_brief_ta_sweep_delegates.py
git commit -m "fix: daily_brief.py delegates ta-sweep-results.json write to ta_sweep_batch.py (removes duplicate writer)"
```
