"""Regression test: harvest_earnings_expectations() must never write to the real,
tracked predictions.jsonl unless explicitly told to.

Root cause (logged in .agent/map-debt.md as OPEN before this fix): the function
had no path-override parameter at all, so any test that forgot to mock
_fetch_consensus_for_ticker/_append_prediction (e.g. a test that only mocked
_load_predictions to simulate a missing-file error) would silently fall through
to a REAL yfinance network call and a REAL append to the tracked ledger file.
This test proves the fix: passing predictions_path routes both the read and
the write to an isolated tmp_path file, never the real one, even when the
per-ticker network/consensus mocks are absent.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
REAL_PREDICTIONS_PATH = REPO_ROOT / "investment_screener/backend/data/predictions.jsonl"

sys.path.insert(0, str(PY_SERVICES))

from earnings_expectations import harvest_earnings_expectations  # noqa: E402


def test_harvest_writes_to_overridden_path_not_the_real_ledger(tmp_path):
    """A fully-mocked harvest call, given an explicit predictions_path, must
    read/write only the tmp_path file and leave the real ledger untouched."""
    fake_path = tmp_path / "predictions.jsonl"
    real_mtime_before = REAL_PREDICTIONS_PATH.stat().st_mtime

    new_consensus = {
        "consensus_eps": 1.05,
        "consensus_revenue": 3.8e11,
        "earnings_date": "2026-07-15",
    }

    with patch("earnings_expectations._fetch_consensus_for_ticker", return_value=new_consensus), \
         patch("earnings_expectations._make_prediction_id", return_value="AAPL:earnings_expectation:2026-07-12"), \
         patch("earnings_expectations.yf.Ticker") as mock_ticker:
        mock_ticker_inst = MagicMock()
        mock_ticker_inst.info = {"currentPrice": 210.0}
        mock_ticker.return_value = mock_ticker_inst

        result = harvest_earnings_expectations(["AAPL"], predictions_path=fake_path)

    assert len(result) == 1
    assert fake_path.exists(), "expected the override path to receive the write"
    assert REAL_PREDICTIONS_PATH.stat().st_mtime == real_mtime_before, \
        "real predictions.jsonl must never be touched when predictions_path is overridden"


def test_harvest_missing_predictions_file_does_not_touch_real_ledger_even_without_full_mocks(tmp_path):
    """Regression for the exact bug found: a test that only mocks _load_predictions
    (to simulate a missing/corrupt file) must not silently fall through to a real
    network call and a real write, just because predictions_path was overridden."""
    fake_path = tmp_path / "predictions.jsonl"
    real_mtime_before = REAL_PREDICTIONS_PATH.stat().st_mtime

    with patch("earnings_expectations._load_predictions",
               side_effect=FileNotFoundError("predictions.jsonl not found")), \
         patch("earnings_expectations._fetch_consensus_for_ticker", return_value=None):
        result = harvest_earnings_expectations(["AAPL"], predictions_path=fake_path)

    assert result == []
    assert REAL_PREDICTIONS_PATH.stat().st_mtime == real_mtime_before
