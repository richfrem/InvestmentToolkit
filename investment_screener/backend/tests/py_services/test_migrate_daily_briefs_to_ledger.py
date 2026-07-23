"""Tests for migrate_daily_briefs_to_ledger.py — mirrors test_migrate_ta_sweep_to_ledger.py's
structure for the daily-briefs domain (Wave 5C)."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from migrate_daily_briefs_to_ledger import migrate


def _write_brief(briefs_dir: Path, date_str: str, regime: str) -> None:
    briefs_dir.mkdir(parents=True, exist_ok=True)
    (briefs_dir / f"{date_str}.json").write_text(json.dumps({
        "date": date_str,
        "macro_regime": {"regime": regime},
        "conviction_scores": [{"ticker": "MSFT", "total": 7, "band": "MAINTAIN"}],
    }))


def test_migrate_dry_run_reports_counts_without_writing(tmp_path):
    briefs_dir = tmp_path / "daily-briefs"
    _write_brief(briefs_dir, "2026-07-17", "BULL")
    _write_brief(briefs_dir, "2026-07-18", "CONGESTION")
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    report = migrate(briefs_dir, jsonl_path, db_path, dry_run=True)

    assert report["source_count"] == 2
    assert report["written_count"] == 0
    assert not jsonl_path.exists()
    assert not db_path.exists()


def test_migrate_write_creates_real_rows(tmp_path):
    briefs_dir = tmp_path / "daily-briefs"
    _write_brief(briefs_dir, "2026-07-17", "BULL")
    _write_brief(briefs_dir, "2026-07-18", "CONGESTION")
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    report = migrate(briefs_dir, jsonl_path, db_path, dry_run=False)

    assert report["source_count"] == 2
    assert report["written_count"] == 2

    import sqlite3
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT effective_at, idempotency_key FROM intelligence_event "
            "WHERE event_type = 'REVIEW_DAILY' ORDER BY effective_at"
        ).fetchall()
    finally:
        conn.close()
    assert rows == [
        ("2026-07-17", "daily-brief-2026-07-17"),
        ("2026-07-18", "daily-brief-2026-07-18"),
    ]


def test_migrate_write_is_idempotent_against_a_real_producer_rerun(tmp_path):
    """A future real daily_brief.py run for an already-backfilled date must not double-write —
    both use the same idempotency_key format (daily-brief-{date})."""
    briefs_dir = tmp_path / "daily-briefs"
    _write_brief(briefs_dir, "2026-07-17", "BULL")
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    migrate(briefs_dir, jsonl_path, db_path, dry_run=False)

    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db

    append_event(
        str(jsonl_path), event_type="REVIEW_DAILY", effective_at="2026-07-17", status="ACTIVE",
        title="Daily Brief for 2026-07-17", body_markdown="rerun",
        ticker=None, source_id="daily_brief", payload={"date": "2026-07-17"},
        idempotency_key="daily-brief-2026-07-17",
    )
    conn = initialize_db(str(db_path))
    try:
        replay_events_to_db(str(jsonl_path), conn)
        count = conn.execute(
            "SELECT COUNT(*) FROM intelligence_event WHERE idempotency_key = ?",
            ("daily-brief-2026-07-17",),
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 1


def test_migrate_skips_files_missing_date_field(tmp_path):
    briefs_dir = tmp_path / "daily-briefs"
    briefs_dir.mkdir(parents=True)
    (briefs_dir / "2026-07-19.json").write_text(json.dumps({"macro_regime": {"regime": "BULL"}}))
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    report = migrate(briefs_dir, jsonl_path, db_path, dry_run=True)

    assert report["source_count"] == 1
    assert report["written_count"] == 0
