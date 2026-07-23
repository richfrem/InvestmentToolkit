"""Wave 5B Task 1: backfilling the one real ta-sweep-results.json snapshot into the
Intelligence Ledger as TECHNICAL_SWEEP events, using the same append_event/replay
machinery ta_sweep_batch.py's own save_sweep_results() already uses for new sweeps.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from migrate_ta_sweep_to_ledger import migrate  # noqa: E402
from intelligence.db_client import initialize_db  # noqa: E402


FIXTURE_RESULTS = [
    {"ticker": "MSFT", "close": 450.0, "changePct": 1.2, "rsi": 55.0, "action": "HOLD"},
    {"ticker": "NVDA", "close": 900.0, "changePct": -0.5, "rsi": 60.0, "action": "ACCUMULATE"},
]


def _write_source_json(path: Path, scan_date: str, results: list[dict]) -> None:
    path.write_text(json.dumps({
        "timestamp": f"{scan_date}T14:46:53.885784+00:00",
        "scan_date": scan_date,
        "count": len(results),
        "results": results,
    }))


def _seed_instruments(db_path: Path, tickers: list[str]) -> None:
    conn = initialize_db(str(db_path))
    for t in tickers:
        conn.execute(
            "INSERT OR IGNORE INTO instrument VALUES (?, ?, 'NASDAQ', ?, '2026-01-01', NULL);",
            (f"us-{t.lower()}", t, t),
        )
    conn.commit()
    conn.close()


def test_dry_run_reports_counts_without_writing(tmp_path):
    json_path = tmp_path / "ta-sweep-results.json"
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    _write_source_json(json_path, "2026-07-10", FIXTURE_RESULTS)
    _seed_instruments(db_path, ["MSFT", "NVDA"])

    report = migrate(json_path, jsonl_path, db_path, dry_run=True)

    assert report["source_count"] == 2
    assert report["written_count"] == 0
    assert not jsonl_path.exists() or jsonl_path.read_text() == ""
    conn = sqlite3.connect(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM intelligence_event WHERE event_type = 'TECHNICAL_SWEEP';"
    ).fetchone()[0]
    conn.close()
    assert count == 0


def test_real_write_creates_technical_sweep_events(tmp_path):
    json_path = tmp_path / "ta-sweep-results.json"
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    _write_source_json(json_path, "2026-07-10", FIXTURE_RESULTS)
    _seed_instruments(db_path, ["MSFT", "NVDA"])

    report = migrate(json_path, jsonl_path, db_path, dry_run=False)

    assert report["source_count"] == 2
    assert report["written_count"] == 2
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT i.ticker, ie.event_type, ie.status, ie.payload_json FROM intelligence_event ie "
        "JOIN instrument i ON i.instrument_id = ie.instrument_id "
        "WHERE ie.event_type = 'TECHNICAL_SWEEP' ORDER BY i.ticker;"
    ).fetchall()
    conn.close()
    assert [r[0] for r in rows] == ["MSFT", "NVDA"]
    assert all(r[1] == "TECHNICAL_SWEEP" and r[2] == "ACTIVE" for r in rows)
    assert json.loads(rows[0][3])["ticker"] == "MSFT"


def test_idempotency_key_matches_producer_format_no_duplicate_on_rerun(tmp_path):
    """Idempotency key must match ta_sweep_batch.py's own format (ta-sweep-{ticker}-{scan_date})
    so a real future sweep for the same ticker/date never double-writes against this backfill.
    """
    json_path = tmp_path / "ta-sweep-results.json"
    jsonl_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    _write_source_json(json_path, "2026-07-10", FIXTURE_RESULTS)
    _seed_instruments(db_path, ["MSFT", "NVDA"])

    migrate(json_path, jsonl_path, db_path, dry_run=False)
    migrate(json_path, jsonl_path, db_path, dry_run=False)  # re-run, same source

    conn = sqlite3.connect(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM intelligence_event WHERE event_type = 'TECHNICAL_SWEEP' AND status = 'ACTIVE';"
    ).fetchone()[0]
    conn.close()
    assert count == 2  # not 4 — replay is idempotent on the same idempotency_key


def test_missing_source_file_raises_filenotfounderror(tmp_path):
    with pytest.raises(FileNotFoundError):
        migrate(tmp_path / "does-not-exist.json", tmp_path / "o.jsonl", tmp_path / "d.sqlite", dry_run=True)
