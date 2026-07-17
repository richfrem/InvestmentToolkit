"""Test for Task 5: Harvest graceful degrade (NULL consensus).

Validates that harvest_earnings_expectations() handles NULL consensus gracefully,
logging no claim and continuing to next ticker.

Every call below passes predictions_path=tmp_path/... so no test in this file
can ever write to the real, tracked predictions.jsonl — including
test_harvest_missing_predictions_file_returns_empty, which previously had no
mocks for _fetch_consensus_for_ticker/_append_prediction at all and made a
real yfinance call + a real ledger write every time the suite ran.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"

sys.path.insert(0, str(PY_SERVICES))

from earnings_expectations import harvest_earnings_expectations  # noqa: E402


class TestHarvestEarningsExpectationsNullConsensus:
    """Verify graceful degrade on NULL consensus."""

    def test_harvest_skips_null_consensus_eps(self, tmp_path):
        """When consensus_eps is None, no claim is logged."""
        null_consensus = {
            "consensus_eps": None,  # NULL
            "consensus_revenue": 3.8e11,
            "earnings_date": "2026-07-15"
        }

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=null_consensus), \
             patch("earnings_expectations._load_predictions", return_value=[]), \
             patch("earnings_expectations._append_prediction") as mock_append:

            result = harvest_earnings_expectations(["AAPL"], predictions_path=tmp_path / "predictions.jsonl")

        # Should NOT append
        mock_append.assert_not_called()
        assert result == []

    def test_harvest_skips_null_consensus_revenue(self, tmp_path):
        """When consensus_revenue is None, claim is still logged (revenue can be missing)."""
        # Note: revenue may be missing for some tickers, but as long as EPS exists,
        # we could log the claim. However, per the design, we check EPS only.
        partial_consensus = {
            "consensus_eps": 1.05,
            "consensus_revenue": None,  # Missing
            "earnings_date": "2026-07-15"
        }

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=partial_consensus), \
             patch("earnings_expectations._load_predictions", return_value=[]), \
             patch("earnings_expectations._append_prediction") as mock_append, \
             patch("earnings_expectations._make_prediction_id",
                   return_value="MSFT:earnings_expectation:2026-07-12"), \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations.yf.Ticker") as mock_ticker:

            mock_date_class.today.return_value.isoformat.return_value = "2026-07-12"

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = {"currentPrice": 210.0}
            mock_ticker.return_value = mock_ticker_inst

            result = harvest_earnings_expectations(["MSFT"], predictions_path=tmp_path / "predictions.jsonl")

        # Should append (EPS is present)
        mock_append.assert_called_once()
        assert len(result) == 1

    def test_harvest_skips_null_earnings_date(self, tmp_path):
        """When earnings_date is None, no claim is logged."""
        no_date_consensus = {
            "consensus_eps": 1.05,
            "consensus_revenue": 3.8e11,
            "earnings_date": None  # No date
        }

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=no_date_consensus), \
             patch("earnings_expectations._load_predictions", return_value=[]), \
             patch("earnings_expectations._append_prediction") as mock_append:

            result = harvest_earnings_expectations(["AAPL"], predictions_path=tmp_path / "predictions.jsonl")

        # Should NOT append (no earnings date)
        mock_append.assert_not_called()
        assert result == []

    def test_harvest_returns_none_on_consensus_fetch_error(self, tmp_path):
        """When _fetch_consensus_for_ticker returns None (API error), gracefully degrade."""
        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=None), \
             patch("earnings_expectations._load_predictions", return_value=[]), \
             patch("earnings_expectations._append_prediction") as mock_append:

            result = harvest_earnings_expectations(["AAPL"], predictions_path=tmp_path / "predictions.jsonl")

        # Should NOT append
        mock_append.assert_not_called()
        assert result == []

    def test_harvest_continues_after_null_consensus_ticker(self, tmp_path):
        """When one ticker has NULL consensus, harvest continues to next ticker."""
        # First ticker: NULL consensus
        # Second ticker: valid consensus
        valid_consensus = {
            "consensus_eps": 1.05,
            "consensus_revenue": 3.8e11,
            "earnings_date": "2026-07-15"
        }

        def mock_fetch(ticker):
            if ticker == "AAPL":
                return None  # NULL for AAPL
            else:
                return valid_consensus  # Valid for MSFT

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   side_effect=mock_fetch), \
             patch("earnings_expectations._load_predictions", return_value=[]), \
             patch("earnings_expectations._append_prediction") as mock_append, \
             patch("earnings_expectations._make_prediction_id",
                   return_value="MSFT:earnings_expectation:2026-07-12"), \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations.yf.Ticker") as mock_ticker:

            mock_date_class.today.return_value.isoformat.return_value = "2026-07-12"

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = {"currentPrice": 210.0}
            mock_ticker.return_value = mock_ticker_inst

            result = harvest_earnings_expectations(["AAPL", "MSFT"], predictions_path=tmp_path / "predictions.jsonl")

        # Should append only MSFT claim
        mock_append.assert_called_once()
        assert len(result) == 1
        assert result[0]["ticker"] == "MSFT"

    def test_harvest_empty_tickers_list_returns_empty(self, tmp_path):
        """When no tickers to harvest, return empty list."""
        with patch("earnings_expectations._load_predictions", return_value=[]):
            result = harvest_earnings_expectations([], predictions_path=tmp_path / "predictions.jsonl")

        assert result == []

    def test_harvest_silently_degrades_on_yfinance_exception(self, tmp_path):
        """When yfinance raises exception during price fetch, silently degrade."""
        valid_consensus = {
            "consensus_eps": 1.05,
            "consensus_revenue": 3.8e11,
            "earnings_date": "2026-07-15"
        }

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=valid_consensus), \
             patch("earnings_expectations._load_predictions", return_value=[]), \
             patch("earnings_expectations._make_prediction_id",
                   return_value="AAPL:earnings_expectation:2026-07-12"), \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations.yf.Ticker",
                   side_effect=Exception("yfinance error")), \
             patch("earnings_expectations._append_prediction") as mock_append:

            mock_date_class.today.return_value.isoformat.return_value = "2026-07-12"

            result = harvest_earnings_expectations(["AAPL"], predictions_path=tmp_path / "predictions.jsonl")

        # Should NOT append (exception during price fetch)
        mock_append.assert_not_called()
        assert result == []

    def test_harvest_missing_predictions_file_returns_empty(self, tmp_path):
        """When predictions.jsonl doesn't exist, gracefully degrade.

        Regression: this test previously mocked only _load_predictions, so when
        harvest_earnings_expectations() caught that exception and continued to
        the per-ticker loop, it made a REAL _fetch_consensus_for_ticker() call
        (real yfinance network hit) and a REAL _append_prediction() write to the
        tracked ledger — the exact bug logged in .agent/map-debt.md. Now fully
        mocked (consensus returns None, so the loop skips the ticker) and given
        an isolated predictions_path, so it can never touch the real file even
        if a future edit reintroduces a missing mock.
        """
        with patch("earnings_expectations._load_predictions",
                   side_effect=FileNotFoundError("predictions.jsonl not found")), \
             patch("earnings_expectations._fetch_consensus_for_ticker", return_value=None), \
             patch("earnings_expectations._append_prediction") as mock_append:

            result = harvest_earnings_expectations(["AAPL"], predictions_path=tmp_path / "predictions.jsonl")

        mock_append.assert_not_called()
        assert result == []
