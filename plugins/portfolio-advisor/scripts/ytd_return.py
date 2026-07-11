#!/usr/bin/env python3
"""
ytd_return.py — Performance tracking script for calculating YTD returns.

Computes both Simple Return and Time-Weighted Rate of Return (TWR) to adjust
for cash inflows/outflows, giving a pure representation of portfolio performance.

Usage:
    python3 plugins/portfolio-advisor/scripts/ytd_return.py
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Resolve project paths
REPO_ROOT = Path(__file__).resolve().parents[3]
PORTFOLIO_PATH = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
CASH_FLOWS_PATH = REPO_ROOT / "investment_screener/backend/data/cash_flows.json"


def load_json(path: Path) -> Dict[str, Any]:
    """Load and parse JSON from a path, returning empty dict if missing."""
    if not path.exists():
        print(f"Warning: {path.name} not found at {path}", file=sys.stderr)
        return {}
    with open(path) as f:
        return json.load(f)


def calculate_twr() -> None:
    """Calculate and print Simple and Time-Weighted YTD returns."""
    flows_data = load_json(CASH_FLOWS_PATH)
    portfolio_data = load_json(PORTFOLIO_PATH)

    if not flows_data:
        print("Error: cash_flows.json data is required.")
        sys.exit(1)

    starting_balance = flows_data.get("starting_balance_cad", 0.0)
    current_balance = (portfolio_data.get("totals") or {}).get("totalCAD", 0.0)
    flows = flows_data.get("cash_flows", [])

    if starting_balance <= 0:
        print("Error: starting_balance_cad must be greater than 0.")
        sys.exit(1)

    # 1. Simple Return Calculation
    total_deposits = sum(f["amount_cad"] for f in flows if f["type"] == "deposit")
    total_withdrawals = sum(f["amount_cad"] for f in flows if f["type"] == "withdrawal")
    net_flows = total_deposits - total_withdrawals
    net_capital_invested = starting_balance + net_flows

    simple_gain = current_balance - net_capital_invested
    simple_return = (simple_gain / net_capital_invested) * 100 if net_capital_invested > 0 else 0.0

    # 2. Time-Weighted Return (TWR) Calculation
    # We sort flows chronologically by date
    sorted_flows = sorted(flows, key=lambda x: x["date"])
    
    sub_periods = []
    prev_start_value = starting_balance
    
    print("\n" + "=" * 80)
    print("  TIME-WEIGHTED RATE OF RETURN (TWR) SUB-PERIODS")
    print("=" * 80)
    print(f"{'Period Start':<12} | {'Period End':<12} | {'Start Val (CAD)':<15} | {'End Val (CAD)':<15} | {'Flow (CAD)':<12} | {'Return %':<10}")
    print("-" * 80)

    twr_product = 1.0

    for i, flow in enumerate(sorted_flows):
        flow_date = flow["date"]
        flow_type = flow["type"]
        flow_amount = flow["amount_cad"]
        end_value = flow.get("portfolio_value_before_flow_cad")

        if end_value is None:
            # Fallback estimation if not provided: assume no change
            end_value = prev_start_value

        # Calculate sub-period return
        sub_period_return = (end_value - prev_start_value) / prev_start_value
        twr_product *= (1 + sub_period_return)

        flow_signed = flow_amount if flow_type == "deposit" else -flow_amount
        
        # Print sub-period details
        period_start_str = "2026-01-01" if i == 0 else sorted_flows[i-1]["date"]
        print(f"{period_start_str:<12} | {flow_date:<12} | {prev_start_value:15,.2f} | {end_value:15,.2f} | {flow_signed:+12,.2f} | {sub_period_return*100:+9.2f}%")

        # Set start value for next period (incorporating the cash flow)
        prev_start_value = end_value + flow_signed

    # Final sub-period from last flow to current date
    final_start_date = sorted_flows[-1]["date"] if sorted_flows else "2026-01-01"
    sub_period_return = (current_balance - prev_start_value) / prev_start_value
    twr_product *= (1 + sub_period_return)
    
    print(f"{final_start_date:<12} | {'Current':<12} | {prev_start_value:15,.2f} | {current_balance:15,.2f} | {'--':>12} | {sub_period_return*100:+9.2f}%")
    print("=" * 80)

    twr_return = (twr_product - 1) * 100

    # 3. Write JSON Report based on template
    report_data = {
        "starting_balance_cad": starting_balance,
        "ending_balance_cad": current_balance,
        "total_deposits_cad": total_deposits,
        "total_withdrawals_cad": total_withdrawals,
        "net_cash_flows_cad": net_flows,
        "net_capital_invested_cad": net_capital_invested,
        "dollar_gain_cad": simple_gain,
        "simple_return_pct": simple_return,
        "time_weighted_return_pct": twr_return,
        "sub_periods": sorted_flows
    }
    
    report_out_path = REPO_ROOT / "investment_screener/backend/data/ytd_performance_report.json"
    with open(report_out_path, "w") as f:
        json.dump(report_data, f, indent=2)

    # 4. Print Summary Report
    print("\n" + "=" * 40)
    print("  YTD PERFORMANCE SUMMARY REPORT (CAD)")
    print("=" * 40)
    print(f"  Starting Balance (Jan 1):  ${starting_balance:,.2f} CAD")
    print(f"  Total Cash Deposits:       ${total_deposits:,.2f} CAD")
    print(f"  Total Cash Withdrawals:    ${total_withdrawals:,.2f} CAD")
    print(f"  Net Cash Flows:           {net_flows:+,.2f} CAD")
    print(f"  Net Capital Invested:      ${net_capital_invested:,.2f} CAD")
    print(f"  Current Balance:           ${current_balance:,.2f} CAD")
    print(f"  Dollar Value Change:       {simple_gain:+,.2f} CAD")
    print("-" * 40)
    print(f"  Simple Net Return:         {simple_return:+.2f}%")
    print(f"  Time-Weighted Return (TWR): {twr_return:+.2f}%")
    print("=" * 40 + "\n")
    print(f"✓ Saved YTD performance report to backend/data/ytd_performance_report.json")


if __name__ == "__main__":
    calculate_twr()
