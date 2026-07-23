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
        event: Dict with keys matching the ``intelligence_event`` columns.
            All nullable columns (``instrument_id``, ``observed_at``,
            ``source_id``, ``confidence_score``, ``payload_json``,
            ``supersedes_event_id``, ``idempotency_key``) are persisted;
            any missing optional key is treated as ``NULL``.

    Returns:
        True if the row was actually inserted (``cursor.rowcount == 1``),
        False if it was rejected/ignored.
    """
    params = {
        "instrument_id": event.get("instrument_id"),
        "observed_at": event.get("observed_at"),
        "source_id": event.get("source_id"),
        "confidence_score": event.get("confidence_score"),
        "payload_json": event.get("payload_json"),
        "supersedes_event_id": event.get("supersedes_event_id"),
        "idempotency_key": event.get("idempotency_key"),
        **event,
    }
    cursor = conn.execute("""
        INSERT OR IGNORE INTO intelligence_event
        (event_id, event_sequence, instrument_id, event_type, effective_at, observed_at,
         ingested_at, source_id, confidence_score, status, title, body_markdown,
         payload_json, supersedes_event_id, idempotency_key, content_hash)
        VALUES (:event_id, :event_sequence, :instrument_id, :event_type, :effective_at,
                :observed_at, :ingested_at, :source_id, :confidence_score, :status, :title,
                :body_markdown, :payload_json, :supersedes_event_id, :idempotency_key,
                :content_hash);
    """, params)
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


def get_latest_event_by_type(conn, event_type: str) -> dict | None:
    """Retrieve the latest active event of the specified event_type."""
    cursor = conn.execute("""
        SELECT ie.event_id, ie.event_sequence, ie.instrument_id, ie.event_type,
               ie.effective_at, ie.observed_at, ie.ingested_at, ie.source_id,
               ie.confidence_score, ie.status, ie.title, ie.body_markdown,
               ie.payload_json, ie.supersedes_event_id, ie.idempotency_key,
               ie.content_hash
        FROM intelligence_event ie
        WHERE ie.event_type = ? AND ie.status = 'ACTIVE'
        ORDER BY ie.effective_at DESC, ie.ingested_at DESC LIMIT 1;
    """, (event_type,))
    columns = [d[0] for d in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None


def list_active_events_by_type(conn, event_type: str) -> list[dict]:
    """Return every ACTIVE event of the given type, newest first.

    Args:
        conn: Open sqlite3 connection with the read-model schema applied.
        event_type: Event type to filter on (e.g. ``REVIEW_DAILY``).

    Returns:
        List of event dicts ordered by effective_at DESC, ingested_at DESC.
    """
    cursor = conn.execute("""
        SELECT ie.event_id, ie.event_sequence, ie.instrument_id, ie.event_type,
               ie.effective_at, ie.observed_at, ie.ingested_at, ie.source_id,
               ie.confidence_score, ie.status, ie.title, ie.body_markdown,
               ie.payload_json, ie.supersedes_event_id, ie.idempotency_key,
               ie.content_hash
        FROM intelligence_event ie
        WHERE ie.event_type = ? AND ie.status = 'ACTIVE'
        ORDER BY ie.effective_at DESC, ie.ingested_at DESC;
    """, (event_type,))
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def list_tickers_with_active_event_type(conn, event_type: str) -> list[str]:
    """Return distinct tickers holding at least one ACTIVE event of the given type.

    Args:
        conn: Open sqlite3 connection with the read-model schema applied.
        event_type: Event type to filter on (e.g. ``RESEARCH_IMPORT``).

    Returns:
        Sorted list of distinct ticker symbols.
    """
    cursor = conn.execute("""
        SELECT DISTINCT i.ticker
        FROM intelligence_event ie
        JOIN instrument i ON i.instrument_id = ie.instrument_id
        WHERE ie.event_type = ? AND ie.status = 'ACTIVE'
        ORDER BY i.ticker;
    """, (event_type,))
    return [row[0] for row in cursor.fetchall()]


def get_latest_event_by_type_and_ticker(conn, event_type: str, ticker: str) -> dict | None:
    """Retrieve the latest active event of the specified type for a specific ticker."""
    cursor = conn.execute("""
        SELECT ie.event_id, ie.event_sequence, ie.instrument_id, ie.event_type,
               ie.effective_at, ie.observed_at, ie.ingested_at, ie.source_id,
               ie.confidence_score, ie.status, ie.title, ie.body_markdown,
               ie.payload_json, ie.supersedes_event_id, ie.idempotency_key,
               ie.content_hash
        FROM intelligence_event ie
        JOIN instrument i ON i.instrument_id = ie.instrument_id
        WHERE ie.event_type = ? AND i.ticker = ? AND ie.status = 'ACTIVE'
        ORDER BY ie.effective_at DESC, ie.ingested_at DESC LIMIT 1;
    """, (event_type, ticker))
    columns = [d[0] for d in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None


