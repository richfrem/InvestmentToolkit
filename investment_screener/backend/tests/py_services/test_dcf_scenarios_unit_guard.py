"""
Guards against the exact bug found 2026-08-28 while running a real DCF for AMAT:
growthRate/netMargin are expected as PERCENTAGE units (e.g. 8 for 8%), since
compute_scenario() does `params["growthRate"] / 100.0` internally. Passing decimal
fractions (0.08 instead of 8) silently produced near-zero 5-year growth and a
weightedFairValue of $1.78 vs an actual price of $463.27 (-99.6%, wrongly flagged
SELL) -- with zero validation error, because the existing checks (weight sum,
growth/PV ordering, netMargin in [0,100]) all still passed on decimal-form input.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from dcf_scenarios import run  # noqa: E402


def _base_scenarios(growth_bear, growth_base, growth_bull, margin=25):
    """Minimal valid 3-scenario dict, varying only growthRate per the test."""
    return {
        "bear": {"growthRate": growth_bear, "netMargin": margin, "exitPE": 15, "qualityMultiplier": 1.0, "shareChange": 0, "weight": 0.2},
        "base": {"growthRate": growth_base, "netMargin": margin, "exitPE": 20, "qualityMultiplier": 1.0, "shareChange": 0, "weight": 0.5},
        "bull": {"growthRate": growth_bull, "netMargin": margin, "exitPE": 25, "qualityMultiplier": 1.0, "shareChange": 0, "weight": 0.3},
    }


def test_decimal_growth_rate_fails_validation():
    """The exact AMAT bug: 0.08/0.15/0.22 instead of 8/15/22 must be rejected."""
    result = run(
        ticker="TEST", base_revenue=1_000_000_000, base_shares=100_000_000,
        scenario_params=_base_scenarios(0.08, 0.15, 0.22), price=100.0,
    )
    assert result["validation"]["valid"] is False
    assert any("growthRate" in e and "decimal" in e.lower() for e in result["validation"]["errors"])


def test_decimal_net_margin_fails_validation():
    scenarios = _base_scenarios(8, 15, 22, margin=25)
    scenarios["base"]["netMargin"] = 0.29  # decimal mistake
    result = run(
        ticker="TEST", base_revenue=1_000_000_000, base_shares=100_000_000,
        scenario_params=scenarios, price=100.0,
    )
    assert result["validation"]["valid"] is False
    assert any("netMargin" in e and "decimal" in e.lower() for e in result["validation"]["errors"])


def test_normal_percentage_inputs_still_pass():
    """Real, correctly-scaled inputs (like the AMAT scenarios once fixed) must
    not be flagged -- this guard must not produce false positives on legitimate
    single-digit-to-twenties percentage growth rates."""
    result = run(
        ticker="TEST", base_revenue=1_000_000_000, base_shares=100_000_000,
        scenario_params=_base_scenarios(8, 15, 22), price=100.0,
    )
    assert result["validation"]["valid"] is True
    assert result["validation"]["errors"] == []


def test_genuine_negative_growth_bear_case_still_allowed():
    """A real declining bear-case (e.g. -5% revenue contraction) must not be
    misflagged as a decimal-fraction mistake -- only the suspiciously-small
    0<x<1 range is a unit-mistake signature, not negative values."""
    result = run(
        ticker="TEST", base_revenue=1_000_000_000, base_shares=100_000_000,
        scenario_params=_base_scenarios(-5, 15, 22), price=100.0,
    )
    assert result["validation"]["valid"] is True


if __name__ == "__main__":
    test_decimal_growth_rate_fails_validation()
    test_decimal_net_margin_fails_validation()
    test_normal_percentage_inputs_still_pass()
    test_genuine_negative_growth_bear_case_still_allowed()
    print("✓ All dcf_scenarios unit-guard tests passed!")
