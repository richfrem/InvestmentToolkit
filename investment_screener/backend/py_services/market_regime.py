#!/usr/bin/env python3
"""
market_regime.py (Python Service)
=====================================

Purpose:
    4-tier market regime classifier (RISK_ON/NEUTRAL/RISK_OFF/STRESS) that
    wraps macro_regime.py's existing 3-signal composite (VIX, SPY vs 200d,
    HYG/LQD credit) and adds term-slope (IEF/SHY), breadth (% of active
    portfolio holdings above their own 200d SMA), and USD strength (UUP vs
    its own 200d) — 6 signals total. Also produces a per-ticker regime
    layer (trend, momentum percentile, volatility percentile) for every
    active holding. Informational only — does not gate any action. See
    docs/superpowers/specs/2026-07-06-market-regime-classifier-design.md.

    macro_regime.py is never modified; this module imports and reuses its
    classifiers directly rather than duplicating them.

Layer: Backend / Python Services / Regime

Usage:
    python3 market_regime.py --pretty
    python3 market_regime.py --no-save --pretty
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
TARGET_PATH = DATA_DIR / "theses/target-portfolio.json"
MARKET_REGIME_PATH = DATA_DIR / "market_regime.json"

INACTIVE_ROLES = {"exit", "avoid"}


def _classify_term_slope(ratio: float) -> tuple[str, int]:
    """Classify the IEF/SHY (10yr/1-3yr Treasury ETF) price ratio trend.

    A rising ratio means long-duration bonds are outperforming short-duration
    ones — the curve is steepening. A falling ratio means the opposite —
    flattening or inverting, a classic recession-risk tell. Same ETF-ratio
    pattern as macro_regime.py's existing HYG/LQD credit proxy.

    Args:
        ratio: IEF close / SHY close.

    Returns:
        Tuple of (signal_label, score_pts).
    """
    if ratio > 1.02:
        return "STEEPENING", 1
    if ratio >= 0.98:
        return "NEUTRAL", 0
    return "FLATTENING", -1


def _classify_breadth(pct: float) -> tuple[str, int]:
    """Classify the % of active portfolio holdings trading above their own 200d SMA.

    Args:
        pct: Percentage (0-100) of active holdings above their own 200d SMA.

    Returns:
        Tuple of (signal_label, score_pts).
    """
    if pct > 60:
        return "HEALTHY", 1
    if pct >= 40:
        return "NEUTRAL", 0
    return "WEAK", -1


def _classify_dxy(pct_vs_200d: float) -> tuple[str, int]:
    """Classify USD strength (UUP vs its own 200d SMA).

    A strong, rising dollar is a risk-off tell for this portfolio's
    international and rate-sensitive names — mirrors _classify_spy's
    ABOVE/NEAR/BELOW shape but the same direction (ABOVE = risk-on points),
    since dollar strength here is being used as one input among six, not
    as a standalone directional call.

    Args:
        pct_vs_200d: Percentage UUP is above (positive) or below (negative)
            its 200D SMA.

    Returns:
        Tuple of (signal_label, score_pts).
    """
    if pct_vs_200d > 2:
        return "ABOVE", 1
    if pct_vs_200d > -2:
        return "NEAR", 0
    return "BELOW", -1


def _classify_regime_v2(score: int, unavailable: int) -> tuple[str, bool]:
    """Map the 6-signal composite score to a 4-tier regime, with a
    degraded-data fail-safe stricter than macro_regime.py's 3-signal version.

    With 3+ of 6 signals unavailable, half the classifier's inputs are dark —
    forced STRESS (the most severe tier) rather than the fail-safe RISK-OFF
    macro_regime.py uses for its 2-of-3 threshold, since STRESS is now the
    floor and losing half the inputs deserves the harshest label, not a
    milder one.

    Args:
        score: Sum of all 6 signals' point contributions.
        unavailable: How many of the 6 component signals failed to fetch.

    Returns:
        Tuple of (regime_label, degraded_flag).
    """
    if unavailable >= 3:
        return "STRESS", True
    if score >= 3:
        return "RISK_ON", False
    if score >= 0:
        return "NEUTRAL", False
    if score >= -3:
        return "RISK_OFF", False
    return "STRESS", False


def _load_active_tickers(target_portfolio_path: Path) -> list[str]:
    """Read target-portfolio.json and return active-holding tickers.

    Active = role not in INACTIVE_ROLES ({"exit", "avoid"}) — the real role
    enum values validated by update_thesis.py. Not portfolio_io.load_portfolio_state():
    that loader reads portfolio.json (broker shares/prices) and has no role field.

    Args:
        target_portfolio_path: Path to target-portfolio.json.

    Returns:
        List of ticker strings (uses the "ticker" key, never "symbol" —
        CLAUDE.md rule 10).
    """
    data = json.loads(Path(target_portfolio_path).read_text())
    return [
        h["ticker"] for h in data.get("holdings", [])
        if h.get("role") not in INACTIVE_ROLES
    ]


def _sma(closes: pd.Series, period: int) -> pd.Series:
    """Simple moving average, full series (not just the latest value).

    Args:
        closes: Close prices, oldest first.
        period: SMA window length.

    Returns:
        A pandas Series of the same length as `closes`, with NaN for the
        first `period - 1` bars (insufficient data to seed the average).
    """
    return closes.rolling(window=period).mean()


def compute_breadth(prices_by_ticker: dict[str, dict]) -> tuple[float | None, list[str]]:
    """% of tickers whose latest close is above their own 200d SMA.

    Args:
        prices_by_ticker: market_data.get_prices() output, {ticker: {"data": [...]}}.

    Returns:
        (breadth_pct, excluded_tickers) — breadth_pct is None if no ticker
        has enough history (200+ rows) to compute a 200d SMA. Excluded
        tickers are never zero-filled into the denominator.
    """
    above = 0
    eligible = 0
    excluded: list[str] = []
    for ticker, payload in prices_by_ticker.items():
        rows = payload.get("data", [])
        if len(rows) < 200:
            excluded.append(ticker)
            continue
        closes = pd.DataFrame(rows)["close"]
        sma200 = _sma(closes, 200).iloc[-1]
        eligible += 1
        if closes.iloc[-1] > sma200:
            above += 1

    if eligible == 0:
        return None, excluded
    return round(above / eligible * 100, 2), excluded


def classify_ticker_trend(closes: pd.Series) -> dict[str, str] | None:
    """Classify a ticker's trend: position vs. its 200d SMA, and that SMA's
    own rising/falling slope over the trailing 20 days.

    Combines into 4 states: UPTREND (above + rising), DOWNTREND (below +
    falling), WEAKENING (above + falling — losing momentum but not yet
    broken down), BASING (below + rising — recovering but not yet reclaimed).

    Args:
        closes: Close prices, oldest first.

    Returns:
        {"position": "ABOVE"|"BELOW", "slope": "RISING"|"FALLING",
        "state": "UPTREND"|"DOWNTREND"|"WEAKENING"|"BASING"}, or None if
        fewer than 220 bars (200 for the SMA + 20 for the slope lookback).
    """
    if len(closes) < 220:
        return None

    sma200 = _sma(closes, 200)
    position = "ABOVE" if closes.iloc[-1] > sma200.iloc[-1] else "BELOW"
    slope = "RISING" if sma200.iloc[-1] > sma200.iloc[-21] else "FALLING"

    state = {
        ("ABOVE", "RISING"): "UPTREND",
        ("ABOVE", "FALLING"): "WEAKENING",
        ("BELOW", "RISING"): "BASING",
        ("BELOW", "FALLING"): "DOWNTREND",
    }[(position, slope)]

    return {"position": position, "slope": slope, "state": state}


def compute_momentum_percentile(closes: pd.Series) -> float | None:
    """12-1 month momentum (skip the most recent month, standard momentum
    convention), ranked as a percentile against that same metric computed at
    every trading day in the ticker's own history.

    momentum_t = close[t-21] / close[t-252] - 1, for every t where both
    indices exist. The current (last) momentum reading is ranked against
    the full historical distribution of that same rolling metric — i.e.
    "is today's 12-1M return stronger than X% of this ticker's own past
    12-1M readings."

    Args:
        closes: Close prices, oldest first.

    Returns:
        Percentile (0-100) of the latest momentum reading vs. its own
        history, or None if fewer than 274 bars (252 + 21 + 1) are
        available to compute at least one momentum value.
    """
    if len(closes) < 252 + 21 + 1:
        return None

    momentum = closes.shift(21) / closes.shift(252) - 1
    momentum = momentum.dropna()
    if momentum.empty:
        return None

    current = momentum.iloc[-1]
    percentile = (momentum <= current).sum() / len(momentum) * 100
    return round(float(percentile), 2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Market regime classifier")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Print only, skip writing market_regime.json")
    args = parser.parse_args()
    print("market_regime.py: orchestrator not yet implemented (see Task 6)", file=sys.stderr)


if __name__ == "__main__":
    main()
