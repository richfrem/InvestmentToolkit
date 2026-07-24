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
        append_prediction(record, path, jsonl_path=tmp_path / "observations.jsonl")
        loaded = load_predictions(path)
        assert loaded == [record]

    def test_appends_without_truncating(self, tmp_path):
        path = tmp_path / "predictions.jsonl"
        ledger_path = tmp_path / "observations.jsonl"
        append_prediction({"id": "A"}, path, jsonl_path=ledger_path)
        append_prediction({"id": "B"}, path, jsonl_path=ledger_path)
        loaded = load_predictions(path)
        assert [r["id"] for r in loaded] == ["A", "B"]

    def test_load_missing_file_returns_empty_list(self, tmp_path):
        assert load_predictions(tmp_path / "does_not_exist.jsonl") == []


class TestAppendAndLoadGraded:
    def test_roundtrip(self, tmp_path):
        path = tmp_path / "graded.jsonl"
        record = {"predictionId": "AAPL:action_rating:2026-01-01", "verdict": "correct"}
        append_grade(record, path, jsonl_path=tmp_path / "observations.jsonl")
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


def test_append_prediction_dual_writes_to_intelligence_ledger(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "investment_screener/backend/py_services"))
    from intelligence.db_client import initialize_db
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.event_repository import get_latest_event_by_type
    from prediction_ledger import append_prediction

    jsonl_path = tmp_path / "predictions.jsonl"
    ledger_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    record = {
        "id": "AAPL:action_rating:2026-07-23",
        "ticker": "AAPL",
        "type": "action_rating",
        "date": "2026-07-23",
        "direction": "bullish",
        "horizonDays": 90,
    }
    append_prediction(record, path=jsonl_path, jsonl_path=ledger_path)

    assert jsonl_path.exists()
    with open(jsonl_path) as f:
        assert len(f.readlines()) == 1

    assert ledger_path.exists()
    conn = initialize_db(str(db_path))
    replay_events_to_db(str(ledger_path), conn)
    event = get_latest_event_by_type(conn, "PREDICTION_CLAIM")
    assert event is not None
    assert event["title"] == "Prediction claim: AAPL action_rating (2026-07-23)"


def test_append_grade_dual_writes_to_intelligence_ledger(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "investment_screener/backend/py_services"))
    from intelligence.db_client import initialize_db
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.event_repository import get_latest_event_by_type
    from prediction_ledger import append_grade

    graded_jsonl_path = tmp_path / "predictions_graded.jsonl"
    ledger_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"

    grade_record = {
        "predictionId": "AAPL:action_rating:2026-07-23",
        "ticker": "AAPL",
        "gradedAt": "2026-10-23",
        "outcome": "correct",
        "relativeReturn": 0.08,
    }
    append_grade(grade_record, path=graded_jsonl_path, jsonl_path=ledger_path)

    assert graded_jsonl_path.exists()
    conn = initialize_db(str(db_path))
    replay_events_to_db(str(ledger_path), conn)
    event = get_latest_event_by_type(conn, "PREDICTION_GRADED")
    assert event is not None
    assert event["title"] == "Prediction grade: AAPL action_rating (correct)"


def test_append_prediction_still_writes_jsonl_when_ledger_write_fails(tmp_path, monkeypatch):
    """JSONL remains the authoritative source during the dual-write window (Hybrid Exit
    Criteria below) -- a ledger-side failure must not silently lose the JSONL append, since
    JSONL is still what every consumer reads until Task 3 cuts them over."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "investment_screener/backend/py_services"))
    import prediction_ledger

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated ledger outage")

    monkeypatch.setattr(prediction_ledger, "_append_prediction_event", _boom)

    jsonl_path = tmp_path / "predictions.jsonl"
    record = {"id": "X:action_rating:2026-07-23", "ticker": "X", "type": "action_rating"}
    prediction_ledger.append_prediction(record, path=jsonl_path)

    assert jsonl_path.exists()
    with open(jsonl_path) as f:
        assert len(f.readlines()) == 1
