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

from compute_conviction_scores import _resolve_pct_to_fv, _score_momentum  # noqa: E402


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

