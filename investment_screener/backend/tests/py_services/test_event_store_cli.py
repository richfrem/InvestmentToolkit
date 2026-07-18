"""Tests for the ``intelligence.event_store`` CLI wrapper (Task 10).

Uses real subprocess execution (no mocking) per
``.agent/rules/test-driven-development.md``'s "No Mocking on Critical
Runtime Paths" rule — this CLI is the entry point SKILL.md instructions
shell out to directly.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"


def test_cli_appends_event_from_body_file(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
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
            "--jsonl-path", str(jsonl_path),
        ],
        cwd=str(SCRIPT_DIR),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    lines = [json.loads(l) for l in jsonl_path.read_text().splitlines()]
    assert len(lines) == 1
    assert lines[0]["ticker"] == "PLTR"
    assert lines[0]["event_type"] == "RESEARCH_IMPORT"
    assert lines[0]["status"] == "ACTIVE"
    assert lines[0]["title"] == "PLTR research update"
    assert lines[0]["body_markdown"] == "# PLTR research\nSome findings."
    assert lines[0]["event_id"] in result.stdout


def test_cli_requires_a_body_source(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"

    result = subprocess.run(
        [
            sys.executable, "-m", "intelligence.event_store",
            "--event-type", "RESEARCH_IMPORT",
            "--ticker", "PLTR",
            "--effective-at", "2026-07-18",
            "--status", "ACTIVE",
            "--title", "PLTR research update",
            "--jsonl-path", str(jsonl_path),
        ],
        cwd=str(SCRIPT_DIR),
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert not jsonl_path.exists()
