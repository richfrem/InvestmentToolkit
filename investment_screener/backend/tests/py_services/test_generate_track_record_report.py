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


def _seed_ledger(tmp_path):
    """Seed a tmp_path-scoped intelligence.sqlite with one claim + one grade
    via the real append_event -> replay_events_to_db pipeline (Wave 5D Task 3
    test-isolation lesson: never point ledger/db writes at real tracked files).
    """
    from intelligence.db_client import initialize_db
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db

    ledger_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    conn = initialize_db(str(db_path))

    append_event(
        str(ledger_path), event_type="PREDICTION_CLAIM", effective_at="2026-07-01T00:00:00Z",
        status="ACTIVE", title="Prediction claim: AAPL action_rating (2026-07-01)",
        body_markdown="Direction: bullish, horizon: 90 days.", ticker="AAPL",
        payload={"id": "A", "ticker": "AAPL", "type": "action_rating", "direction": "bullish"},
        idempotency_key="prediction-claim-A",
    )
    append_event(
        str(ledger_path), event_type="PREDICTION_GRADED", effective_at="2026-10-01T00:00:00Z",
        status="ACTIVE", title="Prediction grade: AAPL action_rating (correct)",
        body_markdown="Outcome: correct, relative return: 0.1.", ticker="AAPL",
        payload={"predictionId": "A", "verdict": "correct", "outcome": "correct", "relativeReturn": 0.1},
        idempotency_key="prediction-grade-A",
    )
    replay_events_to_db(str(ledger_path), conn)
    return str(db_path)


class TestBuildReport:
    def test_report_has_expected_shape(self, tmp_path):
        db_path = _seed_ledger(tmp_path)

        report = build_report(db_path)
        assert report["totalPredictions"] == 1
        assert report["totalGraded"] == 1
        assert report["totalUngraded"] == 0
        assert report["byClaimType"]["action_rating"]["correct"] == 1

    def test_report_on_empty_ledger(self, tmp_path):
        from intelligence.db_client import initialize_db

        db_path = tmp_path / "empty_intelligence.sqlite"
        initialize_db(str(db_path))
        report = build_report(str(db_path))
        assert report["totalPredictions"] == 0
        assert report["byClaimType"] == {}


def test_report_reads_predictions_from_intelligence_ledger(tmp_path):
    """Wave 5D Task 3: build_report() must read PREDICTION_CLAIM/PREDICTION_GRADED
    events from intelligence.sqlite, not predictions.jsonl/predictions_graded.jsonl."""
    db_path = _seed_ledger(tmp_path)

    report = build_report(db_path)
    assert report["totalGraded"] == 1
    assert report["byClaimType"]["action_rating"]["correct"] == 1
