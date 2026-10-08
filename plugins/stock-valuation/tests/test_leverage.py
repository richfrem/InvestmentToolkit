"""Purpose: contract tests for grading balance-sheet risk and what it changes in a valuation.

Layer: Business-logic unit tests. Key Functions: tier, weight shift and rate-basis cases.
Key Input Dependencies: leverage.py pure functions; no database or network.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from leverage import apply_leverage_weights, leverage_profile, rate_basis_check  # noqa: E402

B = 1_000_000_000


def test_a_net_cash_company_with_covered_interest_is_low():
    profile = leverage_profile(total_debt=10 * B, cash=90 * B, ebitda=120 * B, operating_income=100 * B,
                               interest_expense=0.3 * B, current_ratio=1.9, market_cap=2000 * B)
    assert (profile["tier"], profile["points"], profile["reasons"]) == ("LOW", 0, [])
    assert profile["netDebt"] == -80 * B


def test_heavy_debt_against_thin_earnings_is_high_and_says_why():
    """CoreWeave on 2026-10-08: net debt 12x EBITDA, larger than its market value, current ratio 0.46."""
    profile = leverage_profile(total_debt=48 * B, cash=3 * B, ebitda=3.7 * B, operating_income=None,
                               interest_expense=None, current_ratio=0.46, market_cap=36 * B)
    assert (profile["tier"], profile["points"]) == ("SEVERE", 5)
    assert profile["reasons"] == ["Net debt is 12.2x EBITDA", "Net debt is 125% of market value",
                                  "Current ratio 0.46: short-term liabilities exceed liquid assets"]


@pytest.mark.parametrize("ratio,points", [(2.0, 0), (3.0, 1), (5.0, 2), (9.0, 3)])
def test_debt_to_ebitda_bands(ratio, points):
    assert leverage_profile(total_debt=ratio * B, cash=0, ebitda=B, market_cap=100 * B)["points"] == points


def test_debt_with_no_positive_ebitda_and_uncovered_interest_is_stressed():
    profile = leverage_profile(total_debt=B, cash=0.2 * B, ebitda=-0.1 * B, operating_income=-0.2 * B,
                               interest_expense=0.05 * B, current_ratio=1.2, market_cap=5 * B)
    assert profile["tier"] == "HIGH" and profile["points"] == 4
    assert "Net debt with no positive EBITDA to service it" in profile["reasons"]
    assert "Operating income does not cover interest" in profile["reasons"]


def test_interest_expense_sign_does_not_matter_and_thin_cover_scores_one():
    for interest in (0.25 * B, -0.25 * B):
        profile = leverage_profile(total_debt=B, cash=B, ebitda=2 * B, operating_income=B, interest_expense=interest)
        assert (profile["points"], profile["interestCoverage"]) == (1, 4.0)


def test_net_cash_caps_the_tier_and_missing_debt_is_unknown():
    capped = leverage_profile(total_debt=B, cash=5 * B, ebitda=-B, operating_income=-B, interest_expense=B, current_ratio=0.5)
    assert capped["tier"] == "MODERATE" and "Net cash position limits the grade" in capped["reasons"]
    assert leverage_profile(ebitda=B)["tier"] == "UNKNOWN"


def test_only_high_and_severe_move_probability_to_the_bear_case():
    weights = {"bear": 0.30, "base": 0.50, "bull": 0.20}
    for tier in ("LOW", "MODERATE", "UNKNOWN"):
        assert apply_leverage_weights(weights, tier) == weights
    assert apply_leverage_weights(weights, "HIGH") == {"bear": 0.35, "base": 0.50, "bull": 0.15}
    assert apply_leverage_weights(weights, "SEVERE") == {"bear": 0.40, "base": 0.50, "bull": 0.10}


def test_the_shift_takes_from_the_base_case_once_the_bull_case_is_used_up():
    shifted = apply_leverage_weights({"bear": 0.45, "base": 0.50, "bull": 0.05}, "SEVERE")
    assert shifted == {"bear": 0.55, "base": 0.45, "bull": 0.0}
    assert round(sum(shifted.values()), 6) == 1.0


def test_equity_earnings_discounted_below_the_cost_of_equity_is_a_mismatch():
    """A blended rate falls as debt rises; applied to EPS x P/E it rewards borrowing."""
    low = rate_basis_check("terminal_earnings", 0.0816, 0.1423)
    assert low["status"] == "MISMATCH" and "8.16%" in low["note"] and "14.23%" in low["note"]
    assert rate_basis_check("terminal_earnings", 0.1423, 0.1423)["status"] == "OK"
    assert rate_basis_check(None, 0.139, 0.1423)["status"] == "OK"          # within tolerance
    assert rate_basis_check("terminal_earnings", 0.10, None)["status"] == "UNKNOWN"
    assert rate_basis_check("annual_fcff", 0.08, 0.14)["status"] == "OK"     # WACC with a debt bridge
