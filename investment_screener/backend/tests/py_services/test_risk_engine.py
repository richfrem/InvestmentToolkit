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
    compute_concentration,
    compute_marginal_risk_contribution,
    compute_cluster_exposure,
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


# ── compute_marginal_risk_contribution ───────────────────────────────────────

def test_mrc_sums_to_one_property():
    returns = pd.DataFrame({
        "A": [0.01, -0.02, 0.015, 0.005, -0.01, 0.02, 0.01, -0.005],
        "B": [0.02, -0.01, 0.005, 0.015, -0.02, 0.01, -0.005, 0.02],
        "C": [-0.01, 0.02, -0.015, 0.01, 0.005, -0.02, 0.015, -0.01],
    })
    weights = {"A": 0.5, "B": 0.3, "C": 0.2}
    mrc = compute_marginal_risk_contribution(returns, weights, benchmark="SPY")
    assert sum(mrc.values()) == pytest.approx(1.0, abs=1e-4)
    assert set(mrc.keys()) == {"A", "B", "C"}


def test_mrc_zero_variance_ticker_contributes_zero():
    returns = pd.DataFrame({
        "A": [0.01, -0.02, 0.015, 0.005, -0.01, 0.02],
        "FLAT": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    })
    weights = {"A": 0.7, "FLAT": 0.3}
    mrc = compute_marginal_risk_contribution(returns, weights, benchmark="SPY")
    assert mrc["FLAT"] == 0.0


def test_mrc_returns_empty_for_single_holding():
    returns = pd.DataFrame({"A": [0.01, -0.02, 0.015]})
    assert compute_marginal_risk_contribution(returns, {"A": 1.0}, benchmark="SPY") == {}


# ── compute_concentration ─────────────────────────────────────────────────────

def test_concentration_known_weights():
    weights = {"A": 0.5, "B": 0.3, "C": 0.2}
    result = compute_concentration(weights)
    assert result["hhi"] == pytest.approx(0.25 + 0.09 + 0.04)
    assert result["top3Weight"] == 1.0
    assert result["effectiveN"] == pytest.approx(1 / 0.38, abs=1e-2)


def test_concentration_renormalizes_non_100pct_input():
    weights = {"A": 50.0, "B": 30.0, "C": 20.0}  # e.g. raw 0-100 scale weights
    result = compute_concentration(weights)
    assert result["hhi"] == pytest.approx(0.25 + 0.09 + 0.04)


def test_concentration_empty_input_returns_none_shape():
    assert compute_concentration({}) == {"hhi": None, "top3Weight": None, "effectiveN": None}


def test_concentration_top3_with_more_than_three_holdings():
    weights = {"A": 0.4, "B": 0.3, "C": 0.15, "D": 0.15}
    result = compute_concentration(weights)
    assert result["top3Weight"] == pytest.approx(0.85)


# ── compute_cluster_exposure ─────────────────────────────────────────────────


def test_cluster_exposure_groups_by_pillar():
    weights = {"NVDA": 0.4, "CRWV": 0.2, "PANW": 0.25, "CBRS": 0.15}
    pillar_map = {"NVDA": "ai_infra", "CRWV": "ai_infra", "PANW": "cyber", "CBRS": "cyber"}
    mrc = {"NVDA": 0.5, "CRWV": 0.22, "PANW": 0.2, "CBRS": 0.08}

    result = compute_cluster_exposure(weights, pillar_map, mrc)

    ai = next(r for r in result if r["pillarId"] == "ai_infra")
    cyber = next(r for r in result if r["pillarId"] == "cyber")
    assert ai["weight"] == pytest.approx(0.6)
    assert ai["varianceContributionPct"] == pytest.approx(72.0)
    assert cyber["weight"] == pytest.approx(0.4)
    assert cyber["varianceContributionPct"] == pytest.approx(28.0)
    assert result[0]["pillarId"] == "ai_infra"  # sorted by weight descending


def test_cluster_exposure_unassigned_pillar():
    result = compute_cluster_exposure({"NEWTICKER": 1.0}, pillar_map={}, mrc={"NEWTICKER": 1.0})
    assert result == [{"pillarId": "unassigned", "weight": 1.0, "varianceContributionPct": 100.0}]


def test_cluster_exposure_empty_weights_returns_empty_list():
    assert compute_cluster_exposure({}, {}, {}) == []


from risk_engine import compute_stress_replay  # noqa: E402


def _build_return_series(dates_closes: list[tuple[str, float]]) -> pd.DataFrame:
    dates = [d for d, _ in dates_closes]
    closes = [c for _, c in dates_closes]
    df = pd.DataFrame({"A": closes}, index=dates)
    return df.pct_change().iloc[1:]


def test_stress_replay_2022_rate_shock_window():
    dates_closes = [
        ("2022-01-03", 100.0), ("2022-04-01", 90.0),
        ("2022-07-01", 80.0), ("2022-10-14", 70.0), ("2023-01-01", 90.0),
    ]
    returns = _build_return_series(dates_closes)
    result = compute_stress_replay(returns, {"A": 1.0}, benchmark="SPY")

    shock = next(r for r in result if r["scenario"] == "2022_rate_shock")
    assert shock["window"] == ["2022-01-03", "2022-10-14"]
    assert shock["portfolioReturnPct"] == pytest.approx((70.0 / 100.0 - 1) * 100)


def test_stress_replay_worst_drawdown_finds_largest_decline():
    dates_closes = [
        ("2021-01-01", 100.0), ("2021-06-01", 120.0),   # peak
        ("2021-12-01", 60.0),                            # big trough (-50%)
        ("2022-06-01", 100.0), ("2022-10-14", 95.0),     # smaller decline inside named window
        ("2023-01-01", 110.0),
    ]
    returns = _build_return_series(dates_closes)
    result = compute_stress_replay(returns, {"A": 1.0}, benchmark="SPY")

    drawdown = next(r for r in result if r["scenario"] == "worst_drawdown")
    assert drawdown["window"] == ["2021-06-01", "2021-12-01"]
    assert drawdown["portfolioReturnPct"] == pytest.approx((60.0 / 120.0 - 1) * 100)


def test_stress_replay_omits_2022_scenario_when_data_doesnt_cover_it():
    dates_closes = [("2024-01-01", 100.0), ("2024-06-01", 110.0), ("2024-12-01", 105.0)]
    returns = _build_return_series(dates_closes)
    result = compute_stress_replay(returns, {"A": 1.0}, benchmark="SPY")
    assert not any(r["scenario"] == "2022_rate_shock" for r in result)
    assert any(r["scenario"] == "worst_drawdown" for r in result)


def test_stress_replay_empty_for_no_qualifying_holdings():
    returns = pd.DataFrame({"SPY": [0.01, -0.02, 0.03]})
    assert compute_stress_replay(returns, {"A": 1.0}, benchmark="SPY") == []
