"""Tests for harvest_predictions.py — E3 claim harvesting from projections/*.json."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from harvest_predictions import (  # noqa: E402
    _append_if_new,
    build_action_rating_claim,
    build_dcf_fair_value_claim,
    harvest_action_and_dcf_claims,
)


class TestBuildActionRatingClaim:
    def test_accumulate_is_bullish(self):
        projection = {"aiThesis": {"action": "ACCUMULATE", "analyzedAt": "2026-05-02T15:35:09Z"}}
        claim = build_action_rating_claim("CORZ", projection)
        assert claim == {
            "ticker": "CORZ", "type": "action_rating", "date": "2026-05-02",
            "claim": {"action": "ACCUMULATE"}, "direction": "bullish",
        }

    def test_trim_is_bearish(self):
        projection = {"aiThesis": {"action": "TRIM", "analyzedAt": "2026-05-02T15:35:09Z"}}
        claim = build_action_rating_claim("CORZ", projection)
        assert claim["direction"] == "bearish"

    def test_maintain_is_not_harvested(self):
        projection = {"aiThesis": {"action": "MAINTAIN", "analyzedAt": "2026-05-02T15:35:09Z"}}
        assert build_action_rating_claim("CORZ", projection) is None

    def test_watchlist_is_not_harvested(self):
        projection = {"aiThesis": {"action": "WATCHLIST", "analyzedAt": "2026-05-02T15:35:09Z"}}
        assert build_action_rating_claim("CORZ", projection) is None

    def test_missing_action_returns_none(self):
        assert build_action_rating_claim("CORZ", {"aiThesis": {}}) is None


class TestBuildDcfFairValueClaim:
    def test_uses_analytics_log_dcf_when_present(self):
        projection = {
            "aiThesis": {"analyzedAt": "2026-05-02T15:35:09Z"},
            "analyticsLog": {"dcf": {"weightedFairValue": 16.23, "upsidePct": -73}},
        }
        claim = build_dcf_fair_value_claim("CRSP", projection)
        assert claim["claim"] == {"fairValue": 16.23, "upsidePct": -73, "source": "analyticsLog.dcf"}
        assert claim["direction"] == "bearish"

    def test_falls_back_to_ai_thesis_when_no_analytics_dcf(self):
        projection = {
            "aiThesis": {"fairValue": 347.78, "analyzedAt": "2026-05-02T15:35:09Z"},
            "analyticsLog": {"dcf": None},
            "snapshot": {"price": 329.50},
        }
        claim = build_dcf_fair_value_claim("COHR", projection)
        assert claim["claim"]["fairValue"] == 347.78
        assert claim["claim"]["source"] == "aiThesis"
        assert claim["direction"] == "bullish"
        assert claim["claim"]["upsidePct"] == pytest.approx(5.54, abs=0.01)

    def test_missing_fair_value_and_no_snapshot_price_returns_none(self):
        projection = {"aiThesis": {"analyzedAt": "2026-05-02T15:35:09Z"}, "analyticsLog": {}}
        assert build_dcf_fair_value_claim("XYZ", projection) is None

    def test_missing_analyzed_at_returns_none(self):
        projection = {
            "aiThesis": {"fairValue": 100.0},
            "analyticsLog": {"dcf": {"weightedFairValue": 100.0, "upsidePct": 10}},
        }
        assert build_dcf_fair_value_claim("XYZ", projection) is None


class TestAppendIfNew:
    def _claim(self, date="2026-05-02"):
        return {
            "ticker": "CORZ", "type": "action_rating", "date": date,
            "claim": {"action": "ACCUMULATE"}, "direction": "bullish",
        }

    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_appends_new_claim(self, _mock_prices, tmp_path):
        path = tmp_path / "predictions.jsonl"
        result = _append_if_new(self._claim(), [], path)
        assert len(result) == 1
        assert result[0]["basePrice"] == 5.32
        assert result[0]["baseSpyPrice"] == 612.40
        assert result[0]["v"] == 1

    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_skips_unchanged_claim(self, _mock_prices, tmp_path):
        path = tmp_path / "predictions.jsonl"
        existing = _append_if_new(self._claim(), [], path)
        result = _append_if_new(self._claim(date="2026-06-01"), existing, path)
        assert result == []

    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_logs_new_claim_when_value_changed(self, _mock_prices, tmp_path):
        path = tmp_path / "predictions.jsonl"
        existing = _append_if_new(self._claim(), [], path)
        changed = {**self._claim(date="2026-06-01"), "claim": {"action": "TRIM"}, "direction": "bearish"}
        result = _append_if_new(changed, existing, path)
        assert len(result) == 1
        assert result[0]["claim"] == {"action": "TRIM"}

    @patch("harvest_predictions._fetch_base_prices", return_value=None)
    def test_skips_when_price_unavailable(self, _mock_prices, tmp_path):
        path = tmp_path / "predictions.jsonl"
        result = _append_if_new(self._claim(), [], path)
        assert result == []


class TestHarvestActionAndDcfClaims:
    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_harvests_both_claim_types_from_one_projection(self, _mock_prices, tmp_path):
        projections_dir = tmp_path / "projections"
        projections_dir.mkdir()
        (projections_dir / "CORZ.json").write_text(json.dumps([{
            "aiThesis": {"action": "TRIM", "fairValue": 10.64,
                          "analyzedAt": "2026-05-02T15:35:09Z"},
            "analyticsLog": {"dcf": None},
            "snapshot": {"price": 15.0},
        }]))
        predictions_path = tmp_path / "predictions.jsonl"
        result = harvest_action_and_dcf_claims(projections_dir, predictions_path)
        types = {r["type"] for r in result}
        assert types == {"action_rating", "dcf_fair_value"}

    def test_handles_empty_projections_dir(self, tmp_path):
        projections_dir = tmp_path / "projections"
        projections_dir.mkdir()
        result = harvest_action_and_dcf_claims(projections_dir, tmp_path / "predictions.jsonl")
        assert result == []
