"""Tests for update_thesis.py's thesisBreakers CLI functions (B5 task 4)."""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
UPDATE_THESIS_DIR = REPO_ROOT / "plugins/portfolio-advisor/scripts"
sys.path.insert(0, str(UPDATE_THESIS_DIR))

from update_thesis import (  # noqa: E402
    AUTO_METRICS,
    remove_breaker,
    set_breaker,
    set_breaker_status,
    validate_breaker,
)


def _auto_breaker(**overrides) -> dict:
    b = {
        "id": "nbis-trend-breakdown",
        "type": "auto",
        "metric": "trendState",
        "operator": "in",
        "threshold": ["DOWNTREND"],
        "horizon": 5,
        "note": "Sustained downtrend",
    }
    b.update(overrides)
    return b


def _manual_breaker(**overrides) -> dict:
    b = {
        "id": "nbis-ndr-floor",
        "type": "manual",
        "metric": "ndr",
        "operator": "<",
        "threshold": 115,
        "horizon": "2 quarters",
        "note": "NDR floor",
        "status": "OK",
        "statusSetAt": "2026-07-01",
        "statusSetBy": "agent",
        "reviewCadenceDays": 90,
    }
    b.update(overrides)
    return b


class TestValidateBreaker:
    def test_valid_auto_breaker_has_no_errors(self):
        assert validate_breaker(_auto_breaker()) == []

    def test_valid_manual_breaker_has_no_errors(self):
        assert validate_breaker(_manual_breaker()) == []

    def test_missing_id_is_an_error(self):
        b = _auto_breaker()
        del b["id"]
        errors = validate_breaker(b)
        assert any("id" in e for e in errors)

    def test_invalid_type_is_an_error(self):
        errors = validate_breaker(_auto_breaker(type="weird"))
        assert any("type" in e for e in errors)

    def test_auto_metric_outside_enum_is_an_error(self):
        errors = validate_breaker(_auto_breaker(metric="madeUpMetric"))
        assert any("metric" in e for e in errors)

    def test_manual_metric_is_unrestricted(self):
        assert validate_breaker(_manual_breaker(metric="anything")) == []

    def test_invalid_operator_is_an_error(self):
        errors = validate_breaker(_auto_breaker(operator="!="))
        assert any("operator" in e for e in errors)

    def test_in_operator_requires_list_threshold(self):
        errors = validate_breaker(_auto_breaker(operator="in", threshold="DOWNTREND"))
        assert any("threshold" in e for e in errors)

    def test_manual_breaker_missing_status_is_an_error(self):
        b = _manual_breaker()
        del b["status"]
        errors = validate_breaker(b)
        assert any("status" in e for e in errors)

    def test_manual_breaker_invalid_status_is_an_error(self):
        errors = validate_breaker(_manual_breaker(status="MAYBE"))
        assert any("status" in e for e in errors)


class TestSetBreaker:
    def test_adds_breaker_to_holding_with_none_yet(self):
        holding = {"ticker": "NBIS"}
        set_breaker(holding, _auto_breaker())
        assert holding["thesisBreakers"] == [_auto_breaker()]

    def test_appends_to_existing_breakers(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_manual_breaker()]}
        set_breaker(holding, _auto_breaker())
        assert len(holding["thesisBreakers"]) == 2

    def test_duplicate_id_raises(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_auto_breaker()]}
        with pytest.raises(ValueError, match="already exists"):
            set_breaker(holding, _auto_breaker())

    def test_invalid_breaker_raises(self):
        holding = {"ticker": "NBIS"}
        with pytest.raises(ValueError, match="Invalid breaker"):
            set_breaker(holding, _auto_breaker(operator="!="))


class TestSetBreakerStatus:
    def test_updates_manual_breaker_status(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_manual_breaker()]}
        set_breaker_status(holding, "nbis-ndr-floor", "TRIGGERED", "Q2 NDR 108%")
        b = holding["thesisBreakers"][0]
        assert b["status"] == "TRIGGERED"
        assert b["statusSetAt"] == datetime.now(timezone.utc).date().isoformat()

    def test_status_note_appends_rather_than_overwrites(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_manual_breaker(note="NDR floor from 10-Q disclosures")]}
        set_breaker_status(holding, "nbis-ndr-floor", "TRIGGERED", "Q2 NDR 108%")
        b = holding["thesisBreakers"][0]
        assert "NDR floor from 10-Q disclosures" in b["note"]
        assert "Q2 NDR 108%" in b["note"]

    def test_missing_breaker_id_raises(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_manual_breaker()]}
        with pytest.raises(ValueError, match="not found"):
            set_breaker_status(holding, "does-not-exist", "TRIGGERED", None)

    def test_auto_breaker_status_raises(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_auto_breaker()]}
        with pytest.raises(ValueError, match="manual"):
            set_breaker_status(holding, "nbis-trend-breakdown", "TRIGGERED", None)


class TestRemoveBreaker:
    def test_removes_matching_breaker(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_auto_breaker(), _manual_breaker()]}
        remove_breaker(holding, "nbis-trend-breakdown")
        assert len(holding["thesisBreakers"]) == 1
        assert holding["thesisBreakers"][0]["id"] == "nbis-ndr-floor"

    def test_missing_id_raises(self):
        holding = {"ticker": "NBIS", "thesisBreakers": [_auto_breaker()]}
        with pytest.raises(ValueError, match="not found"):
            remove_breaker(holding, "does-not-exist")


def test_auto_metrics_matches_thesis_breakers_module():
    assert AUTO_METRICS == frozenset({
        "rsi", "dcfFairValueGapPct", "trendState", "momentumPercentile", "pillarAvgScore",
    })
