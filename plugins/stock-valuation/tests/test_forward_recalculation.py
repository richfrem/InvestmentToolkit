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
