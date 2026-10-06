"""Purpose: verify reproducible forward valuations use canonical math and actions.

Layer: CLI integration. Usage: python3 -m pytest this file.
Key Functions: test_forward_recalculation.
Key Input Dependencies: checked-in MU/BE model inputs; real calculator subprocess.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("ticker", ("MU", "BE"))
def test_forward_recalculation(ticker: str, tmp_path: Path) -> None:
    """Each input yields validated projections, ordered scenarios and sensitivity."""
    output = tmp_path / ticker
    command = [sys.executable, str(ROOT / "plugins/stock-valuation/scripts/recalculate_forward_valuation.py"),
               "--model", str(ROOT / f"plugins/stock-valuation/tests/fixtures/forward-valuation/{ticker}_inputs.json"),
               "--output", str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = json.loads((output / "valuation.json").read_text())
    payload = json.loads((output / "payload.json").read_text())
    assert report["validation"]["valid"]
    final_period = report["scenarios"]["base"]["annualForecast"][-1]["discountPeriod"]
    assert report["horizon"] == final_period
    assert report["discountDivisor"] == pytest.approx((1 + report["discountRate"]) ** final_period, abs=0.00002)
    assert payload["projection"]["valuationModel"]["scenarios"] == report["scenarios"]
    assert payload["projection"]["action"] == report["action"]
    assert report["recommendation"]["action"] in {"ACCUMULATE", "MAINTAIN", "TRIM"}
    sensitivity = report["sensitivity"]
    assert len(sensitivity) == 9
    assert sensitivity[0]["fairValue"] > sensitivity[6]["fairValue"]
    assert sensitivity[0]["fairValue"] < sensitivity[2]["fairValue"]
    assert report["sources"]
    assert report["scenarios"]["base"]["annualForecast"][0]["freeCashFlow"]
    assert (output / "review.md").exists()
    if ticker == "BE":
        conversion = next(case for case in report["stressCases"] if case["stress"] == "convertible_converted")
        assert conversion["fairValue"] > 0
        assert conversion["action"] == "TRIM"
    assert "standing_decision_type" not in payload
    assert "target_weight" not in payload


def test_nonpositive_terminal_cash_flow_stress_is_reported_and_does_not_abort(tmp_path: Path) -> None:
    """Stress cases that invalidate a perpetuity are disclosed without aborting the base DCF."""
    source = ROOT / "plugins/stock-valuation/tests/fixtures/forward-valuation/BE_inputs.json"
    model = json.loads(source.read_text())
    model["scenarios"]["bear"]["terminalForecast"]["operatingMarginPct"] = 5
    for row in model["scenarios"]["bear"]["annualForecast"]:
        row["capex"] = 4_000_000_000
    model_path = tmp_path / "stress-model.json"
    model_path.write_text(json.dumps(model))
    output = tmp_path / "stress-output"
    command = [sys.executable, str(ROOT / "plugins/stock-valuation/scripts/recalculate_forward_valuation.py"),
               "--model", str(model_path), "--output", str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    valuation = json.loads((output / "valuation.json").read_text())
    margin_stress = next(case for case in valuation["stressCases"]
                         if case["stress"] == "operating_margin_minus_10pp")
    assert margin_stress["status"] == "not_computable"
    assert "terminal free cash flow must be positive" in margin_stress["reason"]
    assert "N/M" in (output / "review.md").read_text()
