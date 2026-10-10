"""
One-time / repeatable backfill: render generated research views for every
ticker with at least one ACTIVE RESEARCH_IMPORT event in the ledger.

Standalone utility. Imports initialize_db, list_tickers_with_active_event_type and
render_ticker_views from the intelligence package to avoid duplicating schema or query
logic (ADR-028).
"""

from pathlib import Path

from intelligence.db_client import initialize_db
from intelligence.event_repository import list_tickers_with_active_event_type
from intelligence.view_generator import render_ticker_views


def render_all_views(db_path, output_dir, event_type="RESEARCH_IMPORT"):
    """Render summary/timeline views for every ticker holding an ACTIVE event of ``event_type``.

    Args:
        db_path: Path to intelligence.sqlite (created if missing).
        output_dir: Directory to write ``{ticker}.summary.md`` /
            ``{ticker}.timeline.md`` into. Created if missing.
        event_type: Event type used to select which tickers to render.

    Returns:
        Dict with ``rendered_tickers`` (sorted list) and ``count``.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    conn = initialize_db(db_path)
    try:
        tickers = list_tickers_with_active_event_type(conn, event_type)
        for ticker in tickers:
            render_ticker_views(ticker, conn, output_dir)
    finally:
        conn.close()
    return {"rendered_tickers": tickers, "count": len(tickers)}
