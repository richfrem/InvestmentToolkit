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
        assert r["recommendation"] == "EXIT"
        assert r["actionable"] is True
        assert r["proposedTrade"]["side"] == "sell"
        assert r["proposedTrade"]["approxValueUSD"] == 320.0   # 1.0% of 32k
        assert "IONQ" not in r["rationale"] or len(r["rationale"]) > 20  # real prose

    def test_exit_band_not_held_is_excluded(self):
        """Watchlist tickers (ASML, POET…) with no position produce no card."""
        recs = build_recommendations(
            scores=[_score("ASML", -2, "TRIM", actual_weight=None)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        assert recs == []

    def test_reduce_band_overweight_recommends_trim(self):
        recs = build_recommendations(
            scores=[_score("DRAM", -1, "TRIM",
                           actual_weight=4.3, target_weight=2.0, weight_gap=-2.3)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        assert recs[0]["recommendation"] == "TRIM"
        # trim down to target: 2.3% of 32k
        assert recs[0]["proposedTrade"]["approxValueUSD"] == 736.0


class TestReduceWithinTargetBand:
    """2026-10-01: a REDUCE signal (DCF-score driven) on a position at or UNDER its target
    fell through to ``trim_pct = actual / 2`` and proposed selling HALF the position.
    RIOT (2.12% actual vs 2.23% target, +0.11pp) got "sell ~$365"; MU (4.33% vs a 3.99%
    target, -0.34pp) jumped from ~$293 to ~$745 the moment its target moved. That
    contradicts AGENTS rule 9 (DCF never silently overrides the user's targets): without a
    material overweight there is no basis for sizing a sell, so no trade is proposed.
    """

    def test_reduce_under_target_proposes_no_sell(self):
        recs = build_recommendations(
            scores=[_score("RIOT", -1, "TRIM",
                           actual_weight=2.1184, target_weight=2.226, weight_gap=0.11)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=34414.0,
        )
        assert len(recs) == 1
        r = recs[0]
        assert r["executionStatus"] == "BLOCKED"
        assert r["proposedTrade"] is None
        assert r["actionable"] is False
        assert "target" in r["rationale"].lower()

    def test_reduce_slightly_overweight_within_band_proposes_no_sell(self):
        """MU after its target moved to ~4%: -0.34pp over target is inside the 0.5pp band."""
        recs = build_recommendations(
            scores=[_score("MU", -2, "TRIM",
                           actual_weight=4.333, target_weight=3.9893, weight_gap=-0.34)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=34414.0,
        )
        assert recs[0]["executionStatus"] == "BLOCKED"
        assert recs[0]["proposedTrade"] is None
        assert recs[0]["actionable"] is False

    def test_reduce_without_a_target_weight_proposes_no_sell(self):
        recs = build_recommendations(
            scores=[_score("ZZZZ", -1, "TRIM",
                           actual_weight=3.0, target_weight=None, weight_gap=None)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        assert recs[0]["executionStatus"] == "BLOCKED"
        assert recs[0]["proposedTrade"] is None

    def test_reduce_materially_overweight_still_trims_to_target(self):
        recs = build_recommendations(
            scores=[_score("DRAM", -1, "TRIM",
                           actual_weight=2.6, target_weight=2.0, weight_gap=-0.6)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        assert recs[0]["recommendation"] == "TRIM"
        assert recs[0]["proposedTrade"]["approxValueUSD"] == 192.0   # 0.6% of 32k

    def test_exit_band_still_sells_the_full_position(self):
        recs = build_recommendations(
            scores=[_score("IONQ", -4, "EXIT", actual_weight=1.0)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        assert recs[0]["recommendation"] == "EXIT"
        assert recs[0]["proposedTrade"]["approxValueUSD"] == 320.0


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
        assert r["executionStatus"] == "BLOCKED"
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
        assert r["executionStatus"] == "LIMIT_ONLY"
        assert "1,350" in r["rationale"] or "1350" in r["rationale"]


class TestMacroGate:

    def test_accumulate_actionable_when_risk_on(self):
        recs = build_recommendations(
            scores=[_score("CRWV", 3, "ACCUMULATE", dcf_action="BUY",
                           actual_weight=3.6, weight_gap=2.4)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        r = recs[0]
        assert r["recommendation"] == "ACCUMULATE"
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
        assert r["executionStatus"] == "QUEUED"
        assert r["actionable"] is False
        assert "risk-off" in r["rationale"].lower()

    def test_accumulate_band_with_zero_target_weight_is_excluded(self):
        """Watchlist tickers with no target weight (e.g. VST) score ACCUMULATE
        on TA/DCF alone but have no real weight gap to close — must not
        produce a misleading 'BUY ~$0' card (regression, 2026-08-13)."""
        recs = build_recommendations(
            scores=[_score("VST", 3, "ACCUMULATE", dcf_action="BUY",
                           actual_weight=None, target_weight=0.0, weight_gap=None)],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        assert recs[0]["proposedTrade"] is None
        assert recs[0]["actionable"] is False

    def test_neutral_macro_requires_score_four(self):
        recs = build_recommendations(
            scores=[
                _score("CRWV", 3, "ACCUMULATE", dcf_action="BUY", weight_gap=2.4),
                _score("PSIX", 4, "ACCUMULATE", dcf_action="BUY", weight_gap=1.2),
            ],
            standing={}, earnings=[], macro=NEUTRAL, total_equity=32000.0,
        )
        by_ticker = {r["ticker"]: r for r in recs}
        assert by_ticker["CRWV"]["executionStatus"] == "QUEUED"
        assert by_ticker["PSIX"]["recommendation"] == "ACCUMULATE"


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
            scores=[_score("MSFT", 2, "HOLD"), _score("CEG", 0, "WATCHLIST")],
            standing={}, earnings=[], macro=RISK_ON, total_equity=32000.0,
        )
        assert recs == []
