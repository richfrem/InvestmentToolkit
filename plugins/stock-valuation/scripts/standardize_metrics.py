#!/usr/bin/env python3
"""
standardize_metrics.py (Python Service)
=====================================

Purpose:
    Enforces the "Canonical Calculation Policy" for fundamental analysis.
    Takes raw financial data and outputs standardized ratios and derivations
    to prevent AI "split-brain" math or inline calculation errors.

Layer: Backend / Python Services / Fundamental Analysis
"""

import json
import sys
import argparse
from typing import Any

def calculate_cagr(start_valValue: float, end_valValue: float, years: int) -> float:
    if start_valValue <= 0 or end_valValue <= 0 or years <= 0:
        return 0.0
    return round(((end_valValue / start_valValue) ** (1 / years) - 1) * 100, 2)

def standardize(raw_data: dict[str, Any]) -> dict[str, Any]:
    m = raw_data.get("metrics", {})
    price = float(m.get("price", 0))
    revenue = float(m.get("revenue", 0))
    net_income = float(m.get("net_income", 0))
    mktcap = float(m.get("market_cap", 0))
    
    # Shares Selection Logic (Mirrored from dcf_scenarios.py and ValuationModeler.tsx)
    shares_diluted = m.get("shares_diluted")
    if shares_diluted and float(shares_diluted) > 0:
        shares = float(shares_diluted)
        share_source = "shares_diluted"
    else:
        shares = mktcap / price if mktcap and price > 0 else float(m.get("shares_outstanding", 1))
        share_source = "market_cap / price" if mktcap and price > 0 else "shares_outstanding"

    # Standardized Ratios
    ps_ratio = mktcap / revenue if revenue > 0 else 0.0
    pe_ratio = price / (net_income / shares) if shares > 0 and net_income > 0 else 0.0
    profit_margin = (net_income / revenue) * 100 if revenue > 0 else 0.0

    # Growth Derivation (Historical)
    hist_rev = raw_data.get("metrics", {}).get("historical_revenue", [])
    rev_cagr_3yr = 0.0
    if len(hist_rev) >= 4: # Need 4 years for 3 growth steps
        rev_cagr_3yr = calculate_cagr(hist_rev[0], hist_rev[-1], 3)

    return {
        "ticker": raw_data.get("symbol", "UNKNOWN"),
        "snapshot": {
            "price": price,
            "shares": shares,
            "share_source": share_source,
            "revenue": revenue,
            "net_income": net_income,
            "market_cap": mktcap,
            "currency": m.get("currency", "USD")
        },
        "ratios": {
            "ps_ratio": round(ps_ratio, 2),
            "pe_ratio": round(pe_ratio, 2),
            "profit_margin": round(profit_margin, 2),
            "rev_cagr_3yr": rev_cagr_3yr
        },
        "quality_flags": []
    }

def main():
    parser = argparse.ArgumentParser(description="Standardize fundamental metrics")
    parser.add_argument("input", help="Path to raw financial JSON, or '-' for stdin")
    args = parser.parse_args()

    if args.input == "-":
        raw_data = json.load(sys.stdin)
    else:
        with open(args.input) as f:
            raw_data = json.load(f)

    result = standardize(raw_data)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
