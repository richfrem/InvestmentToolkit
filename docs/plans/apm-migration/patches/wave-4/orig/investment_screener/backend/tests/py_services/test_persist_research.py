"""Purpose: verify research publication through the real ledger database CLI.

Layer: CLI integration. Key Functions: publish and update/readback checks.
Key Input Dependencies: real persistence/query scripts and a temporary ledger database.
"""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "plugins/stock-valuation/scripts/persist_research.py"
QUERY = ROOT / "investment_screener/backend/py_services/query_ledger_research.py"


def _event_count(db: Path) -> int:
    """Number of RESEARCH_IMPORT events stored in the ledger database."""
    conn = sqlite3.connect(str(db))
    try:
        return conn.execute("SELECT COUNT(*) FROM intelligence_event WHERE event_type = 'RESEARCH_IMPORT';").fetchone()[0]
    finally:
        conn.close()


def test_publish_retry_and_correction_are_visible_in_research_query(tmp_path: Path) -> None:
    """The dated report survives actual ingestion, retries and same-day corrections."""
    report = tmp_path / "APLD_2026-10-07.md"
    db = tmp_path / "intelligence.sqlite"
    command = [sys.executable, str(SCRIPT), "--file", str(report), "--db", str(db)]
    report.write_text("# APLD\nWACC assumptions require review.")
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    assert json.loads(first.stdout)["event_id"] == json.loads(second.stdout)["event_id"]
    assert _event_count(db) == 1
    report.write_text("# APLD\nUpdated sourced discount-rate assumptions.")
    correction = subprocess.run(command, capture_output=True, text=True)
    assert correction.returncode == 0, correction.stderr
    assert _event_count(db) == 2
    query = subprocess.run([sys.executable, str(QUERY), "--get", report.name, "--db-path", str(db)],
                           capture_output=True, text=True)
    assert query.returncode == 0, query.stderr
    assert json.loads(query.stdout)["content"] == report.read_text()


def test_invalid_report_cannot_create_the_database(tmp_path: Path) -> None:
    """Reject invalid dated names before any persistent side effects."""
    report = tmp_path / "APLD_2026-99-07.md"
    report.write_text("Invalid report date")
    db = tmp_path / "intelligence.sqlite"
    result = subprocess.run([sys.executable, str(SCRIPT), "--file", str(report),
                             "--db", str(db)], capture_output=True, text=True)
    assert result.returncode != 0
    assert not db.exists()
