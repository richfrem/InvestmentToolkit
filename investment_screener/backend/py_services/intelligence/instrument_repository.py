"""All ``instrument`` table reads and writes live here (ADR-028)."""


def resolve_instrument(conn, ticker: str, exchange: str | None = None, name: str | None = None) -> str:
    """Return the ``instrument_id`` for a ticker, inserting it if new.

    Idempotent: calling this twice for the same ticker returns the same
    ``instrument_id`` and does not insert a duplicate row.

    Args:
        conn: Open sqlite3 connection with the read-model schema applied.
        ticker: Ticker symbol to resolve.
        exchange: Optional exchange code, used to build a stable
            ``instrument_id`` for newly-created rows.
        name: Optional display name; defaults to ``ticker`` if omitted.

    Returns:
        The resolved (or newly created) ``instrument_id``.
    """
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
