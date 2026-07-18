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
