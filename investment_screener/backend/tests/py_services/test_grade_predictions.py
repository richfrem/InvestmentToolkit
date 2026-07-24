"""Tests for grade_predictions.py — E3 weekly grading job."""
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from grade_predictions import (  # noqa: E402
    find_maturable_predictions,
    grade_prediction,
    run_grading,
)


def _prediction(**overrides):
    base = {
        "id": "CORZ:action_rating:2026-01-01", "date": "2026-01-01", "ticker": "CORZ",
        "type": "action_rating", "claim": {"action": "ACCUMULATE"}, "direction": "bullish",
        "horizonDays": 90, "basePrice": 5.0, "baseSpyPrice": 500.0,
    }
    base.update(overrides)
    return base


class TestFindMaturablePredictions:
    def test_matured_ungraded_is_included(self):
        predictions = [_prediction(date="2026-01-01", horizonDays=90)]
        result = find_maturable_predictions(predictions, graded_ids=set(), today=date(2026, 4, 2))
        assert len(result) == 1

    def test_not_yet_matured_is_excluded(self):
        predictions = [_prediction(date="2026-01-01", horizonDays=90)]
        result = find_maturable_predictions(predictions, graded_ids=set(), today=date(2026, 2, 1))
        assert result == []

    def test_already_graded_is_excluded(self):
        predictions = [_prediction(id="CORZ:action_rating:2026-01-01", date="2026-01-01", horizonDays=90)]
        result = find_maturable_predictions(
            predictions, graded_ids={"CORZ:action_rating:2026-01-01"}, today=date(2026, 4, 2),
        )
        assert result == []


class TestGradePrediction:
    def test_bullish_correct_outperformance(self):
        prediction = _prediction(basePrice=5.0, baseSpyPrice=500.0, direction="bullish")
        grade = grade_prediction(prediction, ticker_price_now=6.0, spy_price_now=505.0, graded_at="2026-04-02")
        assert grade["verdict"] == "correct"
        assert grade["predictionId"] == prediction["id"]
        assert grade["v"] == 1

    def test_bearish_correct_underperformance(self):
        prediction = _prediction(basePrice=5.0, baseSpyPrice=500.0, direction="bearish")
        grade = grade_prediction(prediction, ticker_price_now=4.0, spy_price_now=505.0, graded_at="2026-04-02")
        assert grade["verdict"] == "correct"

    def test_returns_are_rounded_and_present(self):
        prediction = _prediction(basePrice=5.0, baseSpyPrice=500.0, direction="bullish")
        grade = grade_prediction(prediction, ticker_price_now=6.0, spy_price_now=505.0, graded_at="2026-04-02")
        assert "tickerReturn" in grade and "spyReturn" in grade and "relativeReturn" in grade


def _seed_claim_event(tmp_path, db_path):
    """Seed a tmp_path-scoped intelligence.sqlite with one PREDICTION_CLAIM event
    (Wave 5D Task 3: run_grading() now reads from intelligence.sqlite, not JSONL)."""
    from intelligence.db_client import initialize_db
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db

    ledger_path = tmp_path / "observations.jsonl"
    conn = initialize_db(str(db_path))
    append_event(
        str(ledger_path), event_type="PREDICTION_CLAIM", effective_at="2026-01-01T00:00:00Z",
        status="ACTIVE", title="Prediction claim: CORZ action_rating (2026-01-01)",
        body_markdown="Direction: bullish, horizon: 90 days.", ticker="CORZ",
        payload={
            "id": "CORZ:action_rating:2026-01-01", "date": "2026-01-01", "ticker": "CORZ",
            "type": "action_rating", "claim": {"action": "ACCUMULATE"}, "direction": "bullish",
            "horizonDays": 90, "basePrice": 5.0, "baseSpyPrice": 500.0,
        },
        idempotency_key="prediction-claim-CORZ:action_rating:2026-01-01",
    )
    replay_events_to_db(str(ledger_path), conn)


class TestRunGrading:
    @patch("grade_predictions._fetch_current_prices", return_value=(6.0, 505.0))
    @patch("grade_predictions.date")
    def test_grades_matured_predictions_and_appends(self, mock_date, _mock_prices, tmp_path):
        mock_date.today.return_value = date(2026, 4, 2)
        mock_date.fromisoformat = date.fromisoformat
        db_path = tmp_path / "intelligence.sqlite"
        _seed_claim_event(tmp_path, db_path)
        graded_path = tmp_path / "graded.jsonl"
        result = run_grading(str(db_path), graded_path, jsonl_path=tmp_path / "observations.jsonl")
        assert len(result) == 1
        assert result[0]["predictionId"] == "CORZ:action_rating:2026-01-01"

    @patch("grade_predictions._fetch_current_prices", return_value=(6.0, 505.0))
    @patch("grade_predictions.date")
    def test_does_not_regrade_same_prediction_twice(self, mock_date, _mock_prices, tmp_path):
        mock_date.today.return_value = date(2026, 4, 2)
        mock_date.fromisoformat = date.fromisoformat
        from intelligence.replay_ledger import replay_events_to_db
        from intelligence.db_client import initialize_db

        db_path = tmp_path / "intelligence.sqlite"
        _seed_claim_event(tmp_path, db_path)
        graded_path = tmp_path / "graded.jsonl"
        observations_path = tmp_path / "observations.jsonl"

        run_grading(str(db_path), graded_path, jsonl_path=observations_path)
        # In production a periodic replay job re-syncs intelligence.sqlite from
        # the JSONL ledger between grading runs; simulate that step here since
        # this test spans two run_grading() calls within one process.
        replay_events_to_db(str(observations_path), initialize_db(str(db_path)))
        second_run = run_grading(str(db_path), graded_path, jsonl_path=observations_path)
        assert second_run == []

    @patch("grade_predictions._fetch_current_prices", return_value=(6.0, 505.0))
    @patch("grade_predictions.date")
    def test_reads_matured_predictions_from_intelligence_ledger(self, mock_date, _mock_prices, tmp_path):
        """Wave 5D Task 3: run_grading() must read PREDICTION_CLAIM events from
        intelligence.sqlite, not predictions.jsonl."""
        mock_date.today.return_value = date(2026, 4, 2)
        mock_date.fromisoformat = date.fromisoformat
        db_path = tmp_path / "intelligence.sqlite"
        _seed_claim_event(tmp_path, db_path)
        graded_path = tmp_path / "graded.jsonl"
        result = run_grading(str(db_path), graded_path, jsonl_path=tmp_path / "observations.jsonl")
        assert len(result) == 1
        assert result[0]["verdict"] in ("correct", "incorrect", "inconclusive")
