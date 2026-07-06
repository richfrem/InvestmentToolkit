#!/usr/bin/env python3
"""
risk_engine.py (Python Service)
=====================================

Purpose:
    Portfolio-level risk snapshot: correlation matrix, annualized volatility
    and beta (current actual weights), marginal risk contribution per
    holding, concentration (HHI/top-3/effective N), pillar-level cluster
    exposure, historical stress replay (2022 rate shock + worst drawdown),
    and parametric + historical VaR/CVaR (95%/99%, 1-day horizon, labeled
    as estimates). Informational only — does not gate any action. See
    docs/superpowers/specs/2026-07-05-risk-engine-design.md.

Layer: Backend / Python Services / Risk

Usage:
    python3 risk_engine.py --pretty
    python3 risk_engine.py --benchmark SPY --no-save --pretty
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

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
