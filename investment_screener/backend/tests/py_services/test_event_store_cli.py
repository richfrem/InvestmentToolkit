"""Tests for the ``intelligence.event_store`` CLI wrapper.

Uses real subprocess execution (no mocking): this CLI is the entry point SKILL.md
instructions shell out to directly.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"


def test_cli_appends_event_from_body_file(tmp_path):
    db_path = tmp_path / "intelligence.sqlite"
    body_file = tmp_path / "body.md"
    body_file.write_text("# PLTR research\nSome findings.")

    result = subprocess.run(
        [
            sys.executable, "-m", "intelligence.event_store",
            "--event-type", "RESEARCH_IMPORT",
            "--ticker", "PLTR",
            "--effective-at", "2026-07-18",
            "--status", "ACTIVE",
            "--title", "PLTR research update",
            "--body-file", str(body_file),
            "--db-path", str(db_path),
        ],
        cwd=str(SCRIPT_DIR),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT event_id, event_type, status, title, body_markdown FROM intelligence_event;"
    ).fetchall()
    conn.close()
    assert len(rows) == 1
    event_id, event_type, status, title, body = rows[0]
    assert (event_type, status, title) == ("RESEARCH_IMPORT", "ACTIVE", "PLTR research update")
    assert body == "# PLTR research\nSome findings."
    assert event_id in result.stdout


def test_cli_requires_a_body_source(tmp_path):
    db_path = tmp_path / "intelligence.sqlite"

    result = subprocess.run(
        [
            sys.executable, "-m", "intelligence.event_store",
            "--event-type", "RESEARCH_IMPORT",
            "--ticker", "PLTR",
            "--effective-at", "2026-07-18",
            "--status", "ACTIVE",
            "--title", "PLTR research update",
            "--db-path", str(db_path),
        ],
        cwd=str(SCRIPT_DIR),
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert not db_path.exists()
