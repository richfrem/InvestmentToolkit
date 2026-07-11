"""Tests for prediction_ledger.py — E3 append-only prediction ledger core."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from prediction_ledger import (  # noqa: E402
    append_grade,
    append_prediction,
    grade_claim,
    latest_prediction_for,
    load_graded,
    load_predictions,
    make_prediction_id,
)


class TestMakePredictionId:
    def test_format(self):
        assert make_prediction_id("CORZ", "action_rating", "2026-05-02") == \
            "CORZ:action_rating:2026-05-02"


class TestAppendAndLoadPredictions:
    def test_roundtrip(self, tmp_path):
        path = tmp_path / "predictions.jsonl"
        record = {"id": "AAPL:action_rating:2026-01-01", "ticker": "AAPL"}
        append_prediction(record, path)
        loaded = load_predictions(path)
        assert loaded == [record]

    def test_appends_without_truncating(self, tmp_path):
        path = tmp_path / "predictions.jsonl"
        append_prediction({"id": "A"}, path)
        append_prediction({"id": "B"}, path)
        loaded = load_predictions(path)
        assert [r["id"] for r in loaded] == ["A", "B"]

    def test_load_missing_file_returns_empty_list(self, tmp_path):
        assert load_predictions(tmp_path / "does_not_exist.jsonl") == []


class TestAppendAndLoadGraded:
    def test_roundtrip(self, tmp_path):
        path = tmp_path / "graded.jsonl"
        record = {"predictionId": "AAPL:action_rating:2026-01-01", "verdict": "correct"}
        append_grade(record, path)
        assert load_graded(path) == [record]

    def test_load_missing_file_returns_empty_list(self, tmp_path):
        assert load_graded(tmp_path / "does_not_exist.jsonl") == []


class TestLatestPredictionFor:
    def test_returns_most_recent_match(self):
        predictions = [
            {"ticker": "CORZ", "type": "action_rating", "date": "2026-01-01", "claim": {"action": "ACCUMULATE"}},
            {"ticker": "CORZ", "type": "dcf_fair_value", "date": "2026-01-01", "claim": {"fairValue": 10}},
            {"ticker": "CORZ", "type": "action_rating", "date": "2026-03-01", "claim": {"action": "TRIM"}},
        ]
        result = latest_prediction_for("CORZ", "action_rating", predictions)
        assert result["date"] == "2026-03-01"

    def test_returns_none_when_no_match(self):
        assert latest_prediction_for("NVDA", "action_rating", []) is None


class TestGradeClaim:
    def test_bullish_correct(self):
        assert grade_claim("bullish", 0.05) == "correct"

    def test_bullish_incorrect(self):
        assert grade_claim("bullish", -0.05) == "incorrect"

    def test_bullish_inconclusive_within_band(self):
        assert grade_claim("bullish", 0.01) == "inconclusive"

    def test_bearish_correct(self):
        assert grade_claim("bearish", -0.05) == "correct"

    def test_bearish_incorrect(self):
        assert grade_claim("bearish", 0.05) == "incorrect"

    def test_bearish_inconclusive_within_band(self):
        assert grade_claim("bearish", -0.01) == "inconclusive"

    def test_boundary_exactly_at_band_is_inconclusive(self):
        assert grade_claim("bullish", 0.02) == "inconclusive"
        assert grade_claim("bearish", -0.02) == "inconclusive"
