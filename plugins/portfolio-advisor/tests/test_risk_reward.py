"""Purpose: contract tests for the canonical reward-versus-risk and valuation-support view.

Layer: Business-logic unit tests. Key Functions: assessment, support and alignment cases.
Key Input Dependencies: risk_reward.py pure functions; no database or network.
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from risk_reward import assess_risk_reward, reduce_view, valuation_support  # noqa: E402


def scenarios(bear=20.0, base=100.0, bull=200.0, weights=(0.2, 0.5, 0.3)) -> dict:
    """Three priced scenarios with explicit probabilities."""
    return {name: {"price": price, "weight": weight}
            for name, price, weight in zip(("bear", "base", "bull"), (bear, base, bull), weights)}


def test_reward_risk_weights_gains_and_losses_by_scenario_probability() -> None:
    """Expected gain over expected loss, not best case over worst case."""
    result = assess_risk_reward(price=80.0, fair_value=114.0, scenarios=scenarios())
    # gain = 0.5*20 + 0.3*120 = 46; loss = 0.2*60 = 12
    assert result["expected_gain_pct"] == pytest.approx(57.5)
    assert result["expected_loss_pct"] == pytest.approx(15.0)
    assert result["reward_risk"] == pytest.approx(46 / 12)
    assert result["loss_odds_pct"] == pytest.approx(20.0)
    assert result["downside_to_bear_pct"] == pytest.approx(-75.0)
    assert result["premium_pct"] == pytest.approx((80 / 114 - 1) * 100)
    assert result["verdict"] == "FAVOURABLE"


def test_price_above_fair_value_is_unfavourable_with_most_weight_below_price() -> None:
    """A price above fair value is unfavourable and most scenario weight sits below it."""
    result = assess_risk_reward(price=130.0, fair_value=114.0, scenarios=scenarios())
    assert result["premium_pct"] > 0
    assert result["reward_risk"] < 1
    assert result["loss_odds_pct"] == pytest.approx(70.0)
    assert result["verdict"] == "UNFAVOURABLE"


def test_small_upside_against_deep_bear_is_thin_not_favourable() -> None:
    """A little upside against a deep bear case is only thin support."""
    result = assess_risk_reward(price=105.0, fair_value=114.0, scenarios=scenarios())
    assert 1 <= result["reward_risk"] < 2
    assert result["verdict"] == "THIN"


def test_percentage_weights_are_normalised() -> None:
    """Weights stored as 20/50/30 give the same answer as 0.2/0.5/0.3."""
    decimal = assess_risk_reward(80.0, 114.0, scenarios())
    percent = assess_risk_reward(80.0, 114.0, scenarios(weights=(20, 50, 30)))
    assert percent["reward_risk"] == pytest.approx(decimal["reward_risk"])


def test_price_below_every_scenario_has_no_modelled_downside() -> None:
    """No scenario below the price means no ratio, not an infinite one."""
    result = assess_risk_reward(price=10.0, fair_value=114.0, scenarios=scenarios())
    assert result["reward_risk"] is None
    assert result["no_modelled_downside"] is True
    assert result["verdict"] == "FAVOURABLE"


@pytest.mark.parametrize("broken", [
    {}, {"bear": {"price": 20, "weight": 0.2}},
    {"bear": {"price": 20, "weight": None}, "base": {"price": 100, "weight": 0.5}, "bull": {"price": 200, "weight": 0.3}},
])
def test_incomplete_scenarios_are_unrated_rather_than_guessed(broken: dict) -> None:
    """Partial scenarios are never filled in; above fair value still counts."""
    below = assess_risk_reward(80.0, 114.0, broken)
    assert below["reward_risk"] is None and below["verdict"] == "UNRATED"
    above = assess_risk_reward(130.0, 114.0, broken)
    assert above["verdict"] == "UNFAVOURABLE"  # above fair value needs no scenarios


@pytest.mark.parametrize("price,fair_value", [(None, 100.0), (0.0, 100.0), (50.0, None), (float("nan"), 100.0)])
def test_missing_price_or_fair_value_is_unrated(price, fair_value) -> None:
    """Without a usable price and fair value nothing is rated."""
    result = assess_risk_reward(price, fair_value, scenarios())
    assert result["verdict"] == "UNRATED"
    assert result["premium_pct"] is None and result["reward_risk"] is None


def test_support_counts_four_independent_evidence_checks() -> None:
    """A recent, complete, audited and reviewed valuation passes all four checks."""
    audited = {"valuationModel": {"method": "terminal_earnings", "discountRateAudit": {"rateType": "COST_OF_EQUITY"}}}
    strong = valuation_support("2026-10-01T00:00:00Z", audited, scenarios(), today=date(2026, 10, 8))
    assert (strong["level"], strong["score"], strong["age_days"]) == ("STRONG", 4, 7)
    assert all(check["ok"] for check in strong["checks"])


def test_support_names_each_missing_piece() -> None:
    """A legacy valuation says which evidence is missing."""
    legacy = valuation_support("2026-08-31T00:00:00Z", {}, scenarios(), today=date(2026, 10, 8))
    assert legacy["level"] == "PARTIAL" and legacy["score"] == 2
    failed = {check["id"]: check["note"] for check in legacy["checks"] if not check["ok"]}
    assert set(failed) == {"rate_audit", "forward_review"}
    assert "No audited discount rate" in failed["rate_audit"]


def test_support_flags_stale_wide_and_review_flagged_valuations() -> None:
    """Old, over-wide or revaluation-flagged valuations are weakly supported."""
    flagged = {"valuationModel": {"readiness": "NEEDS_REVALUATION", "discountRateAudit": {"rateType": "WACC"}}}
    result = valuation_support("2026-05-01T00:00:00Z", flagged, scenarios(bear=1.0, bull=200.0), today=date(2026, 10, 8))
    failed = {check["id"]: check["note"] for check in result["checks"] if not check["ok"]}
    assert set(failed) == {"fresh", "scenarios", "forward_review"}
    assert "NEEDS_REVALUATION" in failed["forward_review"]
    assert result["level"] == "WEAK"


def test_no_saved_valuation_has_no_support() -> None:
    """No saved valuation means no support level at all."""
    assert valuation_support(None, None, {}, today=date(2026, 10, 8))["level"] == "NONE"


def test_reduce_candidate_is_a_held_position_with_unfavourable_reward() -> None:
    """Only held positions are reduce candidates; target weight adds context."""
    poor = assess_risk_reward(130.0, 114.0, scenarios())
    held = reduce_view(True, "MAINTAIN", poor, current_weight_pct=6.0, target_weight_pct=4.5)
    assert held["reduce_candidate"] is True
    assert held["weight_gap_pp"] == pytest.approx(1.5)
    assert any("above fair value" in reason for reason in held["reduce_reasons"])
    assert any("over target" in reason for reason in held["reduce_reasons"])
    assert held["alignment"]["status"] == "REVIEW"
    assert reduce_view(False, "WATCHLIST", poor, 0.0, None)["reduce_candidate"] is False


@pytest.mark.parametrize("action,price,status", [
    ("ACCUMULATE", 80.0, "ALIGNED"), ("ACCUMULATE", 105.0, "REVIEW"), ("ACCUMULATE", 130.0, "CONFLICT"),
    ("TRIM", 130.0, "ALIGNED"), ("TRIM", 80.0, "CONFLICT"), ("MAINTAIN", 105.0, "ALIGNED"),
    ("EXIT", 80.0, "ALIGNED"), ("WATCHLIST", 130.0, "ALIGNED"),
])
def test_alignment_compares_the_action_with_reward_versus_risk(action: str, price: float, status: str) -> None:
    """Each action is cross-checked against the reward-versus-risk verdict."""
    view = reduce_view(action != "WATCHLIST", action, assess_risk_reward(price, 114.0, scenarios()), 3.0, 3.0)
    assert view["alignment"]["status"] == status
    assert view["alignment"]["note"]


def test_unrated_positions_have_unknown_alignment() -> None:
    """Unrated positions are never flagged or cross-checked."""
    view = reduce_view(True, "MAINTAIN", assess_risk_reward(None, None, {}), 3.0, None)
    assert view["alignment"]["status"] == "UNKNOWN" and view["reduce_candidate"] is False
    assert view["weight_gap_pp"] is None


def test_debt_view_reports_the_saved_leverage_grade_and_rate_check() -> None:
    from risk_reward import debt_view
    log = {"valuationModel": {"leverage": {"tier": "SEVERE", "reasons": ["Net debt is 12.2x EBITDA"]},
                              "rateBasis": {"status": "OK", "note": "Discounted at 14.23%"},
                              "rebasedFrom": {"fairValue": 249.87, "discountRate": 0.0816}}}
    view = debt_view(log, has_valuation=True)
    assert (view["status"], view["tier"], view["reasons"]) == ("ASSESSED", "SEVERE", ["Net debt is 12.2x EBITDA"])
    assert view["rate_status"] == "OK" and view["previous_fair_value"] == 249.87
    assert "Net debt is 12.2x EBITDA" in view["note"]


def test_a_valuation_never_checked_for_debt_says_so_rather_than_looking_clean() -> None:
    from risk_reward import debt_view
    view = debt_view({}, has_valuation=True)
    assert (view["status"], view["tier"]) == ("NOT_ASSESSED", None)
    assert "has not been checked" in view["note"]
    assert debt_view(None, has_valuation=False)["status"] == "NONE"


def test_a_sourced_rate_audit_or_firm_cash_flow_model_counts_as_assessed() -> None:
    from risk_reward import debt_view
    audited = debt_view({"valuationModel": {"discountRateAudit": {"rateType": "COST_OF_EQUITY"}}}, True)
    assert (audited["status"], audited["rate_status"]) == ("ASSESSED", "OK") and audited["tier"] is None
    assert debt_view({"valuationModel": {"method": "annual_fcff"}}, True)["status"] == "ASSESSED"


def test_a_rebased_valuation_is_as_old_as_its_analysis_not_its_save_date() -> None:
    """Re-basing the discount rate on 2026-10-08 made 84 valuations read "0 days old" with a forward review."""
    from risk_reward import evidence_date
    rebased = {"valuationModel": {"method": "terminal_earnings", "leverage": {"tier": "LOW"}, "rateBasis": {"status": "OK"},
                                  "rebasedFrom": {"version": 6, "asOf": "2026-10-08"}}}
    assert evidence_date("2026-10-08T19:40:00+00:00", "2026-09-01T06:49:00.000Z", rebased) == "2026-09-01T06:49:00.000Z"
    assert evidence_date("2026-10-08T19:40:00+00:00", "2026-09-01T06:49:00.000Z", {}) == "2026-10-08T19:40:00+00:00"
    assert evidence_date("2026-10-08T19:40:00+00:00", None, rebased) == "2026-10-08T19:40:00+00:00"
    support = valuation_support(evidence_date("2026-10-08T19:40:00+00:00", "2026-06-01T00:00:00Z", rebased),
                                rebased, scenarios(), date(2026, 10, 8))
    by_id = {check["id"]: check for check in support["checks"]}
    assert support["age_days"] == 129 and by_id["fresh"]["ok"] is False
    assert by_id["forward_review"]["ok"] is False   # re-base bookkeeping is not a forward-earnings review
    assert by_id["rate_audit"]["ok"] is False


def test_real_forward_content_still_counts_after_a_rebase() -> None:
    log = {"valuationModel": {"rebasedFrom": {"version": 2}, "leverage": {"tier": "LOW"}, "capacityBuild": {"mw": 400}}}
    checks = {c["id"]: c["ok"] for c in valuation_support("2026-10-01T00:00:00Z", log, scenarios(), date(2026, 10, 8))["checks"]}
    assert checks["forward_review"] is True


def test_firm_cash_flow_valuations_are_not_described_as_audited() -> None:
    from risk_reward import debt_view
    view = debt_view({"valuationModel": {"method": "annual_fcff"}}, True)
    assert "audit" not in view["note"].lower() and "debt is subtracted" in view["note"].lower()
    assert "sourced audit" in debt_view({"valuationModel": {"discountRateAudit": {"rateType": "WACC"}}}, True)["note"]
