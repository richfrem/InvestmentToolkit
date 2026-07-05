import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from dcf_scenarios import compute_scenario  # noqa: E402
from reverse_dcf import solve_implied_growth  # noqa: E402

BASE_PARAMS = {
    "weight": 1.0, "netMargin": 25.0, "exitPE": 30.0,
    "qualityMultiplier": 1.0, "shareChange": 0.0,
}


def _pv_for_growth(growth: float) -> float:
    return compute_scenario(
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
        discount_rate=0.10, horizon=5,
        params={**BASE_PARAMS, "growthRate": growth},
    )["presentValue"]


def test_reverse_dcf_recovers_input_growth_within_tolerance():
    price = _pv_for_growth(22.0)

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["converged"] is True
    assert abs(result["impliedGrowth"] - 22.0) < 0.1


def test_reverse_dcf_verdict_below_bear_when_price_under_bear_pv():
    price = _pv_for_growth(10.0) * 0.9

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["verdict"] == "BELOW_BEAR"
    assert result["converged"] is True


def test_reverse_dcf_verdict_between_base_and_bull():
    price = (_pv_for_growth(22.0) + _pv_for_growth(35.0)) / 2

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["verdict"] == "BETWEEN_BASE_AND_BULL"


def test_reverse_dcf_verdict_between_bear_and_base():
    price = (_pv_for_growth(10.0) + _pv_for_growth(22.0)) / 2

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["verdict"] == "BETWEEN_BEAR_AND_BASE"


def test_reverse_dcf_verdict_pricing_in_more_than_bull_when_price_over_bull_pv():
    price = _pv_for_growth(35.0) * 1.1

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["verdict"] == "PRICING_IN_MORE_THAN_BULL"


def test_reverse_dcf_out_of_bracket_range_returns_not_converged():
    result = solve_implied_growth(
        price=999_999_999_999.0, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["converged"] is False
    assert result["verdict"] == "OUT_OF_BRACKET_RANGE"
    assert result["impliedGrowth"] is None


def test_reverse_dcf_computes_vs_guidance_when_provided():
    price = _pv_for_growth(22.0)

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0, guided_growth=18.0,
    )

    assert result["impliedGrowthVsGuidance"] is not None
    assert abs(result["impliedGrowthVsGuidance"] - 4.0) < 0.1


def test_reverse_dcf_vs_guidance_is_none_when_not_provided():
    price = _pv_for_growth(22.0)

    result = solve_implied_growth(
        price=price, base_shares=100_000_000.0, discount_rate=0.10, horizon=5,
        margin=25.0, exit_pe=30.0, quality_multiplier=1.0, base_revenue=1_000_000_000.0,
        bear_growth=10.0, base_growth=22.0, bull_growth=35.0,
    )

    assert result["impliedGrowthVsGuidance"] is None
