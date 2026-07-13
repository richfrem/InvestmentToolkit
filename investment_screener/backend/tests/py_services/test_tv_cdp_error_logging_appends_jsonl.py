"""
Task 5A-5: Error Logging (JSONL)

Tests for tv_cdp_health.py log_tv_error() function.
Verifies append-only JSONL error logging for tv_call() failures: file
creation, multi-line append, full field capture (timestamp, function,
args, error, traceback, attempt_number), ISO 8601 UTC timestamps, stack
trace capture, and non-blocking behavior when the file write itself
fails (must never raise).

IMPORTANT: All tests monkeypatch the module-level TV_CDP_ERRORS_PATH
constant to a pytest tmp_path location. None of these tests may write to
the real investment_screener/backend/data/tv_cdp_errors.jsonl path.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import tv_cdp_health  # noqa: E402
from tv_cdp_health import log_tv_error  # noqa: E402


@pytest.fixture
def errors_path(tmp_path, monkeypatch):
    """Point TV_CDP_ERRORS_PATH at a temp file for the duration of a test."""
    path = tmp_path / "tv_cdp_errors.jsonl"
    monkeypatch.setattr(tv_cdp_health, "TV_CDP_ERRORS_PATH", path)
    return path


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# --- Test 1: Creates file if missing ---

def test_log_tv_error_creates_file_if_missing(errors_path):
    """Calling log_tv_error against a nonexistent path creates the JSONL file."""
    assert not errors_path.exists()

    log_tv_error("chart_read", {"symbol": "AAPL"}, ValueError("boom"))

    assert errors_path.exists()


# --- Test 2: Appends without truncating ---

def test_log_tv_error_appends_jsonl_line(errors_path):
    """Two calls to log_tv_error produce two JSONL lines, not an overwrite."""
    log_tv_error("chart_read", {"symbol": "AAPL"}, ValueError("first failure"))
    log_tv_error("chart_read", {"symbol": "TSLA"}, ValueError("second failure"))

    lines = _read_lines(errors_path)

    assert len(lines) == 2
    assert lines[0]["error"] == "first failure"
    assert lines[1]["error"] == "second failure"


# --- Test 3: Captures all schema fields ---

def test_log_tv_error_captures_all_fields(errors_path):
    """Every field in the brief's schema is present and correctly valued."""
    log_tv_error(
        "pine_inject",
        {"file": "ai-ta-levels.pine"},
        RuntimeError("injection failed"),
        attempt_number=2,
    )

    record = _read_lines(errors_path)[0]

    assert record["function"] == "pine_inject"
    assert record["args"] == {"file": "ai-ta-levels.pine"}
    assert record["error"] == "injection failed"
    assert isinstance(record["traceback"], str)
    assert record["attempt_number"] == 2
    assert "timestamp" in record


# --- Test 4: Timestamp is valid ISO 8601 with timezone ---

def test_log_tv_error_timestamp_iso_8601(errors_path):
    """The timestamp field parses as ISO 8601 and carries timezone info (UTC)."""
    log_tv_error("chart_read", {}, ValueError("boom"))

    record = _read_lines(errors_path)[0]
    parsed = datetime.fromisoformat(record["timestamp"])

    assert parsed.tzinfo is not None


# --- Test 5: Stack trace included when logging from an except block ---

def test_log_tv_error_stack_trace_included(errors_path):
    """A real raised exception's traceback text is captured in the record."""
    try:
        raise ValueError("simulated tv_call failure")
    except ValueError as e:
        log_tv_error("chart_read", {"symbol": "AAPL"}, e, attempt_number=1)

    record = _read_lines(errors_path)[0]

    assert "Traceback" in record["traceback"]
    assert "simulated tv_call failure" in record["traceback"]


# --- Test 6: Non-blocking — file I/O failure doesn't raise ---

def test_log_tv_error_nonblocking_on_file_error(errors_path):
    """If the underlying JSONL append fails, log_tv_error swallows it silently."""
    with patch.object(tv_cdp_health, "_append_error_jsonl", side_effect=OSError("disk full")):
        log_tv_error("chart_read", {"symbol": "AAPL"}, ValueError("boom"))

    # No exception propagated, and (since the append was mocked out) no file
    # was actually written for this call.
