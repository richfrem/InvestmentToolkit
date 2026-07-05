import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from wacc import (  # noqa: E402
    compute_beta,
    compute_cost_of_debt,
    compute_risk_free_rate,
    compute_wacc,
    WACC_CAP,
    WACC_FLOOR,
)


def _make_price_series(closes: list[float]) -> list[dict]:
    start = date(2024, 1, 1)
    return [{"date": (start + timedelta(days=i)).isoformat(), "close": c} for i, c in enumerate(closes)]


def _closes_from_returns(start_price: float, returns: list[float]) -> list[float]:
    closes = [start_price]
    for r in returns:
        closes.append(closes[-1] * math.exp(r))
    return closes


def test_compute_beta_matches_known_multiplier():
    random.seed(42)
    spy_returns = [random.uniform(-0.02, 0.02) for _ in range(40)]
    ticker_returns = [2 * r for r in spy_returns]
    spy_prices = _make_price_series(_closes_from_returns(100.0, spy_returns))
    ticker_prices = _make_price_series(_closes_from_returns(50.0, ticker_returns))

    result = compute_beta(ticker_prices, spy_prices)

    assert result["usedFallback"] is False
    assert abs(result["beta"] - 2.0) < 0.05


def test_compute_beta_falls_back_with_insufficient_history():
    spy_prices = _make_price_series([100.0, 101.0, 99.5, 100.5, 102.0])
    ticker_prices = _make_price_series([50.0, 50.5, 49.8, 50.2, 51.0])

    result = compute_beta(ticker_prices, spy_prices)

    assert result["usedFallback"] is True
    assert result["beta"] == 1.2


def test_compute_cost_of_debt_normal_case():
    result = compute_cost_of_debt(interest_expense=50_000_000.0, total_debt=1_000_000_000.0, tax_rate=0.21)
    assert result["costOfDebt"] == 0.0395
    assert result["usedFallback"] is False


def test_compute_cost_of_debt_missing_total_debt_falls_back():
    result = compute_cost_of_debt(interest_expense=50_000_000.0, total_debt=None)
    assert result["usedFallback"] is True
    assert result["costOfDebt"] == 0.05


def test_compute_cost_of_debt_zero_total_debt_falls_back():
    result = compute_cost_of_debt(interest_expense=50_000_000.0, total_debt=0.0)
    assert result["usedFallback"] is True


def test_compute_risk_free_rate_divides_tnx_close_correctly():
    with patch("wacc.get_prices", return_value={
        "^TNX": {"data": [{"date": "2026-07-01", "close": 42.79}], "source": "yfinance", "asOf": "x"}
    }):
        result = compute_risk_free_rate()
    assert result["riskFreeRate"] == 0.04279
    assert result["usedFallback"] is False


def test_compute_risk_free_rate_falls_back_when_no_data():
    with patch("wacc.get_prices", return_value={}):
        result = compute_risk_free_rate()
    assert result["usedFallback"] is True
    assert result["riskFreeRate"] == 0.04


def test_compute_wacc_uses_overrides_and_returns_source_decomposition():
    with patch("wacc.compute_risk_free_rate", return_value={"riskFreeRate": 0.04, "usedFallback": False}), \
         patch("wacc.get_fundamentals", return_value={}):
        result = compute_wacc(
            ticker="TESTCO", market_cap=1_000_000_000.0,
            beta_override=1.0, cost_of_debt_override=0.03,
        )
    assert result["source"]["beta"] == "override"
    assert result["source"]["costOfDebt"] == "override"
    assert result["betaWarning"] is None


def test_compute_wacc_incorporates_debt_weighting():
    with patch("wacc.compute_risk_free_rate", return_value={"riskFreeRate": 0.04, "usedFallback": False}), \
         patch("wacc.get_fundamentals", return_value={
             "totalDebt": {"value": 200_000_000.0, "source": "yfinance", "asOf": "x"}
         }):
        result = compute_wacc(
            ticker="TESTCO", market_cap=800_000_000.0, erp=0.06,
            beta_override=1.0, cost_of_debt_override=0.05,
        )
    # cost_of_equity = 0.04 + 1.0*0.06 = 0.10; equity_weight=800/1000=0.8, debt_weight=0.2
    # wacc = 0.8*0.10 + 0.2*0.05 = 0.09
    assert result["wacc"] == 0.09
    assert result["capApplied"] is False
    assert result["floorApplied"] is False


def test_compute_wacc_caps_at_upper_bound():
    with patch("wacc.compute_risk_free_rate", return_value={"riskFreeRate": 0.04, "usedFallback": False}), \
         patch("wacc.get_fundamentals", return_value={}):
        result = compute_wacc(
            ticker="TESTCO", market_cap=1_000_000_000.0,
            beta_override=5.0, cost_of_debt_override=0.05, erp=0.045,
        )
    assert result["capApplied"] is True
    assert result["wacc"] == WACC_CAP
    assert result["betaWarning"] is not None


def test_compute_wacc_floors_at_lower_bound():
    with patch("wacc.compute_risk_free_rate", return_value={"riskFreeRate": 0.01, "usedFallback": False}), \
         patch("wacc.get_fundamentals", return_value={}):
        result = compute_wacc(
            ticker="TESTCO", market_cap=1_000_000_000.0,
            beta_override=0.1, cost_of_debt_override=0.01, erp=0.02,
        )
    assert result["floorApplied"] is True
    assert result["wacc"] == WACC_FLOOR
    assert result["betaWarning"] is not None
