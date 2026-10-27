#!/usr/bin/env python3
"""
leverage.py - Balance-sheet risk for a valuation: one tier, and what it changes.

Purpose:
    Earnings-multiple valuations (year-5 EPS x exit P/E) have no line for debt, so a
    heavily borrowed company could show the same fair value and reward:risk as a
    debt-free one. This module is the single place that (1) grades leverage from net
    debt/EBITDA, interest coverage, current ratio and net debt/market value, (2) says
    how much scenario probability moves from the upside cases to the bear case for
    that grade, and (3) checks that an equity valuation is discounted at the cost of
    equity rather than a debt-diluted blended rate (WACC).

Layer:
    Stock valuation business logic (pure functions; no database, network or clock).

Usage:
    from leverage import leverage_profile, apply_leverage_weights, rate_basis_check

Key Functions:
    leverage_profile(...)                 metrics, tier LOW|MODERATE|HIGH|SEVERE|UNKNOWN, reasons
    apply_leverage_weights(weights, tier) scenario weights after the leverage shift
    rate_basis_check(method, rate, ke)    OK | MISMATCH | UNKNOWN for the discount rate

Key Input Dependencies:
    Fundamentals in one currency: totalDebt, cashAndEquivalents, ebitda, operatingIncome,
    interestExpense, currentRatio, marketCap.

Key Output Dependencies:
    None. Callers save the result under valuationModel.leverage / .rateBasis.
"""
from __future__ import annotations

from typing import Any

# Thresholds as (watch, stressed). Interest coverage and current ratio match the
# quality score's bands (framework_score.FLAT_THRESHOLDS), which imports them from here.
NET_DEBT_TO_EBITDA = (2.5, 4.0, 8.0)  # above: 1 point, 2 points, 3 points
INTEREST_COVERAGE = (5.0, 2.0)        # below: 1 point, 2 points
CURRENT_RATIO = (1.5, 1.0)            # below the second: 1 point
NET_DEBT_TO_MARKET_CAP = 0.5          # above: 1 point
# Points needed for each tier.
TIER_POINTS = (("SEVERE", 5), ("HIGH", 3), ("MODERATE", 1), ("LOW", 0))
# Probability moved to the bear case, taken from bull first and then base.
BEAR_WEIGHT_SHIFT = {"LOW": 0.0, "MODERATE": 0.0, "HIGH": 0.05, "SEVERE": 0.10, "UNKNOWN": 0.0}
# An equity valuation may sit this far below the cost of equity before it is a mismatch.
RATE_TOLERANCE = 0.005


def _number(value: Any) -> float | None:
    """A finite float, or None for missing and non-numeric input."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def leverage_profile(total_debt: Any = None, cash: Any = None, ebitda: Any = None,
                     operating_income: Any = None, interest_expense: Any = None,
                     current_ratio: Any = None, market_cap: Any = None) -> dict[str, Any]:
    """Grade balance-sheet risk from the fundamentals available.

    Returns:
        {"tier", "points", "reasons": [...], "netDebt", "netDebtToEbitda",
        "interestCoverage", "currentRatio", "netDebtToMarketCap"}. The tier is UNKNOWN
        when debt is not known. A company with net cash is at most MODERATE.
    """
    debt, cash_value = _number(total_debt), _number(cash) or 0.0
    ebitda_value, operating = _number(ebitda), _number(operating_income)
    interest = abs(_number(interest_expense) or 0.0) or None
    ratio, cap = _number(current_ratio), _number(market_cap)
    if debt is None:
        return {"tier": "UNKNOWN", "points": 0, "reasons": ["Debt not available"], "netDebt": None,
                "netDebtToEbitda": None, "interestCoverage": None, "currentRatio": ratio, "netDebtToMarketCap": None}
    net_debt = debt - cash_value
    points, reasons = 0, []
    debt_to_ebitda = net_debt / ebitda_value if ebitda_value and ebitda_value > 0 else None
    coverage = operating / interest if operating is not None and interest else None
    debt_to_cap = net_debt / cap if cap and cap > 0 else None

    if net_debt > 0:
        if ebitda_value is not None and ebitda_value <= 0:
            points += 2
            reasons.append("Net debt with no positive EBITDA to service it")
        elif debt_to_ebitda is not None and debt_to_ebitda > NET_DEBT_TO_EBITDA[0]:
            points += 1 + sum(debt_to_ebitda > level for level in NET_DEBT_TO_EBITDA[1:])
            reasons.append(f"Net debt is {debt_to_ebitda:.1f}x EBITDA")
        if debt_to_cap is not None and debt_to_cap > NET_DEBT_TO_MARKET_CAP:
            points += 1
            reasons.append(f"Net debt is {debt_to_cap * 100:.0f}% of market value")
    if coverage is not None and coverage < INTEREST_COVERAGE[0]:
        stressed = coverage < INTEREST_COVERAGE[1]
        points += 2 if stressed else 1
        reasons.append("Operating income does not cover interest" if coverage <= 0
                       else f"Operating income covers interest only {coverage:.1f}x")
    if ratio is not None and ratio < CURRENT_RATIO[1]:
        points += 1
        reasons.append(f"Current ratio {ratio:.2f}: short-term liabilities exceed liquid assets")
    tier = next(name for name, needed in TIER_POINTS if points >= needed)
    if net_debt <= 0 and tier in ("HIGH", "SEVERE"):
        tier = "MODERATE"
        reasons.append("Net cash position limits the grade")
    return {"tier": tier, "points": points, "reasons": reasons, "netDebt": net_debt,
            "netDebtToEbitda": debt_to_ebitda, "interestCoverage": coverage, "currentRatio": ratio,
            "netDebtToMarketCap": debt_to_cap}


def apply_leverage_weights(weights: dict[str, float], tier: str) -> dict[str, float]:
    """Move probability to the bear case for a leveraged balance sheet.

    Debt raises the odds of the downside for shareholders (refinancing, dilution,
    covenants) without changing the upside cases' prices. The shift comes out of the
    bull case first, then the base case; totals are unchanged.

    Args:
        weights: {"bear", "base", "bull"} as fractions summing to 1.
        tier: leverage_profile()["tier"].

    Returns:
        New weights rounded to 4 places. Unchanged for LOW, MODERATE and UNKNOWN.
    """
    shift = BEAR_WEIGHT_SHIFT.get(tier, 0.0)
    bear, base, bull = (float(weights[name]) for name in ("bear", "base", "bull"))
    from_bull = min(shift, bull)
    from_base = min(shift - from_bull, base)
    return {"bear": round(bear + from_bull + from_base, 4), "base": round(base - from_base, 4),
            "bull": round(bull - from_bull, 4)}


def rate_basis_check(method: str | None, discount_rate: Any, cost_of_equity: Any) -> dict[str, Any]:
    """Check that an equity valuation is not discounted at a rate below the cost of equity.

    Year-5 EPS x exit P/E values what belongs to shareholders, so it must be discounted
    at the cost of equity. A blended rate (WACC) is lower the more a company borrows,
    which would make more debt produce a higher fair value.

    Returns:
        {"status": OK|MISMATCH|UNKNOWN, "note"}. Firm-level methods (annual_fcff) are OK:
        they use WACC and subtract debt explicitly.
    """
    rate, ke = _number(discount_rate), _number(cost_of_equity)
    if (method or "terminal_earnings") == "annual_fcff":
        return {"status": "OK", "note": "Firm cash flows discounted at WACC; debt is subtracted in the equity bridge"}
    if rate is None or ke is None:
        return {"status": "UNKNOWN", "note": "Cost of equity not available to check the discount rate"}
    if rate < ke - RATE_TOLERANCE:
        return {"status": "MISMATCH", "note": (f"Equity earnings are discounted at {rate * 100:.2f}%, below the "
                                               f"{ke * 100:.2f}% cost of equity; fair value is overstated")}
    return {"status": "OK", "note": f"Discounted at {rate * 100:.2f}%, at or above the {ke * 100:.2f}% cost of equity"}
