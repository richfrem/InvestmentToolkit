"""
Caught live 2026-08-29 valuing APLD (Applied Digital, AI/HPC infra buildout):
compute_scenario()'s year5PriceUndiscounted = year5EPS * exitPE * qualityMultiplier
has no floor. When a scenario's Year-5 net margin stays negative (a real,
common outcome for capex-heavy growth companies still ramping toward
profitability), year5EPS is negative, producing a literal NEGATIVE stock
price -- a company's worst real-world outcome for equity holders is a total
loss (price = $0), never a negative number. That negative "price" then
silently corrupts the weighted-average fair value alongside genuinely
positive scenarios, with no warning that the P/E-based terminal-value
method broke down for that scenario.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_dcf_scenarios_negative_price_floor.py -v
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from dcf_scenarios import compute_scenario, run  # noqa: E402


def _loss_making_params(growth=25, margin=-25, pe=12, qm=0.8, share_change=5.0, weight=0.25):
    return {
        "growthRate": growth, "netMargin": margin, "exitPE": pe,
        "qualityMultiplier": qm, "shareChange": share_change, "weight": weight,
    }


def test_negative_eps_scenario_floors_price_at_zero():
    """A scenario with negative Year-5 net margin must never produce a
    negative year5PriceUndiscounted or presentValue -- floor at 0.0."""
    result = compute_scenario(
        base_revenue=611_311_000, base_shares=284_303_812,
        discount_rate=0.10, horizon=5,
        params=_loss_making_params(),
    )
    assert result["year5EPS"] < 0, "test setup should produce negative EPS"
    assert result["year5PriceUndiscounted"] == 0.0
    assert result["presentValue"] == 0.0


def test_positive_eps_scenario_unaffected_by_floor():
    """The floor must not clip or alter a genuinely profitable scenario's price."""
    result = compute_scenario(
        base_revenue=611_311_000, base_shares=284_303_812,
        discount_rate=0.10, horizon=5,
        params=_loss_making_params(growth=65, margin=10, pe=25, qm=1.15, share_change=1.5),
    )
    assert result["year5EPS"] > 0
    assert result["year5PriceUndiscounted"] > 0
    assert result["presentValue"] > 0


def test_run_warns_when_any_scenario_hits_the_zero_floor():
    """run()'s validation.warnings must flag when a scenario's P/E-based terminal
    value went negative and was floored -- silently flooring to $0 without a
    warning would hide that the method broke down for that scenario (e.g. bear/
    base still loss-making at year 5), which the agent should know to reconsider
    (e.g. switch to a revenue-multiple method) rather than trust the $0 blindly."""
    result = run(
        ticker="APLD", base_revenue=611_311_000, base_shares=284_303_812,
        scenario_params={
            "bear": _loss_making_params(growth=25, margin=-25, pe=12, qm=0.8, share_change=5.0, weight=0.25),
            "base": _loss_making_params(growth=48, margin=-5, pe=18, qm=1.0, share_change=3.0, weight=0.50),
            "bull": _loss_making_params(growth=65, margin=10, pe=25, qm=1.15, share_change=1.5, weight=0.25),
        },
        price=25.34,
    )
    warnings = result["validation"]["warnings"]
    assert any("floored" in w.lower() and "bear" in w.lower() for w in warnings)
    assert any("floored" in w.lower() and "base" in w.lower() for w in warnings)
    assert not any("floored" in w.lower() and "bull" in w.lower() for w in warnings)


if __name__ == "__main__":
    test_negative_eps_scenario_floors_price_at_zero()
    test_positive_eps_scenario_unaffected_by_floor()
    test_run_warns_when_any_scenario_hits_the_zero_floor()
    print("✓ All dcf_scenarios negative-price-floor tests passed!")
