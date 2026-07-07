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


def main() -> None:
    parser = argparse.ArgumentParser(description="Market regime classifier")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Print only, skip writing market_regime.json")
    args = parser.parse_args()
    print("market_regime.py: orchestrator not yet implemented (see Task 6)", file=sys.stderr)


if __name__ == "__main__":
    main()
