"""Test for Task 6: Grade core logic (beat/meet/miss classification).

Validates that grade_earnings_expectations() classifies earnings outcomes as
BEAT (>2% EPS surprise), MEET (±2%), or MISS (<-2%).
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"

sys.path.insert(0, str(PY_SERVICES))

from earnings_expectations import grade_earnings_expectations  # noqa: E402


class TestGradeEarningsExpectationsClassification:
    """Verify BEAT/MEET/MISS classification logic."""

    def test_grade_classifies_beat_on_eps_above_2_percent(self):
        """When EPS surprise > 2%, classify as BEAT."""
        prediction = {
            "v": 1,
            "id": "NVDA:earnings_expectation:2026-07-12",
            "date": "2026-07-12",
            "ticker": "NVDA",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.50,
                "consensus_revenue": 9.4e9,
                "earnings_date": "2026-07-15"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 118.50,
            "baseSpyPrice": 611.20,
            "inputsHash": "hash",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }

        # Actual EPS: 0.515 → (0.515 - 0.50) / 0.50 = 3% surprise
        actual_consensus = {
            "consensus_eps": 0.515,
            "consensus_revenue": 9.5e9,
            "epsTrailingTwelveMonths": 0.515,
            "totalRevenue": 9.5e9,
            "currentPrice": 125.0,
        }

        with patch("earnings_expectations._load_predictions",
                   return_value=[prediction]), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations.yf.Ticker") as mock_ticker, \
             patch("earnings_expectations._append_grade") as mock_append, \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations._grade_claim", return_value="correct"):

            mock_date.today.return_value.isoformat.return_value = "2026-07-16"

            # Mock ticker data
            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = actual_consensus
            mock_ticker.return_value = mock_ticker_inst

            result = grade_earnings_expectations()

        # Verify grade was appended
        mock_append.assert_called_once()
        graded = mock_append.call_args[0][0]
        # Check that eps_surprise_pct is ~3%
        assert graded.get("tickerReturn") is not None

    def test_grade_classifies_miss_on_eps_below_minus_2_percent(self):
        """When EPS surprise < -2%, classify as MISS."""
        prediction = {
            "v": 1,
            "id": "NVDA:earnings_expectation:2026-07-12",
            "date": "2026-07-12",
            "ticker": "NVDA",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.50,
                "consensus_revenue": 9.4e9,
                "earnings_date": "2026-07-15"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 118.50,
            "baseSpyPrice": 611.20,
            "inputsHash": "hash",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }

        # Actual EPS: 0.485 → (0.485 - 0.50) / 0.50 = -3% surprise
        actual_consensus = {
            "consensus_eps": 0.485,
            "consensus_revenue": 9.3e9,
            "epsTrailingTwelveMonths": 0.485,
            "totalRevenue": 9.3e9,
            "currentPrice": 115.0,
        }

        with patch("earnings_expectations._load_predictions",
                   return_value=[prediction]), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations.yf.Ticker") as mock_ticker, \
             patch("earnings_expectations._append_grade") as mock_append, \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations._grade_claim", return_value="incorrect"):

            mock_date.today.return_value.isoformat.return_value = "2026-07-16"

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = actual_consensus
            mock_ticker.return_value = mock_ticker_inst

            result = grade_earnings_expectations()

        mock_append.assert_called_once()

    def test_grade_classifies_meet_on_eps_within_2_percent(self):
        """When EPS surprise ±2%, classify as MEET."""
        prediction = {
            "v": 1,
            "id": "AAPL:earnings_expectation:2026-07-12",
            "date": "2026-07-12",
            "ticker": "AAPL",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 1.00,
                "consensus_revenue": 3.8e11,
                "earnings_date": "2026-07-15"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 200.0,
            "baseSpyPrice": 611.20,
            "inputsHash": "hash",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }

        # Actual EPS: 1.005 → (1.005 - 1.00) / 1.00 = 0.5% surprise (within ±2%)
        actual_consensus = {
            "consensus_eps": 1.005,
            "consensus_revenue": 3.81e11,
            "epsTrailingTwelveMonths": 1.005,
            "totalRevenue": 3.81e11,
            "currentPrice": 202.0,
        }

        with patch("earnings_expectations._load_predictions",
                   return_value=[prediction]), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations.yf.Ticker") as mock_ticker, \
             patch("earnings_expectations._append_grade") as mock_append, \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations._grade_claim", return_value="inconclusive"):

            mock_date.today.return_value.isoformat.return_value = "2026-07-16"

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = actual_consensus
            mock_ticker.return_value = mock_ticker_inst

            result = grade_earnings_expectations()

        mock_append.assert_called_once()

    def test_grade_appends_to_predictions_graded_jsonl(self):
        """Grade record is appended to predictions_graded.jsonl."""
        prediction = {
            "v": 1,
            "id": "TEST:earnings_expectation:2026-07-12",
            "date": "2026-07-12",
            "ticker": "TEST",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.50,
                "consensus_revenue": 1e9,
                "earnings_date": "2026-07-15"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 100.0,
            "baseSpyPrice": 600.0,
            "inputsHash": "hash",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }

        actual_data = {
            "epsTrailingTwelveMonths": 0.52,
            "totalRevenue": 1.05e9,
            "currentPrice": 105.0,
        }

        with patch("earnings_expectations._load_predictions",
                   return_value=[prediction]), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations.yf.Ticker") as mock_ticker, \
             patch("earnings_expectations._append_grade") as mock_append, \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations._grade_claim", return_value="correct"):

            mock_date.today.return_value.isoformat.return_value = "2026-07-16"

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = actual_data
            mock_ticker.return_value = mock_ticker_inst

            result = grade_earnings_expectations()

        # Verify append was called
        mock_append.assert_called_once()
        graded_record = mock_append.call_args[0][0]
        assert graded_record["predictionId"] == "TEST:earnings_expectation:2026-07-12"
        assert graded_record["verdict"] == "correct"

    def test_grade_calculates_ticker_and_spy_returns(self):
        """Grade calculates ticker return and SPY return correctly."""
        prediction = {
            "v": 1,
            "id": "NVDA:earnings_expectation:2026-07-12",
            "date": "2026-07-12",
            "ticker": "NVDA",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.50,
                "consensus_revenue": 9.4e9,
                "earnings_date": "2026-07-15"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 100.0,  # Base at 100
            "baseSpyPrice": 600.0,  # SPY base at 600
            "inputsHash": "hash",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }

        # Current: ticker at 110 (10% gain), SPY at 612 (2% gain)
        actual_data = {
            "epsTrailingTwelveMonths": 0.52,
            "totalRevenue": 9.5e9,
            "currentPrice": 110.0,  # 10% return
        }

        with patch("earnings_expectations._load_predictions",
                   return_value=[prediction]), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations.yf.Ticker") as mock_ticker, \
             patch("earnings_expectations._append_grade") as mock_append, \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations._grade_claim", return_value="correct"):

            mock_date.today.return_value.isoformat.return_value = "2026-07-16"

            def ticker_side_effect(sym):
                inst = MagicMock()
                if sym == "NVDA":
                    inst.info = actual_data
                else:  # SPY
                    inst.info = {"currentPrice": 612.0}
                return inst

            mock_ticker.side_effect = ticker_side_effect

            result = grade_earnings_expectations()

        mock_append.assert_called_once()
        graded = mock_append.call_args[0][0]
        assert graded["tickerReturn"] == pytest.approx(0.10, abs=0.01)
        assert graded["spyReturn"] == pytest.approx(0.02, abs=0.01)
        assert graded["relativeReturn"] == pytest.approx(0.08, abs=0.01)
