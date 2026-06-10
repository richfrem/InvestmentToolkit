"""Tests for brief_recommendations.py — actionable recommendation builder.

Converts conviction scores + standing decisions + macro gate + earnings flags
into per-ticker recommendation cards (action, rationale, proposed trade) for
the Daily Brief modal. Standing decisions ANNOTATE — they never mute the
signal (no-sycophancy rule) — but they do downgrade the proposed action so
the system never recommends trades against the user's documented calls.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_brief_recommendations.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from brief_recommendations import build_recommendations  # noqa: E402


def _score(ticker: str, total: int, band: str, **kw) -> dict:
    """Minimal conviction-score row fixture."""
    base = {
        "ticker": ticker, "total": total, "band": band,
        "dcf_action": "SELL" if total < 0 else "BUY",
        "pct_to_fv": -50.0 if total < 0 else 80.0,
        "rsi": 50.0, "adx": 25.0, "vol_bias": None,
        "actual_weight": 2.0, "target_weight": 2.0, "weight_gap": 0.0,
        "flags": [],
    }
    base.update(kw)
    return base


RISK_ON = {"regime": "RISK-ON", "score": 2, "degraded": False}
RISK_OFF = {"regime": "RISK-OFF", "score": -2, "degraded": False}
NEUTRAL = {"regime": "NEUTRAL", "score": 1, "degraded": False}


class TestSellRecommendations:

    def test_exit_band_held_no_standing_decision_recommends_sell(self):
        recs = build_recommendations(
            scores=[_score("IONQ", -4, "EXIT", actual_weight=1.0)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        assert len(recs) == 1
        r = recs[0]
        assert r["ticker"] == "IONQ"
        assert r["recommendation"] == "SELL"
        assert r["actionable"] is True
        assert r["proposedTrade"]["side"] == "sell"
        assert r["proposedTrade"]["approxValueUSD"] == 320.0   # 1.0% of 32k
        assert "IONQ" not in r["rationale"] or len(r["rationale"]) > 20  # real prose

    def test_exit_band_not_held_is_excluded(self):
        """Watchlist tickers (ASML, POET…) with no position produce no card."""
        recs = build_recommendations(
            scores=[_score("ASML", -2, "REDUCE", actual_weight=None)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        assert recs == []

    def test_reduce_band_overweight_recommends_trim(self):
        recs = build_recommendations(
            scores=[_score("DRAM", -1, "REDUCE",
                           actual_weight=4.3, target_weight=2.0, weight_gap=-2.3)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        assert recs[0]["recommendation"] == "TRIM"
        # trim down to target: 2.3% of 32k
        assert recs[0]["proposedTrade"]["approxValueUSD"] == 736.0


class TestStandingDecisions:

    def test_standing_decision_downgrades_sell_to_hold(self):
        """CORZ: EXIT signal + allowlisted conflict → HOLD card, signal still shown."""
        standing = {"CORZ": {
            "type": "ALLOWLISTED_CONFLICT",
            "reason": "SA LP long vs DCF SELL — user allowlisted.",
        }}
        recs = build_recommendations(
            scores=[_score("CORZ", -3, "EXIT", actual_weight=3.6)],
            standing=standing, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        r = recs[0]
        assert r["recommendation"] == "HOLD"
        assert r["actionable"] is False
        assert r["standingDecision"]["type"] == "ALLOWLISTED_CONFLICT"
        assert r["signal"] == "EXIT"          # signal is never muted
        assert "allowlisted" in r["rationale"].lower()

    def test_standing_decision_on_accumulate_with_max_entry(self):
        """SNDK-style: BUY signal but never add above targetEntryPrice."""
        standing = {"SNDK": {
            "type": "NO_ADD_ABOVE_ENTRY",
            "reason": "Do not add above $1,350.",
            "maxEntryPrice": 1350.0,
        }}
        recs = build_recommendations(
            scores=[_score("SNDK", 3, "ACCUMULATE",
                           actual_weight=3.7, weight_gap=1.0)],
            standing=standing, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        r = recs[0]
        assert r["recommendation"] == "BUY_LIMIT"
        assert "1,350" in r["rationale"] or "1350" in r["rationale"]


class TestMacroGate:

    def test_accumulate_actionable_when_risk_on(self):
        recs = build_recommendations(
            scores=[_score("CRWV", 3, "ACCUMULATE", dcf_action="BUY",
                           actual_weight=3.6, weight_gap=2.4)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        r = recs[0]
        assert r["recommendation"] == "BUY"
        assert r["actionable"] is True
        assert r["proposedTrade"]["side"] == "buy"
        assert r["proposedTrade"]["approxValueUSD"] == 768.0   # 2.4% of 32k

    def test_accumulate_queued_when_risk_off(self):
        recs = build_recommendations(
            scores=[_score("CRWV", 3, "ACCUMULATE", dcf_action="BUY",
                           actual_weight=3.6, weight_gap=2.4)],
            standing={}, earnings=[], macro=RISK_OFF, total_equity=32000.0,
        )
        r = recs[0]
        assert r["recommendation"] == "QUEUED"
        assert r["actionable"] is False
        assert "risk-off" in r["rationale"].lower()

    def test_neutral_macro_requires_score_four(self):
        recs = build_recommendations(
            scores=[
                _score("CRWV", 3, "ACCUMULATE", dcf_action="BUY", weight_gap=2.4),
                _score("PSIX", 4, "ACCUMULATE", dcf_action="BUY", weight_gap=1.2),
            ],
            standing={}, earnings=[], macro=NEUTRAL, total_equity=32000.0,
        )
        by_ticker = {r["ticker"]: r for r in recs}
        assert by_ticker["CRWV"]["recommendation"] == "QUEUED"
        assert by_ticker["PSIX"]["recommendation"] == "BUY"


class TestEarningsAndOrdering:

    def test_imminent_earnings_flagged_in_rationale(self):
        recs = build_recommendations(
            scores=[_score("CBRS", -3, "EXIT", actual_weight=2.7)],
            standing={},
            earnings=[{"ticker": "CBRS", "earnings_date": "2026-06-14",
                       "days_away": 4, "flag": "IMMINENT"}],
            macro=RISK_ON, total_equity=32000.0,
        )
        r = recs[0]
        assert r["earnings"]["flag"] == "IMMINENT"
        assert "4" in r["rationale"] and "earnings" in r["rationale"].lower()

    def test_sells_ranked_before_buys_worst_score_first(self):
        recs = build_recommendations(
            scores=[
                _score("CRWV", 3, "ACCUMULATE", dcf_action="BUY", weight_gap=2.4),
                _score("IONQ", -4, "EXIT", actual_weight=1.0),
                _score("CLSK", -3, "EXIT", actual_weight=2.1),
            ],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        assert [r["ticker"] for r in recs] == ["IONQ", "CLSK", "CRWV"]

    def test_hold_and_watch_bands_produce_no_cards(self):
        recs = build_recommendations(
            scores=[_score("MSFT", 2, "HOLD"), _score("CEG", 0, "WATCH")],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        assert recs == []
