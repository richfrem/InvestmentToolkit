import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.event_store import append_event  # noqa: E402


def test_append_event_assigns_incrementing_sequence(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    event_id_1 = append_event(
        str(jsonl_path), event_type="NEWS_SWEEP", effective_at="2026-07-18",
        status="ACTIVE", title="First", body_markdown="Body 1", ticker="PLTR",
    )
    event_id_2 = append_event(
        str(jsonl_path), event_type="NEWS_SWEEP", effective_at="2026-07-18",
        status="ACTIVE", title="Second", body_markdown="Body 2", ticker="PLTR",
    )
    lines = [json.loads(l) for l in jsonl_path.read_text().splitlines()]
    assert len(lines) == 2
    assert lines[0]["event_sequence"] == 1
    assert lines[1]["event_sequence"] == 2
    assert lines[0]["event_id"] == event_id_1
    assert lines[1]["event_id"] == event_id_2
    assert lines[0]["content_hash"] != lines[1]["content_hash"]


def test_append_event_idempotency_key_dedups(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    id_1 = append_event(
        str(jsonl_path), event_type="NEWS_SWEEP", effective_at="2026-07-18",
        status="ACTIVE", title="First", body_markdown="Body 1", ticker="PLTR",
        idempotency_key="dedup-key-1",
    )
    id_2 = append_event(
        str(jsonl_path), event_type="NEWS_SWEEP", effective_at="2026-07-18",
        status="ACTIVE", title="First (retry)", body_markdown="Body 1", ticker="PLTR",
        idempotency_key="dedup-key-1",
    )
    lines = jsonl_path.read_text().splitlines()
    assert len(lines) == 1
    assert id_1 == id_2
