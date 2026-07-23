"""Tests for compute_conviction_scores.py — scoring component behavior.

Covers:
  - _score_momentum direction gate: ADX measures trend STRENGTH, not direction.
    A strong downtrend must never earn the +1 "momentum intact" bonus
    (falling-knife amplifier regression).
  - _resolve_pct_to_fv: % to fair value must be recomputed from the sweep's
    live close price, not trusted from the (historically FV-denominated)
    enriched pctToFV field, and must fall back to the projection value.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_compute_conviction_scores.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from compute_conviction_scores import _load_actual_weights, _resolve_pct_to_fv, _score_momentum  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402


class TestLoadActualWeightsReadsSqlite:
    """Wave 3 Task 6: _load_actual_weights() must read domain_model.sqlite,
    never portfolio.json."""

    def test_computes_weight_pct_from_sqlite_holdings(self, tmp_path):
        db_path = tmp_path / "domain_model.sqlite"
        conn = initialize_db(str(db_path))
        upsert_account(conn, "TFSA", "TFSA", "TFSA")
        aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
        msft_id = resolve_investment(conn, "MSFT", asset_class="EQUITY", currency="USD")
        upsert_investment_price(conn, aapl_id, price=100.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_investment_price(conn, msft_id, price=100.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_account_investment(
            conn, "TFSA", aapl_id, quantity=10, average_cost=90.0,
            book_value=900.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
        upsert_account_investment(
            conn, "TFSA", msft_id, quantity=10, average_cost=90.0,
            book_value=900.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
        conn.close()

        result = _load_actual_weights(db_path)
        assert result == {"AAPL": 50.0, "MSFT": 50.0}

    def test_missing_db_returns_empty(self, tmp_path):
        assert _load_actual_weights(tmp_path / "missing.sqlite") == {}


class TestScoreMomentumDirection:
    """ADX is directionless — the +1 bonus requires evidence the trend is UP."""

    def test_strong_uptrend_no_cooling_scores_plus_one(self):
        """ADX 40, RSI 60, no cooling → momentum intact, +1."""
        assert _score_momentum(40.0, [], rsi=60.0) == 1

    def test_strong_trend_with_cooling_scores_minus_one(self):
        """ADX 40 + RSI_COOLING → fading strong trend, −1 (unchanged behavior)."""
        assert _score_momentum(40.0, ["RSI_COOLING"], rsi=60.0) == -1

    def test_strong_downtrend_scores_minus_one(self):
        """ADX 40, RSI 35 → strong DOWNTREND. Must be −1, never +1.

        Regression: a stock in free-fall (ADX 45, RSI 35, no cooling flag
        because RSI never peaked) previously earned +1 'momentum intact' —
        amplifying falling knives in the ACCUMULATE queue.
        """
        assert _score_momentum(40.0, [], rsi=35.0) == -1

    def test_ambiguous_direction_scores_zero(self):
        """ADX 40, RSI 47 (45–55 band) → direction unclear, no bonus or penalty."""
        assert _score_momentum(40.0, [], rsi=47.0) == 0

    def test_weak_adx_scores_zero(self):
        """ADX 20 → no directional evidence regardless of RSI."""
        assert _score_momentum(20.0, [], rsi=60.0) == 0

    def test_none_adx_scores_zero(self):
        assert _score_momentum(None, [], rsi=60.0) == 0

    def test_strong_adx_unknown_rsi_scores_zero(self):
        """ADX 40 but RSI missing → direction unknowable, no +1 bonus."""
        assert _score_momentum(40.0, [], rsi=None) == 0


class TestResolvePctToFV:
    """% to FV must use the live sweep close as denominator when available."""

    def test_recomputes_from_sweep_close_and_fv(self):
        """Sweep has close 40.92 + FV 58.35 → +42.6%, ignoring the stored
        (FV-denominated, wrong) pctToFV of 29.9."""
        ta = {"close": 40.92, "dcf": {"fairValue": 58.35, "pctToFV": 29.9}}
        assert _resolve_pct_to_fv(ta, {}) == 42.6

    def test_downside_bounded_at_minus_100(self):
        """OKLO-style row: close 56.03, FV 6.65 → −88.1, not −742.6."""
        ta = {"close": 56.03, "dcf": {"fairValue": 6.65, "pctToFV": -742.6}}
        pct = _resolve_pct_to_fv(ta, {})
        assert pct == -88.1
        assert pct >= -100

    def test_falls_back_to_projection_when_no_sweep_data(self):
        assert _resolve_pct_to_fv({}, {"pctToFV": 12.0}) == 12.0

    def test_falls_back_when_sweep_missing_fair_value(self):
        ta = {"close": 40.92, "dcf": {"fairValue": None, "pctToFV": None}}
        assert _resolve_pct_to_fv(ta, {"pctToFV": 8.5}) == 8.5

    def test_projection_zero_pct_preserved(self):
        """A projection pctToFV of exactly 0.0 must survive (no `or` truthiness)."""
        assert _resolve_pct_to_fv({}, {"pctToFV": 0.0}) == 0.0

    def test_returns_none_when_no_data_anywhere(self):
        assert _resolve_pct_to_fv({}, {}) is None


class TestScoreLoadTaLedger:
    """_load_ta must be able to load TECHNICAL_SWEEP events from the SQLite DB."""

    def test_load_ta_from_sqlite(self, tmp_path):
        import sqlite3
        sys.path.insert(0, str(PY_SERVICES))
        from intelligence.db_client import initialize_db  # noqa: E402
        from intelligence.event_store import append_event  # noqa: E402
        from compute_conviction_scores import _load_ta  # noqa: PLC0415

        db_path = tmp_path / "intelligence.sqlite"
        jsonl_path = tmp_path / "observations.jsonl"

        # 1. Initialize the database and instrument
        conn = initialize_db(str(db_path))
        conn.execute("INSERT INTO instrument VALUES ('us-msft', 'MSFT', 'NASDAQ', 'Microsoft', '2026-07-18', NULL);")
        conn.commit()
        conn.close()

        # 2. Append TECHNICAL_SWEEP event to ledger
        append_event(
            str(jsonl_path),
            event_type="TECHNICAL_SWEEP",
            effective_at="2026-07-18",
            status="ACTIVE",
            title="TA Sweep MSFT",
            body_markdown="Sweep for MSFT",
            ticker="MSFT",
            source_id="tradingview-cdp",
            payload={
                "ticker": "MSFT",
                "close": 420.0,
                "rsi": 55.0,
                "adx": 30.0,
                "flags": ["ACCUM_SIGNAL"]
            },
            idempotency_key="ta-sweep-msft-2026-07-18"
        )

        # 3. Replay event to DB
        from intelligence.replay_ledger import replay_events_to_db
        conn = sqlite3.connect(str(db_path))
        replay_events_to_db(str(jsonl_path), conn)
        conn.close()

        # 4. Load from DB
        ta_map, stale_days = _load_ta(db_path=str(db_path))
        assert "MSFT" in ta_map
        assert ta_map["MSFT"]["close"] == 420.0
        assert ta_map["MSFT"]["rsi"] == 55.0
        assert ta_map["MSFT"]["flags"] == ["ACCUM_SIGNAL"]

    def test_load_ta_has_no_json_fallback_signature(self):
        """_load_ta must not accept a ta_json_path parameter — Wave 5B removed the fallback."""
        import inspect
        from compute_conviction_scores import _load_ta  # noqa: PLC0415
        sig = inspect.signature(_load_ta)
        assert "ta_json_path" not in sig.parameters

    def test_load_ta_returns_empty_on_missing_db_no_json_read(self, tmp_path, monkeypatch):
        """With no DB and no fallback, a missing db_path must return ({}, None) — never attempt
        to read any JSON file (Wave 5B: no fallback exists to attempt).
        """
        from compute_conviction_scores import _load_ta  # noqa: PLC0415
        missing_db = tmp_path / "does-not-exist.sqlite"
        ta_map, stale = _load_ta(db_path=str(missing_db))
        assert ta_map == {}
        assert stale is None


class TestLoadDcf:
    """_load_dcf must read from the domain_model SQLite `projection_version` table
    (Wave 1 Task 7A), preferring the latest AI_AGENT-sourced row over MAX(version)."""

    def _init_domain_db(self, tmp_path):
        import json as _json
        from domain_model.db_client import initialize_db  # noqa: PLC0415
        from domain_model.investment_repository import resolve_investment  # noqa: PLC0415
        from domain_model.projection_repository import save_projection_version  # noqa: PLC0415

        db_path = tmp_path / "domain_model.sqlite"
        conn = initialize_db(str(db_path))
        investment_id = resolve_investment(conn, "MSFT")
        # version 1: AI_AGENT, older
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-01-01T00:00:00Z",
            fair_value=300.0, action="HOLD", source="AI_AGENT",
            snapshot_json=_json.dumps({"price": 280.0}),
        )
        # version 2: ETF_ANALYSIS, newer, HIGHER version — must be ignored in favor
        # of the AI_AGENT row (Task 6 finding: MAX(version) alone is unsafe).
        save_projection_version(
            conn, investment_id, version=2, saved_at="2026-02-01T00:00:00Z",
            fair_value=999.0, action="SELL", source="ETF_ANALYSIS",
            snapshot_json=_json.dumps({"price": 280.0}),
        )
        conn.close()
        return db_path

    def test_prefers_latest_ai_agent_over_higher_version_other_source(self, tmp_path):
        from compute_conviction_scores import _load_dcf  # noqa: PLC0415

        db_path = self._init_domain_db(tmp_path)
        result = _load_dcf("MSFT", db_path=db_path)

        assert result["action"] == "HOLD"
        assert result["fairValue"] == 300.0
        assert result["pctToFV"] == round((300.0 - 280.0) / 280.0 * 100, 1)

    def test_falls_back_to_latest_version_when_no_ai_agent_row(self, tmp_path):
        import json as _json
        from domain_model.db_client import initialize_db  # noqa: PLC0415
        from domain_model.investment_repository import resolve_investment  # noqa: PLC0415
        from domain_model.projection_repository import save_projection_version  # noqa: PLC0415
        from compute_conviction_scores import _load_dcf  # noqa: PLC0415

        db_path = tmp_path / "domain_model.sqlite"
        conn = initialize_db(str(db_path))
        investment_id = resolve_investment(conn, "ETFX")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-01-01T00:00:00Z",
            fair_value=50.0, action="MAINTAIN", source="ETF_ANALYSIS",
            snapshot_json=_json.dumps({"price": 45.0}),
        )
        conn.close()

        result = _load_dcf("ETFX", db_path=db_path)
        assert result["action"] == "MAINTAIN"
        assert result["fairValue"] == 50.0

    def test_returns_empty_dict_when_ticker_unknown(self, tmp_path):
        from domain_model.db_client import initialize_db  # noqa: PLC0415
        from compute_conviction_scores import _load_dcf  # noqa: PLC0415

        db_path = tmp_path / "domain_model.sqlite"
        initialize_db(str(db_path)).close()

        assert _load_dcf("NOPE", db_path=db_path) == {}


class TestLoadTargetWeights:
    """_load_target_weights must read investment.target_weight from
    domain_model.sqlite (Wave 2 consumer cutover), not target-portfolio.json."""

    def test_reads_target_weight_from_sqlite(self, tmp_path):
        from domain_model.db_client import initialize_db  # noqa: PLC0415
        from domain_model.investment_repository import (  # noqa: PLC0415
            resolve_investment,
            update_investment_fields,
        )
        from compute_conviction_scores import _load_target_weights  # noqa: PLC0415

        db_path = tmp_path / "domain_model.sqlite"
        conn = initialize_db(str(db_path))
        investment_id = resolve_investment(conn, "MSFT")
        update_investment_fields(conn, investment_id, target_weight=5.5)
        conn.close()

        targets = _load_target_weights(db_path=str(db_path))
        assert targets["MSFT"] == 5.5

    def test_missing_target_weight_defaults_to_zero(self, tmp_path):
        from domain_model.db_client import initialize_db  # noqa: PLC0415
        from domain_model.investment_repository import resolve_investment  # noqa: PLC0415
        from compute_conviction_scores import _load_target_weights  # noqa: PLC0415

        db_path = tmp_path / "domain_model.sqlite"
        conn = initialize_db(str(db_path))
        resolve_investment(conn, "ZZZ")
        conn.close()

        targets = _load_target_weights(db_path=str(db_path))
        assert targets["ZZZ"] == 0

