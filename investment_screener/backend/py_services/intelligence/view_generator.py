"""Renders generated research view files from the ``intelligence.sqlite`` read model.

Per ADR-028, this module never issues its own SQL against
``intelligence_event`` — it consumes only the repository function
``event_repository.list_active_events_for_ticker()``, keeping
``event_repository.py`` the single place that owns that table's queries.
"""

from datetime import datetime, timezone
from pathlib import Path

from intelligence.event_repository import list_active_events_for_ticker
from intelligence.db_client import initialize_db
from intelligence.replay_ledger import replay_events_to_db


def render_ticker_views(ticker: str, conn, output_dir: str) -> None:
    """Write ``{ticker}.summary.md`` and ``{ticker}.timeline.md`` to ``output_dir``.

    Args:
        conn: Open sqlite3 connection with the read-model schema applied.
        ticker: Ticker symbol whose ACTIVE events should be rendered.
        output_dir: Directory to write the generated ``.summary.md`` and
            ``.timeline.md`` files into. Must already exist.
    """
    events = list_active_events_for_ticker(conn, ticker)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = Path(output_dir)

    summary = (
        "---\n"
        "schemaVersion: 1\n"
        "documentType: generated-research-summary\n"
        f"ticker: \"{ticker}\"\n"
        f"generatedAt: \"{generated_at}\"\n"
        "---\n\n"
        f"# {ticker} Canonical Research Summary\n\n"
        "*This file is a generated view. Do not edit directly. Authoritative observations are "
        "stored in the JSONL event ledger and indexed in `intelligence.sqlite`.*\n\n"
        f"{events[0]['body_markdown'] if events else '_No active research events yet._'}\n"
    )
    (out / f"{ticker}.summary.md").write_text(summary)

    timeline_lines = [f"# {ticker} Research Timeline\n"]
    for event in events:
        timeline_lines.append(f"\n## {event['effective_at']} — {event['title']}\n\n{event['body_markdown']}\n")
    (out / f"{ticker}.timeline.md").write_text("".join(timeline_lines))


def _default_data_dir() -> Path:
    """Return the canonical ``investment_screener/backend/data`` directory.

    Derived from this file's location so defaults work regardless of the
    caller's cwd, per the convention used by ``market_regime.py`` et al.

    Returns:
        The repo-relative default data directory path.
    """
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "investment_screener/backend/data"


def _main() -> None:
    """CLI entry point: replay the ledger, then render one ticker's views.

    Thin wrapper for SKILL.md-driven callers (see
    ``plugins/stock-valuation/skills/stock_valuation/SKILL.md`` and
    ``.../stock-research/SKILL.md``) that shell out via
    ``python3 -m intelligence.view_generator {TICKER}`` after appending a
    new event via ``intelligence.event_store``. Opens (creating if needed)
    the SQLite read model, replays any not-yet-applied events from the
    JSONL ledger via ``replay_ledger.replay_events_to_db`` (idempotent —
    safe to call every time), then calls ``render_ticker_views`` so the
    freshly-appended event is reflected in the generated
    ``{ticker}.summary.md`` / ``{ticker}.timeline.md`` views.
    """
    import argparse

    data_dir = _default_data_dir()
    parser = argparse.ArgumentParser(
        description="Replay the ledger and render generated research views for one ticker."
    )
    parser.add_argument("ticker")
    parser.add_argument(
        "--jsonl-path",
        dest="jsonl_path",
        default=str(data_dir / "observations.jsonl"),
        help="Path to the observations.jsonl ledger (default: %(default)s).",
    )
    parser.add_argument(
        "--db-path",
        dest="db_path",
        default=str(data_dir / "intelligence.sqlite"),
        help="Path to the intelligence.sqlite read model (default: %(default)s).",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=str(data_dir / "research"),
        help="Directory to write {ticker}.summary.md / {ticker}.timeline.md into (default: %(default)s).",
    )
    args = parser.parse_args()

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    conn = initialize_db(args.db_path)
    try:
        replay_events_to_db(args.jsonl_path, conn)
        render_ticker_views(args.ticker, conn, args.output_dir)
    finally:
        conn.close()


if __name__ == "__main__":
    _main()
