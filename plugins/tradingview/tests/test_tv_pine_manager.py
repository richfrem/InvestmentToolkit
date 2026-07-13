"""
test_tv_pine_manager.py — pytest tests for the tv_pine_manager Python wrapper.

Tests mock at the subprocess.run boundary — no live TradingView or Node CLI required.
Live end-to-end tests live in tv_test_harness.py (Section 1).

Task 5A-8 note: tv_pine_manager's _run_node_cli() calls tv_client.tv_call(),
which is the resilience-wrapped tv_call() introduced in 5A-8 — even though
subprocess.run is mocked here (so no real CLI/Chrome call happens), tv_call()
still unconditionally writes the successful result through to the on-disk
last-known-good cache (tv_cdp_health.cache_set) and would write failures to
the errors JSONL (tv_cdp_health.log_tv_error). Left unpatched, that means
these tests write synthetic test data to the REAL, non-gitignored
investment_screener/backend/data/tv_cdp_responses_cache.jsonl file. The
isolated_jsonl_paths fixture below (same pattern as
investment_screener/backend/tests/api/test_tv_client_wrapped_calls_survive_transient_errors.py)
redirects both paths to tmp_path for every test in this file.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

REPO_ROOT = Path(__file__).resolve().parents[3]
HEALTH_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(HEALTH_DIR))

import tv_cdp_health  # noqa: E402
from tv_pine_manager import inject_pine, read_pine, remove_pine  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_jsonl_paths(tmp_path, monkeypatch):
    """Redirect the errors JSONL and cache JSONL to tmp_path for every test.

    Without this, tv_call()'s resilience layer (5A-8) writes real cache/
    error entries to investment_screener/backend/data/ even though
    subprocess.run is mocked.
    """
    errors_path = tmp_path / "tv_cdp_errors.jsonl"
    cache_path = tmp_path / "tv_cdp_responses_cache.jsonl"
    monkeypatch.setattr(tv_cdp_health, "TV_CDP_ERRORS_PATH", errors_path)
    monkeypatch.setattr(tv_cdp_health, "TV_CDP_CACHE_PATH", cache_path)
    return {"errors": errors_path, "cache": cache_path}


def _make_run_result(payload: dict, returncode: int = 0) -> MagicMock:
    mock = MagicMock()
    mock.stdout = json.dumps(payload)
    mock.returncode = returncode
    return mock


def test_inject_pine(tmp_path):
    script_path = tmp_path / "ai_indicator.pine"
    script_path.write_text("//@version=5\nindicator('Test')\nplot(close)")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _make_run_result({"success": True})
        result = inject_pine(str(script_path))

    assert result["success"] is True
    mock_run.assert_called_once()
    assert "pine" in " ".join(mock_run.call_args[0][0])
    assert "inject" in " ".join(mock_run.call_args[0][0])


def test_read_pine():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _make_run_result({"success": True, "data": {"MACD": 1.5}})
        result = read_pine("AI_Custom_TA")

    assert result["success"] is True
    assert "read" in " ".join(mock_run.call_args[0][0])


def test_remove_pine():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = _make_run_result({"success": True})
        result = remove_pine("AI_Custom_TA")

    assert result["success"] is True
    assert "remove" in " ".join(mock_run.call_args[0][0])
