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


def test_stress_replay_day0_peak_limitation():
    """Documents a known limitation: worst-drawdown search cannot detect a peak
    on day 0 of the returns window because day 0 is dropped upstream as the
    pct_change() baseline (no return can be computed relative to itself).

    For a synthetic 4-price series [100, 90, 95, 80], the mathematically true
    worst drawdown is day0(100)->day3(80) = -20.00%. However, because day 0
    cannot be observed in the cumulative return series (it's the baseline), the
    function observes the peak at day2(95)->day3(80) = -15.79%. This limitation
    only manifests when the true worst peak occurs on day 0 specifically. This
    test pins that behavior so future regressions are caught.
    """
    # Prices: [100, 90, 95, 80]
    # Returns (pct_change): [-0.10, 0.0556, -0.1579]
    # Cumulative: [0.90, 0.9501, 0.8001]
    # The cumulative series starts from index 1 (day 1), missing the day 0 peak.
    # Running max: [0.90, 0.9501, 0.9501]
    # Min drawdown is at index 2, with peak at index 1 (2026-01-03, price 95)
    dates_closes = [
        ("2026-01-01", 100.0),  # Day 0 (true peak, but invisible to drawdown search)
        ("2026-01-02", 90.0),   # Day 1
        ("2026-01-03", 95.0),   # Day 2 (observed peak in cumulative series)
        ("2026-01-04", 80.0),   # Day 3 (trough)
    ]
    returns = _build_return_series(dates_closes)
    result = compute_stress_replay(returns, {"A": 1.0}, benchmark="SPY")

    drawdown = next(r for r in result if r["scenario"] == "worst_drawdown")
    # The function reports day2->day3 drawdown, not the true day0->day3
    assert drawdown["window"] == ["2026-01-03", "2026-01-04"]
    # (80/95 - 1) * 100 ≈ -15.79%, NOT the true -20%
    assert drawdown["portfolioReturnPct"] == pytest.approx(-15.79, abs=0.01)


from risk_engine import compute_var_cvar  # noqa: E402

_SAMPLE_RETURNS = [
    0.02, -0.03, 0.01, -0.05, 0.015, -0.01, 0.03, -0.02, 0.005, -0.04,
    0.01, -0.015, 0.025, -0.01, 0.005, -0.03, 0.02, -0.005, 0.01, -0.02,
]


def test_var_cvar_cvar_worse_than_var_property():
    result = compute_var_cvar(pd.Series(_SAMPLE_RETURNS))
    for method in ("parametric", "historical"):
        for level in ("p95", "p99"):
            assert result["cvar"][method][level] <= result["var"][method][level]


def test_var_cvar_p99_more_extreme_than_p95():
    result = compute_var_cvar(pd.Series(_SAMPLE_RETURNS))
    assert result["var"]["parametric"]["p99"] <= result["var"]["parametric"]["p95"]
    assert result["var"]["historical"]["p99"] <= result["var"]["historical"]["p95"]


def test_var_cvar_historical_matches_quantile_definition():
    portfolio_returns = pd.Series([
        0.05, 0.03, 0.01, -0.01, -0.03, -0.05, 0.02, -0.02, 0.04, -0.04,
        0.0, 0.015, -0.015, 0.025, -0.025, 0.035, -0.035, 0.045, -0.045, 0.005,
    ])
    result = compute_var_cvar(portfolio_returns)
    expected_p95 = round(float(portfolio_returns.quantile(0.05)), 4)
    assert result["var"]["historical"]["p95"] == pytest.approx(expected_p95)


def test_var_cvar_empty_for_insufficient_data():
    result = compute_var_cvar(pd.Series([0.01]))
    assert result["var"]["parametric"] == {}
    assert result["var"]["historical"] == {}
    assert result["cvar"]["parametric"] == {}
    assert result["cvar"]["historical"] == {}


# ── compute_risk_snapshot (orchestrator) ──────────────────────────────────────

import json
from unittest.mock import patch

from risk_engine import compute_risk_snapshot  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    update_investment_fields,
)
from domain_model.pillar_repository import resolve_pillar  # noqa: E402
import portfolio_io  # noqa: E402


def _seed_pillar_map(db_path: Path, holdings: list[dict]) -> None:
    """holdings: list of {"ticker": ..., "pillarId": ...} dicts, matching the
    real target-portfolio.json holding shape. compute_risk_snapshot() now
    reads pillar_id from domain_model.sqlite (Wave 2 consumer cutover)."""
    conn = initialize_db(str(db_path))
    for h in holdings:
        resolve_pillar(conn, h["pillarId"], h["pillarId"])
        investment_id = resolve_investment(conn, h["ticker"], asset_class="EQUITY", currency="USD")
        update_investment_fields(conn, investment_id, pillar_id=h["pillarId"])
    conn.close()


def _write_portfolio(path: Path, shares: dict, prices: dict, total_usd: float) -> None:
    payload = {
        "holdings": [{"ticker": t, "shares": q, "price": prices[t]} for t, q in shares.items()],
        "totals": {"totalUSD": total_usd},
    }
    path.write_text(json.dumps(payload))


def _seed_positions(db_path: Path, shares: dict, prices: dict) -> None:
    """Seed SQLite-backed portfolio positions matching a shares/prices map into
    domain_model.sqlite -- the real source load_portfolio_state() reads
    post-Wave-3 (see test_portfolio_io.py's _build_test_db for the same
    pattern). Replaces the old portfolio.json "holdings"/"totals" fixture for
    computing actual weights; _write_portfolio()'s JSON file is now unused by
    compute_risk_snapshot() but kept as the portfolio_path argument for call-
    site compatibility.
    """
    from domain_model.account_repository import upsert_account
    from domain_model.investment_price_repository import upsert_investment_price
    from domain_model.account_investment_repository import upsert_account_investment

    conn = initialize_db(str(db_path))
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    for ticker, qty in shares.items():
        price = prices[ticker]
        inv_id = resolve_investment(conn, ticker, asset_class="EQUITY", currency="USD")
        upsert_investment_price(conn, inv_id, price=price, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_account_investment(
            conn, "TFSA", inv_id, quantity=qty, average_cost=price,
            book_value=qty * price, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
    conn.close()


def _bdate_rows(n: int, start_price: float, drift: float) -> list[dict]:
    dates = pd.bdate_range("2024-01-01", periods=n)
    return [
        {"date": d.strftime("%Y-%m-%d"), "open": start_price + drift * i,
         "high": start_price + drift * i, "low": start_price + drift * i,
         "close": start_price + drift * i, "volume": 1000.0}
        for i, d in enumerate(dates)
    ]


def test_compute_risk_snapshot_full_shape(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    portfolio_path = tmp_path / "portfolio.json"
    _seed_pillar_map(db_path, [
        {"ticker": "NVDA", "pillarId": "ai_infra"},
        {"ticker": "PANW", "pillarId": "cyber"},
    ])
    _write_portfolio(
        portfolio_path,
        shares={"NVDA": 10.0, "PANW": 20.0},
        prices={"NVDA": 100.0, "PANW": 50.0},
        total_usd=2000.0,
    )
    _seed_positions(db_path, shares={"NVDA": 10.0, "PANW": 20.0}, prices={"NVDA": 100.0, "PANW": 50.0})
    monkeypatch.setattr(portfolio_io, "_DB_PATH", str(db_path))

    nvda_rows = _bdate_rows(120, 100.0, 0.1)
    panw_rows = _bdate_rows(120, 50.0, 0.05)
    spy_rows = _bdate_rows(120, 400.0, 0.2)

    def fake_get_prices(tickers, period, interval="1d"):
        data = {"NVDA": nvda_rows, "PANW": panw_rows, "SPY": spy_rows}
        return {t: {"data": data[t]} for t in tickers if t in data}

    with patch("risk_engine.get_prices", side_effect=fake_get_prices):
        snapshot = compute_risk_snapshot(
            db_path=db_path, portfolio_path=portfolio_path, benchmark="SPY",
        )

    expected_keys = {
        "asOf", "benchmark", "portfolioVol", "portfolioBeta", "correlationMatrix",
        "marginalRiskContribution", "concentration", "clusterExposure",
        "stressReplay", "var", "cvar", "warnings",
    }
    assert expected_keys <= set(snapshot.keys())
    assert snapshot["benchmark"] == "SPY"
    assert snapshot["portfolioVol"] is not None
    assert snapshot["portfolioBeta"] is not None
    assert set(snapshot["marginalRiskContribution"].keys()) == {"NVDA", "PANW"}
    assert snapshot["var"]["estimate"] is True
    assert snapshot["var"]["horizonDays"] == 1
    assert snapshot["cvar"]["estimate"] is True
    assert snapshot["warnings"] == []


def test_compute_risk_snapshot_excludes_short_history_ticker_with_warning(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    portfolio_path = tmp_path / "portfolio.json"
    _seed_pillar_map(db_path, [
        {"ticker": "NVDA", "pillarId": "ai_infra"},
        {"ticker": "CBRS", "pillarId": "power"},
    ])
    _write_portfolio(
        portfolio_path,
        shares={"NVDA": 10.0, "CBRS": 3.0},
        prices={"NVDA": 100.0, "CBRS": 200.0},
        total_usd=1600.0,
    )
    _seed_positions(db_path, shares={"NVDA": 10.0, "CBRS": 3.0}, prices={"NVDA": 100.0, "CBRS": 200.0})
    monkeypatch.setattr(portfolio_io, "_DB_PATH", str(db_path))

    nvda_rows = _bdate_rows(120, 100.0, 0.1)
    cbrs_rows = _bdate_rows(10, 200.0, 0.0)  # too short — below MIN_HISTORY_DAYS
    spy_rows = _bdate_rows(120, 400.0, 0.2)

    def fake_get_prices(tickers, period, interval="1d"):
        data = {"NVDA": nvda_rows, "CBRS": cbrs_rows, "SPY": spy_rows}
        return {t: {"data": data[t]} for t in tickers if t in data}

    with patch("risk_engine.get_prices", side_effect=fake_get_prices):
        snapshot = compute_risk_snapshot(
            db_path=db_path, portfolio_path=portfolio_path, benchmark="SPY",
        )

    assert any("CBRS" in w for w in snapshot["warnings"])
    assert "CBRS" not in snapshot["marginalRiskContribution"]
    # CBRS's pillar ("power") must not appear at all — cluster exposure is built
    # from the same mrc-eligible ticker set as concentration, so an excluded
    # ticker's weight never leaks into a pillar figure it has no mrc data for.
    cluster_pillars = {c["pillarId"] for c in snapshot["clusterExposure"]}
    assert "power" not in cluster_pillars
    ai_infra = next(c for c in snapshot["clusterExposure"] if c["pillarId"] == "ai_infra")
    assert ai_infra["weight"] == pytest.approx(1.0)  # NVDA is the only mrc-eligible holding
