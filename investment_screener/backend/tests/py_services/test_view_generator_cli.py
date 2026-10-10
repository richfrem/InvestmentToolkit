"""Tests for the ``intelligence.view_generator`` CLI wrapper (Task 10).

Uses real subprocess execution (no mocking) per
``.agent/rules/test-driven-development.md``'s "No Mocking on Critical
Runtime Paths" rule — this CLI is the entry point SKILL.md instructions
shell out to directly, after ``intelligence.event_store``.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"

sys.path.insert(0, str(SCRIPT_DIR))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.event_store import append_event  # noqa: E402


def _seed(db_path, **event):
    conn = initialize_db(str(db_path))
    try:
        append_event(conn, **event)
    finally:
        conn.close()


def test_cli_renders_views_from_the_ledger(tmp_path):
    db_path = tmp_path / "intelligence.sqlite"
    output_dir = tmp_path / "research"

    _seed(
        db_path,
        event_type="RESEARCH_IMPORT",
        effective_at="2026-07-18",
        status="ACTIVE",
        title="PLTR research update",
        body_markdown="Palantir ontology builds secure node.",
        ticker="PLTR",
    )

    result = subprocess.run(
        [
            sys.executable, "-m", "intelligence.view_generator", "PLTR",
            "--db-path", str(db_path),
            "--output-dir", str(output_dir),
        ],
        cwd=str(SCRIPT_DIR),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    summary = (output_dir / "PLTR.summary.md").read_text()
    timeline = (output_dir / "PLTR.timeline.md").read_text()
    assert "ticker: \"PLTR\"" in summary
    assert "Palantir ontology builds secure node." in summary
    assert "Palantir ontology builds secure node." in timeline


def test_cli_creates_output_dir_if_missing(tmp_path):
    db_path = tmp_path / "intelligence.sqlite"
    output_dir = tmp_path / "nested" / "research"

    _seed(
        db_path,
        event_type="RESEARCH_IMPORT",
        effective_at="2026-07-18",
        status="ACTIVE",
        title="CORZ research update",
        body_markdown="Core Scientific update.",
        ticker="CORZ",
    )

    result = subprocess.run(
        [
            sys.executable, "-m", "intelligence.view_generator", "CORZ",
            "--db-path", str(db_path),
            "--output-dir", str(output_dir),
        ],
        cwd=str(SCRIPT_DIR),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "CORZ.summary.md").exists()
