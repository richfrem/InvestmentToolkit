"""Test for Task 4: Harvest on consensus change.

Validates that harvest_earnings_expectations() appends new claim when
consensus updates mid-week (multi-source scenario).
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"

sys.path.insert(0, str(PY_SERVICES))

from earnings_expectations import harvest_earnings_expectations  # noqa: E402


class TestHarvestEarningsExpectationsConsensusChange:
    """Verify harvest logs when consensus updates."""

    def test_harvest_logs_eps_estimate_revision(self):
        """When EPS estimate is revised mid-week, new claim is logged."""
        # Prior consensus (Monday)
        prior_pred = {
            "v": 1,
            "id": "NVDA:earnings_expectation:2026-07-07",
            "date": "2026-07-07",
            "ticker": "NVDA",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.52,
                "consensus_revenue": 9.4e9,
                "earnings_date": "2026-07-15"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 118.50,
            "baseSpyPrice": 611.20,
            "inputsHash": "hash1",
            "harvestedAt": "2026-07-07T10:00:00Z"
        }

        # Updated consensus (Wednesday — EPS revised up)
        updated_consensus = {
            "consensus_eps": 0.55,  # Revised up 5.8%
            "consensus_revenue": 9.4e9,
            "earnings_date": "2026-07-15"
        }

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=updated_consensus), \
             patch("earnings_expectations._load_predictions",
                   return_value=[prior_pred]), \
             patch("earnings_expectations._append_prediction") as mock_append, \
             patch("earnings_expectations._make_prediction_id",
                   return_value="NVDA:earnings_expectation:2026-07-10"), \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations.yf.Ticker") as mock_ticker:

            mock_date.today.return_value.isoformat.return_value = "2026-07-10"

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = {"currentPrice": 125.00, "regularMarketPrice": 125.00}
            mock_ticker.return_value = mock_ticker_inst

            result = harvest_earnings_expectations(["NVDA"])

        # Should log new claim
        mock_append.assert_called_once()
        appended_claim = mock_append.call_args[0][0]
        assert appended_claim["claim"]["consensus_eps"] == 0.55

    def test_harvest_logs_revenue_estimate_revision(self):
        """When revenue estimate is revised, new claim is logged."""
        prior_pred = {
            "v": 1,
            "id": "AAPL:earnings_expectation:2026-07-07",
            "date": "2026-07-07",
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
            "inputsHash": "hash1",
            "harvestedAt": "2026-07-07T10:00:00Z"
        }

        # Revenue revised down
        updated_consensus = {
            "consensus_eps": 1.05,
            "consensus_revenue": 3.75e11,  # Revised down 1.3%
            "earnings_date": "2026-07-15"
        }

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=updated_consensus), \
             patch("earnings_expectations._load_predictions",
                   return_value=[prior_pred]), \
             patch("earnings_expectations._append_prediction") as mock_append, \
             patch("earnings_expectations._make_prediction_id",
                   return_value="AAPL:earnings_expectation:2026-07-10"), \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations.yf.Ticker") as mock_ticker:

            mock_date.today.return_value.isoformat.return_value = "2026-07-10"

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = {"currentPrice": 210.0}
            mock_ticker.return_value = mock_ticker_inst

            result = harvest_earnings_expectations(["AAPL"])

        mock_append.assert_called_once()
        appended_claim = mock_append.call_args[0][0]
        assert appended_claim["claim"]["consensus_revenue"] == 3.75e11

    def test_harvest_appends_multiple_revisions_same_ticker(self):
        """Multiple revisions for same ticker on different days are all logged."""
        # Monday consensus
        monday_pred = {
            "v": 1,
            "id": "NVDA:earnings_expectation:2026-07-07",
            "date": "2026-07-07",
            "ticker": "NVDA",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.52,
                "consensus_revenue": 9.4e9,
                "earnings_date": "2026-07-15"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 118.50,
            "baseSpyPrice": 611.20,
            "inputsHash": "hash1",
            "harvestedAt": "2026-07-07T10:00:00Z"
        }

        # Wednesday revision
        wednesday_pred = {
            "v": 1,
            "id": "NVDA:earnings_expectation:2026-07-09",
            "date": "2026-07-09",
            "ticker": "NVDA",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.54,
                "consensus_revenue": 9.5e9,
                "earnings_date": "2026-07-15"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 120.00,
            "baseSpyPrice": 612.00,
            "inputsHash": "hash2",
            "harvestedAt": "2026-07-09T14:00:00Z"
        }

        # Friday revision (today)
        friday_consensus = {
            "consensus_eps": 0.56,  # Revised up further
            "consensus_revenue": 9.6e9,
            "earnings_date": "2026-07-15"
        }

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=friday_consensus), \
             patch("earnings_expectations._load_predictions",
                   return_value=[monday_pred, wednesday_pred]), \
             patch("earnings_expectations._append_prediction") as mock_append, \
             patch("earnings_expectations._make_prediction_id",
                   return_value="NVDA:earnings_expectation:2026-07-12"), \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations.yf.Ticker") as mock_ticker:

            mock_date.today.return_value.isoformat.return_value = "2026-07-12"

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = {"currentPrice": 125.00}
            mock_ticker.return_value = mock_ticker_inst

            result = harvest_earnings_expectations(["NVDA"])

        # Should append new claim (Friday's revision)
        mock_append.assert_called_once()
        appended_claim = mock_append.call_args[0][0]
        assert appended_claim["claim"]["consensus_eps"] == 0.56
        assert appended_claim["claim"]["consensus_revenue"] == 9.6e9

    def test_harvest_dedupes_same_consensus_across_sources(self):
        """If consensus is the same from multiple sources, no new claim."""
        prior_pred = {
            "v": 1,
            "id": "MSFT:earnings_expectation:2026-07-09",
            "date": "2026-07-09",
            "ticker": "MSFT",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 2.72,
                "consensus_revenue": 5.2e10,
                "earnings_date": "2026-07-18"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 430.0,
            "baseSpyPrice": 612.00,
            "inputsHash": "hash1",
            "harvestedAt": "2026-07-09T14:00:00Z"
        }

        # Same consensus (from new source poll, but same values)
        same_consensus = {
            "consensus_eps": 2.72,
            "consensus_revenue": 5.2e10,
            "earnings_date": "2026-07-18"
        }

        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=same_consensus), \
             patch("earnings_expectations._load_predictions",
                   return_value=[prior_pred]), \
             patch("earnings_expectations._append_prediction") as mock_append:

            result = harvest_earnings_expectations(["MSFT"])

        # Should NOT append (consensus unchanged)
        mock_append.assert_not_called()
        assert len(result) == 0
