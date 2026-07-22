"""All ``investment`` table reads and writes live here, mirroring
``py_services/intelligence/instrument_repository.py``'s anti-duplication rule (ADR-028,
extended to the domain-model package by ADR-029).
"""

import sqlite3
from datetime import datetime, timezone


def resolve_investment(
    conn: sqlite3.Connection,
    symbol: str,
    asset_class: str = "EQUITY",
    currency: str = "USD",
    name: str | None = None,
) -> str:
    """Return the ``investment_id`` for a symbol, inserting it if new.

    Idempotent: calling this twice for the same symbol returns the same
    ``investment_id`` and does not insert a duplicate row.
    """
    cursor = conn.execute("SELECT investment_id FROM investment WHERE symbol = ?;", (symbol,))
    row = cursor.fetchone()
    if row:
        return row[0]
    investment_id = symbol.upper()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO investment (investment_id, symbol, name, asset_class, currency, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        (investment_id, symbol, name or symbol, asset_class, currency, now),
    )
    conn.commit()
    return investment_id


def get_investment(conn: sqlite3.Connection, investment_id: str) -> dict | None:
    """Return the investment row as a dict, or ``None`` if it doesn't exist."""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM investment WHERE investment_id = ?;", (investment_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


_UPDATABLE_FIELDS = {
    "lifecycle_status", "target_weight", "target_action",
    "standing_decision_type", "standing_decision_reason",
    "standing_decision_source", "standing_decision_review",
    "pillar_id", "sub_strategy_id", "thesis_for_inclusion",
    "agent_rationale", "is_watchlisted", "watchlist_added_at",
    "thesis_breaker_status", "sector", "industry",
}


def update_investment_fields(conn: sqlite3.Connection, investment_id: str, **fields) -> None:
    """Update any subset of the named investment columns, leaving the rest untouched.

    Raises ValueError on an unrecognized field name -- fail loud rather than
    silently no-op, since a silently-dropped standing_decision_* update would
    violate CLAUDE.md rule #8 (the standingDecision anchor rule).
    """
    unknown = set(fields) - _UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"Unknown investment field(s): {sorted(unknown)}")
    if not fields:
        return
    fields = {**fields, "updated_at": datetime.now(timezone.utc).isoformat()}
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    params = list(fields.values()) + [investment_id]
    conn.execute(
        f"UPDATE investment SET {set_clause} WHERE investment_id = ?;", params,
    )
    conn.commit()


def update_investment_sector(
    conn: sqlite3.Connection,
    investment_id: str,
    sector: str | None,
    industry: str | None,
) -> None:
    """Persist the yfinance/SECTOR_OVERRIDES-resolved sector/industry for an
    investment (Wave 3 completion). Convenience wrapper over
    ``update_investment_fields`` so the /refresh-prices price-refresh path — the
    real code that already resolves sector/industry via fetch_portfolio_heatmap.py
    — has a single named write for these two enriched-display columns.

    A ``None``/``"Unknown"`` value is written through as-is (the reader falls back
    to "Unknown"), never silently dropped, so a genuine "sector could not be
    resolved" fact is distinguishable from "never refreshed".
    """
    update_investment_fields(conn, investment_id, sector=sector, industry=industry)


def list_investments(
    conn: sqlite3.Connection,
    lifecycle_status: str | None = None,
    pillar_id: str | None = None,
    is_watchlisted: bool | None = None,
) -> list[dict]:
    """Bulk-read helper for consumers that currently iterate the whole
    holdings array (e.g. scan_opportunities.py, weekly_review.py) rather than
    looking up a single ticker."""
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM investment WHERE 1=1"
    params: list = []
    if lifecycle_status is not None:
        query += " AND lifecycle_status = ?"
        params.append(lifecycle_status)
    if pillar_id is not None:
        query += " AND pillar_id = ?"
        params.append(pillar_id)
    if is_watchlisted is not None:
        query += " AND is_watchlisted = ?"
        params.append(int(is_watchlisted))
    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
