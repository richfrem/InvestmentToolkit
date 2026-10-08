"""Purpose: contract tests for reconciling a standing decision with the valuation action.

Layer: Business-logic unit tests. Key Functions: agreement, conflict, waiting, outdated and age cases.
Key Input Dependencies: standing_decision_check.py pure functions; no database or network.
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from standing_decision_check import check_standing_decision, decision_condition, decision_direction  # noqa: E402

TODAY = date(2026, 10, 8)


def decision(kind: str, source: str | None = None) -> dict:
    return {"type": kind, "reason": "Recorded reason.", "source": source}


@pytest.mark.parametrize("kind,direction", [
    ("HOLD_AT_TARGET", "hold"), ("HOLD_NO_ADD", "hold"), ("NO_ADD_AT_MARKET", "hold"), ("MAINTAIN", "hold"),
    ("MAINTAIN_TRIM_EXTREME", "hold"), ("TRIM_ON_BOUNCE", "reduce"), ("TRIM_ON_STRENGTH", "reduce"),
    ("ACCUMULATE_200_EMA_RETEST", "add"), ("ACCUMULATE_ON_PULLBACK", "add"), ("INITIATE_STARTER_TRANCHE", "add"),
    ("WATCHLIST_WAIT_FOR_PULLBACK", "wait"), ("WATCHLIST_MONITOR_ENTRY", "wait"), ("WATCHLIST_AWAIT_PRODUCTION", "wait"),
    ("AVOID_DILUTION_RISK", "wait"), ("SOMETHING_ELSE", None), ("USER", None),
])
def test_decision_types_are_read_by_their_leading_word(kind, direction):
    """The stored type is free text; its first word says which way the decision points."""
    assert decision_direction(kind) == direction


def test_no_standing_decision_leaves_the_action_as_it_is():
    result = check_standing_decision("TRIM", True, None, None, TODAY)
    assert result == {"relation": "NONE", "effective": "TRIM", "note": "", "age_days": None}


@pytest.mark.parametrize("action,held,kind", [
    ("TRIM", True, "TRIM_ON_BOUNCE"), ("ACCUMULATE", True, "ACCUMULATE_ON_RETRACEMENT"), ("MAINTAIN", True, "HOLD_AT_TARGET"),
    ("WATCHLIST", False, "WATCHLIST_WAIT_FOR_PULLBACK"), ("INITIATE", False, "INITIATE_STARTER_TRANCHE"),
    ("INITIATE", False, "ACCUMULATE_ON_PULLBACK"),
])
def test_same_direction_agrees_and_keeps_the_action(action, held, kind):
    result = check_standing_decision(action, held, decision(kind), None, TODAY)
    assert (result["relation"], result["effective"]) == ("AGREES", action)
    assert "agrees" in result["note"]


@pytest.mark.parametrize("action,kind", [
    ("TRIM", "HOLD_AT_TARGET"), ("TRIM", "ACCUMULATE_200_EMA_RETEST"), ("ACCUMULATE", "HOLD_NO_ADD"),
    ("ACCUMULATE", "NO_ADD_AT_MARKET"), ("ACCUMULATE", "TRIM_ON_STRENGTH"),
])
def test_opposing_directions_on_a_held_position_conflict_and_hold_until_resolved(action, kind):
    """Two sources disagree: neither a buy nor a sell is the effective stance."""
    result = check_standing_decision(action, True, decision(kind), None, TODAY)
    assert (result["relation"], result["effective"]) == ("CONFLICT", "MAINTAIN")
    assert action in result["note"] and kind.replace("_", " ").lower() in result["note"].lower()


@pytest.mark.parametrize("kind", ["ACCUMULATE_ON_PULLBACK", "TRIM_ON_BOUNCE", "INITIATE_WESTERN_RARE_EARTH_MONOPOLY"])
def test_a_neutral_valuation_never_conflicts_with_a_conditional_decision(kind):
    """MAINTAIN means valuation has no view; the decision's own condition decides when to act."""
    result = check_standing_decision("MAINTAIN", True, decision(kind), None, TODAY)
    assert (result["relation"], result["effective"]) == ("AGREES", "MAINTAIN")
    assert "neutral" in result["note"]


def test_wanting_to_start_while_the_decision_says_wait_is_waiting_not_a_conflict():
    result = check_standing_decision("INITIATE", False, decision("WATCHLIST_WAIT_FOR_PULLBACK"), None, TODAY)
    assert (result["relation"], result["effective"]) == ("WAITS", "WATCHLIST")
    assert "wait" in result["note"].lower()


def test_an_entry_decision_on_a_position_already_held_is_outdated():
    """A watchlist call cannot govern a position that is now owned; the action stands and the decision is flagged."""
    result = check_standing_decision("TRIM", True, decision("WATCHLIST_WAIT_FOR_PULLBACK"), None, TODAY)
    assert (result["relation"], result["effective"]) == ("OUTDATED", "TRIM")
    assert "already hold" in result["note"]


def test_unreadable_decision_types_ask_for_review_without_changing_the_action():
    result = check_standing_decision("TRIM", True, decision("SOMETHING_ELSE"), None, TODAY)
    assert (result["relation"], result["effective"]) == ("UNCLEAR", "TRIM")


def test_the_age_of_the_decision_is_reported_when_its_source_carries_a_date():
    result = check_standing_decision("TRIM", True, decision("HOLD_AT_TARGET", "user 2026-06-21"), None, TODAY)
    assert result["age_days"] == 109 and "109 days ago" in result["note"]
    assert check_standing_decision("TRIM", True, decision("HOLD_AT_TARGET", "strategic review"), None, TODAY)["age_days"] is None


def test_a_recent_trade_against_the_decision_is_called_out():
    """Selling a position your own decision says to hold means the decision is probably out of date."""
    recent = {"sold_shares": 9, "bought_shares": 0, "count": 2, "last": {"date": "2026-10-06"}}
    result = check_standing_decision("TRIM", True, decision("HOLD_AT_TARGET", "user 2026-06-21"), recent, TODAY)
    assert "you sold 9 shares on or before 2026-10-06" in result["note"]
    bought = {"sold_shares": 0, "bought_shares": 2, "count": 1, "last": {"date": "2026-10-05"}}
    assert "you bought 2 shares" in check_standing_decision("ACCUMULATE", True, decision("HOLD_NO_ADD"), bought, TODAY)["note"]
    assert "you sold" not in check_standing_decision("TRIM", True, decision("TRIM_ON_BOUNCE"), recent, TODAY)["note"]


def test_a_recently_set_decision_that_disagrees_is_confirmed_not_an_open_question():
    """The owner just decided: the stance is theirs and nothing is asked of them again."""
    result = check_standing_decision("ACCUMULATE", True, decision("HOLD_NO_ADD", "user 2026-10-08"), None, TODAY)
    assert (result["relation"], result["effective"]) == ("CONFIRMED", "MAINTAIN")
    assert "you decided" in result["note"].lower() and "until you update" not in result["note"]
    edge = check_standing_decision("ACCUMULATE", True, decision("HOLD_NO_ADD", "user 2026-09-08"), None, TODAY)
    assert edge["relation"] == "CONFIRMED"   # exactly 30 days
    old = check_standing_decision("ACCUMULATE", True, decision("HOLD_NO_ADD", "user 2026-09-07"), None, TODAY)
    assert old["relation"] == "CONFLICT"


def test_a_price_condition_in_the_decision_type_is_checked_against_the_price():
    below = decision_condition(decision("ACCUMULATE_BELOW_9"), 10.26)
    assert (below["kind"], below["level"], below["met"]) == ("below", 9.0, False)
    assert below["distance_pct"] == 14.0 and "$10.26 is 14.0% above your $9.00 level" in below["note"]
    assert decision_condition(decision("ACCUMULATE_BELOW_9"), 8.8)["met"] is True
    above = decision_condition(decision("TRIM_ABOVE_54_60"), 57.0)
    assert (above["kind"], above["level"], above["met"]) == ("above", 54.6, True)


def test_a_moving_average_condition_uses_the_chart_level_or_the_one_written_in_the_decision():
    stm = {"type": "HOLD_AT_200_EMA", "reason": "Hold 24 shares; add only if 200 EMA ($48.60) is tested.", "source": "user 2026-10-08"}
    recorded = decision_condition(stm, 54.70)
    assert (recorded["kind"], recorded["level"], recorded["met"], recorded["level_source"]) == ("ema", 48.6, False, "decision")
    assert "200 EMA" in recorded["note"] and "12.6% above" in recorded["note"] and "recorded in your decision" in recorded["note"]
    live = decision_condition(stm, 54.70, {"ema200": 54.0})
    assert (live["level"], live["met"], live["level_source"]) == (54.0, True, "chart")   # within 2% counts as tested


def test_decisions_without_a_readable_level_have_no_condition():
    assert decision_condition(decision("HOLD_NO_ADD"), 10.0) is None
    assert decision_condition(decision("ACCUMULATE_200_EMA_RETEST"), 10.0) is None   # no level anywhere
    assert decision_condition(decision("ACCUMULATE_BELOW_9"), None) is None
    assert decision_condition(None, 10.0) is None
