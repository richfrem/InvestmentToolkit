"""Tests for migrate_daily_briefs_to_ledger.py (daily-brief snapshot files -> REVIEW_DAILY events)."""
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
    db_path = tmp_path / "intelligence.sqlite"

    report = migrate(briefs_dir, db_path, dry_run=True)

    assert report["source_count"] == 2
    assert report["written_count"] == 0
    assert report["to_write_count"] == 2
    assert not db_path.exists()


def test_migrate_write_creates_real_rows(tmp_path):
    briefs_dir = tmp_path / "daily-briefs"
    _write_brief(briefs_dir, "2026-07-17", "BULL")
    _write_brief(briefs_dir, "2026-07-18", "CONGESTION")
    db_path = tmp_path / "intelligence.sqlite"

    report = migrate(briefs_dir, db_path, dry_run=False)

    assert report["source_count"] == 2
    assert report["written_count"] == 2
    assert report["already_present"] == 0

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
    db_path = tmp_path / "intelligence.sqlite"
    migrate(briefs_dir, db_path, dry_run=False)

    from intelligence.event_store import append_event
    from intelligence.db_client import initialize_db

    conn = initialize_db(str(db_path))
    try:
        append_event(
            conn, event_type="REVIEW_DAILY", effective_at="2026-07-17", status="ACTIVE",
            title="Daily Brief for 2026-07-17", body_markdown="rerun",
            ticker=None, source_id="daily_brief", payload={"date": "2026-07-17"},
            idempotency_key="daily-brief-2026-07-17",
        )
        count = conn.execute(
            "SELECT COUNT(*) FROM intelligence_event WHERE idempotency_key = ?",
            ("daily-brief-2026-07-17",),
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 1


def test_migrate_second_run_writes_nothing_and_reports_already_present(tmp_path):
    briefs_dir = tmp_path / "daily-briefs"
    _write_brief(briefs_dir, "2026-07-17", "BULL")
    db_path = tmp_path / "intelligence.sqlite"
    migrate(briefs_dir, db_path, dry_run=False)

    report = migrate(briefs_dir, db_path, dry_run=False)

    assert report["written_count"] == 0 and report["already_present"] == 1


def test_migrate_skips_files_missing_date_field(tmp_path):
    briefs_dir = tmp_path / "daily-briefs"
    briefs_dir.mkdir(parents=True)
    (briefs_dir / "2026-07-19.json").write_text(json.dumps({"macro_regime": {"regime": "BULL"}}))
    db_path = tmp_path / "intelligence.sqlite"

    report = migrate(briefs_dir, db_path, dry_run=True)

    assert report["source_count"] == 1
    assert report["written_count"] == 0
