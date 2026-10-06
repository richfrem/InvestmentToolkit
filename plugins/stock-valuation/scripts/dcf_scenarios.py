#!/usr/bin/env python3
"""
dcf_scenarios.py - Discounted Cash Flow scenario calculator.

Purpose:
    Canonical engine for annual FCFF DCF and legacy discounted terminal earnings valuations.
    Supports bear, base, and bull scenarios with probability weighting and structural validation.

Layer:
    Backend / Python Services / Valuation Math

Usage Examples:
    # With raw financial data file + inline scenario JSON
    python3 dcf_scenarios.py --raw AAPL_raw.json --scenarios AAPL_scenarios.json --pretty

    # With explicit base params
    python3 dcf_scenarios.py --ticker MSFT --revenue 211000000000 --shares 7400000000 --scenarios MSFT_scenarios.json

    # Pipe scenarios via stdin
    echo '<scenarios_json>' | python3 dcf_scenarios.py --raw AAPL_raw.json --scenarios -

Key Functions (Index):
    - _finite_number(value, label) - Reject non-finite numeric inputs
    - _annual_cash_flow(row) - Calculate NOPAT, investment and FCFF for one year
    - compute_cash_flow_scenario(...) - Discount annual FCFF and normalized terminal FCFF
    - compute_scenario(base_revenue, base_shares, discount_rate, horizon, params) - Compute all derived values for one scenario
    - validate_scenarios(results) - Validate ordering and weight constraints
    - run(ticker, base_revenue, base_shares, scenario_params, discount_rate, horizon, price) - Main calculation entry point
    - load_raw_json(path) - Extract ticker, revenue, shares, price from fetch_financials output
    - _resolve_discount_rate(explicit_rate, wacc_file) - Resolve discount-rate from inputs
    - main() - Main CLI entry point

Key Input Dependencies:
    - Scenario JSON and dated financial inputs; recommendation.valuation_signal

Key Output Dependencies:
    None
"""

import argparse
import json
import math
import sys
from typing import Any
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "investment_screener/backend/py_services"))
from recommendation import valuation_signal


REQUIRED_SCENARIO_KEYS = {
    "weight", "growthRate", "netMargin", "exitPE", "qualityMultiplier", "shareChange"
}
SCENARIO_NAMES = ("bear", "base", "bull")


# Validate numeric inputs before any cash-flow arithmetic.
def _finite_number(value: Any, label: str) -> float:
    """Return a finite number or raise a labeled input error."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


# Convert an explicit annual operating forecast to unlevered cash flow.
def _annual_cash_flow(row: dict[str, Any]) -> dict[str, Any]:
    """Compute FCFF in dollars; operating margin includes SBC and lease expenses."""
    required = ("revenue", "operatingMarginPct", "taxRatePct", "depreciation", "capex", "workingCapitalChange")
    values = {key: _finite_number(row[key], key) for key in required}
    if values["revenue"] <= 0 or values["capex"] < 0 or values["depreciation"] < 0:
        raise ValueError("Revenue must be positive; capex and depreciation must be non-negative")
    if not -100 <= values["operatingMarginPct"] <= 100 or not 0 <= values["taxRatePct"] <= 100:
        raise ValueError("Margin and tax must use percentage units within their valid ranges")
    operating_profit = values["revenue"] * values["operatingMarginPct"] / 100
    taxes = max(operating_profit, 0) * values["taxRatePct"] / 100
    nopat = operating_profit - taxes
    fcff = nopat + values["depreciation"] - values["capex"] - values["workingCapitalChange"]
    return {**row, "operatingProfit": operating_profit, "cashTaxes": taxes,
            "nopat": nopat, "freeCashFlow": fcff}


# Value annual cash flows and a separately normalized terminal business.
def compute_cash_flow_scenario(
    base_revenue: float, base_shares: float, discount_rate: float,
    horizon: int, params: dict[str, Any],
) -> dict[str, Any]:
    """Discount end-year FCFF, add net cash once, and divide by supplied equity shares.

    terminalForecast is the normalized year-horizon cash-flow base; terminalGrowth
    grows it once into year horizon+1. Dollar inputs remain dollars in the audit.
    SBC remains an economic operating expense; no extra share-change haircut is
    supported. Convertible debt/share treatment belongs in the disclosed bridge.
    """
    rate = _finite_number(discount_rate, "discount rate")
    growth = _finite_number(params["terminalGrowth"], "terminal growth")
    if not 0 <= growth < rate or rate > 1:
        raise ValueError("Require 0 <= terminal growth < discount rate <= 1 in decimal units")
    if _finite_number(base_revenue, "base revenue") <= 0 or _finite_number(base_shares, "shares") <= 0:
        raise ValueError("Base revenue and shares must be positive")
    if horizon < 1 or len(params["annualForecast"]) != horizon:
        raise ValueError("Annual forecast length must equal the positive horizon")
    if params.get("sbcTreatment") != "expensed_in_operating_margin" or params.get("shareChange", 0) != 0:
        raise ValueError("SBC must remain expensed in operating margin; no share-change double count")
    if params.get("optionalityAdjustment", 0) != 0:
        raise ValueError("FCFF does not accept an optionality adjustment")
    bridge = {key: _finite_number(params[key], key) for key in ("cash", "debt", "otherClaims")}
    if any(value < 0 for value in bridge.values()):
        raise ValueError("Cash, debt and other claims must be non-negative")
    annual = [_annual_cash_flow(row) for row in params["annualForecast"]]
    prior_period = 0.0
    for year, row in enumerate(annual, start=1):
        period = _finite_number(row.get("discountPeriod", year), "discount period")
        if period <= prior_period:
            raise ValueError("Discount periods must be positive and strictly increasing")
        row["discountPeriod"] = period
        row["presentValueCashFlow"] = row["freeCashFlow"] / (1 + rate) ** period
        prior_period = period
    terminal = _annual_cash_flow(params["terminalForecast"])
    if terminal["freeCashFlow"] <= 0:
        raise ValueError("Normalized terminal free cash flow must be positive for a perpetuity")
    terminal_pv = terminal["freeCashFlow"] * (1 + growth) / (rate - growth) / (1 + rate) ** prior_period
    enterprise = sum(row["presentValueCashFlow"] for row in annual) + terminal_pv
    equity = enterprise + bridge["cash"] - bridge["debt"] - bridge["otherClaims"]
    last = annual[-1]
    return {**params, "annualForecast": annual, "terminalForecast": terminal,
            "growthRate": (last["revenue"] / base_revenue) ** (1 / prior_period) * 100 - 100,
            "netMargin": last["nopat"] / last["revenue"] * 100,
            "exitPE": 0, "qualityMultiplier": 1, "shareChange": 0,
            "year5Revenue": round(last["revenue"] / 1_000_000, 1),
            "terminalFreeCashFlow": terminal["freeCashFlow"], "terminalValuePV": terminal_pv,
            "terminalValuePct": terminal_pv / enterprise * 100 if enterprise > 0 else None,
            "enterpriseValue": enterprise, "equityValue": equity,
            "presentValue": round(max(equity, 0) / base_shares, 2), "priceFloored": equity < 0}


def compute_scenario(
    base_revenue: float,
    base_shares: float,
    discount_rate: float,
    horizon: int,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Compute all derived values for one scenario.
    
    Supports 'optionalityAdjustment' ($ in dollars) which is added after the 
    DCF terminal value calculation to account for massive committed but 
    unrealized projects (e.g. data center buildouts).
    """
    if params.get("method") == "annual_fcff":
        return compute_cash_flow_scenario(base_revenue, base_shares, discount_rate, horizon, params)
    if params.get("method", "terminal_earnings") != "terminal_earnings":
        raise ValueError("Unknown valuation method")
    growth = params["growthRate"] / 100.0
    margin = params["netMargin"] / 100.0
    sc = params["shareChange"] / 100.0
    pe = params["exitPE"]
    qm = params["qualityMultiplier"]
    optionality = params.get("optionalityAdjustment", 0.0)

    divisor = (1 + discount_rate) ** horizon

    y5_revenue = base_revenue * (1 + growth) ** horizon
    y5_net_income = y5_revenue * margin
    y5_shares = base_shares * (1 + sc) ** horizon
    y5_eps = y5_net_income / y5_shares if y5_shares > 0 else 0.0
    
    # Core Valuation Mirror logic
    # Note: Optionality is added to the undiscounted price (future value)
    y5_price_undiscounted = (y5_eps * pe * qm) + (optionality / y5_shares if y5_shares > 0 else 0.0)
    # Floor at $0: a negative EPS produces a mathematically negative "price," but
    # equity holders' worst real-world outcome is a total loss (price=$0), never a
    # negative number. Caught live 2026-08-29 valuing APLD, where an unfloored
    # negative bear/base price silently corrupted the weighted-average fair value.
    price_was_negative = y5_price_undiscounted < 0
    y5_price_undiscounted = max(y5_price_undiscounted, 0.0)
    present_value = y5_price_undiscounted / divisor

    return {
        **params,
        "year5Revenue": round(y5_revenue / 1_000_000, 1),       # stored in $M
        "year5NetIncome": round(y5_net_income / 1_000_000, 1),   # stored in $M
        "year5Shares": round(y5_shares / 1_000_000, 1),          # stored in $M
        "year5EPS": round(y5_eps, 2),
        "year5PriceUndiscounted": round(y5_price_undiscounted, 2),
        "presentValue": round(present_value, 2),
        "priceFloored": price_was_negative,
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

    # A tie at the $0 floor between bear and base is not a real ordering
    # violation -- both are genuinely, equally worthless in this model when both
    # hit the negative-EPS floor (see priceFloored). Bull must still strictly
    # exceed base; only the bear<=base leg tolerates a floor tie.
    bear_base_ok = (
        bear["presentValue"] < base["presentValue"]
        or (bear.get("priceFloored") and base.get("priceFloored") and bear["presentValue"] == base["presentValue"])
    )
    pv_ok = bear_base_ok and base["presentValue"] < bull["presentValue"]
    if not pv_ok:
        errors.append(
            f"PV ordering violated: bear={bear['presentValue']} "
            f"base={base['presentValue']} bull={bull['presentValue']}"
        )

    # Warn on quality multiplier > 1.1 without a moat citation (can't check here,
    # but flag it so the agent documents justification in the rationale field)
    for name, s in results.items():
        if not math.isfinite(s["weight"]) or not 0 <= s["weight"] <= 1:
            errors.append(f"{name}.weight must be a finite probability in [0, 1]")
        if s["qualityMultiplier"] > 1.1:
            warnings.append(
                f"{name}.qualityMultiplier={s['qualityMultiplier']} > 1.1 — "
                "ensure ≥1 structural moat is cited in scenario rationale"
            )
        if s.get("priceFloored") and s.get("method") == "annual_fcff":
            warnings.append(f"{name}.equityValue was floored to $0 after debt and other claims")
        elif s.get("priceFloored"):
            warnings.append(
                f"{name}.year5PriceUndiscounted was floored to $0 (negative EPS × exitPE "
                "produced a negative price) — the P/E-based terminal-value method breaks "
                "down for a scenario still loss-making at year 5; consider a revenue-multiple "
                "terminal value for this scenario instead of trusting the $0 floor blindly"
            )
        if not (-5.0 <= s["shareChange"] <= 5.0):
            errors.append(f"{name}.shareChange={s['shareChange']} out of range [-5, +5]")
        # SKILL.md Step 3 constraint #4 documents netMargin as "-100% to 100%" --
        # caught live 2026-08-28 valuing SHAZ (pre-revenue AI infra), whose bear
        # case legitimately needs a negative margin (e.g. -15%) that this check
        # previously rejected by enforcing [0, 100] instead of the documented range.
        if not (-100 <= s["netMargin"] <= 100):
            errors.append(f"{name}.netMargin={s['netMargin']} out of range [-100, 100]")
        # growthRate/netMargin are consumed as percentage units (8 means 8%) via
        # an internal /100.0 division. A value strictly between 0 and 1 is the
        # signature of a decimal-fraction mistake (0.08 instead of 8) — caught live
        # on AMAT 2026-08-28, where it silently produced a -99.6% fair value with
        # no validation error under the pre-existing checks.
        if 0 < s["growthRate"] < 1:
            errors.append(
                f"{name}.growthRate={s['growthRate']} looks like a decimal fraction, "
                "not a percentage — use 8 for 8%, not 0.08"
            )
        if 0 < s["netMargin"] < 1:
            errors.append(
                f"{name}.netMargin={s['netMargin']} looks like a decimal fraction, "
                "not a percentage — use 26 for 26%, not 0.26"
            )

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
        required = {"weight", "annualForecast", "terminalForecast", "terminalGrowth", "cash", "debt", "otherClaims"} if scenario_params[name].get("method") == "annual_fcff" else REQUIRED_SCENARIO_KEYS
        missing = required - set(scenario_params[name].keys())
        if missing:
            raise ValueError(f"Scenario '{name}' missing keys: {missing}")

    annual_fcff = scenario_params["base"].get("method") == "annual_fcff"
    if annual_fcff:
        periods_present = [
            "discountPeriod" in scenario_params[name]["annualForecast"][-1]
            for name in SCENARIO_NAMES
        ]
        if any(periods_present) and not all(periods_present):
            raise ValueError("Annual FCFF scenarios must all declare their final discountPeriod")
        periods = {
            name: float(scenario_params[name]["annualForecast"][-1]["discountPeriod"])
            for name in SCENARIO_NAMES
        } if all(periods_present) else {}
        if periods and len(set(periods.values())) != 1:
            raise ValueError(f"Annual FCFF scenarios must share a forecast horizon: {periods}")
        effective_horizon = next(iter(periods.values())) if periods else horizon
    else:
        effective_horizon = horizon
    divisor = round((1 + discount_rate) ** effective_horizon, 5)

    computed = {
        name: compute_scenario(base_revenue, base_shares, discount_rate, horizon, scenario_params[name])
        for name in SCENARIO_NAMES
    }

    weighted_fv = round(
        sum(computed[n]["weight"] * computed[n]["presentValue"] for n in SCENARIO_NAMES), 2
    )

    pct = (weighted_fv - price) / price * 100 if price is not None and price > 0 else None
    action = valuation_signal(pct) or "HOLD"

    return {
        "ticker": ticker,
        "baseRevenue": base_revenue,
        "baseShares": base_shares,
        "discountRate": discount_rate,
        "horizon": effective_horizon,
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
    price = float(m["price"])
    # Prefer NI/EPS-derived diluted share count — captures full dilution from options/warrants/RSUs.
    # Fall back to mktcap/price (basic shares) if shares_diluted is missing or zero.
    #
    # Sanity check (caught live 2026-08-29 on CBRS): normal option/RSU dilution
    # makes shares_diluted modestly >= shares_outstanding (typically 5-20%
    # higher). A divergence beyond 25% in EITHER direction is not genuine
    # forward-looking dilution -- it's a signal the diluted figure reflects a
    # stale/mismatched weighted-average period (e.g. pre-IPO, pre-split) and
    # should not be trusted. CBRS: diluted was 4.4x outstanding, silently
    # producing a materially understated EPS/fair value. BE: diluted was ~19%
    # BELOW outstanding (also abnormal -- diluted should never be lower), and
    # was used despite the persisted projection's own shareCountMethod field
    # claiming shares_outstanding was used.
    shares_diluted = m.get("shares_diluted")
    shares_outstanding = m.get("shares_outstanding")
    if shares_diluted and float(shares_diluted) > 0:
        diluted = float(shares_diluted)
        if shares_outstanding and float(shares_outstanding) > 0:
            outstanding = float(shares_outstanding)
            if outstanding <= diluted <= outstanding * 1.25:
                shares = diluted
            else:
                shares = outstanding
        else:
            shares = diluted
    else:
        mcap = float(m.get("market_cap") or 0)
        shares = mcap / price if mcap and price else float(m["shares_outstanding"])
    return ticker, revenue, shares, price


def _resolve_discount_rate(explicit_rate: float | None, wacc_file: str | None) -> float:
    """CLI-layer discount-rate resolution: --discount-rate (explicit) wins over
    --wacc-file (derived) wins over the 0.10 default — preserves old-run
    reproducibility while letting wacc.py drive the rate when no explicit
    override is given.

    Args:
        explicit_rate: Value of --discount-rate, or None if not passed.
        wacc_file: Path to a wacc.py JSON output file, or None.

    Returns:
        The resolved discount rate as a decimal fraction.
    """
    if explicit_rate is not None:
        return explicit_rate
    if wacc_file:
        with open(wacc_file) as f:
            wacc_data = json.load(f)
        return wacc_data["wacc"]
    return 0.10


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
    parser.add_argument(
        "--discount-rate", type=float, default=None,
        help="Explicit discount rate override — wins over --wacc-file. Defaults to 0.10 if neither is given.",
    )
    parser.add_argument(
        "--wacc-file", default=None,
        help="Path to wacc.py's JSON output; used as the discount rate unless --discount-rate is explicitly set.",
    )
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

    discount_rate = _resolve_discount_rate(args.discount_rate, args.wacc_file)

    result = run(
        ticker=ticker,
        base_revenue=revenue,
        base_shares=shares,
        scenario_params=scenario_params,
        discount_rate=discount_rate,
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
