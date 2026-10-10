"""Tests for harvest_predictions.py — E3 claim harvesting from projections/*.json."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.projection_repository import save_projection_version  # noqa: E402
from harvest_predictions import (  # noqa: E402
    _append_if_new,
    _load_projection_from_db,
    build_action_rating_claim,
    build_dcf_fair_value_claim,
    harvest_action_and_dcf_claims,
)
from harvest_predictions import (  # noqa: E402
    build_breaker_forecast_claims,
    build_rebalance_order_claims,
    harvest_rebalance_and_breaker_claims,
)


class TestLoadProjectionFromDb:
    def test_selects_latest_ai_agent_entry_by_saved_at(self, tmp_path):
        """Mirrors real ANET.json history: multiple AI_AGENT revisions, latest
        saved_at wins (get_latest_projection_by_source's convention -- NOT
        MAX(version), per that function's own real-data-investigation docstring).
        """
        conn = initialize_db(str(tmp_path / "test.sqlite"))
        investment_id = resolve_investment(conn, "ANET", asset_class="EQUITY", currency="USD")
        save_projection_version(conn, investment_id, version=1, saved_at="2026-01-01T00:00:00Z",
                                 action="BUY", source="AI_AGENT")
        save_projection_version(conn, investment_id, version=2, saved_at="2026-03-01T00:00:00Z",
                                 action="INITIATE", source="AI_AGENT")
        result = _load_projection_from_db(conn, investment_id)
        assert result["aiThesis"]["action"] == "INITIATE"

    def test_single_entry_still_works(self, tmp_path):
        conn = initialize_db(str(tmp_path / "test.sqlite"))
        investment_id = resolve_investment(conn, "SINGLE", asset_class="EQUITY", currency="USD")
        save_projection_version(conn, investment_id, version=1, saved_at="2026-01-01T00:00:00Z",
                                 action="ACCUMULATE", source="AI_AGENT")
        result = _load_projection_from_db(conn, investment_id)
        assert result["aiThesis"]["action"] == "ACCUMULATE"

    def test_no_ai_agent_entries_returns_none(self, tmp_path):
        conn = initialize_db(str(tmp_path / "test.sqlite"))
        investment_id = resolve_investment(conn, "NOAI", asset_class="EQUITY", currency="USD")
        save_projection_version(conn, investment_id, version=1, saved_at="2026-01-01T00:00:00Z",
                                 action="BUY", source="HUMAN")
        assert _load_projection_from_db(conn, investment_id) is None


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
        result = _append_if_new(self._claim(), [], path, tmp_path / "observations.jsonl")
        assert len(result) == 1
        assert result[0]["basePrice"] == 5.32
        assert result[0]["baseSpyPrice"] == 612.40
        assert result[0]["v"] == 1

    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_skips_unchanged_claim(self, _mock_prices, tmp_path):
        path = tmp_path / "predictions.jsonl"
        jsonl_path = tmp_path / "observations.jsonl"
        existing = _append_if_new(self._claim(), [], path, jsonl_path)
        result = _append_if_new(self._claim(date="2026-06-01"), existing, path, jsonl_path)
        assert result == []

    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_logs_new_claim_when_value_changed(self, _mock_prices, tmp_path):
        path = tmp_path / "predictions.jsonl"
        jsonl_path = tmp_path / "observations.jsonl"
        existing = _append_if_new(self._claim(), [], path, jsonl_path)
        changed = {**self._claim(date="2026-06-01"), "claim": {"action": "TRIM"}, "direction": "bearish"}
        result = _append_if_new(changed, existing, path, jsonl_path)
        assert len(result) == 1
        assert result[0]["claim"] == {"action": "TRIM"}

    @patch("harvest_predictions._fetch_base_prices", return_value=None)
    def test_skips_when_price_unavailable(self, _mock_prices, tmp_path):
        path = tmp_path / "predictions.jsonl"
        result = _append_if_new(self._claim(), [], path, tmp_path / "observations.jsonl")
        assert result == []


class TestHarvestActionAndDcfClaims:
    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_harvests_both_claim_types_from_one_projection(self, _mock_prices, tmp_path):
        db_path = tmp_path / "test.sqlite"
        conn = initialize_db(str(db_path))
        investment_id = resolve_investment(conn, "CORZ", asset_class="EQUITY", currency="USD")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-05-02T15:35:09Z",
            analyzed_at="2026-05-02T15:35:09Z", action="TRIM", fair_value=10.64,
            source="AI_AGENT",
            snapshot_json=json.dumps({"price": 15.0}),
            analytics_log_json=json.dumps({"dcf": None}),
        )
        predictions_path = tmp_path / "predictions.jsonl"
        result = harvest_action_and_dcf_claims(
            db_path, predictions_path,
            intel_db_path=tmp_path / "intelligence.sqlite",
            jsonl_path=tmp_path / "observations.jsonl",
        )
        types = {r["type"] for r in result}
        assert types == {"action_rating", "dcf_fair_value"}

    def test_handles_no_investments_with_projections(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        initialize_db(str(db_path))
        result = harvest_action_and_dcf_claims(
            db_path, tmp_path / "predictions.jsonl",
            intel_db_path=tmp_path / "intelligence.sqlite",
            jsonl_path=tmp_path / "observations.jsonl",
        )
        assert result == []

    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_reads_existing_predictions_from_intelligence_ledger_for_dedup(self, _mock_prices, tmp_path):
        """Wave 5D Task 3: harvest_action_and_dcf_claims() must read existing
        prediction claims from intelligence.sqlite (for dedup), not
        predictions.jsonl."""
        from intelligence.db_client import initialize_db as intel_init
        from intelligence.event_store import append_event
        from intelligence.replay_ledger import replay_events_to_db

        db_path = tmp_path / "test.sqlite"
        conn = initialize_db(str(db_path))
        investment_id = resolve_investment(conn, "CORZ", asset_class="EQUITY", currency="USD")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-05-02T15:35:09Z",
            analyzed_at="2026-05-02T15:35:09Z", action="TRIM", fair_value=10.64,
            source="AI_AGENT",
            snapshot_json=json.dumps({"price": 15.0}),
            analytics_log_json=json.dumps({"dcf": None}),
        )

        # Seed the intelligence ledger with an existing, unchanged action_rating
        # claim for CORZ — dedup should skip re-appending it, proving the read
        # came from the ledger (not an empty predictions.jsonl).
        intel_db_path = tmp_path / "intelligence.sqlite"
        intel_ledger_path = tmp_path / "observations.jsonl"
        intel_conn = intel_init(str(intel_db_path))
        append_event(
            str(intel_ledger_path), event_type="PREDICTION_CLAIM", effective_at="2026-05-02",
            status="ACTIVE", title="Prediction claim: CORZ action_rating (2026-05-02)",
            body_markdown="Direction: bearish, horizon: 90 days.", ticker="CORZ",
            payload={
                "ticker": "CORZ", "type": "action_rating", "date": "2026-05-02",
                "claim": {"action": "TRIM"}, "direction": "bearish",
                "id": "CORZ:action_rating:2026-05-02",
            },
            idempotency_key="prediction-claim-CORZ:action_rating:2026-05-02",
        )
        replay_events_to_db(str(intel_ledger_path), intel_conn)

        result = harvest_action_and_dcf_claims(
            db_path, tmp_path / "predictions.jsonl",
            intel_db_path=intel_db_path, jsonl_path=tmp_path / "new_observations.jsonl",
        )
        types = {r["type"] for r in result}
        # action_rating is deduped (unchanged claim already on ledger); only
        # dcf_fair_value should be newly harvested.
        assert types == {"dcf_fair_value"}


class TestBuildRebalanceOrderClaims:
    def test_buy_is_bullish(self):
        plan = {"orders": [{"ticker": "CORZ", "action": "buy", "riskGateWarnings": [], "breakerWarnings": []}]}
        claims = build_rebalance_order_claims(plan, "2026-07-10")
        assert claims == [{
            "ticker": "CORZ", "type": "rebalance_order", "date": "2026-07-10",
            "claim": {"action": "buy", "gateWarningsPresent": False}, "direction": "bullish",
        }]

    def test_sell_is_bearish(self):
        plan = {"orders": [{"ticker": "PSU-U.TO", "action": "sell", "riskGateWarnings": [], "breakerWarnings": []}]}
        claims = build_rebalance_order_claims(plan, "2026-07-10")
        assert claims[0]["direction"] == "bearish"

    def test_gate_warnings_present_flag(self):
        plan = {"orders": [{"ticker": "NBIS", "action": "buy", "riskGateWarnings": ["cluster cap"], "breakerWarnings": []}]}
        claims = build_rebalance_order_claims(plan, "2026-07-10")
        assert claims[0]["claim"]["gateWarningsPresent"] is True

    def test_empty_orders_returns_empty_list(self):
        assert build_rebalance_order_claims({"orders": []}, "2026-07-10") == []

    def test_missing_ticker_or_action_skipped(self):
        plan = {"orders": [{"ticker": None, "action": "buy"}, {"ticker": "X", "action": "hold"}]}
        assert build_rebalance_order_claims(plan, "2026-07-10") == []


class TestBuildBreakerForecastClaims:
    def test_triggered_breaker_is_harvested_as_bearish(self):
        breaker_state = {"holdings": {"NBIS": {"rsi_breach": {"status": "TRIGGERED"}}}}
        target_data = {"holdings": [{"ticker": "NBIS", "thesisBreakers": [
            {"id": "rsi_breach", "metric": "rsi"}
        ]}]}
        claims = build_breaker_forecast_claims(breaker_state, target_data, "2026-07-10")
        assert claims == [{
            "ticker": "NBIS", "type": "breaker_forecast", "date": "2026-07-10",
            "claim": {"breakerId": "rsi_breach", "metric": "rsi", "status": "TRIGGERED"},
            "direction": "bearish",
        }]

    def test_non_triggered_breaker_is_not_harvested(self):
        breaker_state = {"holdings": {"NBIS": {"rsi_breach": {"status": "OK"}}}}
        target_data = {"holdings": [{"ticker": "NBIS", "thesisBreakers": [{"id": "rsi_breach", "metric": "rsi"}]}]}
        assert build_breaker_forecast_claims(breaker_state, target_data, "2026-07-10") == []

    def test_empty_holdings_returns_empty_list(self):
        assert build_breaker_forecast_claims({"holdings": {}}, {"holdings": []}, "2026-07-10") == []


class TestHarvestRebalanceAndBreakerClaims:
    @staticmethod
    def _db(tmp_path, with_triggered_breaker=False):
        """A temporary database, optionally holding one TRIGGERED breaker on NBIS evaluated 2026-07-10."""
        from domain_model.db_client import initialize_db
        from domain_model.investment_repository import resolve_investment, update_investment_fields
        from domain_model.thesis_breaker_repository import replace_breaker_state, upsert_breaker
        db_path = tmp_path / "domain_model.sqlite"
        conn = initialize_db(str(db_path))
        if with_triggered_breaker:
            update_investment_fields(conn, resolve_investment(conn, "NBIS"), target_weight=5.0)
            upsert_breaker(conn, "NBIS", {"id": "rsi_breach", "type": "auto", "metric": "rsi", "operator": "<", "threshold": 30, "horizon": 3})
            replace_breaker_state(conn, {"NBIS": {"rsi_breach": {
                "type": "auto", "currentValue": 20.0, "conditionMet": True, "currentStreak": 3,
                "lastEvaluatedAt": "2026-07-10T14:00:00Z", "status": "TRIGGERED"}}})
        conn.close()
        return db_path

    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_missing_rebalance_plan_and_no_breaker_state_is_not_an_error(self, _mock_prices, tmp_path):
        """No stored plan and no evaluated breaker state harvests nothing, without error."""
        result = harvest_rebalance_and_breaker_claims(
            db_path=self._db(tmp_path),
            predictions_path=tmp_path / "predictions.jsonl",
            intel_db_path=tmp_path / "intelligence.sqlite",
            jsonl_path=tmp_path / "observations.jsonl",
        )
        assert result == []

    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_harvests_from_both_sources_when_present(self, _mock_prices, tmp_path):
        """A stored rebalance plan plus a TRIGGERED breaker in SQLite give both claim types."""
        from domain_model.computed_snapshot_repository import save_snapshot
        db_path = self._db(tmp_path, with_triggered_breaker=True)
        conn = initialize_db(str(db_path))
        save_snapshot(conn, "rebalance_plan", {
            "generatedAt": "2026-07-10T14:00:00Z",
            "orders": [{"ticker": "CORZ", "action": "buy", "riskGateWarnings": [], "breakerWarnings": []}],
        })
        conn.close()
        result = harvest_rebalance_and_breaker_claims(
            db_path=db_path,
            predictions_path=tmp_path / "predictions.jsonl",
            intel_db_path=tmp_path / "intelligence.sqlite",
            jsonl_path=tmp_path / "observations.jsonl",
        )
        types = {r["type"] for r in result}
        assert types == {"rebalance_order", "breaker_forecast"}
        breaker = next(r for r in result if r["type"] == "breaker_forecast")
        assert breaker["claim"] == {"breakerId": "rsi_breach", "metric": "rsi", "status": "TRIGGERED"}
        assert breaker["date"] == "2026-07-10"

    def test_harvester_takes_no_json_file_parameters(self):
        """The retired target-portfolio and breaker-state file parameters are gone."""
        import inspect
        params = inspect.signature(harvest_rebalance_and_breaker_claims).parameters
        assert "target_portfolio_path" not in params and "thesis_breaker_state_path" not in params
        import harvest_predictions
        assert not hasattr(harvest_predictions, "THESIS_BREAKER_STATE_PATH") and not hasattr(harvest_predictions, "TARGET_PATH")
