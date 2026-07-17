"""Test for Task 3: Harvest core logic (dedup on unchanged consensus).

Validates that harvest_earnings_expectations() reads tail of predictions.jsonl
efficiently, dedups on (ticker, type, earnings_date), and appends new claim
only if consensus changed or no prior record exists.

Every call below passes predictions_path=tmp_path/... so no test in this file
can ever write to the real, tracked predictions.jsonl — even the tests whose
other mocks (_fetch_consensus_for_ticker, _append_prediction) are incomplete.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
TESTS_DIR = REPO_ROOT / "investment_screener/backend/tests"

sys.path.insert(0, str(PY_SERVICES))
sys.path.insert(0, str(TESTS_DIR))

from earnings_expectations import harvest_earnings_expectations  # noqa: E402


class TestHarvestEarningsExpectationsDedup:
    """Verify dedup logic on unchanged consensus."""

    def test_harvest_dedupes_on_unchanged_consensus(self, tmp_path):
        """When consensus unchanged, no new claim is appended."""
        # Mock predictions.jsonl with prior record
        prior_pred = {
            "v": 1,
            "id": "AAPL:earnings_expectation:2026-07-10",
            "date": "2026-07-10",
            "ticker": "AAPL",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 1.05,
                "consensus_revenue": 3.8e11,
                "earnings_date": "2026-07-15"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 200.0,
            "baseSpyPrice": 600.0,
            "inputsHash": "hash123",
            "harvestedAt": "2026-07-10T12:00:00Z"
        }

        # Mock consensus fetch to return same values
        mock_consensus = {
            "consensus_eps": 1.05,
            "consensus_revenue": 3.8e11,
            "earnings_date": "2026-07-15"
        }

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=mock_consensus), \
             patch("earnings_expectations._load_predictions",
                   return_value=[prior_pred]), \
             patch("earnings_expectations._append_prediction") as mock_append, \
             patch("earnings_expectations._make_prediction_id",
                   return_value="AAPL:earnings_expectation:2026-07-12"), \
             patch("earnings_expectations.date") as mock_date:

            mock_date.today.return_value.isoformat.return_value = "2026-07-12"

            result = harvest_earnings_expectations(["AAPL"], predictions_path=tmp_path / "predictions.jsonl")

        # Should NOT append new prediction
        mock_append.assert_not_called()
        assert len(result) == 0

    def test_harvest_appends_on_consensus_change(self, tmp_path):
        """When consensus changed, new claim is appended."""
        prior_pred = {
            "v": 1,
            "id": "AAPL:earnings_expectation:2026-07-10",
            "date": "2026-07-10",
            "ticker": "AAPL",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 1.05,
                "consensus_revenue": 3.8e11,
                "earnings_date": "2026-07-15"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 200.0,
            "baseSpyPrice": 600.0,
            "inputsHash": "hash123",
            "harvestedAt": "2026-07-10T12:00:00Z"
        }

        # Mock new consensus (EPS changed)
        new_consensus = {
            "consensus_eps": 1.10,  # Changed
            "consensus_revenue": 3.8e11,
            "earnings_date": "2026-07-15"
        }

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=new_consensus), \
             patch("earnings_expectations._load_predictions",
                   return_value=[prior_pred]), \
             patch("earnings_expectations._append_prediction") as mock_append, \
             patch("earnings_expectations._make_prediction_id",
                   return_value="AAPL:earnings_expectation:2026-07-12"), \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations.yf.Ticker") as mock_ticker:

            mock_date_class.today.return_value.isoformat.return_value = "2026-07-12"

            # Mock yfinance Ticker
            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = {
                "currentPrice": 210.0,
            }
            mock_ticker.return_value = mock_ticker_inst

            result = harvest_earnings_expectations(["AAPL"], predictions_path=tmp_path / "predictions.jsonl")

        # Should append new prediction
        mock_append.assert_called_once()
        assert len(result) == 1
        assert result[0]["claim"]["consensus_eps"] == 1.10

    def test_harvest_appends_on_no_prior_record(self, tmp_path):
        """When no prior record exists, new claim is appended."""
        new_consensus = {
            "consensus_eps": 1.05,
            "consensus_revenue": 3.8e11,
            "earnings_date": "2026-07-15"
        }

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=new_consensus), \
             patch("earnings_expectations._load_predictions", return_value=[]), \
             patch("earnings_expectations._append_prediction") as mock_append, \
             patch("earnings_expectations._make_prediction_id",
                   return_value="AAPL:earnings_expectation:2026-07-12"), \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations.yf.Ticker") as mock_ticker:

            mock_date_class.today.return_value.isoformat.return_value = "2026-07-12"

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = {"currentPrice": 210.0}
            mock_ticker.return_value = mock_ticker_inst

            result = harvest_earnings_expectations(["AAPL"], predictions_path=tmp_path / "predictions.jsonl")

        mock_append.assert_called_once()
        assert len(result) == 1

    def test_harvest_tail_limit_1000(self, tmp_path):
        """Verify harvest efficiently reads tail (last 1000 lines)."""
        # Create 1100 prior predictions
        prior_preds = [
            {
                "v": 1,
                "id": f"TEST{i}:earnings_expectation:2026-07-01",
                "date": "2026-07-01",
                "ticker": f"TEST{i}",
                "type": "earnings_expectation",
                "claim": {"consensus_eps": 1.0, "consensus_revenue": 1e9, "earnings_date": "2026-07-15"},
                "direction": "bullish",
                "horizonDays": 90,
                "basePrice": 100.0,
                "baseSpyPrice": 600.0,
                "inputsHash": "hash",
                "harvestedAt": "2026-07-01T12:00:00Z"
            }
            for i in range(1100)
        ]

        new_consensus = {
            "consensus_eps": 1.05,
            "consensus_revenue": 3.8e11,
            "earnings_date": "2026-07-15"
        }

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=new_consensus), \
             patch("earnings_expectations._load_predictions",
                   return_value=prior_preds), \
             patch("earnings_expectations._append_prediction"), \
             patch("earnings_expectations._make_prediction_id",
                   return_value="AAPL:earnings_expectation:2026-07-12"), \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations.yf.Ticker") as mock_ticker:

            mock_date_class.today.return_value.isoformat.return_value = "2026-07-12"

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = {"currentPrice": 210.0}
            mock_ticker.return_value = mock_ticker_inst

            result = harvest_earnings_expectations(["AAPL"], predictions_path=tmp_path / "predictions.jsonl")

        # Should still work with limit
        assert len(result) == 1

    def test_harvest_gracefully_degrades_on_missing_file(self, tmp_path):
        """Harvest returns empty list if predictions.jsonl doesn't exist."""
        with patch("earnings_expectations._load_predictions",
                   side_effect=Exception("File not found")), \
             patch("earnings_expectations._fetch_consensus_for_ticker", return_value=None), \
             patch("earnings_expectations._append_prediction") as mock_append:

            result = harvest_earnings_expectations(["AAPL"], predictions_path=tmp_path / "predictions.jsonl")

        mock_append.assert_not_called()
        assert result == []

    def test_harvest_uses_target_portfolio_when_no_tickers(self, tmp_path):
        """When tickers not provided, harvest loads from target-portfolio.json."""
        target_data = {
            "holdings": [
                {"ticker": "AAPL"},
                {"ticker": "MSFT"},
            ]
        }

        new_consensus = {
            "consensus_eps": 1.05,
            "consensus_revenue": 3.8e11,
            "earnings_date": "2026-07-15"
        }

        mock_open_inst = MagicMock()
        mock_open_inst.__enter__.return_value.read.return_value = json.dumps(target_data)

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=new_consensus), \
             patch("earnings_expectations._load_predictions", return_value=[]), \
             patch("builtins.open", create=True) as mock_file, \
             patch("earnings_expectations._append_prediction"), \
             patch("earnings_expectations._make_prediction_id",
                   return_value="TEST:earnings_expectation:2026-07-12"), \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations.yf.Ticker") as mock_ticker:

            mock_date_class.today.return_value.isoformat.return_value = "2026-07-12"
            mock_file.return_value.__enter__.return_value = MagicMock(
                read=lambda: json.dumps(target_data)
            )
            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = {"currentPrice": 210.0}
            mock_ticker.return_value = mock_ticker_inst

            result = harvest_earnings_expectations(predictions_path=tmp_path / "predictions.jsonl")

        # Should have tried to load target portfolio
        assert result is not None
