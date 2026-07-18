import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from replay_ledger import replay_events_to_db  # noqa: E402
from db_client import initialize_db  # noqa: E402


def test_replay_loop(tmp_path):
    jsonl_file = tmp_path / "test_observations.jsonl"
    db_path = tmp_path / "test_intelligence.sqlite"

    event = {
        "event_id": "evt_1",
        "event_sequence": 1,
        "ticker": "PLTR",
        "event_type": "NEWS_SWEEP",
        "effective_at": "2026-07-18",
        "ingested_at": "2026-07-18",
        "status": "ACTIVE",
        "title": "PLTR Contract",
        "body_markdown": "Palantir deal",
        "content_hash": "hash_1",
    }
    jsonl_file.write_text(json.dumps(event) + "\n")

    conn = initialize_db(str(db_path))
    replay_events_to_db(str(jsonl_file), conn)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM intelligence_event;")
    assert cursor.fetchone()[0] == 1


def test_replay_loop_records_checkpoint(tmp_path):
    jsonl_file = tmp_path / "test_observations.jsonl"
    db_path = tmp_path / "test_intelligence.sqlite"

    event = {
        "event_id": "evt_1",
        "event_sequence": 1,
        "ticker": "PLTR",
        "event_type": "NEWS_SWEEP",
        "effective_at": "2026-07-18",
        "ingested_at": "2026-07-18",
        "status": "ACTIVE",
        "title": "PLTR Contract",
        "body_markdown": "Palantir deal",
        "content_hash": "hash_1",
    }
    jsonl_file.write_text(json.dumps(event) + "\n")

    conn = initialize_db(str(db_path))
    replay_events_to_db(str(jsonl_file), conn)

    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_event_sequence, last_event_id FROM ledger_checkpoint WHERE checkpoint_id = 'global';"
    )
    row = cursor.fetchone()
    assert row == (1, "evt_1")


def test_replay_loop_is_idempotent_on_rerun(tmp_path):
    jsonl_file = tmp_path / "test_observations.jsonl"
    db_path = tmp_path / "test_intelligence.sqlite"

    event = {
        "event_id": "evt_1",
        "event_sequence": 1,
        "ticker": "PLTR",
        "event_type": "NEWS_SWEEP",
        "effective_at": "2026-07-18",
        "ingested_at": "2026-07-18",
        "status": "ACTIVE",
        "title": "PLTR Contract",
        "body_markdown": "Palantir deal",
        "content_hash": "hash_1",
    }
    jsonl_file.write_text(json.dumps(event) + "\n")

    conn = initialize_db(str(db_path))
    replay_events_to_db(str(jsonl_file), conn)
    replay_events_to_db(str(jsonl_file), conn)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM intelligence_event;")
    assert cursor.fetchone()[0] == 1
