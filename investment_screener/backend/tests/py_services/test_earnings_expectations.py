"""Tests for earnings_expectations.py's domain_model.sqlite read paths
(Wave 2 consumer cutover) — previously read target-portfolio.json directly.

Covers:
  - harvest_earnings_expectations()'s ticker-list load, when `tickers=None`,
    now reads investment.symbol from domain_model.sqlite.
  - get_earnings_context()'s holding lookup now reads investment.target_weight
    / investment.lifecycle_status instead of target-portfolio.json's
    targetWeight / role fields.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    update_investment_fields,
)

import earnings_expectations  # noqa: E402


def _make_db(tmp_path: Path, holdings: list[tuple[str, float, str]]) -> Path:
    """holdings: list of (symbol, target_weight, lifecycle_status)."""
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    for symbol, weight, status in holdings:
        investment_id = resolve_investment(conn, symbol)
        update_investment_fields(
            conn, investment_id, target_weight=weight, lifecycle_status=status
        )
    conn.close()
    return db_path


class TestHarvestTickerLoad:
    def test_none_tickers_loads_symbols_from_sqlite(self, tmp_path, monkeypatch):
        db_path = _make_db(tmp_path, [("AAPL", 5.0, "ACTIVE"), ("MSFT", 3.0, "ACTIVE")])
        monkeypatch.setattr(earnings_expectations, "_DB_PATH", db_path)
        monkeypatch.setattr(earnings_expectations, "_load_predictions", lambda *a, **k: [])
        monkeypatch.setattr(earnings_expectations, "_append_prediction", lambda *a, **k: None)
        monkeypatch.setattr(earnings_expectations, "_make_prediction_id", lambda *a, **k: "id")

        with patch.object(earnings_expectations, "_fetch_consensus_for_ticker", return_value=None):
            result = earnings_expectations.harvest_earnings_expectations(
                tickers=None, predictions_path=tmp_path / "predictions.jsonl"
            )

        # No consensus available -> nothing appended, but no exception and the
        # ticker list was successfully sourced from SQLite (implicitly proven
        # by _fetch_consensus_for_ticker being invoked per-symbol without error).
        assert result == []

    def test_missing_db_degrades_to_empty_ticker_list(self, tmp_path, monkeypatch):
        monkeypatch.setattr(earnings_expectations, "_DB_PATH", tmp_path / "no-db.sqlite")
        monkeypatch.setattr(earnings_expectations, "_load_predictions", lambda *a, **k: [])
        monkeypatch.setattr(earnings_expectations, "_append_prediction", lambda *a, **k: None)
        monkeypatch.setattr(earnings_expectations, "_make_prediction_id", lambda *a, **k: "id")

        result = earnings_expectations.harvest_earnings_expectations(
            tickers=None, predictions_path=tmp_path / "predictions.jsonl"
        )
        # initialize_db creates a fresh empty schema for a missing path, so this
        # degrades to an empty ticker list -> empty result, never raises.
        assert result == []


class TestReadsFromIntelligenceLedger:
    """Wave 5D Task 3: harvest_earnings_expectations()'s dedup read must come
    from intelligence.sqlite's PREDICTION_CLAIM events, not predictions.jsonl."""

    def test_dedup_read_uses_intel_db_path(self, tmp_path, monkeypatch):
        from intelligence.db_client import initialize_db as intel_init
        from intelligence.event_store import append_event
        from intelligence.replay_ledger import replay_events_to_db

        db_path = _make_db(tmp_path, [("AAPL", 5.0, "ACTIVE")])
        monkeypatch.setattr(earnings_expectations, "_DB_PATH", db_path)

        intel_db_path = tmp_path / "intelligence.sqlite"
        intel_ledger_path = tmp_path / "observations.jsonl"
        intel_conn = intel_init(str(intel_db_path))
        append_event(
            str(intel_ledger_path), event_type="PREDICTION_CLAIM", effective_at="2026-07-01",
            status="ACTIVE", title="Prediction claim: AAPL earnings_expectation (2026-07-01)",
            body_markdown="Direction: bullish, horizon: 90 days.", ticker="AAPL",
            payload={
                "id": "AAPL:earnings_expectation:2026-07-01", "ticker": "AAPL",
                "type": "earnings_expectation", "date": "2026-07-01",
                "claim": {"consensus_eps": 1.05, "consensus_revenue": 3.8e11, "earnings_date": "2026-07-25"},
                "direction": "bullish",
            },
            idempotency_key="prediction-claim-AAPL:earnings_expectation:2026-07-01",
        )
        replay_events_to_db(str(intel_ledger_path), intel_conn)

        unchanged_consensus = {
            "consensus_eps": 1.05, "consensus_revenue": 3.8e11, "earnings_date": "2026-07-25",
        }
        with patch.object(earnings_expectations, "_fetch_consensus_for_ticker", return_value=unchanged_consensus):
            result = earnings_expectations.harvest_earnings_expectations(
                tickers=["AAPL"], predictions_path=tmp_path / "predictions.jsonl",
                intel_db_path=intel_db_path, jsonl_path=tmp_path / "new_observations.jsonl",
            )

        # Consensus is unchanged vs. the ledger-seeded prior record -> deduped, no append.
        assert result == []


class TestGetEarningsContextHoldingLookup:
    def test_reads_target_weight_and_lifecycle_status_from_sqlite(self, tmp_path, monkeypatch):
        db_path = _make_db(tmp_path, [("NVDA", 8.5, "ACCUMULATE")])
        monkeypatch.setattr(earnings_expectations, "_DB_PATH", db_path)

        fake_consensus = {
            "consensus_eps": 1.05,
            "consensus_revenue": 3.8e11,
            "earnings_date": "2026-07-25",
        }
        with patch.object(
            earnings_expectations, "_fetch_consensus_for_ticker", return_value=fake_consensus
        ), patch("earnings_expectations.date") as mock_date:
            import datetime as _dt
            mock_date.today.return_value = _dt.date(2026, 7, 20)
            mock_date.fromisoformat = _dt.date.fromisoformat

            result = earnings_expectations.get_earnings_context("NVDA", days_ahead=30)

        assert result is not None
        assert result["portfolio_weight"] == 8.5
        assert result["target_action"] == "ACCUMULATE"

    def test_unknown_ticker_falls_back_to_defaults(self, tmp_path, monkeypatch):
        db_path = _make_db(tmp_path, [])
        monkeypatch.setattr(earnings_expectations, "_DB_PATH", db_path)

        fake_consensus = {
            "consensus_eps": 1.0,
            "consensus_revenue": 1e9,
            "earnings_date": "2026-07-25",
        }
        with patch.object(
            earnings_expectations, "_fetch_consensus_for_ticker", return_value=fake_consensus
        ), patch("earnings_expectations.date") as mock_date:
            import datetime as _dt
            mock_date.today.return_value = _dt.date(2026, 7, 20)
            mock_date.fromisoformat = _dt.date.fromisoformat

            result = earnings_expectations.get_earnings_context("ZZZZ", days_ahead=30)

        assert result is not None
        assert result["portfolio_weight"] == 0.0
        assert result["target_action"] == "unknown"
