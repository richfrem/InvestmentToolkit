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
    make_prediction_id,
)


class TestMakePredictionId:
    def test_format(self):
        assert make_prediction_id("CORZ", "action_rating", "2026-05-02") == \
            "CORZ:action_rating:2026-05-02"


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


def test_append_prediction_writes_a_prediction_claim_event(tmp_path):
    """append_prediction() stores one PREDICTION_CLAIM event in the ledger database."""
    from intelligence.db_client import initialize_db
    from intelligence.event_repository import get_latest_event_by_type

    db_path = tmp_path / "intelligence.sqlite"
    record = {
        "id": "AAPL:action_rating:2026-07-23",
        "ticker": "AAPL",
        "type": "action_rating",
        "date": "2026-07-23",
        "direction": "bullish",
        "horizonDays": 90,
    }
    append_prediction(record, db_path)
    append_prediction(record, db_path)  # idempotent on the prediction id

    conn = initialize_db(str(db_path))
    try:
        event = get_latest_event_by_type(conn, "PREDICTION_CLAIM")
        count = conn.execute("SELECT COUNT(*) FROM intelligence_event WHERE event_type = 'PREDICTION_CLAIM';").fetchone()[0]
    finally:
        conn.close()
    assert event is not None
    assert event["title"] == "Prediction claim: AAPL action_rating (2026-07-23)"
    assert count == 1
    assert not list(tmp_path.glob("*.jsonl"))


def test_append_grade_writes_a_prediction_graded_event(tmp_path):
    """append_grade() stores one PREDICTION_GRADED event in the ledger database."""
    from intelligence.db_client import initialize_db
    from intelligence.event_repository import get_latest_event_by_type

    db_path = tmp_path / "intelligence.sqlite"
    grade_record = {
        "predictionId": "AAPL:action_rating:2026-07-23",
        "ticker": "AAPL",
        "gradedAt": "2026-10-23",
        "outcome": "correct",
        "relativeReturn": 0.08,
    }
    append_grade(grade_record, db_path)

    conn = initialize_db(str(db_path))
    try:
        event = get_latest_event_by_type(conn, "PREDICTION_GRADED")
    finally:
        conn.close()
    assert event is not None
    assert event["title"] == "Prediction grade: AAPL action_rating (correct)"
    assert not list(tmp_path.glob("*.jsonl"))


def test_append_prediction_raises_when_the_ledger_write_fails(tmp_path):
    """There is no file fallback: a ledger failure propagates."""
    import pytest

    record = {"id": "X:action_rating:2026-07-23", "ticker": "X", "type": "action_rating", "date": "bad"}
    bad_db = tmp_path / "missing_dir" / "ledger.sqlite"
    with pytest.raises(Exception):
        append_prediction(record, bad_db)
