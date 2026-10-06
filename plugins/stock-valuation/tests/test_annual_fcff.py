"""Purpose: verify annual FCFF math, guardrails and legacy model compatibility.

Layer: Valuation math contracts.
Usage: python3 -m pytest plugins/stock-valuation/tests/test_annual_fcff.py
Key Functions: test_cash_flow_bridge, test_invalid_inputs, test_legacy_unchanged.
Key Input Dependencies: canonical dcf_scenarios.py; no network or live database.
"""
import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "annual_dcf", Path(__file__).resolve().parents[1] / "scripts/dcf_scenarios.py"
)
dcf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dcf)


def cash_flow_params() -> dict:
    """Return a hand-checkable one-year forecast in dollars and percentage units."""
    row = {"revenue": 100, "operatingMarginPct": 20, "taxRatePct": 20,
           "depreciation": 5, "capex": 7, "workingCapitalChange": 2}
    return {"method": "annual_fcff", "weight": 1, "annualForecast": [row],
            "terminalForecast": row, "terminalGrowth": 0,
            "cash": 20, "debt": 10, "otherClaims": 5,
            "sbcTreatment": "expensed_in_operating_margin"}


def test_cash_flow_bridge() -> None:
    """FCFF=12; discounted year one plus perpetuity EV=120; equity=125."""
    result = dcf.compute_scenario(90, 10, 0.10, 1, cash_flow_params())
    assert result["annualForecast"][0]["freeCashFlow"] == 12
    assert result["enterpriseValue"] == pytest.approx(120)
    assert result["equityValue"] == pytest.approx(125)
    assert result["presentValue"] == 12.5
    assert result["terminalValuePct"] == pytest.approx(90.9091, abs=0.0001)


@pytest.mark.parametrize("field,value,message", [
    ("terminalGrowth", 0.10, "terminal growth"),
    ("annualForecast", [], "horizon"),
    ("cash", float("nan"), "finite"),
    ("shareChange", 1, "SBC"),
    ("optionalityAdjustment", 100, "optionality"),
])
def test_invalid_inputs(field: str, value: object, message: str) -> None:
    """Bad periods, units and double counting must fail before persistence."""
    params = cash_flow_params()
    params[field] = value
    with pytest.raises(ValueError, match=message):
        dcf.compute_scenario(90, 10, 0.10, 1, params)


def test_terminal_normalization_and_cash_counted_once() -> None:
    """A normalized terminal row must replace peak cash flow, not supplement it."""
    params = cash_flow_params()
    params["terminalForecast"] = deepcopy(params["terminalForecast"])
    params["terminalForecast"]["operatingMarginPct"] = 10
    result = dcf.compute_scenario(90, 10, 0.10, 1, params)
    assert result["terminalFreeCashFlow"] == 4
    assert result["presentValue"] == 5.23


def test_legacy_unchanged() -> None:
    """Existing terminal EPS/P-E inputs retain their established value."""
    params = {"weight": 1, "growthRate": 10, "netMargin": 20,
              "exitPE": 15, "qualityMultiplier": 1, "shareChange": 0}
    assert dcf.compute_scenario(100, 10, 0.10, 5, params)["presentValue"] == 30


def test_explicit_periods_and_non_monotonic_rejection() -> None:
    """A fiscal stub discounts at its stated time rather than a full year."""
    params = cash_flow_params()
    params["annualForecast"][0]["discountPeriod"] = 0.25
    result = dcf.compute_scenario(90, 10, 0.10, 1, params)
    assert result["annualForecast"][0]["presentValueCashFlow"] == pytest.approx(11.71745, abs=0.0001)
    params["annualForecast"].append(deepcopy(params["annualForecast"][0]))
    with pytest.raises(ValueError, match="increasing"):
        dcf.compute_scenario(90, 10, 0.10, 2, params)


def test_cash_flow_run_and_negative_weight() -> None:
    """The canonical run accepts FCFF inputs and rejects negative probabilities."""
    scenarios = {name: cash_flow_params() for name in dcf.SCENARIO_NAMES}
    for name, revenue, weight in (("bear", 95, 0.2), ("base", 100, 0.6), ("bull", 110, 0.2)):
        scenarios[name]["weight"] = weight
        scenarios[name]["annualForecast"][0]["revenue"] = revenue
    assert dcf.run("TEST", 90, 10, scenarios, horizon=1)["validation"]["valid"]
    scenarios["bear"]["weight"] = -0.2
    assert not dcf.run("TEST", 90, 10, scenarios, horizon=1)["validation"]["valid"]
