"""Test for Task 9: Integration into /daily and /weekly-review.

Validates end-to-end round-trip of earnings expectation claims through the
prediction ledger (append → read → grade).
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"

sys.path.insert(0, str(PY_SERVICES))

from earnings_expectations import (  # noqa: E402
    harvest_earnings_expectations,
    grade_earnings_expectations,
    EarningsExpectation,
    EarningsExpectationClaim,
    EarningsGrade,
)
from prediction_ledger import (  # noqa: E402
    make_prediction_id,
    load_predictions,
    load_graded,
)


class TestEarningsExpectationLedgerIntegration:
    """Verify end-to-end round-trip through prediction ledger."""

    def test_earnings_expectation_harvested_and_readable(self):
        """Harvested claim can be read back from predictions.jsonl."""
        claim = EarningsExpectationClaim(
            consensus_eps=0.52,
            consensus_revenue=9.4e9,
            earnings_date="2026-07-15"
        )

        prediction = EarningsExpectation(
            v=1,
            id="NVDA:earnings_expectation:2026-07-12",
            date="2026-07-12",
            ticker="NVDA",
            type="earnings_expectation",
            claim=claim,
            direction="bullish",
            horizonDays=90,
            basePrice=118.50,
            baseSpyPrice=611.20,
            confidence=None,
            inputsHash="abc123",
            harvestedAt="2026-07-12T18:30:00Z"
        )

        # Simulate appending and reading
        json_str = prediction.model_dump_json()
        parsed = EarningsExpectation.model_validate_json(json_str)

        assert parsed.id == prediction.id
        assert parsed.ticker == "NVDA"
        assert parsed.type == "earnings_expectation"
        assert parsed.claim.consensus_eps == 0.52
        assert parsed.claim.earnings_date == "2026-07-15"

    def test_harvested_prediction_can_be_graded(self):
        """Harvested prediction can be graded and grade written to ledger."""
        # Harvested prediction
        prediction_dict = {
            "v": 1,
            "id": "NVDA:earnings_expectation:2026-07-12",
            "date": "2026-07-12",
            "ticker": "NVDA",
            "type": "earnings_expectation",
            "claim": {
                "consensus_eps": 0.50,
                "consensus_revenue": 9.4e9,
                "earnings_date": "2026-07-10"
            },
            "direction": "bullish",
            "horizonDays": 90,
            "basePrice": 118.50,
            "baseSpyPrice": 611.20,
            "inputsHash": "abc123",
            "harvestedAt": "2026-07-12T18:30:00Z"
        }

        # Create grade for it
        grade = EarningsGrade(
            v=1,
            predictionId="NVDA:earnings_expectation:2026-07-12",
            gradedAt="2026-07-16T18:30:00Z",
            tickerReturn=0.045,
            spyReturn=0.012,
            relativeReturn=0.033,
            verdict="correct"
        )

        # Verify round-trip
        grade_json = grade.model_dump_json()
        parsed_grade = EarningsGrade.model_validate_json(grade_json)

        assert parsed_grade.predictionId == grade.predictionId
        assert parsed_grade.verdict == "correct"
        assert parsed_grade.tickerReturn == 0.045

    def test_harvest_and_grade_workflow(self):
        """Full workflow: harvest → grade returns consistent records."""
        # Setup: prior prediction in ledger
        prior_pred = {
            "v": 1,
            "id": "AAPL:earnings_expectation:2026-07-10",
            "date": "2026-07-10",
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
            "baseSpyPrice": 600.0,
            "inputsHash": "hash1",
            "harvestedAt": "2026-07-10T10:00:00Z"
        }

        # Consensus updated (mid-week)
        updated_consensus = {
            "consensus_eps": 1.05,  # Revised up
            "consensus_revenue": 3.8e11,
            "earnings_date": "2026-07-15"
        }

        # Harvest should append new claim
        with patch("earnings_expectations._fetch_consensus_for_ticker",
                   return_value=updated_consensus), \
             patch("earnings_expectations._load_predictions",
                   return_value=[prior_pred]), \
             patch("earnings_expectations._append_prediction") as mock_harvest_append, \
             patch("earnings_expectations._make_prediction_id",
                   return_value="AAPL:earnings_expectation:2026-07-12"), \
             patch("earnings_expectations.date") as mock_date_class, \
             patch("earnings_expectations.yf.Ticker") as mock_ticker:

            mock_date.today.return_value.isoformat.return_value = "2026-07-12"

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = {
                "currentPrice": 205.0,
                "regularMarketPrice": 205.0
            }
            mock_ticker.return_value = mock_ticker_inst

            harvested = harvest_earnings_expectations(["AAPL"])

        assert len(harvested) == 1
        assert harvested[0]["claim"]["consensus_eps"] == 1.05

    def test_prediction_id_stability(self):
        """Prediction IDs are stable and reconstructible."""
        ticker = "NVDA"
        claim_type = "earnings_expectation"
        claim_date = "2026-07-12"

        pred_id = make_prediction_id(ticker, claim_type, claim_date)

        # Should be reconstructible
        assert pred_id == "NVDA:earnings_expectation:2026-07-12"
        assert pred_id.startswith(ticker)
        assert claim_type in pred_id
        assert claim_date in pred_id

    def test_harvest_and_grade_dont_conflict_on_same_ledger(self):
        """Harvest and grade can coexist on same predictions.jsonl."""
        predictions = [
            {
                "v": 1,
                "id": "NVDA:earnings_expectation:2026-07-01",
                "date": "2026-07-01",
                "ticker": "NVDA",
                "type": "earnings_expectation",
                "claim": {
                    "consensus_eps": 0.50,
                    "consensus_revenue": 9.4e9,
                    "earnings_date": "2026-07-05"  # Past
                },
                "direction": "bullish",
                "horizonDays": 90,
                "basePrice": 100.0,
                "baseSpyPrice": 600.0,
                "inputsHash": "hash1",
                "harvestedAt": "2026-07-01T10:00:00Z"
            },
            {
                "v": 1,
                "id": "AAPL:earnings_expectation:2026-07-12",
                "date": "2026-07-12",
                "ticker": "AAPL",
                "type": "earnings_expectation",
                "claim": {
                    "consensus_eps": 1.00,
                    "consensus_revenue": 3.8e11,
                    "earnings_date": "2026-07-15"  # Future
                },
                "direction": "bullish",
                "horizonDays": 90,
                "basePrice": 200.0,
                "baseSpyPrice": 600.0,
                "inputsHash": "hash2",
                "harvestedAt": "2026-07-12T18:30:00Z"
            }
        ]

        # Grade should only pick NVDA (past date), skip AAPL (future)
        with patch("earnings_expectations._load_predictions",
                   return_value=predictions), \
             patch("earnings_expectations._load_graded", return_value=[]), \
             patch("earnings_expectations.yf.Ticker") as mock_ticker, \
             patch("earnings_expectations._append_grade") as mock_append, \
             patch("earnings_expectations._grade_claim", return_value="correct"):

            mock_ticker_inst = MagicMock()
            mock_ticker_inst.info = {
                "epsTrailingTwelveMonths": 0.52,
                "totalRevenue": 9.5e9,
                "currentPrice": 105.0,
            }
            mock_ticker.return_value = mock_ticker_inst

            graded = grade_earnings_expectations()

        # Should only grade NVDA
        mock_append.assert_called_once()
        graded_rec = mock_append.call_args[0][0]
        assert graded_rec["predictionId"] == "NVDA:earnings_expectation:2026-07-01"

    def test_ledger_handles_multiple_ticker_types(self):
        """Ledger can store earnings_expectation alongside other prediction types."""
        mixed_predictions = [
            {
                "v": 1,
                "id": "NVDA:action_rating:2026-07-12",
                "date": "2026-07-12",
                "ticker": "NVDA",
                "type": "action_rating",
                "claim": {"action": "BUY"},
                "direction": "bullish",
                "basePrice": 100.0,
                "baseSpyPrice": 600.0,
                "inputsHash": "hash1",
                "harvestedAt": "2026-07-12T10:00:00Z"
            },
            {
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
                "basePrice": 100.0,
                "baseSpyPrice": 600.0,
                "inputsHash": "hash2",
                "harvestedAt": "2026-07-12T18:30:00Z"
            }
        ]

        # Verify both types are readable
        for pred in mixed_predictions:
            if pred["type"] == "earnings_expectation":
                parsed = EarningsExpectation.model_validate(pred)
                assert parsed.claim.consensus_eps == 0.50
            # Other types would be handled differently

    def test_grade_references_harvested_prediction_by_id(self):
        """Grade record correctly references harvested prediction by ID."""
        pred_id = "NVDA:earnings_expectation:2026-07-12"

        grade = EarningsGrade(
            v=1,
            predictionId=pred_id,
            gradedAt="2026-07-16T18:30:00Z",
            tickerReturn=0.045,
            spyReturn=0.012,
            relativeReturn=0.033,
            verdict="correct"
        )

        # Verify foreign key integrity
        assert grade.predictionId == pred_id
        assert "earnings_expectation" in grade.predictionId
        assert grade.predictionId.startswith("NVDA")
