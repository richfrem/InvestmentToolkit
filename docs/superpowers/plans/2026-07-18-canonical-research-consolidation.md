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

### Task 4: Rebuild DB & Backup Verification Script

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
