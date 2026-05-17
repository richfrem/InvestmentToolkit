"""
test_tv_pine_manager.py — pytest tests for the tv_pine_manager Python wrapper.

Tests mock at the subprocess.run boundary — no live TradingView or Node CLI required.
Live end-to-end tests live in tv_test_harness.py (Section 1).
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from tv_pine_manager import inject_pine, read_pine, remove_pine


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
