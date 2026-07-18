# Canonical Research Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the workstation intelligence folder system to consolidate research observations into a SQLite database read-model mapped from a JSONL event stream, with generated split Markdown views.

**Architecture:** Use a hybrid event sourcing model where observations are written to an append-only JSONL master log, SQLite acts as a query index (replayed from JSONL), and Markdown views are generated summaries.

**Tech Stack:** SQLite, Python, Node.js/Express, JSONL.

## Global Constraints
* No production code without a failing test first.
* All SQLite writes must utilize Write-Ahead Logging (WAL) mode for concurrency.
* Strict event type taxonomy and status constraints must be enforced at the database level.
* No raw dated research markdown files are to be deleted until the deterministic migration verification gate passes.

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
import pytest
from db_client import initialize_db

def test_db_initialization(tmp_path):
    db_path = tmp_path / "test_intelligence.sqlite"
    conn = initialize_db(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='instrument';")
    assert cursor.fetchone() is not None
```

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
        processed_at TEXT NOT NULL
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

### Task 2: Implement FTS5 Table and Triggers

**Files:**
- Modify: `investment_screener/backend/py_services/db_client.py`
- Test: `investment_screener/backend/tests/py_services/test_db_client.py`

- [ ] **Step 1: Write failing test for FTS sync**

Add to `test_db_client.py`:
```python
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
    
    # Check if FTS indexes automatically
    cursor = conn.cursor()
    cursor.execute("SELECT rowid FROM intelligence_event_fts WHERE intelligence_event_fts MATCH 'Nvidia';")
    assert cursor.fetchone() is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest investment_screener/backend/tests/py_services/test_db_client.py -k test_fts_search_sync -v`
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

    # Setup triggers
    conn.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_intelligence_event_ai AFTER INSERT ON intelligence_event BEGIN
        INSERT INTO intelligence_event_fts(rowid, title, body_markdown)
        VALUES (new.rowid, new.title, new.body_markdown);
    END;
    """)
    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest investment_screener/backend/tests/py_services/test_db_client.py -k test_fts_search_sync -v`
Expected: PASS

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

def replay_events_to_db(jsonl_path, conn):
    # Load last sequence offset from checkpoint
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(last_event_sequence) FROM ledger_checkpoint;")
    row = cursor.fetchone()
    last_seq = row[0] if row and row[0] is not None else 0
    
    with open(jsonl_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            event = json.loads(line)
            if event["event_sequence"] <= last_seq:
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
            
    # Update checkpoint
    conn.execute("INSERT OR REPLACE INTO ledger_checkpoint VALUES ('global', ?, 'latest', 1, '2026-07-18');", (event["event_sequence"],))
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
