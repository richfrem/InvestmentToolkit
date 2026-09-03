#!/usr/bin/env python3
"""
wacc.py (Python Service)
=====================================

Purpose:
    Compute a per-company weighted average cost of capital (WACC) to replace
    dcf_scenarios.py's flat 10% discount-rate default with a risk-adjusted
    rate: risk-free rate (10Y Treasury), levered beta (local OLS regression
    vs SPY), equity risk premium, and after-tax cost of debt, weighted by
    market-cap/debt capital structure.

Layer: Backend / Python Services / Valuation Math

Usage:
    python3 wacc.py --ticker NVDA --market-cap 3200000000000 --cik 0001045810 --pretty
    python3 wacc.py --ticker NVDA --market-cap 3200000000000 --beta 1.8 --cost-of-debt 0.04

Key Functions:
    - compute_beta() - Local OLS slope of ticker log returns vs SPY log returns
    - compute_cost_of_debt() - After-tax cost of debt from interest expense / total debt
    - compute_risk_free_rate() - 10Y Treasury yield via market_data.get_prices(["^TNX"])
    - compute_wacc() - Primary orchestrator: combines all inputs into a capped/floored WACC

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Internal state database)
"""

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from market_data import get_prices, get_fundamentals  # noqa: E402

WACC_FLOOR = 0.07
WACC_CAP = 0.14
DEFAULT_ERP = 0.045
DEFAULT_TAX_RATE = 0.21
FALLBACK_BETA = 1.2
FALLBACK_COST_OF_DEBT = 0.05
FALLBACK_RISK_FREE_RATE = 0.04
MIN_REGRESSION_OBSERVATIONS = 30


def compute_beta(ticker_prices: list[dict], spy_prices: list[dict]) -> dict:
    """Compute levered beta via OLS slope of ticker log returns vs SPY log returns.

    Args:
        ticker_prices: List of {"date","close",...} dicts (from market_data.get_prices()).
        spy_prices: Same shape, for SPY.

    Returns:
        {"beta": float, "usedFallback": bool, "nObservations": int}. Falls back
        to a fixed sector-average beta (never a garbage regression result) when
        fewer than 30 overlapping daily return observations are available —
        e.g. a recent IPO with no 2-year price history.
    """
    ticker_by_date = {row["date"]: row["close"] for row in ticker_prices}
    spy_by_date = {row["date"]: row["close"] for row in spy_prices}
    common_dates = sorted(set(ticker_by_date) & set(spy_by_date))

    ticker_closes = [ticker_by_date[d] for d in common_dates]
    spy_closes = [spy_by_date[d] for d in common_dates]

    ticker_returns = [
        math.log(ticker_closes[i] / ticker_closes[i - 1])
        for i in range(1, len(ticker_closes))
        if ticker_closes[i - 1] > 0 and ticker_closes[i] > 0
    ]
    spy_returns = [
        math.log(spy_closes[i] / spy_closes[i - 1])
        for i in range(1, len(spy_closes))
        if spy_closes[i - 1] > 0 and spy_closes[i] > 0
    ]

    n = min(len(ticker_returns), len(spy_returns))
    if n < MIN_REGRESSION_OBSERVATIONS:
        return {"beta": FALLBACK_BETA, "usedFallback": True, "nObservations": n}

    ticker_returns = ticker_returns[-n:]
    spy_returns = spy_returns[-n:]

    spy_mean = sum(spy_returns) / n
    ticker_mean = sum(ticker_returns) / n
    covariance = sum(
        (spy_returns[i] - spy_mean) * (ticker_returns[i] - ticker_mean) for i in range(n)
    ) / n
    variance = sum((r - spy_mean) ** 2 for r in spy_returns) / n

    if variance == 0:
        return {"beta": FALLBACK_BETA, "usedFallback": True, "nObservations": n}

    return {"beta": round(covariance / variance, 3), "usedFallback": False, "nObservations": n}


def compute_cost_of_debt(
    interest_expense: float | None, total_debt: float | None, tax_rate: float = DEFAULT_TAX_RATE
) -> dict:
    """After-tax cost of debt: interest_expense / total_debt * (1 - tax_rate).

    Returns:
        {"costOfDebt": float, "usedFallback": bool}. Falls back to a fixed
        5% pre-tax-equivalent estimate when debt or interest data is
        missing/zero — never divides by zero, never fabricates from partial data.
    """
    if not interest_expense or not total_debt or total_debt <= 0:
        return {"costOfDebt": FALLBACK_COST_OF_DEBT, "usedFallback": True}
    pre_tax = interest_expense / total_debt
    return {"costOfDebt": round(pre_tax * (1 - tax_rate), 4), "usedFallback": False}


def compute_risk_free_rate() -> dict:
    """Fetch the 10Y Treasury yield via market_data.get_prices(["^TNX"]).

    Yahoo Finance quotes ^TNX as the yield * 10 (e.g. close 42.79 = 4.279%
    yield = 0.04279 as a decimal fraction). Falls back to a fixed 4.0%
    estimate if no fresh quote is available.
    """
    prices = get_prices(["^TNX"], period="5d")
    rows = prices.get("^TNX", {}).get("data", [])
    if not rows:
        return {"riskFreeRate": FALLBACK_RISK_FREE_RATE, "usedFallback": True}
    latest_close = rows[-1]["close"]
    return {"riskFreeRate": round(latest_close / 1000, 5), "usedFallback": False}


def compute_wacc(
    ticker: str,
    market_cap: float,
    cik: str | None = None,
    erp: float = DEFAULT_ERP,
    tax_rate: float = DEFAULT_TAX_RATE,
    beta_override: float | None = None,
    cost_of_debt_override: float | None = None,
) -> dict:
    """Compute per-company WACC from risk-free rate, beta, ERP, and after-tax cost of debt.

    Capital structure weighting uses market_cap (equity) and totalDebt (debt)
    from market_data.get_fundamentals(). Result is capped/floored to
    [WACC_FLOOR, WACC_CAP] — pre-revenue/illiquid names can otherwise produce
    a garbage beta and an unusable discount rate.

    Args:
        ticker: Ticker symbol.
        market_cap: Equity market cap in dollars (caller-supplied — already
            computed upstream in the /update-stock-analysis pipeline).
        cik: SEC CIK for EDGAR lookups in get_fundamentals(), or None.
        erp: Equity risk premium (decimal), default 4.5%.
        tax_rate: Marginal tax rate for the after-tax cost of debt, default 21%.
        beta_override: Skip the OLS regression and use this beta directly.
        cost_of_debt_override: Skip the fundamentals-derived cost of debt.

    Returns:
        {"wacc", "riskFreeRate", "beta", "erp", "costOfDebt", "capApplied",
         "floorApplied", "betaWarning", "source": {"riskFree","beta","costOfDebt"}}
    """
    rf = compute_risk_free_rate()

    if beta_override is not None:
        beta_result = {"beta": beta_override, "usedFallback": False}
    else:
        prices = get_prices([ticker, "SPY"], period="2y", interval="1d")
        beta_result = compute_beta(
            prices.get(ticker, {}).get("data", []),
            prices.get("SPY", {}).get("data", []),
        )

    fundamentals = get_fundamentals(ticker, cik=cik)
    total_debt = fundamentals.get("totalDebt", {}).get("value") or 0.0

    if cost_of_debt_override is not None:
        cod_result = {"costOfDebt": cost_of_debt_override, "usedFallback": False}
    else:
        interest_expense = fundamentals.get("interestExpense", {}).get("value")
        cod_result = compute_cost_of_debt(interest_expense, total_debt, tax_rate)

    beta = beta_result["beta"]
    cost_of_equity = rf["riskFreeRate"] + beta * erp

    total_value = market_cap + total_debt
    equity_weight = market_cap / total_value if total_value > 0 else 1.0
    debt_weight = 1.0 - equity_weight

    raw_wacc = equity_weight * cost_of_equity + debt_weight * cod_result["costOfDebt"]

    beta_warning = None
    if beta > 2.5 or beta < 0.2:
        beta_warning = f"beta {beta} outside typical range [0.2, 2.5] — pre-revenue or illiquid name?"

    cap_applied = raw_wacc > WACC_CAP
    floor_applied = raw_wacc < WACC_FLOOR
    final_wacc = min(max(raw_wacc, WACC_FLOOR), WACC_CAP)

    return {
        "wacc": round(final_wacc, 4),
        "riskFreeRate": rf["riskFreeRate"],
        "beta": beta,
        "erp": erp,
        "costOfDebt": cod_result["costOfDebt"],
        "capApplied": cap_applied,
        "floorApplied": floor_applied,
        "betaWarning": beta_warning,
        "dataQuality": fundamentals.get(
            "dataQuality", {"staleness": False, "dataConflicts": [], "flags": []}
        ),
        "source": {
            "riskFree": "fallback" if rf["usedFallback"] else "market_data:^TNX",
            "beta": "override" if beta_override is not None else (
                "fallback_sector_average" if beta_result["usedFallback"] else "local_ols_2y"
            ),
            "costOfDebt": "override" if cost_of_debt_override is not None else (
                "fallback" if cod_result["usedFallback"] else "market_data:get_fundamentals"
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-company WACC calculator")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--market-cap", type=float, required=True, help="Equity market cap in dollars")
    parser.add_argument("--cik", default=None, help="SEC CIK, omit for non-US tickers")
    parser.add_argument("--erp", type=float, default=DEFAULT_ERP)
    parser.add_argument("--tax-rate", type=float, default=DEFAULT_TAX_RATE)
    parser.add_argument("--beta", type=float, default=None, help="Override computed beta")
    parser.add_argument("--cost-of-debt", type=float, default=None, help="Override computed after-tax cost of debt")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = compute_wacc(
        ticker=args.ticker,
        market_cap=args.market_cap,
        cik=args.cik,
        erp=args.erp,
        tax_rate=args.tax_rate,
        beta_override=args.beta,
        cost_of_debt_override=args.cost_of_debt,
    )
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
