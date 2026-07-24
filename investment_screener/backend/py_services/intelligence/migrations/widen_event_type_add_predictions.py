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
