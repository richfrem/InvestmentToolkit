#!/usr/bin/env python3
"""
reverse_dcf.py (Python Service)
=====================================

Purpose:
    Invert dcf_scenarios.py's compute_scenario(): instead of "what is fair
    value given my growth guess," ask "what 5-year revenue CAGR is *priced
    in* at the current quote." Bisection-solves for the growth rate that
    reproduces the current price as presentValue, holding margin/exitPE/
    qualityMultiplier/shareChange fixed at the base-case values.

Layer: Backend / Python Services / Valuation Math

Usage:
    python3 reverse_dcf.py --price 185.50 --revenue 1000000000 --shares 100000000 \
        --margin 25 --exit-pe 30 --quality-multiplier 1.0 \
        --bear-growth 10 --base-growth 22 --bull-growth 35 --pretty

Key Functions:
    - solve_implied_growth() - Bisection solve + verdict classification (the
      round-trip inverse of dcf_scenarios.compute_scenario())
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dcf_scenarios import compute_scenario  # noqa: E402

BRACKET_LOW_GROWTH = -50.0
BRACKET_HIGH_GROWTH = 500.0
MAX_ITERATIONS = 200
RELATIVE_TOLERANCE = 1e-4


def solve_implied_growth(
    price: float,
    base_shares: float,
    discount_rate: float,
    horizon: int,
    margin: float,
    exit_pe: float,
    quality_multiplier: float,
    base_revenue: float,
    bear_growth: float,
    base_growth: float,
    bull_growth: float,
    guided_growth: float | None = None,
    share_change: float = 0.0,
    weight: float = 1.0,
    optionality_adjustment: float = 0.0,
) -> dict:
    """Bisection-solve the 5yr revenue CAGR the market is pricing in at `price`.

    Inverts compute_scenario(): holds margin, exitPE, qualityMultiplier,
    shareChange, discountRate, horizon fixed, and solves for the growthRate
    that reproduces `price` as presentValue. bear/base/bull growth define
    the verdict bands; guided_growth (company's own guidance) is optional.

    Returns:
        {"impliedGrowth": float | None, "impliedGrowthVsBaseCase": float | None,
         "impliedGrowthVsGuidance": float | None,
         "verdict": "PRICING_IN_MORE_THAN_BULL" | "BETWEEN_BASE_AND_BULL"
                   | "BETWEEN_BEAR_AND_BASE" | "BELOW_BEAR" | "OUT_OF_BRACKET_RANGE",
         "converged": bool, "iterations": int}
    """
    params = {
        "weight": weight, "netMargin": margin, "exitPE": exit_pe,
        "qualityMultiplier": quality_multiplier, "shareChange": share_change,
        "optionalityAdjustment": optionality_adjustment,
    }

    def pv_at(growth: float) -> float:
        trial = {**params, "growthRate": growth}
        return compute_scenario(base_revenue, base_shares, discount_rate, horizon, trial)["presentValue"]

    lo, hi = BRACKET_LOW_GROWTH, BRACKET_HIGH_GROWTH
    pv_lo, pv_hi = pv_at(lo), pv_at(hi)

    if price < pv_lo or price > pv_hi:
        return {
            "impliedGrowth": None, "impliedGrowthVsBaseCase": None,
            "impliedGrowthVsGuidance": None, "verdict": "OUT_OF_BRACKET_RANGE",
            "converged": False, "iterations": 0,
        }

    tolerance = RELATIVE_TOLERANCE * max(price, 1.0)
    iterations = 0
    mid = (lo + hi) / 2
    converged = False
    while iterations < MAX_ITERATIONS:
        mid = (lo + hi) / 2
        pv_mid = pv_at(mid)
        if abs(pv_mid - price) < tolerance:
            converged = True
            break
        if pv_mid < price:
            lo = mid
        else:
            hi = mid
        iterations += 1

    implied_growth = round(mid, 4)

    if implied_growth >= bull_growth:
        verdict = "PRICING_IN_MORE_THAN_BULL"
    elif implied_growth >= base_growth:
        verdict = "BETWEEN_BASE_AND_BULL"
    elif implied_growth >= bear_growth:
        verdict = "BETWEEN_BEAR_AND_BASE"
    else:
        verdict = "BELOW_BEAR"

    return {
        "impliedGrowth": implied_growth,
        "impliedGrowthVsBaseCase": round(implied_growth - base_growth, 4),
        "impliedGrowthVsGuidance": (
            round(implied_growth - guided_growth, 4) if guided_growth is not None else None
        ),
        "verdict": verdict,
        "converged": converged,
        "iterations": iterations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reverse-DCF implied growth solver")
    parser.add_argument("--price", type=float, required=True)
    parser.add_argument("--revenue", type=float, required=True, help="TTM base revenue in dollars")
    parser.add_argument("--shares", type=float, required=True)
    parser.add_argument("--margin", type=float, required=True, help="Base-case net margin, percent")
    parser.add_argument("--exit-pe", type=float, required=True)
    parser.add_argument("--quality-multiplier", type=float, default=1.0)
    parser.add_argument("--share-change", type=float, default=0.0)
    parser.add_argument("--discount-rate", type=float, default=0.10)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--bear-growth", type=float, required=True)
    parser.add_argument("--base-growth", type=float, required=True)
    parser.add_argument("--bull-growth", type=float, required=True)
    parser.add_argument("--guided-growth", type=float, default=None)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = solve_implied_growth(
        price=args.price, base_shares=args.shares, discount_rate=args.discount_rate,
        horizon=args.horizon, margin=args.margin, exit_pe=args.exit_pe,
        quality_multiplier=args.quality_multiplier, base_revenue=args.revenue,
        bear_growth=args.bear_growth, base_growth=args.base_growth, bull_growth=args.bull_growth,
        guided_growth=args.guided_growth, share_change=args.share_change,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
