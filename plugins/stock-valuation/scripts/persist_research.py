#!/usr/bin/env python3
"""Purpose: publish dated research through the canonical ledger into SQLite.

Layer: Stock Valuation / Persistence.
Usage: python3 persist_research.py --file TICKER_YYYY-MM-DD.md --db PATH --jsonl PATH.
Key Functions: persist_research — append/correct and replay; main — CLI entry point.
Key Input Dependencies: reviewed report file, intelligence event_store/replay APIs,
    observations.jsonl and intelligence.sqlite (explicit main paths from worktrees).
"""
import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "investment_screener/backend/py_services"))
from intelligence.db_client import initialize_db
from intelligence.event_store import append_or_supersede_event
from intelligence.replay_ledger import replay_events_to_db
from query_ledger_research import DATED_FILE_RE


def persist_research(report_path: Path, db_path: Path, ledger_path: Path) -> dict:
    """Publish a reviewed report; retry unchanged content or supersede a correction.

    Args:
        report_path: Dated report file to read without moving or deleting it.
        db_path: Actual intelligence SQLite read model.
        ledger_path: Canonical observations event ledger.

    Returns:
        Publication receipt with event ID, filename and replay result.
    """
    match = DATED_FILE_RE.fullmatch(report_path.name)
    if not match:
        raise ValueError("Research file must be TICKER_YYYY-MM-DD.md")
    ticker, effective_at = match.groups()
    date.fromisoformat(effective_at)
    body = report_path.read_text(encoding="utf-8")
    if not body.strip():
        raise ValueError("Research report must not be empty")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = initialize_db(str(db_path))
    try:
        event_id = append_or_supersede_event(
            str(ledger_path), idempotency_key=f"research-import-{report_path.name}",
            payload={"filename": report_path.name, "bodySha256": hashlib.sha256(body.encode()).hexdigest()},
            event_type="RESEARCH_IMPORT", effective_at=effective_at, status="ACTIVE",
            title=f"{ticker} Research {effective_at}", body_markdown=body,
            ticker=ticker, source_id="stock-valuation:research",
        )
        replay = replay_events_to_db(str(ledger_path), conn)
        if replay["skipped"]:
            raise RuntimeError(f"Ledger replay skipped events: {replay['skipped']}")
        return {"status": "success", "event_id": event_id, "filename": report_path.name, "replay": replay}
    finally:
        conn.close()


def main() -> None:
    """Read explicit file/data paths and print a machine-readable receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=ROOT / "investment_screener/backend/data/intelligence.sqlite")
    parser.add_argument("--jsonl", type=Path, default=ROOT / "investment_screener/backend/data/observations.jsonl")
    args = parser.parse_args()
    print(json.dumps(persist_research(args.file, args.db, args.jsonl)))


if __name__ == "__main__":
    main()
