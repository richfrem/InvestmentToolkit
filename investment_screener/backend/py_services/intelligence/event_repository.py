"""All ``intelligence_event`` table reads and writes live here.

Per ADR-028, every SQL statement touching ``intelligence_event`` (and its
``intelligence_event_fts`` shadow table) should be routed through this
module so callers never write raw SQL against those tables directly.
"""


def insert_event(conn, event: dict) -> bool:
    """Insert one event row into ``intelligence_event``.

    Uses ``INSERT OR IGNORE`` so a row that violates a UNIQUE constraint
    (duplicate ``event_id``/``event_sequence``/``idempotency_key``) or a
    CHECK constraint (invalid ``event_type``/``status`` taxonomy value) is
    skipped rather than raising ``IntegrityError``. Callers (see
    ``replay_ledger.py``) must inspect the return value to know whether the
    row was actually persisted before advancing any checkpoint bookkeeping.

    Args:
        conn: Open sqlite3 connection with the read-model schema applied.
        event: Dict with keys matching (a subset of) the
            ``intelligence_event`` columns. Missing optional keys are
            treated as ``NULL``.

    Returns:
        True if the row was actually inserted (``cursor.rowcount == 1``),
        False if it was rejected/ignored.
    """
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
    """Full-text search over event titles/bodies via the FTS5 shadow table.

    Args:
        conn: Open sqlite3 connection with the read-model schema applied.
        query: FTS5 MATCH query string.

    Returns:
        A list of dicts, one per matching event, with keys ``event_id``,
        ``title``, ``body_markdown``, ``effective_at``.
    """
    cursor = conn.execute("""
        SELECT ie.event_id, ie.title, ie.body_markdown, ie.effective_at
        FROM intelligence_event_fts fts
        JOIN intelligence_event ie ON ie.rowid = fts.rowid
        WHERE intelligence_event_fts MATCH ?;
    """, (query,))
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def list_active_events_for_ticker(conn, ticker: str) -> list[dict]:
    """Return all ACTIVE events for a ticker, newest first.

    Args:
        conn: Open sqlite3 connection with the read-model schema applied.
        ticker: Ticker symbol to filter on (joined via ``instrument``).

    Returns:
        A list of dicts, one per matching event, ordered by
        ``effective_at`` descending.
    """
    cursor = conn.execute("""
        SELECT ie.event_id, ie.event_sequence, ie.instrument_id, ie.event_type,
               ie.effective_at, ie.observed_at, ie.ingested_at, ie.source_id,
               ie.confidence_score, ie.status, ie.title, ie.body_markdown,
               ie.payload_json, ie.supersedes_event_id, ie.idempotency_key,
               ie.content_hash
        FROM intelligence_event ie
        JOIN instrument i ON i.instrument_id = ie.instrument_id
        WHERE i.ticker = ? AND ie.status = 'ACTIVE'
        ORDER BY ie.effective_at DESC;
    """, (ticker,))
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
