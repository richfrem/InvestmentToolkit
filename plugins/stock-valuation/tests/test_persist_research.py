"""Purpose: verify research publication through the real ledger and SQLite CLI.

Layer: CLI integration. Key Functions: publish and update/readback checks.
Key Input Dependencies: real persistence/query scripts and temporary ledger/database.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "plugins/stock-valuation/scripts/persist_research.py"
QUERY = ROOT / "investment_screener/backend/py_services/query_ledger_research.py"


def test_publish_retry_and_correction_are_visible_in_research_query(tmp_path: Path) -> None:
    """The dated report survives actual ingestion, retries and same-day corrections."""
    report = tmp_path / "APLD_2026-10-07.md"
    db = tmp_path / "intelligence.sqlite"
    ledger = tmp_path / "observations.jsonl"
    command = [sys.executable, str(SCRIPT), "--file", str(report), "--db", str(db), "--jsonl", str(ledger)]
    report.write_text("# APLD\nWACC assumptions require review.")
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    assert json.loads(first.stdout)["event_id"] == json.loads(second.stdout)["event_id"]
    assert len(ledger.read_text().splitlines()) == 1
    report.write_text("# APLD\nUpdated sourced discount-rate assumptions.")
    correction = subprocess.run(command, capture_output=True, text=True)
    assert correction.returncode == 0, correction.stderr
    assert len(ledger.read_text().splitlines()) == 2
    query = subprocess.run([sys.executable, str(QUERY), "--get", report.name, "--db-path", str(db)],
                           capture_output=True, text=True)
    assert query.returncode == 0, query.stderr
    assert json.loads(query.stdout)["content"] == report.read_text()


def test_invalid_report_cannot_create_database_or_ledger(tmp_path: Path) -> None:
    """Reject invalid dated names before any persistent side effects."""
    report = tmp_path / "APLD_2026-99-07.md"
    report.write_text("Invalid report date")
    db, ledger = tmp_path / "intelligence.sqlite", tmp_path / "observations.jsonl"
    result = subprocess.run([sys.executable, str(SCRIPT), "--file", str(report),
                             "--db", str(db), "--jsonl", str(ledger)], capture_output=True, text=True)
    assert result.returncode != 0
    assert not db.exists()
    assert not ledger.exists()
