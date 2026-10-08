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


def _recent(status: str, note: str, sold: float = 0, bought: float = 0) -> dict:
    """recent_trades field as recommendation.py attaches it."""
    return {"window_days": 14, "sold_shares": sold, "bought_shares": bought, "count": 1,
            "last": {"date": "2026-10-06", "action": "sell" if sold else "buy", "shares": sold or bought, "price": 1, "account": "TFSA"},
            "context": {"status": status, "note": note}}


class TestRecentTradeContext:

    def test_trim_card_says_it_was_already_acted_on_and_frames_the_rest_as_further(self):
        """A trim the owner just made is acknowledged; any remaining sizing is a further trade."""
        note = "Sold 1.5 shares in the last 14 days, last on 2026-10-06: TRIM already acted on"
        s = _score("BE", -2, "TRIM", actual_weight=4.9, target_weight=4.1, weight_gap=-0.8,
                   recent_trades=_recent("ACTED", note, sold=1.5))
        card = build_recommendations([s], {}, [], RISK_ON, 100_000)[0]
        assert card["recentTrades"]["context"]["status"] == "ACTED"
        assert note in card["rationale"]
        assert "a further" in card["rationale"]
        assert card["proposedTrade"]["approxValueUSD"] == 800.0

    def test_blocked_and_standing_decision_cards_also_carry_the_trade_note(self):
        note = "Sold 9 shares in the last 14 days, last on 2026-10-06: TRIM already acted on"
        within_band = _score("IREN", -2, "TRIM", recent_trades=_recent("ACTED", note, sold=9))
        decided = _score("PANW", -2, "TRIM", recent_trades=_recent("ACTED", note, sold=9))
        cards = build_recommendations([within_band, decided], {"PANW": {"type": "TRIM_ON_BOUNCE", "reason": "Trim on bounce."}}, [], RISK_ON, 100_000)
        assert all(note in card["rationale"] for card in cards)
        assert all(card["proposedTrade"] is None for card in cards)

    def test_a_trade_against_the_action_is_called_out(self):
        note = "Bought 4 shares in the last 14 days, last on 2026-10-05, while the action is TRIM"
        s = _score("RIOT", -2, "TRIM", actual_weight=4.9, target_weight=4.1, weight_gap=-0.8,
                   recent_trades=_recent("OPPOSED", note, bought=4))
        card = build_recommendations([s], {}, [], RISK_ON, 100_000)[0]
        assert note in card["rationale"] and "a further" not in card["rationale"]

    def test_buy_card_acknowledges_a_recent_buy(self):
        note = "Bought 5 shares in the last 14 days, last on 2026-10-05: ACCUMULATE already acted on"
        s = _score("SHAZ", 5, "ACCUMULATE", actual_weight=1.0, target_weight=2.0, weight_gap=1.0,
                   recent_trades=_recent("ACTED", note, bought=5))
        card = build_recommendations([s], {}, [], RISK_ON, 100_000)[0]
        assert note in card["rationale"] and "a further" in card["rationale"]

    def test_cards_without_recent_trades_are_unchanged(self):
        s = _score("BE", -2, "TRIM", actual_weight=4.9, target_weight=4.1, weight_gap=-0.8)
        card = build_recommendations([s], {}, [], RISK_ON, 100_000)[0]
        assert card["recentTrades"] is None
        assert "last 14 days" not in card["rationale"] and "a further" not in card["rationale"]


def _check(relation: str, effective: str, note: str) -> dict:
    """decision_check field as recommendation.py attaches it."""
    return {"relation": relation, "effective": effective, "note": note, "age_days": None}


class TestStandingDecisionCoherence:

    def test_conflicting_decision_shows_one_stance_and_says_why(self):
        """TRIM against a hold decision is shown as MAINTAIN with the disagreement spelled out."""
        note = "Valuation says TRIM, but your standing decision is 'hold at target' (set 109 days ago). They disagree, so the stance is hold and no trade is proposed until you update one of them."
        s = _score("IREN", -2, "TRIM", decision_check=_check("CONFLICT", "MAINTAIN", note))
        card = build_recommendations([s], {"IREN": {"type": "HOLD_AT_TARGET", "reason": "Hold at target weight."}}, [], RISK_ON, 100_000)[0]
        assert (card["signal"], card["recommendation"], card["executionStatus"]) == ("TRIM", "MAINTAIN", "BLOCKED")
        assert note in card["rationale"] and "Hold at target weight." in card["rationale"]
        assert card["decisionCheck"]["relation"] == "CONFLICT" and card["proposedTrade"] is None

    def test_outdated_entry_decision_no_longer_blocks_a_sized_trim(self):
        """A watchlist call on a position already held is flagged, and the trim is sized as usual."""
        note = "Standing decision 'watchlist wait for pullback' is an entry call, but you already hold this position, so it no longer applies."
        s = _score("GEV", -2, "TRIM", actual_weight=4.9, target_weight=4.1, weight_gap=-0.8,
                   decision_check=_check("OUTDATED", "TRIM", note))
        card = build_recommendations([s], {"GEV": {"type": "WATCHLIST_WAIT_FOR_PULLBACK", "reason": "Wait."}}, [], RISK_ON, 100_000)[0]
        assert (card["recommendation"], card["executionStatus"]) == ("TRIM", "READY")
        assert card["proposedTrade"]["approxValueUSD"] == 800.0 and note in card["rationale"]

    def test_agreeing_decision_keeps_the_action_and_its_timing_note(self):
        note = "Standing decision 'trim on bounce' agrees with TRIM; it sets the timing."
        s = _score("PANW", -2, "TRIM", decision_check=_check("AGREES", "TRIM", note))
        card = build_recommendations([s], {"PANW": {"type": "TRIM_ON_BOUNCE", "reason": "Trim on 21 EMA bounce."}}, [], RISK_ON, 100_000)[0]
        assert (card["recommendation"], card["executionStatus"]) == ("TRIM", "BLOCKED")
        assert note in card["rationale"]


class TestPriorityOrder:

    def _cards(self):
        acted = {"window_days": 14, "sold_shares": 3, "bought_shares": 0, "count": 1,
                 "last": {"date": "2026-10-06", "action": "sell", "shares": 3, "price": 1, "account": "TFSA"},
                 "context": {"status": "ACTED", "note": "Sold 3 shares in the last 14 days, last on 2026-10-06: TRIM already acted on"}}
        scores = [
            _score("ACTD", -2, "TRIM", actual_weight=4.9, target_weight=4.1, weight_gap=-0.8, pct_to_fv=-70.0, recent_trades=acted),
            _score("BLKD", -2, "TRIM", pct_to_fv=-30.0),
            _score("CNFL", -2, "TRIM", pct_to_fv=-25.0, decision_check=_check("CONFLICT", "MAINTAIN", "They disagree.")),
            _score("RDY1", -2, "TRIM", actual_weight=4.9, target_weight=4.1, weight_gap=-0.8, pct_to_fv=-20.0),
            _score("RDY2", -2, "TRIM", actual_weight=4.9, target_weight=4.1, weight_gap=-0.8, pct_to_fv=-60.0),
            _score("BUY1", 5, "ACCUMULATE", actual_weight=1.0, target_weight=2.0, weight_gap=1.0, pct_to_fv=40.0),
            _score("WAIT", 2, "INITIATE", actual_weight=0.0, target_weight=1.0, weight_gap=1.0, pct_to_fv=90.0,
                   decision_check=_check("WAITS", "WATCHLIST", "Wait for your condition.")),
        ]
        standing = {"CNFL": {"type": "HOLD_AT_TARGET", "reason": "Hold."}, "WAIT": {"type": "WATCHLIST_WAIT_FOR_PULLBACK", "reason": "Wait."}}
        return build_recommendations(scores, standing, [], RISK_ON, 100_000)

    def test_ready_trades_lead_and_already_acted_on_trades_go_last(self):
        """Order: ready to act, needs your decision, no trade proposed, waiting, already acted on."""
        cards = self._cards()
        assert [c["ticker"] for c in cards] == ["RDY2", "RDY1", "BUY1", "CNFL", "BLKD", "WAIT", "ACTD"]
        assert [c["urgency"] for c in cards] == [1, 2, 3, 4, 5, 6, 7]

    def test_each_card_says_why_it_ranks_where_it_does(self):
        reasons = {c["ticker"]: c["priority"]["label"] for c in self._cards()}
        assert reasons == {"RDY2": "Ready to act", "RDY1": "Ready to act", "BUY1": "Ready to act", "CNFL": "Needs your decision",
                           "BLKD": "No trade proposed", "WAIT": "Waiting for your condition", "ACTD": "Already acted on"}

    def test_within_a_group_the_larger_valuation_gap_ranks_first(self):
        cards = self._cards()
        assert [c["ticker"] for c in cards[:2]] == ["RDY2", "RDY1"]  # -60% before -20%


class TestOneStancePerCard:

    def test_a_card_held_by_the_owners_decision_never_reads_as_a_second_recommendation(self):
        """MAINTAIN beside 'Score +2 (ACCUMULATE)' read as two recommendations (2026-10-08)."""
        note = "You decided 'hold no add' today, so the stance is hold."
        s = _score("SPCX", 2, "ACCUMULATE", pct_to_fv=219.0, decision_check=_check("CONFIRMED", "MAINTAIN", note))
        card = build_recommendations([s], {"SPCX": {"type": "HOLD_NO_ADD", "reason": "Hold."}}, [], RISK_ON, 100_000)[0]
        assert card["recommendation"] == "MAINTAIN" and card["rationale"].startswith(note)
        assert "(ACCUMULATE)" not in card["rationale"] and "DCF BUY" not in card["rationale"]
        assert "valuation model rates it a buy, +219.0% to fair value" in card["rationale"]

    def test_a_confirmed_decision_is_not_asked_again(self):
        s = _score("SPCX", 2, "ACCUMULATE", decision_check=_check("CONFIRMED", "MAINTAIN", "You decided."))
        card = build_recommendations([s], {"SPCX": {"type": "HOLD_NO_ADD", "reason": "Hold."}}, [], RISK_ON, 100_000)[0]
        assert card["priority"] == {"tier": 2, "label": "Holding by your decision"}

    def test_cards_whose_stance_is_the_action_keep_the_score_summary(self):
        card = build_recommendations([_score("AMAT", 5, "ACCUMULATE", actual_weight=1.0, target_weight=2.0, weight_gap=1.0)],
                                     {}, [], RISK_ON, 100_000)[0]
        assert card["rationale"].startswith("Score +5 (ACCUMULATE)")


class TestDecisionConditions:

    def _card(self, price):
        s = _score("BTDR", 2, "ACCUMULATE", price=price,
                   decision_check=_check("AGREES", "ACCUMULATE", "Standing decision 'accumulate below 9' agrees with ACCUMULATE; it sets the timing."))
        return build_recommendations([s], {"BTDR": {"type": "ACCUMULATE_BELOW_9", "reason": "Add only below $9.00."}}, [], RISK_ON, 100_000)[0]

    def test_an_unmet_condition_waits_and_says_how_far_away_it_is(self):
        card = self._card(10.26)
        assert card["priority"] == {"tier": 3, "label": "Waiting for your condition"}
        assert card["condition"]["met"] is False and "14.0% above your $9.00 level" in card["rationale"]

    def test_a_met_condition_moves_the_card_to_the_top_group(self):
        card = self._card(8.80)
        assert card["priority"] == {"tier": 0, "label": "Your condition is met"}
        assert "condition is met" in card["rationale"]

    def test_cards_without_a_price_or_condition_are_unchanged(self):
        s = _score("PANW", -2, "TRIM", decision_check=_check("AGREES", "TRIM", "Agrees."))
        card = build_recommendations([s], {"PANW": {"type": "TRIM_ON_BOUNCE", "reason": "Trim."}}, [], RISK_ON, 100_000)[0]
        assert card["condition"] is None and card["priority"]["label"] == "No trade proposed"


class TestRefreshFirst:

    STALE = {"level": "PARTIAL", "age_days": 37, "checks": [
        {"id": "fresh", "label": "Recent valuation", "ok": True, "note": "Saved 37 days ago"},
        {"id": "forward_review", "label": "Forward-earnings review", "ok": False, "note": "No forward-earnings review recorded with this valuation"}]}
    FRESH = {"level": "STRONG", "age_days": 3, "checks": [{"id": "fresh", "label": "Recent valuation", "ok": True, "note": "Saved 3 days ago"}]}

    def _cards(self, support):
        scores = [_score(f"T{i}", 5, "ACCUMULATE", actual_weight=1.0, target_weight=2.0, weight_gap=1.0,
                         pct_to_fv=90.0 - i, support=support) for i in range(7)]
        return build_recommendations(scores, {}, [], RISK_ON, 100_000)

    def test_the_top_five_cards_ask_for_a_refresh_when_their_valuation_is_stale(self):
        cards = self._cards(self.STALE)
        assert [bool(c["refreshFirst"]) for c in cards] == [True] * 5 + [False] * 2
        first = cards[0]["refreshFirst"]
        assert first["command"] == "/update-stock-analysis T0"
        assert first["reasons"] == ["Valuation saved 37 days ago", "No forward-earnings review recorded with this valuation"]

    def test_fresh_fully_supported_valuations_need_no_refresh(self):
        assert all(c["refreshFirst"] is None for c in self._cards(self.FRESH))

    def test_cards_without_support_data_are_left_alone(self):
        assert all(c["refreshFirst"] is None for c in self._cards(None))
