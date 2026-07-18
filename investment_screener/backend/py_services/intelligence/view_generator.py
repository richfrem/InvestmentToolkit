"""Renders generated research view files from the ``intelligence.sqlite`` read model.

Per ADR-028, this module never issues its own SQL against
``intelligence_event`` — it consumes only the repository function
``event_repository.list_active_events_for_ticker()``, keeping
``event_repository.py`` the single place that owns that table's queries.
"""

from datetime import datetime, timezone
from pathlib import Path

from intelligence.event_repository import list_active_events_for_ticker


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
