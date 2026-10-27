#!/usr/bin/env python3
"""Purpose: publish dated research into the intelligence ledger (intelligence.sqlite).

Layer: Stock Valuation / Persistence.
Usage: python3 persist_research.py --file TICKER_YYYY-MM-DD.md --db PATH.
Key Functions: persist_research — append or correct the report event; main — CLI entry point.
Key Input Dependencies: reviewed report file, intelligence event_store API, intelligence.sqlite
    (explicit main-checkout path when run from a worktree).
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
from query_ledger_research import DATED_FILE_RE


def persist_research(report_path: Path, db_path: Path) -> dict:
    """Publish a reviewed report; retry unchanged content or supersede a correction.

    Args:
        report_path: Dated report file to read without moving or deleting it.
        db_path: The intelligence ledger database.

    Returns:
        Publication receipt with event ID and filename.
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
            conn, idempotency_key=f"research-import-{report_path.name}",
            payload={"filename": report_path.name, "bodySha256": hashlib.sha256(body.encode()).hexdigest()},
            event_type="RESEARCH_IMPORT", effective_at=effective_at, status="ACTIVE",
            title=f"{ticker} Research {effective_at}", body_markdown=body,
            ticker=ticker, source_id="stock-valuation:research",
        )
        return {"status": "success", "event_id": event_id, "filename": report_path.name}
    finally:
        conn.close()


def main() -> None:
    """Read explicit file/data paths and print a machine-readable receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=ROOT / "investment_screener/backend/data/intelligence.sqlite")
    args = parser.parse_args()
    print(json.dumps(persist_research(args.file, args.db)))


if __name__ == "__main__":
    main()
