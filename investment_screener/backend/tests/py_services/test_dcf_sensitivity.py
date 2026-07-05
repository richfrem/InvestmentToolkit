import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from dcf_sensitivity import sensitivity_grid, monte_carlo  # noqa: E402

BEAR = {"growthRate": 10.0, "netMargin": 15.0, "exitPE": 20.0, "qualityMultiplier": 1.0, "shareChange": 0.0}
BASE = {"growthRate": 22.0, "netMargin": 25.0, "exitPE": 30.0, "qualityMultiplier": 1.0, "shareChange": 0.0}
BULL = {"growthRate": 35.0, "netMargin": 32.0, "exitPE": 40.0, "qualityMultiplier": 1.0, "shareChange": 0.0}


def test_sensitivity_grid_dimensions_and_bounds():
    result = sensitivity_grid(
        BASE, discount_rate=0.10, horizon=5,
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
    )

    assert len(result["grid"]) == 7 * 7  # default growth_points=3, pe_points=3 -> 7 values each axis
    growths = sorted({row["growthRate"] for row in result["grid"]})
    assert growths[0] == 7.0    # 22 - 3*5
    assert growths[-1] == 37.0  # 22 + 3*5
    pes = sorted({row["exitPE"] for row in result["grid"]})
    assert pes[0] == 18.0   # 30 - 3*4
    assert pes[-1] == 42.0  # 30 + 3*4
    assert all(isinstance(row["fairValue"], float) for row in result["grid"])


def test_sensitivity_grid_fair_value_increases_with_growth_at_fixed_pe():
    result = sensitivity_grid(
        BASE, discount_rate=0.10, horizon=5,
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
    )
    at_center_pe = sorted(
        (row for row in result["grid"] if row["exitPE"] == 30.0),
        key=lambda r: r["growthRate"],
    )
    fair_values = [row["fairValue"] for row in at_center_pe]
    assert fair_values == sorted(fair_values)


def test_monte_carlo_is_deterministic_with_fixed_seed():
    result_a = monte_carlo(
        BEAR, BASE, BULL, discount_rate=0.10, horizon=5,
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
        current_price=50.0, n=500, seed=42,
    )
    result_b = monte_carlo(
        BEAR, BASE, BULL, discount_rate=0.10, horizon=5,
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
        current_price=50.0, n=500, seed=42,
    )
    assert result_a == result_b


def test_monte_carlo_percentiles_are_ordered_and_probability_is_valid():
    result = monte_carlo(
        BEAR, BASE, BULL, discount_rate=0.10, horizon=5,
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
        current_price=50.0, n=2000, seed=7,
    )
    assert result["p10"] <= result["p50"] <= result["p90"]
    assert 0.0 <= result["probabilityOvervalued"] <= 1.0
    assert result["n"] == 2000
    assert result["seed"] == 7


def test_monte_carlo_high_price_yields_high_overvalued_probability():
    result = monte_carlo(
        BEAR, BASE, BULL, discount_rate=0.10, horizon=5,
        base_revenue=1_000_000_000.0, base_shares=100_000_000.0,
        current_price=1_000_000.0, n=1000, seed=1,
    )
    assert result["probabilityOvervalued"] > 0.95
