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

    conn.execute("""
    CREATE TABLE IF NOT EXISTS intelligence_event (
        event_id TEXT PRIMARY KEY,
        event_sequence INTEGER NOT NULL UNIQUE,
        instrument_id TEXT,
        event_type TEXT NOT NULL CHECK (
            event_type IN ('RESEARCH_IMPORT', 'NEWS_SWEEP', 'EARNINGS', 'VALUATION_UPDATE', 'TECHNICAL_SWEEP', 'PORTFOLIO_DECISION', 'THESIS_UPDATE', 'MACRO_EVENT', 'REVIEW_DAILY', 'REVIEW_WEEKLY', 'PREDICTION_CLAIM', 'PREDICTION_GRADED')
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
    return conn
