"""Tests for generate_track_record_report.py — E3 rolling hit-rate report."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from generate_track_record_report import build_report, compute_hit_rates  # noqa: E402


class TestComputeHitRates:
    def test_hit_rate_excludes_inconclusive_from_denominator(self):
        predictions = [
            {"id": "A", "type": "action_rating"},
            {"id": "B", "type": "action_rating"},
            {"id": "C", "type": "action_rating"},
        ]
        graded = [
            {"predictionId": "A", "verdict": "correct"},
            {"predictionId": "B", "verdict": "incorrect"},
            {"predictionId": "C", "verdict": "inconclusive"},
        ]
        result = compute_hit_rates(predictions, graded)
        assert result["action_rating"]["hitRate"] == 0.5
        assert result["action_rating"]["gradedTotal"] == 3

    def test_ungraded_predictions_are_excluded(self):
        predictions = [{"id": "A", "type": "action_rating"}, {"id": "B", "type": "action_rating"}]
        graded = [{"predictionId": "A", "verdict": "correct"}]
        result = compute_hit_rates(predictions, graded)
        assert result["action_rating"]["gradedTotal"] == 1

    def test_no_decisive_verdicts_yields_null_hit_rate(self):
        predictions = [{"id": "A", "type": "dcf_fair_value"}]
        graded = [{"predictionId": "A", "verdict": "inconclusive"}]
        result = compute_hit_rates(predictions, graded)
        assert result["dcf_fair_value"]["hitRate"] is None

    def test_empty_input_yields_empty_report(self):
        assert compute_hit_rates([], []) == {}


class TestBuildReport:
    def test_report_has_expected_shape(self, tmp_path):
        predictions_path = tmp_path / "predictions.jsonl"
        predictions_path.write_text(json.dumps({"id": "A", "type": "action_rating"}) + "\n")
        graded_path = tmp_path / "graded.jsonl"
        graded_path.write_text(json.dumps({"predictionId": "A", "verdict": "correct"}) + "\n")

        report = build_report(predictions_path, graded_path)
        assert report["totalPredictions"] == 1
        assert report["totalGraded"] == 1
        assert report["totalUngraded"] == 0
        assert report["byClaimType"]["action_rating"]["correct"] == 1

    def test_report_on_empty_ledger(self, tmp_path):
        report = build_report(tmp_path / "no_predictions.jsonl", tmp_path / "no_graded.jsonl")
        assert report["totalPredictions"] == 0
        assert report["byClaimType"] == {}
