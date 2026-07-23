"""Real (non-mocked) test for daily_brief.py's REVIEW_DAILY dual-write block.

Isolates the append_event -> replay_events_to_db sequence daily_brief.py:636-667
performs, run against a tmp_path JSONL + SQLite pair, so a real row is asserted to land
without depending on daily_brief.py's full external I/O (TV CDP, yfinance, etc.).
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))


def test_review_daily_dual_write_lands_real_row(tmp_path):
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db

    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    brief = {
        "date": "2026-07-23",
        "macro_regime": {"regime": "BULL"},
        "conviction_scores": [{"ticker": "MSFT", "total": 8, "band": "ACCUMULATE"}],
    }

    append_event(
        str(jsonl_path),
        event_type="REVIEW_DAILY",
        effective_at="2026-07-23",
        status="ACTIVE",
        title="Daily Brief for 2026-07-23",
        body_markdown="Generated daily brief summary metrics.",
        ticker=None,
        source_id="daily_brief",
        payload=brief,
        idempotency_key="daily-brief-2026-07-23",
    )

    conn = initialize_db(str(db_path))
    try:
        replay_events_to_db(str(jsonl_path), conn)
        row = conn.execute(
            "SELECT event_type, effective_at, payload_json FROM intelligence_event "
            "WHERE idempotency_key = ?",
            ("daily-brief-2026-07-23",),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == "REVIEW_DAILY"
    assert row[1] == "2026-07-23"
    assert json.loads(row[2])["conviction_scores"][0]["ticker"] == "MSFT"


def test_review_daily_dual_write_is_idempotent_on_rerun(tmp_path):
    """A second append_event call with the same idempotency_key must not create a duplicate row."""
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db

    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    brief = {"date": "2026-07-23", "macro_regime": {"regime": "BULL"}, "conviction_scores": []}

    for _ in range(2):
        append_event(
            str(jsonl_path),
            event_type="REVIEW_DAILY",
            effective_at="2026-07-23",
            status="ACTIVE",
            title="Daily Brief for 2026-07-23",
            body_markdown="Generated daily brief summary metrics.",
            ticker=None,
            source_id="daily_brief",
            payload=brief,
            idempotency_key="daily-brief-2026-07-23",
        )

    conn = initialize_db(str(db_path))
    try:
        replay_events_to_db(str(jsonl_path), conn)
        count = conn.execute(
            "SELECT COUNT(*) FROM intelligence_event WHERE idempotency_key = ?",
            ("daily-brief-2026-07-23",),
        ).fetchone()[0]
    finally:
        conn.close()

    assert count == 1
