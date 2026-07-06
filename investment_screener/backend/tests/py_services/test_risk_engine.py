"""Tests for risk_engine.py — portfolio risk snapshot (Phase 3, E1)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from risk_engine import (  # noqa: E402
    build_returns_matrix,
    compute_correlation_matrix,
    compute_portfolio_vol_beta,
)


def _price_rows(closes: list[float], start_day: int = 1) -> list[dict]:
    return [
        {"date": f"2026-01-{start_day + i:02d}", "open": c, "high": c, "low": c,
         "close": c, "volume": 1000.0}
        for i, c in enumerate(closes)
    ]


# ── build_returns_matrix ──────────────────────────────────────────────────────

def test_build_returns_matrix_aligns_and_computes_pct_change():
    closes_a = [100.0, 102.0, 101.0, 105.0, 104.0]
    closes_b = [50.0, 51.0, 50.5, 52.0, 51.5]
    prices = {"A": {"data": _price_rows(closes_a)}, "B": {"data": _price_rows(closes_b)}}

    returns, excluded = build_returns_matrix(prices, min_days=3)

    assert excluded == []
    assert set(returns.columns) == {"A", "B"}
    assert len(returns) == 4  # 5 closes -> 4 daily returns
    assert returns["A"].iloc[0] == pytest.approx((102.0 - 100.0) / 100.0)
    assert returns["B"].iloc[0] == pytest.approx((51.0 - 50.0) / 50.0)


def test_build_returns_matrix_excludes_short_history_ticker():
    long_history = _price_rows([100.0 + i for i in range(90)])
    short_history = _price_rows([50.0, 51.0, 49.0], start_day=1)
    prices = {"LONG": {"data": long_history}, "SHORT": {"data": short_history}}

    returns, excluded = build_returns_matrix(prices, min_days=60)

    assert excluded == ["SHORT"]
    assert "SHORT" not in returns.columns
    assert returns.empty  # only 1 ticker survives -> need 2+ to build a matrix


def test_build_returns_matrix_returns_empty_for_fewer_than_two_tickers():
    prices = {"ONLY": {"data": _price_rows([100.0] * 90)}}
    returns, excluded = build_returns_matrix(prices, min_days=60)
    assert returns.empty
    assert excluded == []


def test_build_returns_matrix_inner_joins_on_mismatched_dates():
    # A trades every day; B is missing 2026-01-03 (e.g. TSX holiday).
    rows_a = _price_rows([100.0, 101.0, 102.0, 103.0, 104.0], start_day=1)
    rows_b = [
        {"date": "2026-01-01", "open": 50.0, "high": 50.0, "low": 50.0, "close": 50.0, "volume": 1000.0},
        {"date": "2026-01-02", "open": 51.0, "high": 51.0, "low": 51.0, "close": 51.0, "volume": 1000.0},
        {"date": "2026-01-04", "open": 52.0, "high": 52.0, "low": 52.0, "close": 52.0, "volume": 1000.0},
        {"date": "2026-01-05", "open": 53.0, "high": 53.0, "low": 53.0, "close": 53.0, "volume": 1000.0},
    ]
    prices = {"A": {"data": rows_a}, "B": {"data": rows_b}}

    returns, excluded = build_returns_matrix(prices, min_days=3)

    assert excluded == []
    # 2026-01-03 dropped for both (B has no row that day) -> 4 aligned dates -> 3 returns
    assert len(returns) == 3


# ── compute_correlation_matrix ───────────────────────────────────────────────

def test_correlation_matrix_identical_series_is_one():
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.03, 0.01], "B": [0.01, -0.02, 0.03, 0.01]})
    corr = compute_correlation_matrix(returns)
    assert corr["A"]["B"] == 1.0
    assert corr["B"]["A"] == 1.0
    assert "A" not in corr["A"]  # no self-entry


def test_correlation_matrix_inverse_series_is_negative_one():
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.03, 0.01], "B": [-0.01, 0.02, -0.03, -0.01]})
    corr = compute_correlation_matrix(returns)
    assert corr["A"]["B"] == -1.0


def test_correlation_matrix_empty_for_single_ticker():
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.03]})
    assert compute_correlation_matrix(returns) == {}


# ── compute_portfolio_vol_beta ───────────────────────────────────────────────

def test_vol_beta_beta_is_one_when_portfolio_matches_benchmark_exactly():
    spy_returns = [0.01, -0.02, 0.015, 0.005, -0.01, 0.02]
    returns = pd.DataFrame({"SPY": spy_returns, "A": spy_returns})
    result = compute_portfolio_vol_beta(returns, {"A": 1.0}, benchmark="SPY")

    assert result["beta"] == pytest.approx(1.0, abs=1e-6)
    expected_vol = pd.Series(spy_returns).std(ddof=1) * (252 ** 0.5)
    assert result["vol"] == pytest.approx(expected_vol, abs=1e-4)


def test_vol_beta_returns_none_when_benchmark_missing():
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.03]})
    result = compute_portfolio_vol_beta(returns, {"A": 1.0}, benchmark="SPY")
    assert result == {"vol": None, "beta": None}


def test_vol_beta_ignores_tickers_with_no_weight():
    spy_returns = [0.01, -0.02, 0.015, 0.005, -0.01, 0.02]
    returns = pd.DataFrame({
        "SPY": spy_returns, "A": spy_returns,
        "B": [0.5, -0.5, 0.5, -0.5, 0.5, -0.5],
    })
    # No weight entry for B -> must not affect beta despite wild returns.
    result = compute_portfolio_vol_beta(returns, {"A": 1.0}, benchmark="SPY")
    assert result["beta"] == pytest.approx(1.0, abs=1e-6)
