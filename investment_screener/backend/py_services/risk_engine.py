#!/usr/bin/env python3
"""
risk_engine.py - Python utility script.

Purpose:
    Portfolio-level risk snapshot: correlation matrix, annualized volatility
    and beta (current actual weights), marginal risk contribution per
    holding, concentration (HHI/top-3/effective N), pillar-level cluster
    exposure, historical stress replay (2022 rate shock + worst drawdown),
    and parametric + historical VaR/CVaR (95%/99%, 1-day horizon, labeled
    as estimates). Informational only — does not gate any action. See
    docs/superpowers/specs/2026-07-05-risk-engine-design.md.

Layer:
    Backend / Python Services

Usage Examples:
    python3 risk_engine.py --pretty
    python3 risk_engine.py --benchmark SPY --no-save --pretty

Key Functions (Index):
    - _normalize_weights()
    - build_returns_matrix()
    - compute_correlation_matrix()
    - _weighted_portfolio_returns()
    - compute_portfolio_vol_beta()
    - compute_marginal_risk_contribution()
    - compute_concentration()
    - compute_cluster_exposure()
    - compute_stress_replay()
    - _normal_pdf()
    - compute_var_cvar()
    - compute_risk_snapshot()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
import argparse
import json
import math
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from market_data import get_prices  # noqa: E402
from portfolio_io import load_portfolio_state, compute_weights  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
TARGET_PATH = DATA_DIR / "theses/target-portfolio.json"
PORTFOLIO_PATH = DATA_DIR / "portfolio.json"
RISK_SNAPSHOT_PATH = DATA_DIR / "risk_snapshot.json"

MIN_HISTORY_DAYS = 60
Z_SCORES = {0.95: 1.645, 0.99: 2.326}
STRESS_WINDOWS = {"2022_rate_shock": ("2022-01-03", "2022-10-14")}


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Renormalize a weight subset to sum to 1.0.

    Used whenever a calc operates on a subset of holdings (e.g. after
    excluding tickers with insufficient price history) so the remaining
    weights still sum to 1.0 rather than silently understating exposure.

    Args:
        weights: {ticker: weight_fraction}, need not sum to 1.0.

    Returns:
        {ticker: weight_fraction} summing to 1.0, or {} if input is empty
        or sums to <= 0.
    """
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {t: w / total for t, w in weights.items()}


def build_returns_matrix(
    prices: dict[str, dict], min_days: int = MIN_HISTORY_DAYS
) -> tuple[pd.DataFrame, list[str]]:
    """Build a date-aligned daily-return matrix from get_prices() output.

    Tickers with fewer than `min_days` price rows are excluded before
    alignment — a single short-history ticker (recent IPO, delisted) must
    never collapse everyone else's sample window down to its own. Excluded
    tickers are returned separately so callers can surface a warning rather
    than silently shrinking the window.

    Args:
        prices: get_prices() output, {ticker: {"data": [...]}}.
        min_days: Minimum row count to include a ticker.

    Returns:
        (returns_df, excluded_tickers) — returns_df has dates (ISO strings,
        sorted) as index, tickers as columns, no NaN values (inner join
        across included tickers' dates); empty DataFrame if fewer than 2
        tickers have enough history to align.
    """
    closes: dict[str, pd.Series] = {}
    excluded: list[str] = []
    for ticker, payload in prices.items():
        rows = payload.get("data", [])
        if len(rows) < min_days:
            excluded.append(ticker)
            continue
        df = pd.DataFrame(rows)[["date", "close"]].set_index("date")
        closes[ticker] = df["close"]

    if len(closes) < 2:
        return pd.DataFrame(), excluded

    combined = pd.DataFrame(closes).sort_index().dropna(how="any")
    returns = combined.pct_change().iloc[1:]
    return returns, excluded


def compute_correlation_matrix(returns: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Ticker x ticker Pearson correlation of daily returns.

    Args:
        returns: Aligned daily-return DataFrame from build_returns_matrix().

    Returns:
        {ticker: {other_ticker: correlation}} excluding the diagonal (a
        ticker is never listed against itself); {} if fewer than 2 tickers.
    """
    if returns.shape[1] < 2:
        return {}
    corr = returns.corr()
    return {
        t: {u: round(float(corr.loc[t, u]), 4) for u in corr.columns if u != t}
        for t in corr.index
    }


def _weighted_portfolio_returns(
    returns: pd.DataFrame, weights: dict[str, float], exclude: set[str] | None = None
) -> pd.Series:
    """Build the weighted daily portfolio-return series from a returns matrix.

    Args:
        returns: Aligned daily-return DataFrame (may include a benchmark column).
        weights: {ticker: weight_fraction}, need not sum to 1.0 or cover
            every column in `returns` — only tickers present in both
            `returns.columns` and `weights` (minus `exclude`) contribute.
        exclude: Column names to never treat as holdings (e.g. the benchmark).

    Returns:
        A pandas Series of weighted daily returns, empty if no ticker qualifies.
    """
    exclude = exclude or set()
    tickers = [t for t in returns.columns if t in weights and t not in exclude]
    if not tickers:
        return pd.Series(dtype=float)
    normalized = _normalize_weights({t: weights[t] for t in tickers})
    if not normalized:
        return pd.Series(dtype=float)
    return sum(returns[t] * w for t, w in normalized.items())


def compute_portfolio_vol_beta(
    returns: pd.DataFrame, weights: dict[str, float], benchmark: str
) -> dict[str, float | None]:
    """Annualized portfolio volatility and beta vs. the benchmark.

    Args:
        returns: Aligned daily-return DataFrame, must include `benchmark`'s column.
        weights: {ticker: weight_fraction} for holdings (benchmark excluded automatically).
        benchmark: Benchmark ticker column name (e.g. "SPY").

    Returns:
        {"vol": annualized_stdev_or_None, "beta": beta_or_None}. None for
        either field if the benchmark is missing or fewer than 2 return
        observations are available.
    """
    portfolio_returns = _weighted_portfolio_returns(returns, weights, exclude={benchmark})
    if portfolio_returns.empty or benchmark not in returns.columns or len(portfolio_returns) < 2:
        return {"vol": None, "beta": None}

    vol = float(portfolio_returns.std(ddof=1) * (252 ** 0.5))
    bench_returns = returns[benchmark]
    bench_var = float(bench_returns.var(ddof=1))
    covariance = float(portfolio_returns.cov(bench_returns))
    beta = covariance / bench_var if bench_var > 0 else None

    return {
        "vol": round(vol, 4),
        "beta": round(beta, 3) if beta is not None else None,
    }


def compute_marginal_risk_contribution(
    returns: pd.DataFrame, weights: dict[str, float], benchmark: str
) -> dict[str, float]:
    """Fraction of total portfolio variance contributed by each holding.

    MRC_i = w_i * (Sigma . w)_i / portfolio_variance, so the returned
    values always sum to 1.0 across included holdings (100% of variance
    decomposed) — this is the property that makes "MRC leader: NVDA 18%"
    a meaningful sentence rather than an arbitrary score.

    Args:
        returns: Aligned daily-return DataFrame, may include a benchmark column.
        weights: {ticker: weight_fraction}.
        benchmark: Benchmark column name to exclude from the holdings set.

    Returns:
        {ticker: fraction_of_variance}, {} if fewer than 2 holdings qualify
        or portfolio variance is 0.
    """
    tickers = [t for t in returns.columns if t in weights and t != benchmark]
    if len(tickers) < 2:
        return {}
    normalized = _normalize_weights({t: weights[t] for t in tickers})
    if not normalized:
        return {}

    cov_matrix = returns[tickers].cov() * 252  # annualize
    w = pd.Series(normalized).reindex(tickers)
    portfolio_variance = float(w @ cov_matrix @ w)
    if portfolio_variance <= 0:
        return {}

    marginal = cov_matrix @ w  # per-ticker (Sigma . w)
    contribution = (w * marginal) / portfolio_variance
    return {t: round(float(contribution[t]), 4) for t in tickers}


def compute_concentration(weights: dict[str, float]) -> dict[str, float | None]:
    """Herfindahl-Hirschman Index, top-3 weight, and effective N.

    Args:
        weights: {ticker: weight_fraction}, need not sum to 1.0 (renormalized
            internally so a partial/excluded-tickers input is still meaningful).

    Returns:
        {"hhi", "top3Weight", "effectiveN"} — all None if weights is empty
        or sums to <= 0.
    """
    normalized = _normalize_weights(weights)
    if not normalized:
        return {"hhi": None, "top3Weight": None, "effectiveN": None}

    values = sorted(normalized.values(), reverse=True)
    hhi = sum(w * w for w in values)
    top3 = sum(values[:3])
    effective_n = 1 / hhi if hhi > 0 else None

    return {
        "hhi": round(hhi, 4),
        "top3Weight": round(top3, 4),
        "effectiveN": round(effective_n, 2) if effective_n is not None else None,
    }


def compute_cluster_exposure(
    weights: dict[str, float], pillar_map: dict[str, str], mrc: dict[str, float]
) -> list[dict[str, Any]]:
    """Pillar-level weight and variance-contribution exposure.

    Groups holdings by their existing target-portfolio.json `pillarId` (the
    curated taxonomy, not a correlation-derived cluster) and sums weight and
    marginal-risk-contribution within each pillar. Produces the "72% of
    portfolio variance from one cluster" sentence.

    Args:
        weights: {ticker: weight_fraction}, need not sum to 1.0.
        pillar_map: {ticker: pillarId}, from target-portfolio.json holdings.
        mrc: Output of compute_marginal_risk_contribution() — {ticker: fraction}.

    Returns:
        List of {"pillarId", "weight", "varianceContributionPct"}, sorted by
        weight descending. A ticker with no pillarId entry is grouped under
        "unassigned". Weight is renormalized over the supplied weights dict.
    """
    normalized = _normalize_weights(weights)
    if not normalized:
        return []

    pillar_weight: dict[str, float] = {}
    pillar_mrc: dict[str, float] = {}
    for ticker, weight in normalized.items():
        pillar = pillar_map.get(ticker, "unassigned")
        pillar_weight[pillar] = pillar_weight.get(pillar, 0.0) + weight
        pillar_mrc[pillar] = pillar_mrc.get(pillar, 0.0) + mrc.get(ticker, 0.0)

    result = [
        {
            "pillarId": pillar,
            "weight": round(pillar_weight[pillar], 4),
            "varianceContributionPct": round(pillar_mrc[pillar] * 100, 2),
        }
        for pillar in pillar_weight
    ]
    return sorted(result, key=lambda r: r["weight"], reverse=True)


def compute_stress_replay(
    returns_5y: pd.DataFrame, weights: dict[str, float], benchmark: str = "SPY"
) -> list[dict[str, Any]]:
    """Portfolio P&L through the 2022 rate-shock window plus the worst
    drawdown found anywhere in the supplied 5-year return history.

    Current weights are held static across the whole replay window — a
    documented simplifying assumption (true historical weights aren't
    tracked anywhere in the system; see design doc). The worst-drawdown
    search is performed on the cumulative portfolio return series, which
    begins at day 1 (not day 0) because day 0 is dropped upstream when
    converting prices to daily returns (pct_change has no return for the
    baseline date). As a result, if the true worst peak occurs on day 0
    of the supplied returns window, the function will report a shallower
    drawdown magnitude than the true one. This is a known limitation; if
    systematic understatement is observed in production, check this
    constraint first.

    Args:
        returns_5y: Aligned daily-return DataFrame spanning ~5 years, must
            include `benchmark`'s column (excluded from holdings).
        weights: {ticker: weight_fraction} for current holdings.
        benchmark: Benchmark column name to exclude from holdings.

    Returns:
        List of scenario dicts: [{"scenario", "window": [start, end],
        "portfolioReturnPct"}, ...]. 2022_rate_shock is omitted entirely if
        the supplied data doesn't cover that window. worst_drawdown is
        omitted if the portfolio-return series is empty.
    """
    portfolio_returns = _weighted_portfolio_returns(returns_5y, weights, exclude={benchmark})
    if portfolio_returns.empty:
        return []

    results: list[dict[str, Any]] = []
    for scenario, (start, end) in STRESS_WINDOWS.items():
        window = portfolio_returns.loc[
            (portfolio_returns.index >= start) & (portfolio_returns.index <= end)
        ]
        if window.empty:
            continue
        window_cum = (1 + window).cumprod()
        pct_return = float((window_cum.iloc[-1] - 1) * 100)
        results.append({
            "scenario": scenario,
            "window": [start, end],
            "portfolioReturnPct": round(pct_return, 2),
        })

    cumulative = (1 + portfolio_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    trough_date = drawdown.idxmin()
    peak_date = cumulative.loc[:trough_date].idxmax()
    results.append({
        "scenario": "worst_drawdown",
        "window": [peak_date, trough_date],
        "portfolioReturnPct": round(float(drawdown.min() * 100), 2),
    })

    return results


def _normal_pdf(z: float) -> float:
    """Standard normal probability density at z (no scipy dependency — see
    design doc's documented simplification on avoiding a new dependency
    for two constants and one closed-form density).
    """
    return math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)


def compute_var_cvar(
    portfolio_returns: pd.Series, confidences: tuple[float, ...] = (0.95, 0.99)
) -> dict[str, dict[str, dict[str, float]]]:
    """Parametric and historical VaR/CVaR at the given confidence levels.

    Parametric assumes daily returns are normally distributed (mean, std of
    the supplied series); the expected-shortfall (CVaR) closed form is
    mean - std * (phi(z) / (1 - confidence)). Historical uses the empirical
    return distribution directly (no distributional assumption). Both are
    1-day-horizon figures — the caller (compute_risk_snapshot) is
    responsible for labeling them as estimates in the output, not this
    function, which has no opinion on presentation.

    Args:
        portfolio_returns: Daily weighted portfolio-return series (e.g.
            from _weighted_portfolio_returns()).
        confidences: Confidence levels to compute, e.g. (0.95, 0.99).

    Returns:
        {"var": {"parametric": {"p95": ..., "p99": ...}, "historical": {...}},
         "cvar": {"parametric": {...}, "historical": {...}}}. All values are
         negative-or-zero (a loss). Empty nested dicts if `portfolio_returns`
         has fewer than 2 observations.
    """
    empty = {
        "var": {"parametric": {}, "historical": {}},
        "cvar": {"parametric": {}, "historical": {}},
    }
    if len(portfolio_returns) < 2:
        return empty

    mean = float(portfolio_returns.mean())
    std = float(portfolio_returns.std(ddof=1))

    var_parametric: dict[str, float] = {}
    var_historical: dict[str, float] = {}
    cvar_parametric: dict[str, float] = {}
    cvar_historical: dict[str, float] = {}

    for c in confidences:
        key = f"p{int(c * 100)}"
        z = Z_SCORES[c]

        var_param = mean - z * std
        es_param = mean - std * (_normal_pdf(z) / (1 - c))
        var_parametric[key] = round(var_param, 4)
        cvar_parametric[key] = round(es_param, 4)

        var_hist = float(portfolio_returns.quantile(1 - c))
        tail = portfolio_returns[portfolio_returns <= var_hist]
        cvar_hist = float(tail.mean()) if not tail.empty else var_hist
        var_historical[key] = round(var_hist, 4)
        cvar_historical[key] = round(cvar_hist, 4)

    return {
        "var": {"parametric": var_parametric, "historical": var_historical},
        "cvar": {"parametric": cvar_parametric, "historical": cvar_historical},
    }


def compute_risk_snapshot(
    target_portfolio_path: Path = TARGET_PATH,
    portfolio_path: Path = PORTFOLIO_PATH,
    benchmark: str = "SPY",
) -> dict[str, Any]:
    """Primary orchestrator — builds the full portfolio risk snapshot.

    Loads current actual weights (never re-derived from raw shares x price
    — portfolio_io.compute_weights() against the broker-authoritative
    total), fetches 2y daily prices for correlation/vol/beta/MRC/VaR and a
    separate 5y fetch for stress replay (2y doesn't reach the 2022 rate-
    shock window), then assembles every compute_*() result into one dict.
    Does not write to disk — see main() for the CLI's --no-save-gated write.

    Args:
        target_portfolio_path: Path to target-portfolio.json (pillars/holdings).
        portfolio_path: Path to portfolio.json (actual broker state).
        benchmark: Benchmark ticker for beta/relative calcs.

    Returns:
        The full risk snapshot dict — see docs/superpowers/specs/
        2026-07-05-risk-engine-design.md for the field-by-field shape.
    """
    target_data = json.loads(Path(target_portfolio_path).read_text())
    pillar_map = {
        h["ticker"]: h.get("pillarId", "unassigned")
        for h in target_data.get("holdings", [])
    }

    state = load_portfolio_state(Path(portfolio_path))
    weights_pct = compute_weights(state["shares"], state["prices"], state["total_usd"])
    tickers = list(weights_pct.keys())
    weights_frac = {t: w / 100.0 for t, w in weights_pct.items()}

    warnings: list[str] = []

    prices_2y = get_prices(tickers + [benchmark], period="2y", interval="1d")
    returns_2y, excluded_2y = build_returns_matrix(prices_2y)
    for t in excluded_2y:
        if t != benchmark:
            warnings.append(f"{t} excluded from correlation/vol/beta/VaR: insufficient price history")

    prices_5y = get_prices(tickers + [benchmark], period="5y", interval="1d")
    returns_5y, excluded_5y = build_returns_matrix(prices_5y)
    for t in excluded_5y:
        if t != benchmark and t not in excluded_2y:
            warnings.append(f"{t} excluded from stress replay: insufficient price history")

    holdings_2y = [t for t in returns_2y.columns if t != benchmark]
    vol_beta = compute_portfolio_vol_beta(returns_2y, weights_frac, benchmark)
    correlation = (
        compute_correlation_matrix(returns_2y[holdings_2y]) if len(holdings_2y) >= 2 else {}
    )
    mrc = compute_marginal_risk_contribution(returns_2y, weights_frac, benchmark)
    weights_2y = {t: weights_frac[t] for t in holdings_2y if t in weights_frac}
    concentration = compute_concentration(weights_2y)
    # Filtered to weights_2y, not the full weights_frac — a ticker excluded from
    # returns_2y (insufficient history) has no mrc entry; passing the unfiltered
    # weights here would keep its full weight in a pillar's "weight" figure while
    # mrc.get() silently zeroes its variance contribution, understating cluster
    # risk (the exact thing this feature exists to surface). Same exclusion set
    # as concentration keeps both figures computed over the same ticker basis.
    cluster = compute_cluster_exposure(weights_2y, pillar_map, mrc)
    stress = compute_stress_replay(returns_5y, weights_frac, benchmark)

    portfolio_returns_2y = _weighted_portfolio_returns(returns_2y, weights_frac, exclude={benchmark})
    var_cvar = compute_var_cvar(portfolio_returns_2y)

    return {
        "asOf": date.today().isoformat(),
        "benchmark": benchmark,
        "portfolioVol": vol_beta["vol"],
        "portfolioBeta": vol_beta["beta"],
        "correlationMatrix": correlation,
        "marginalRiskContribution": mrc,
        "concentration": concentration,
        "clusterExposure": cluster,
        "stressReplay": stress,
        "var": {**var_cvar["var"], "horizonDays": 1, "estimate": True},
        "cvar": {**var_cvar["cvar"], "estimate": True},
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio risk snapshot")
    parser.add_argument("--benchmark", default="SPY")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Print only, skip writing risk_snapshot.json")
    args = parser.parse_args()

    snapshot = compute_risk_snapshot(benchmark=args.benchmark)
    if not args.no_save:
        RISK_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RISK_SNAPSHOT_PATH, "w") as f:
            json.dump(snapshot, f, indent=2)

    print(json.dumps(snapshot, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
