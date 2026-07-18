import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.replay_ledger import replay_events_to_db  # noqa: E402
from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.instrument_repository import resolve_instrument  # noqa: E402


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


def test_replay_skips_and_reports_taxonomy_violation_without_advancing_checkpoint(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    jsonl_path.write_text(
        '{"event_id": "evt_1", "event_sequence": 1, "event_type": "BOGUS_NOT_IN_TAXONOMY", '
        '"effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", '
        '"title": "T", "body_markdown": "B", "content_hash": "h1"}\n'
    )
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    result = replay_events_to_db(str(jsonl_path), conn)
    assert result["processed"] == 0
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["event_id"] == "evt_1"
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ledger_checkpoint;")
    assert cursor.fetchone()[0] == 0  # checkpoint must not advance past a rejected event


def test_replay_incremental_resume_picks_up_newly_appended_events(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    jsonl_path.write_text(
        '{"event_id": "evt_1", "event_sequence": 1, "event_type": "NEWS_SWEEP", '
        '"effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", '
        '"title": "T1", "body_markdown": "B1", "content_hash": "h1"}\n'
    )
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    replay_events_to_db(str(jsonl_path), conn)

    with open(jsonl_path, "a") as f:
        f.write(
            '{"event_id": "evt_2", "event_sequence": 2, "event_type": "NEWS_SWEEP", '
            '"effective_at": "2026-07-18", "ingested_at": "2026-07-18", "status": "ACTIVE", '
            '"title": "T2", "body_markdown": "B2", "content_hash": "h2"}\n'
        )
    replay_events_to_db(str(jsonl_path), conn)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM intelligence_event;")
    assert cursor.fetchone()[0] == 2
    cursor.execute("SELECT last_event_sequence FROM ledger_checkpoint WHERE checkpoint_id = 'global';")
    assert cursor.fetchone()[0] == 2


def test_replay_resolves_ticker_to_instrument_id(tmp_path):
    """append_event() writes a "ticker" field, not "instrument_id". Replay
    must resolve the ticker string to a real instrument_id via
    instrument_repository.resolve_instrument() so that
    event_repository.list_active_events_for_ticker() (which joins on
    instrument.instrument_id = intelligence_event.instrument_id) can ever
    match a row written through the sanctioned append_event() API.
    """
    jsonl_path = tmp_path / "observations.jsonl"
    jsonl_path.write_text(
        '{"event_id": "evt_1", "event_sequence": 1, "ticker": "PLTR", '
        '"event_type": "NEWS_SWEEP", "effective_at": "2026-07-18", '
        '"ingested_at": "2026-07-18", "status": "ACTIVE", "title": "T", '
        '"body_markdown": "B", "content_hash": "h1"}\n'
    )
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    replay_events_to_db(str(jsonl_path), conn)

    cursor = conn.cursor()
    cursor.execute("SELECT instrument_id FROM intelligence_event WHERE event_id = 'evt_1';")
    instrument_id = cursor.fetchone()[0]
    assert instrument_id is not None

    expected_instrument_id = resolve_instrument(conn, "PLTR")
    assert instrument_id == expected_instrument_id
