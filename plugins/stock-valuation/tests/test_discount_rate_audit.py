"""Purpose: verify sourced rate calculations match the valuation claim without defaults.

Layer: Valuation unit/CLI tests. Key Functions: model matching, input rejection, CLI audit.
Key Input Dependencies: canonical wacc.py; explicit test inputs; real CLI subprocess.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "plugins/stock-valuation/scripts"))
import wacc


def rate_inputs(method: str = "annual_fcff") -> dict:
    """Provide a complete deterministic example; sources are test evidence only."""
    return {"method": method, "asOf": "2026-10-07", "currency": "USD",
            "riskFreeRate": 0.04, "beta": 1, "erp": 0.06,
            "marketCap": 800, "totalDebt": 200, "costOfDebtPreTax": 0.05,
            "taxShieldRate": 0.20,
            "sources": [{"date": "2026-10-07", "url": "https://example.org/test-fixture",
                         "use": "Synthetic unit-test inputs, not a researched stock"}]}


def test_rate_matches_business_or_common_equity_claim() -> None:
    """The same inputs yield different rates for enterprise and equity valuations."""
    fcff = wacc.compute_discount_rate(rate_inputs())
    equity = wacc.compute_discount_rate(rate_inputs("terminal_earnings"))
    assert fcff["rateType"] == "WACC"
    assert fcff["selectedRate"] == pytest.approx(0.088)
    assert equity["rateType"] == "COST_OF_EQUITY"
    assert equity["selectedRate"] == pytest.approx(0.10)
    assert fcff["components"]["equityWeight"] == pytest.approx(0.8)
    assert fcff["components"]["costOfDebtAfterTax"] == pytest.approx(0.04)


def test_no_tax_shield_and_no_artificial_rate_cap() -> None:
    """Loss-making borrowers can have no current shield; high equity rates survive."""
    inputs = rate_inputs()
    inputs["taxShieldRate"] = 0
    assert wacc.compute_discount_rate(inputs)["selectedRate"] == pytest.approx(0.09)
    inputs.update(method="terminal_earnings", beta=5, erp=0.045)
    assert wacc.compute_discount_rate(inputs)["selectedRate"] == pytest.approx(0.265)


@pytest.mark.parametrize("field", ["riskFreeRate", "erp", "beta", "totalDebt", "sources"])
def test_missing_inputs_are_not_silently_substituted(field: str) -> None:
    """Missing debt is distinct from confirmed zero debt and requires investigation."""
    inputs = rate_inputs()
    inputs.pop(field)
    with pytest.raises(ValueError, match=field):
        wacc.compute_discount_rate(inputs)


@pytest.mark.parametrize("field,value", [("riskFreeRate", 4), ("erp", float("nan")),
                                        ("costOfDebtPreTax", -0.05)])
def test_invalid_units_and_values_are_rejected(field: str, value: float) -> None:
    """Reject nonfinite inputs, invalid costs and percentage/decimal confusion."""
    inputs = rate_inputs()
    inputs[field] = value
    with pytest.raises(ValueError, match=field):
        wacc.compute_discount_rate(inputs)


def test_unsupported_fcfe_is_not_relabelled() -> None:
    """Do not imply the current engine supports an annual FCFE method."""
    with pytest.raises(ValueError, match="method"):
        wacc.compute_discount_rate(rate_inputs("annual_fcfe"))


def test_real_cli_retains_inputs_and_provenance(tmp_path: Path) -> None:
    """A saved audit can reproduce a rate without network or database access."""
    inputs = rate_inputs("terminal_earnings")
    file = tmp_path / "rate-inputs.json"
    file.write_text(json.dumps(inputs))
    result = subprocess.run([sys.executable, str(ROOT / "plugins/stock-valuation/scripts/wacc.py"),
                             "--inputs", str(file), "--pretty"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    audit = json.loads(result.stdout)
    assert audit["selectedRate"] == pytest.approx(0.10)
    assert audit["inputs"] == inputs
    assert audit["readiness"] == "REVIEW_REQUIRED"
