"""Test for Task 7: Grade structural checks (past-date-only, idempotence).

Validates that grade_earnings_expectations() only grades predictions with
earnings_date <= today and that grading is idempotent.
"""
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"

sys.path.insert(0, str(PY_SERVICES))

from earnings_expectations import grade_earnings_expectations  # noqa: E402


class TestGradeEarningsExpectationsStructural:
    """Verify structural checks and idempotence."""

    def test_grade_only_grades_past_earnings_dates(self):
        """Predictions with future earnings_date are not graded."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        # Future earnings date
        future_prediction = {
            "v": 1,
            "id": "NVDA:earnings_expectation:2026-07-12",
            "date": "2026-07-12",
            "ticker": "NVDA",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.50,
                "consensus_revenue": 9.4e9,
                "earnings_date": tomorrow  # Future
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 118.50,
            "baseSpyPrice": 611.20,
            "inputsHash": "hash",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }

        with patch("earnings_expectations._load_predictions",
                   return_value=[future_prediction]), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations._append_grade") as mock_append:

            result = grade_earnings_expectations()

        # Should NOT grade (future date)
        mock_append.assert_not_called()
        assert result == []

    def test_grade_grades_today_earnings_date(self):
        """Predictions with earnings_date == today are graded."""
        today = date.today().isoformat()

        today_prediction = {
            "v": 1,
            "id": "NVDA:earnings_expectation:2026-07-12",
            "date": "2026-07-12",
            "ticker": "NVDA",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.50,
                "consensus_revenue": 9.4e9,
                "earnings_date": today  # Today
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 118.50,
            "baseSpyPrice": 611.20,
            "inputsHash": "hash",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }

        actual_data = {
            "epsTrailingTwelveMonths": 0.52,
            "totalRevenue": 9.5e9,
            "currentPrice": 120.0,
        }

        with patch("earnings_expectations._load_predictions",
                   return_value=[today_prediction]), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations.yf.Ticker") as mock_ticker, \
             patch("earnings_expectations._append_grade") as mock_append, \
             patch("earnings_expectations._grade_claim", return_value="correct"):

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = actual_data
            mock_ticker.return_value = mock_ticker_inst

            result = grade_earnings_expectations()

        # Should grade
        mock_append.assert_called_once()

    def test_grade_grades_past_earnings_dates(self):
        """Predictions with earnings_date < today are graded."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        past_prediction = {
            "v": 1,
            "id": "AAPL:earnings_expectation:2026-07-10",
            "date": "2026-07-10",
            "ticker": "AAPL",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 1.00,
                "consensus_revenue": 3.8e11,
                "earnings_date": yesterday  # Past
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 200.0,
            "baseSpyPrice": 600.0,
            "inputsHash": "hash",
            "harvestedAt": "2026-07-10T18:30:00Z"
        }

        actual_data = {
            "epsTrailingTwelveMonths": 1.02,
            "totalRevenue": 3.85e11,
            "currentPrice": 205.0,
        }

        with patch("earnings_expectations._load_predictions",
                   return_value=[past_prediction]), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations.yf.Ticker") as mock_ticker, \
             patch("earnings_expectations._append_grade") as mock_append, \
             patch("earnings_expectations._grade_claim", return_value="correct"):

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = actual_data
            mock_ticker.return_value = mock_ticker_inst

            result = grade_earnings_expectations()

        mock_append.assert_called_once()

    def test_grade_idempotent_same_prediction_twice(self):
        """Grading the same prediction twice produces identical output."""
        prediction = {
            "v": 1,
            "id": "NVDA:earnings_expectation:2026-07-12",
            "date": "2026-07-12",
            "ticker": "NVDA",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.50,
                "consensus_revenue": 9.4e9,
                "earnings_date": "2026-07-10"  # Past
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 118.50,
            "baseSpyPrice": 611.20,
            "inputsHash": "hash",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }

        actual_data = {
            "epsTrailingTwelveMonths": 0.52,
            "totalRevenue": 9.5e9,
            "currentPrice": 120.0,
        }

        # First grading
        with patch("earnings_expectations._load_predictions",
                   return_value=[prediction]), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations.yf.Ticker") as mock_ticker, \
             patch("earnings_expectations._append_grade") as mock_append1, \
             patch("earnings_expectations._grade_claim", return_value="correct"):

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = actual_data
            mock_ticker.return_value = mock_ticker_inst

            result1 = grade_earnings_expectations()
            first_grade = mock_append1.call_args[0][0] if mock_append1.call_args else None

        # Second grading (prediction already graded)
        graded_record = {
            "v": 1,
            "predictionId": "NVDA:earnings_expectation:2026-07-12",
            "gradedAt": "2026-07-16T18:30:00Z",
            "tickerReturn": 0.01176,
            "spyReturn": 0.0,
            "relativeReturn": 0.01176,
            "verdict": "correct"
        }

        with patch("earnings_expectations._load_predictions",
                   return_value=[prediction]), \
             patch("earnings_expectations._load_graded", return_value=[graded_record]), \
             patch("earnings_expectations._append_grade") as mock_append2:

            result2 = grade_earnings_expectations()

        # Second grading should NOT append (idempotence)
        mock_append2.assert_not_called()
        assert len(result2) == 0

    def test_grade_skips_non_earnings_expectation_types(self):
        """Predictions with type != 'earnings_expectation' are skipped."""
        other_type_prediction = {
            "v": 1,
            "id": "AAPL:action_rating:2026-07-12",
            "date": "2026-07-12",
            "ticker": "AAPL",
            "type": "action_rating",  # Not earnings_expectation
            "claim": {
                "action": "BUY",
                "conviction": 0.85
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 200.0,
            "baseSpyPrice": 600.0,
            "inputsHash": "hash",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }

        with patch("earnings_expectations._load_predictions",
                   return_value=[other_type_prediction]), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations._append_grade") as mock_append:

            result = grade_earnings_expectations()

        # Should NOT grade
        mock_append.assert_not_called()
        assert result == []

    def test_grade_skips_missing_earnings_date(self):
        """Predictions with missing earnings_date are skipped."""
        no_date_prediction = {
            "v": 1,
            "id": "NVDA:earnings_expectation:2026-07-12",
            "date": "2026-07-12",
            "ticker": "NVDA",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.50,
                "consensus_revenue": 9.4e9,
                "earnings_date": None  # Missing
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 118.50,
            "baseSpyPrice": 611.20,
            "inputsHash": "hash",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }

        with patch("earnings_expectations._load_predictions",
                   return_value=[no_date_prediction]), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations._append_grade") as mock_append:

            result = grade_earnings_expectations()

        mock_append.assert_not_called()
        assert result == []

    def test_grade_silently_degrades_on_missing_actual_data(self):
        """When actual EPS/revenue data unavailable, skip prediction gracefully."""
        prediction = {
            "v": 1,
            "id": "NVDA:earnings_expectation:2026-07-12",
            "date": "2026-07-12",
            "ticker": "NVDA",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.50,
                "consensus_revenue": 9.4e9,
                "earnings_date": "2026-07-10"  # Past
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 118.50,
            "baseSpyPrice": 611.20,
            "inputsHash": "hash",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }

        # Missing actual data
        actual_data = {
            "epsTrailingTwelveMonths": None,  # Missing
            "totalRevenue": None,  # Missing
            "currentPrice": 120.0,
        }

        with patch("earnings_expectations._load_predictions",
                   return_value=[prediction]), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations.yf.Ticker") as mock_ticker, \
             patch("earnings_expectations._append_grade") as mock_append:

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = actual_data
            mock_ticker.return_value = mock_ticker_inst

            result = grade_earnings_expectations()

        # Should NOT grade (missing data)
        mock_append.assert_not_called()
        assert result == []
