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
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))

from market_data import get_prices  # noqa: E402
from macro_regime import (  # noqa: E402
    get_macro_regime, _classify_vix, _classify_spy, _classify_credit,
)
from technicals import _true_range, _wilder_smooth  # noqa: E402

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


def compute_volatility_percentile(
    highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14
) -> float | None:
    """ATR% (ATR / close) at every day in the supplied history, current
    value ranked as a percentile against that same-ticker history.

    technicals.py's compute_atr() only returns the latest scalar value, so
    this reuses its internal _true_range/_wilder_smooth series helpers
    directly (not duplicated) to build the full ATR series first.

    Args:
        highs: High prices, oldest first.
        lows: Low prices, oldest first.
        closes: Close prices, oldest first.
        period: ATR lookback period, default 14 (matches technicals.py).

    Returns:
        Percentile (0-100) of the latest ATR% reading vs. its own history,
        or None if fewer than period+2 bars are available.
    """
    if len(closes) < period + 2:
        return None

    tr = _true_range(highs, lows, closes).dropna()
    atr_series = _wilder_smooth(tr, period).dropna()
    if atr_series.empty:
        return None

    atr_pct = atr_series / closes.loc[atr_series.index]
    current = atr_pct.iloc[-1]
    percentile = (atr_pct <= current).sum() / len(atr_pct) * 100
    return round(float(percentile), 2)


def _fetch_ratio(numerator: str, denominator: str) -> float | None:
    """Fetch two tickers' latest closes and return numerator/denominator.

    Used for the IEF/SHY term-slope proxy — same ETF-ratio-via-yfinance
    pattern as macro_regime.py's HYG/LQD credit signal.

    Args:
        numerator: Ticker whose close is the ratio's numerator.
        denominator: Ticker whose close is the ratio's denominator.

    Returns:
        The ratio, or None if either fetch fails.
    """
    try:
        num_close = float(yf.Ticker(numerator).history(period="5d")["Close"].to_numpy()[-1])
        den_close = float(yf.Ticker(denominator).history(period="5d")["Close"].to_numpy()[-1])
        return num_close / den_close if den_close > 0 else None
    except Exception:
        return None


def _fetch_dxy_vs_200d(ticker: str = "UUP") -> float | None:
    """Fetch UUP's % distance above/below its own 200D SMA.

    Same pattern as macro_regime.py's SPY-vs-200d signal.

    Args:
        ticker: USD-strength proxy ETF ticker, default UUP.

    Returns:
        Percentage above (positive) or below (negative) the 200D SMA, or
        None if the fetch fails.
    """
    try:
        hist = yf.Ticker(ticker).history(period="1y")
        close = float(hist["Close"].to_numpy()[-1])
        sma_200 = float(hist["Close"].tail(200).mean().item())
        return (close - sma_200) / sma_200 * 100
    except Exception:
        return None


def compute_market_regime(target_portfolio_path: Path = TARGET_PATH) -> dict[str, Any]:
    """Primary orchestrator — 4-tier composite regime + per-ticker regime layer.

    Reuses macro_regime.get_macro_regime() for 3 of the 6 macro signals,
    fetches the 3 new ones (term-slope, breadth, DXY), classifies the
    composite regime, then classifies trend/momentum/volatility for every
    active holding. Does not write to disk itself — see main() for the
    CLI's --no-save-gated write, same convention as risk_engine.py's
    compute_risk_snapshot().

    Args:
        target_portfolio_path: Path to target-portfolio.json.

    Returns:
        Full market regime snapshot dict — see docs/superpowers/specs/
        2026-07-06-market-regime-classifier-design.md for the field-by-field shape.
    """
    macro = get_macro_regime()
    tickers = _load_active_tickers(target_portfolio_path)
    prices = get_prices(tickers, period="2y", interval="1d") if tickers else {}

    warnings: list[str] = []

    breadth_pct, breadth_excluded = compute_breadth(prices)
    for t in breadth_excluded:
        warnings.append(f"{t} excluded from breadth/trend: insufficient price history")

    term_slope_ratio = _fetch_ratio("IEF", "SHY")
    dxy_pct = _fetch_dxy_vs_200d()

    score = 0
    unavailable = 0
    signals: dict[str, Any] = {}

    # Re-invoke macro_regime.py's own classifiers on its raw values rather than
    # duplicating a second copy of their point tables — if macro_regime.py's
    # thresholds ever change, this stays in sync automatically. macro.vix_signal
    # (etc.) is still used for the UNAVAILABLE check, since a failed fetch
    # leaves the raw value at its harmless default (e.g. vix=20.0) rather than
    # None, and classifying that default would silently look like real data.
    if macro.vix_signal == "UNAVAILABLE":
        unavailable += 1
    else:
        _, vix_pts = _classify_vix(macro.vix)
        score += vix_pts
    if macro.spy_signal == "UNAVAILABLE":
        unavailable += 1
    else:
        _, spy_pts = _classify_spy(macro.spy_vs_200d)
        score += spy_pts
    if macro.credit_signal == "UNAVAILABLE":
        unavailable += 1
    else:
        _, credit_pts = _classify_credit(macro.hyg_lqd_ratio)
        score += credit_pts

    signals["vix"] = {"value": macro.vix, "signal": macro.vix_signal}
    signals["spy200d"] = {"value": macro.spy_vs_200d, "signal": macro.spy_signal}
    signals["credit"] = {"value": macro.hyg_lqd_ratio, "signal": macro.credit_signal}

    if term_slope_ratio is None:
        signals["termSlope"] = {"value": None, "signal": "UNAVAILABLE"}
        unavailable += 1
    else:
        term_signal, term_pts = _classify_term_slope(term_slope_ratio)
        signals["termSlope"] = {"value": round(term_slope_ratio, 4), "signal": term_signal}
        score += term_pts

    if breadth_pct is None:
        signals["breadth"] = {"value": None, "signal": "UNAVAILABLE"}
        unavailable += 1
    else:
        breadth_signal, breadth_pts = _classify_breadth(breadth_pct)
        signals["breadth"] = {"value": breadth_pct, "signal": breadth_signal}
        score += breadth_pts

    if dxy_pct is None:
        signals["dxy"] = {"value": None, "signal": "UNAVAILABLE"}
        unavailable += 1
    else:
        dxy_signal, dxy_pts = _classify_dxy(dxy_pct)
        signals["dxy"] = {"value": round(dxy_pct, 2), "signal": dxy_signal}
        score += dxy_pts

    regime, degraded = _classify_regime_v2(score, unavailable)

    ticker_regimes: list[dict[str, Any]] = []
    for ticker in tickers:
        rows = prices.get(ticker, {}).get("data", [])
        if not rows:
            ticker_regimes.append({
                "ticker": ticker, "trend": None,
                "momentumPercentile": None, "volatilityPercentile": None,
            })
            continue
        df = pd.DataFrame(rows)
        ticker_regimes.append({
            "ticker": ticker,
            "trend": classify_ticker_trend(df["close"]),
            "momentumPercentile": compute_momentum_percentile(df["close"]),
            "volatilityPercentile": compute_volatility_percentile(
                df["high"], df["low"], df["close"]
            ),
        })

    return {
        "asOf": date.today().isoformat(),
        "regime": regime,
        "score": score,
        "degraded": degraded,
        "signals": signals,
        "tickerRegimes": ticker_regimes,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Market regime classifier")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Print only, skip writing market_regime.json")
    args = parser.parse_args()

    snapshot = compute_market_regime()
    if not args.no_save:
        MARKET_REGIME_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MARKET_REGIME_PATH, "w") as f:
            json.dump(snapshot, f, indent=2)

    print(json.dumps(snapshot, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
