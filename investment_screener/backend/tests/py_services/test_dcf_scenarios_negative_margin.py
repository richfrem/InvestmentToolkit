"""
Caught live 2026-08-28 valuing SHAZ (SharonAI Holdings, pre-revenue AI infra
company): update-stock-analysis/SKILL.md Step 3 constraint #4 documents
`netMargin` as "Realistic (-100% to 100%)", but validate_scenarios() actually
enforced [0, 100] -- rejecting the legitimate negative bear-case margin a
loss-making/pre-revenue company's bear scenario requires (e.g. -15% for a
capex-heavy AI datacenter buildout that underdelivers). Fixed to match the
documented -100 to 100 range.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_dcf_scenarios_negative_margin.py -v
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from dcf_scenarios import run  # noqa: E402


def _scenarios(bear_margin, base_margin=5, bull_margin=15):
    return {
        "bear": {"growthRate": -5, "netMargin": bear_margin, "exitPE": 10, "qualityMultiplier": 0.8, "shareChange": 5.0, "weight": 0.35},
        "base": {"growthRate": 10, "netMargin": base_margin, "exitPE": 18, "qualityMultiplier": 1.0, "shareChange": 3.0, "weight": 0.40},
        "bull": {"growthRate": 25, "netMargin": bull_margin, "exitPE": 25, "qualityMultiplier": 1.1, "shareChange": 1.5, "weight": 0.25},
    }


def test_negative_bear_margin_within_documented_range_is_valid():
    """SKILL.md documents netMargin as -100 to 100 -- a -15% bear-case margin
    for a loss-making pre-revenue company must not be rejected."""
    result = run(
        ticker="SHAZ", base_revenue=1_536_071_250, base_shares=35_667_164,
        scenario_params=_scenarios(bear_margin=-15), price=52.37,
    )
    assert result["validation"]["valid"] is True
    assert result["validation"]["errors"] == []


def test_margin_below_negative_100_still_rejected():
    """The documented floor is -100% (i.e. losing $1 for every $1 of revenue) --
    anything below that is still a real error, not a valid loss-making margin."""
    result = run(
        ticker="SHAZ", base_revenue=1_536_071_250, base_shares=35_667_164,
        scenario_params=_scenarios(bear_margin=-150), price=52.37,
    )
    assert result["validation"]["valid"] is False
    assert any("netMargin" in e for e in result["validation"]["errors"])


def test_margin_above_100_still_rejected():
    result = run(
        ticker="SHAZ", base_revenue=1_536_071_250, base_shares=35_667_164,
        scenario_params=_scenarios(bear_margin=5, base_margin=5, bull_margin=150),
        price=52.37,
    )
    assert result["validation"]["valid"] is False
    assert any("netMargin" in e for e in result["validation"]["errors"])


if __name__ == "__main__":
    test_negative_bear_margin_within_documented_range_is_valid()
    test_margin_below_negative_100_still_rejected()
    test_margin_above_100_still_rejected()
    print("✓ All dcf_scenarios negative-margin tests passed!")
