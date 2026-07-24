import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.migrations.widen_event_type_add_predictions import (  # noqa: E402
    widen_event_type_constraint,
)
from intelligence.event_repository import list_active_events_by_type  # noqa: E402
from migrate_predictions_to_ledger import migrate  # noqa: E402


def _write_fixture_predictions(path):
    records = [
        {"id": "AAPL:action_rating:2026-01-01", "ticker": "AAPL", "type": "action_rating",
         "claimDate": "2026-01-01", "direction": "bullish", "horizonDays": 90},
        {"id": "MSFT:dcf_fair_value:2026-01-02", "ticker": "MSFT", "type": "dcf_fair_value",
         "claimDate": "2026-01-02", "direction": "bearish", "horizonDays": 180},
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return records


def test_migrate_dry_run_reports_counts_without_writing(tmp_path):
    predictions_path = tmp_path / "predictions.jsonl"
    _write_fixture_predictions(predictions_path)
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    report = migrate(predictions_path, jsonl_path, db_path, dry_run=True)

    assert report["source_count"] == 2
    assert not jsonl_path.exists()


def test_migrate_write_widens_constraint_then_backfills_all_rows(tmp_path):
    predictions_path = tmp_path / "predictions.jsonl"
    _write_fixture_predictions(predictions_path)
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    conn = initialize_db(str(db_path))
    # Use a high, non-colliding event_sequence: in real usage the jsonl ledger and the
    # DB are always kept in sync via append_event/replay (Tasks 2-3), so a pre-existing
    # DB row's sequence would already be reflected in the jsonl file too. This raw
    # fixture insert bypasses the jsonl file entirely (by design, to isolate the
    # widen-preserves-existing-rows behavior), so we pick a sequence number that can't
    # collide with the fresh event_sequence=1/2 the migration assigns to the two
    # fixture prediction rows below.
    conn.execute(
        "INSERT INTO intelligence_event (event_id, event_sequence, event_type, effective_at, "
        "ingested_at, status, content_hash) VALUES ('r-1', 100, 'RESEARCH_IMPORT', "
        "'2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 'ACTIVE', 'hash-1');"
    )
    conn.commit()
    conn.close()

    report = migrate(predictions_path, jsonl_path, db_path, dry_run=False)

    assert report["written_count"] == 2
    conn = initialize_db(str(db_path))
    events = list_active_events_by_type(conn, "PREDICTION_CLAIM")
    assert len(events) == 2
    tickers = {json.loads(e["payload_json"])["ticker"] for e in events}
    assert tickers == {"AAPL", "MSFT"}
    # The pre-existing RESEARCH_IMPORT row must survive the widening rebuild untouched.
    research_events = list_active_events_by_type(conn, "RESEARCH_IMPORT")
    assert len(research_events) == 1


def test_migrate_is_idempotent_on_rerun(tmp_path):
    predictions_path = tmp_path / "predictions.jsonl"
    _write_fixture_predictions(predictions_path)
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    migrate(predictions_path, jsonl_path, db_path, dry_run=False)
    report_second = migrate(predictions_path, jsonl_path, db_path, dry_run=False)

    conn = initialize_db(str(db_path))
    events = list_active_events_by_type(conn, "PREDICTION_CLAIM")
    assert len(events) == 2  # no duplicates from the idempotency_key dedup in append_event
