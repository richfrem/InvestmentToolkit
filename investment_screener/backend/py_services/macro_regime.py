#!/usr/bin/env python3
"""
macro_regime.py - Python utility script.

Purpose:
    Macro regime classifier — RISK-ON / NEUTRAL / RISK-OFF.

Fetches VIX, SPY, and HYG/LQD data via yfinance to classify the current
macro environment. Used as a hard gate in the daily brief to filter which
conviction signals are actionable.

Usage:
    python3 macro_regime.py
    python3 macro_regime.py --json

Key Input Dependencies:
    - investment_screener/backend/data/daily-briefs/ (Updates macroeconomic regime)

Layer:
    Backend / Python Services

Usage Examples:
    python3 macro_regime.py
    python3 macro_regime.py --json

Key Functions (Index):
    - MacroRegimeResult()
    - _classify_regime()
    - _classify_vix()
    - _classify_spy()
    - _classify_credit()
    - get_macro_regime()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass
class MacroRegimeResult:
    """Macro regime classification with component signals."""

    regime: str          # RISK-ON | NEUTRAL | RISK-OFF
    score: int           # positive = risk-on; negative = risk-off
    vix: float
    vix_signal: str      # LOW | NEUTRAL | ELEVATED | HIGH
    spy_vs_200d: float   # % SPY above/below its 200D SMA
    spy_signal: str      # ABOVE | NEAR | BELOW
    hyg_lqd_ratio: float | None
    credit_signal: str   # HEALTHY | NEUTRAL | STRESSED | UNAVAILABLE
    details: list[str]
    degraded: bool = False   # True when regime was forced RISK-OFF by missing data


def _classify_regime(score: int, unavailable: int) -> tuple[str, bool]:
    """Map composite score to regime, with a degraded-data fail-safe.

    The macro gate is the only systemic risk control in the daily loop, and
    yfinance outages cluster during volatility spikes — exactly when the gate
    matters. With 2+ of the 3 component signals unavailable, a score near 0 is
    ignorance, not neutrality: fail SAFE to RISK-OFF rather than open to
    NEUTRAL (which permits high-conviction ACCUMULATE actions).

    Args:
        score: Sum of component score contributions.
        unavailable: How many of the 3 component signals failed to fetch.

    Returns:
        Tuple of (regime_label, degraded_flag).
    """
    if unavailable >= 2:
        return "RISK-OFF", True
    if score >= 2:
        return "RISK-ON", False
    if score >= 0:
        return "NEUTRAL", False
    return "RISK-OFF", False


def _classify_vix(vix: float) -> tuple[str, int]:
    """Return VIX signal string and score contribution.

    Args:
        vix: Current VIX index value.

    Returns:
        Tuple of (signal_label, score_pts).
    """
    if vix < 16:
        return "LOW", +1
    if vix < 23:
        return "NEUTRAL", 0
    if vix < 30:
        return "ELEVATED", -1
    return "HIGH", -2


def _classify_spy(pct: float) -> tuple[str, int]:
    """Return SPY vs 200D signal string and score contribution.

    Args:
        pct: Percentage SPY is above (positive) or below (negative) its 200D SMA.

    Returns:
        Tuple of (signal_label, score_pts).
    """
    if pct > 2:
        return "ABOVE", +1
    if pct > -2:
        return "NEAR", 0
    return "BELOW", -2


def _classify_credit(ratio: float | None) -> tuple[str, int]:
    """Return credit spread signal string and score contribution.

    HYG/LQD ratio proxies high-yield vs. investment-grade spread.
    Higher ratio → tighter spreads → healthier credit conditions.

    Args:
        ratio: HYG price / LQD price.

    Returns:
        Tuple of (signal_label, score_pts).
    """
    if ratio is None:
        return "UNAVAILABLE", 0
    if ratio > 0.62:
        return "HEALTHY", +1
    if ratio > 0.58:
        return "NEUTRAL", 0
    return "STRESSED", -1


def get_macro_regime() -> MacroRegimeResult:
    """Fetch live market data and classify the current macro regime.

    Returns:
        MacroRegimeResult with regime label and all component signals.
    """
    try:
        import yfinance as yf
    except ImportError:
        return MacroRegimeResult(
            regime="RISK-OFF", score=0, vix=20.0,
            vix_signal="UNAVAILABLE", spy_vs_200d=0.0,
            spy_signal="UNAVAILABLE", hyg_lqd_ratio=None,
            credit_signal="UNAVAILABLE",
            details=["yfinance not installed — run: pip install yfinance",
                     "⚠️ DEGRADED DATA — regime forced RISK-OFF (fail-safe)"],
            degraded=True,
        )

    score = 0
    details: list[str] = []
    vix = 20.0
    vix_signal = "UNAVAILABLE"
    spy_vs_200 = 0.0
    spy_signal = "UNAVAILABLE"
    ratio: float | None = None
    credit_signal = "UNAVAILABLE"

    # ── VIX ───────────────────────────────────────────────────────────────────
    try:
        vix_hist = yf.Ticker("^VIX").history(period="5d")
        vix = float(vix_hist["Close"].to_numpy()[-1])
        vix_signal, vix_pts = _classify_vix(vix)
        score += vix_pts
        details.append(f"VIX {vix:.1f} → {vix_signal}")
    except Exception as exc:
        details.append(f"VIX unavailable: {exc}")

    # ── SPY vs 200D SMA ───────────────────────────────────────────────────────
    try:
        spy_hist = yf.Ticker("SPY").history(period="1y")
        spy_close = float(spy_hist["Close"].to_numpy()[-1])
        sma_200 = float(spy_hist["Close"].tail(200).mean().item())
        spy_vs_200 = (spy_close - sma_200) / sma_200 * 100
        spy_signal, spy_pts = _classify_spy(spy_vs_200)
        score += spy_pts
        details.append(f"SPY {spy_vs_200:+.1f}% vs 200D SMA → {spy_signal}")
    except Exception as exc:
        details.append(f"SPY data unavailable: {exc}")

    # ── HYG/LQD credit proxy ─────────────────────────────────────────────────
    try:
        hyg_close = float(yf.Ticker("HYG").history(period="5d")["Close"].to_numpy()[-1])
        lqd_close = float(yf.Ticker("LQD").history(period="5d")["Close"].to_numpy()[-1])
        ratio = hyg_close / lqd_close if lqd_close > 0 else None
        credit_signal, credit_pts = _classify_credit(ratio)
        score += credit_pts
        details.append(f"HYG/LQD {ratio:.3f} → {credit_signal}")
    except Exception as exc:
        details.append(f"Credit data unavailable: {exc}")

    # ── Regime classification ─────────────────────────────────────────────────
    unavailable = sum(
        1 for sig in (vix_signal, spy_signal, credit_signal)
        if sig == "UNAVAILABLE"
    )
    regime, degraded = _classify_regime(score, unavailable)
    if degraded:
        details.append(
            f"⚠️ DEGRADED DATA — {unavailable}/3 macro signals unavailable; "
            f"regime forced RISK-OFF (fail-safe)"
        )

    return MacroRegimeResult(
        regime=regime,
        score=score,
        vix=vix,
        vix_signal=vix_signal,
        spy_vs_200d=round(spy_vs_200, 2),
        spy_signal=spy_signal,
        hyg_lqd_ratio=round(ratio, 4) if ratio is not None else None,
        credit_signal=credit_signal,
        details=details,
        degraded=degraded,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Macro regime classifier")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    result = get_macro_regime()
    if args.json:
        print(json.dumps(asdict(result), indent=2))
        return

    icon = {"RISK-ON": "✅", "NEUTRAL": "⚠️", "RISK-OFF": "🔴"}.get(result.regime, "")
    print(f"\n{icon} MACRO REGIME: {result.regime}  (score={result.score})")
    for d in result.details:
        print(f"  {d}")
    if result.regime == "RISK-OFF":
        print("  ⚠️  Only REDUCE/EXIT actions permitted today.")


if __name__ == "__main__":
    main()
