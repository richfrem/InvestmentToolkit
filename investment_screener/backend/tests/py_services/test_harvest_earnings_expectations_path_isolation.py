"""Regression test: harvest_earnings_expectations() must never write to the real
ledger database unless explicitly told to.

The write lands in the intelligence ledger database given by ``intel_db_path``. A test that
only mocked ``_load_predictions`` (to simulate a failure) once fell through to a REAL yfinance
network call and a REAL write. These tests prove that passing ``intel_db_path`` routes both the
read and the write to an isolated tmp_path database, even when the per-ticker network and
consensus mocks are absent.
"""
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
REAL_LEDGER_PATH = DATA_DIR / "intelligence.sqlite"

sys.path.insert(0, str(PY_SERVICES))

from earnings_expectations import harvest_earnings_expectations  # noqa: E402


def _real_files_state():
    """(exists, mtime, size) of the real ledger database — gitignored, so absent in a fresh worktree."""
    p = REAL_LEDGER_PATH
    return [(p.exists(), p.stat().st_mtime, p.stat().st_size) if p.exists() else (False, None, None)]


def test_harvest_writes_to_the_overridden_database_not_the_real_ledger(tmp_path):
    """A fully-mocked harvest call, given an explicit intel_db_path, reads and writes only that
    database and leaves the real ledger untouched."""
    fake_db = tmp_path / "intelligence.sqlite"
    real_before = _real_files_state()

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

        result = harvest_earnings_expectations(["AAPL"], intel_db_path=fake_db)

    assert len(result) == 1
    conn = sqlite3.connect(str(fake_db))
    keys = [r[0] for r in conn.execute("SELECT idempotency_key FROM intelligence_event;")]
    conn.close()
    assert "prediction-claim-AAPL:earnings_expectation:2026-07-12" in keys, \
        "expected the override ledger to receive the write"
    assert _real_files_state() == real_before, \
        "the real ledger database must never be touched when intel_db_path is overridden"


def test_harvest_load_failure_does_not_touch_the_real_ledger_even_without_full_mocks(tmp_path):
    """A test that only mocks _load_predictions (to simulate a failure) must not silently fall
    through to a real network call and a real write, just because intel_db_path was overridden."""
    fake_db = tmp_path / "intelligence.sqlite"
    real_before = _real_files_state()

    with patch("earnings_expectations._load_predictions",
               side_effect=FileNotFoundError("ledger not found")), \
         patch("earnings_expectations._fetch_consensus_for_ticker", return_value=None):
        result = harvest_earnings_expectations(["AAPL"], intel_db_path=fake_db)

    assert result == []
    assert _real_files_state() == real_before
