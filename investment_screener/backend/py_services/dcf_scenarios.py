#!/usr/bin/env python3
"""
DCF Scenario Calculator — InvestmentToolkit
============================================
Canonical calculation engine for 5-year DCF scenario valuations.

Usage (from repo root):
  # With raw financial data file + inline scenario JSON:
  python3 investment_screener/backend/py_services/dcf_scenarios.py \\
    --raw /tmp/PANW_raw.json \\
    --scenarios /tmp/PANW_scenarios.json

  # With explicit base params + inline scenario JSON:
  python3 investment_screener/backend/py_services/dcf_scenarios.py \\
    --ticker PANW \\
    --revenue 9221500000 \\
    --shares 811000000 \\
    --scenarios /tmp/PANW_scenarios.json

  # Pipe scenarios via stdin:
  echo '<scenarios_json>' | python3 ... --raw /tmp/PANW_raw.json --scenarios -

Scenario JSON schema (bear/base/bull each require):
  {
    "bear": {
      "weight": 0.20,       // probability weight (bear+base+bull must sum to 1.0)
      "growthRate": 11,     // 5-year revenue CAGR as a percentage (e.g. 11 = 11%)
      "netMargin": 9,       // Year-5 net profit margin as a percentage (e.g. 9 = 9%)
      "exitPE": 20,         // Terminal P/E multiple applied to Year-5 EPS
      "qualityMultiplier":  // Moat/management quality adjustment (0.8–1.35)
      "shareChange": -0.5   // Annual % change in share count (+dilution, -buyback)
    },
    "base": { ... },
    "bull": { ... }
  }

Output: JSON to stdout with all intermediate values + validation flags.
"""

import argparse
import json
import sys
from typing import Any


REQUIRED_SCENARIO_KEYS = {
    "weight", "growthRate", "netMargin", "exitPE", "qualityMultiplier", "shareChange"
}
SCENARIO_NAMES = ("bear", "base", "bull")


def compute_scenario(
    base_revenue: float,
    base_shares: float,
    discount_rate: float,
    horizon: int,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Compute all derived values for one scenario."""
    growth = params["growthRate"] / 100.0
    margin = params["netMargin"] / 100.0
    sc = params["shareChange"] / 100.0
    pe = params["exitPE"]
    qm = params["qualityMultiplier"]

    divisor = (1 + discount_rate) ** horizon

    y5_revenue = base_revenue * (1 + growth) ** horizon
    y5_net_income = y5_revenue * margin
    y5_shares = base_shares * (1 + sc) ** horizon
    y5_eps = y5_net_income / y5_shares if y5_shares > 0 else 0.0
    y5_price_undiscounted = y5_eps * pe * qm
    present_value = y5_price_undiscounted / divisor

    return {
        **params,
        "year5Revenue": round(y5_revenue / 1_000_000, 1),       # stored in $M
        "year5NetIncome": round(y5_net_income / 1_000_000, 1),   # stored in $M
        "year5Shares": round(y5_shares / 1_000_000, 1),          # stored in $M
        "year5EPS": round(y5_eps, 2),
        "year5PriceUndiscounted": round(y5_price_undiscounted, 2),
        "presentValue": round(present_value, 2),
    }


def validate_scenarios(results: dict[str, dict]) -> dict[str, Any]:
    """Validate ordering and weight constraints. Returns a validation block."""
    errors = []
    warnings = []

    bear = results["bear"]
    base = results["base"]
    bull = results["bull"]

    weight_sum = round(bear["weight"] + base["weight"] + bull["weight"], 4)
    weight_ok = abs(weight_sum - 1.0) <= 0.01
    if not weight_ok:
        errors.append(f"Weight sum {weight_sum} deviates from 1.0 by more than ±0.01")

    growth_ok = bear["growthRate"] < base["growthRate"] < bull["growthRate"]
    if not growth_ok:
        errors.append(
            f"Growth ordering violated: bear={bear['growthRate']} "
            f"base={base['growthRate']} bull={bull['growthRate']}"
        )

    pv_ok = bear["presentValue"] < base["presentValue"] < bull["presentValue"]
    if not pv_ok:
        errors.append(
            f"PV ordering violated: bear={bear['presentValue']} "
            f"base={base['presentValue']} bull={bull['presentValue']}"
        )

    # Warn on quality multiplier > 1.1 without a moat citation (can't check here,
    # but flag it so the agent documents justification in the rationale field)
    for name, s in results.items():
        if s["qualityMultiplier"] > 1.1:
            warnings.append(
                f"{name}.qualityMultiplier={s['qualityMultiplier']} > 1.1 — "
                "ensure ≥1 structural moat is cited in scenario rationale"
            )
        if not (-5.0 <= s["shareChange"] <= 5.0):
            errors.append(f"{name}.shareChange={s['shareChange']} out of range [-5, +5]")
        if not (0 <= s["netMargin"] <= 100):
            errors.append(f"{name}.netMargin={s['netMargin']} out of range [0, 100]")

    return {
        "weightSum": weight_sum,
        "weightSumOk": weight_ok,
        "growthOrdering": growth_ok,
        "pvOrdering": pv_ok,
        "errors": errors,
        "warnings": warnings,
        "valid": len(errors) == 0,
    }


def run(
    ticker: str,
    base_revenue: float,
    base_shares: float,
    scenario_params: dict[str, dict],
    discount_rate: float = 0.10,
    horizon: int = 5,
    price: float | None = None,
) -> dict[str, Any]:
    """
    Main calculation entry point. Returns full result dict including
    weighted fair value, per-scenario computed values, and validation.
    """
    for name in SCENARIO_NAMES:
        if name not in scenario_params:
            raise ValueError(f"Missing scenario: '{name}'")
        missing = REQUIRED_SCENARIO_KEYS - set(scenario_params[name].keys())
        if missing:
            raise ValueError(f"Scenario '{name}' missing keys: {missing}")

    divisor = round((1 + discount_rate) ** horizon, 5)

    computed = {
        name: compute_scenario(base_revenue, base_shares, discount_rate, horizon, scenario_params[name])
        for name in SCENARIO_NAMES
    }

    weighted_fv = round(
        sum(computed[n]["weight"] * computed[n]["presentValue"] for n in SCENARIO_NAMES), 2
    )

    action = "HOLD"
    if price is not None:
        pct = (weighted_fv - price) / price * 100
        if pct > 15:
            action = "BUY"
        elif pct < -5:
            action = "SELL"
    else:
        pct = None

    return {
        "ticker": ticker,
        "baseRevenue": base_revenue,
        "baseShares": base_shares,
        "discountRate": discount_rate,
        "horizon": horizon,
        "discountDivisor": divisor,
        "currentPrice": price,
        "weightedFairValue": weighted_fv,
        "upsidePct": round(pct, 1) if pct is not None else None,
        "action": action if price is not None else "N/A (no price provided)",
        "scenarios": computed,
        "validation": validate_scenarios(computed),
    }


def load_raw_json(path: str) -> tuple[str, float, float, float]:
    """Extract ticker, revenue, shares, price from fetch_financials output."""
    with open(path) as f:
        d = json.load(f)
    ticker = d.get("ticker") or d.get("symbol", "UNKNOWN")
    m = d["metrics"]
    revenue = float(m["revenue"])
    # Prefer mktcap-implied share count (most current snapshot); fall back to shares_outstanding
    price = float(m["price"])
    mcap = float(m.get("market_cap") or 0)
    shares = mcap / price if mcap and price else float(m["shares_outstanding"])
    return ticker, revenue, shares, price


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DCF Scenario Calculator — compute 5-year scenario valuations"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--raw", help="Path to fetch_financials.py output JSON")
    group.add_argument("--revenue", type=float, help="TTM revenue in dollars")

    parser.add_argument("--ticker", default="UNKNOWN", help="Ticker symbol")
    parser.add_argument("--shares", type=float, help="Share count (required if --revenue used)")
    parser.add_argument("--price", type=float, help="Current share price (for upside calc)")
    parser.add_argument(
        "--scenarios",
        required=True,
        help="Path to scenario params JSON, or '-' to read from stdin",
    )
    parser.add_argument("--discount-rate", type=float, default=0.10)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print output JSON")

    args = parser.parse_args()

    # Load scenario params
    if args.scenarios == "-":
        scenario_params = json.load(sys.stdin)
    else:
        with open(args.scenarios) as f:
            scenario_params = json.load(f)

    # Load base financial data
    if args.raw:
        ticker, revenue, shares, price = load_raw_json(args.raw)
        if args.ticker != "UNKNOWN":
            ticker = args.ticker
        if args.price:
            price = args.price
    else:
        if not args.revenue or not args.shares:
            parser.error("--revenue and --shares are required when not using --raw")
        ticker = args.ticker
        revenue = args.revenue
        shares = args.shares
        price = args.price

    result = run(
        ticker=ticker,
        base_revenue=revenue,
        base_shares=shares,
        scenario_params=scenario_params,
        discount_rate=args.discount_rate,
        horizon=args.horizon,
        price=price,
    )

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent))

    # Exit non-zero if validation failed so CI/workflow can detect errors
    if not result["validation"]["valid"]:
        sys.stderr.write("VALIDATION ERRORS:\n")
        for e in result["validation"]["errors"]:
            sys.stderr.write(f"  • {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
