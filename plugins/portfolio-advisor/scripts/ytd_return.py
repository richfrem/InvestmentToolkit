#!/usr/bin/env python3
"""
ytd_return.py - Time-weighted rate of return performance tracker.

Purpose:
    Computes both Simple Return and Time-Weighted Rate of Return (TWR) to adjust
    for cash inflows/outflows, giving a pure representation of portfolio performance.

Layer:
    Codify

Usage Examples:
    python3 plugins/portfolio-advisor/scripts/ytd_return.py [--json]

Key Functions (Index):
    - load_json(path) - Loads JSON file from path
    - calculate_simple_metrics(current_value, cash_flows) - Calculates simple return and dollar gains
    - calculate_twr_return(initial_value, final_value, subperiod_cash_flows) - Computes subperiod TWR percentage
    - save_and_print_report(report_data, is_json_mode) - Persists performance metrics to output path
    - calculate_twr() - Main execution pipeline orchestrator

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Live portfolio balances)
    - investment_screener/backend/data/cash_flows.json (Deposit & withdrawal history)

Key Output Dependencies:
    - investment_screener/backend/data/ytd_performance_report.json (TWR performance metrics)
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Resolve project paths
REPO_ROOT = Path(__file__).resolve().parents[3]
PORTFOLIO_PATH = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
CASH_FLOWS_PATH = REPO_ROOT / "investment_screener/backend/data/cash_flows.json"


# External comment: Reads file contents as JSON
def load_json(path: Path) -> Dict[str, Any]:
    """Load and parse JSON from a path, returning empty dict if missing."""
    if not path.exists():
        print(f"Warning: {path.name} not found at {path}", file=sys.stderr)
        return {}
    with open(path) as f:
        return json.load(f)


# External comment: Computes simple return metrics based on starting and ending balances
def calculate_simple_metrics(
    starting_balance: float, 
    current_balance: float, 
    flows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Computes deposits, withdrawals, net flows, net capital invested, simple gain, and simple return %.
    """
    total_deposits = sum(f["amount_cad"] for f in flows if f["type"] == "deposit")
    total_withdrawals = sum(f["amount_cad"] for f in flows if f["type"] == "withdrawal")
    net_flows = total_deposits - total_withdrawals
    net_capital_invested = starting_balance + net_flows

    simple_gain = current_balance - net_capital_invested
    simple_return = (simple_gain / net_capital_invested) * 100 if net_capital_invested > 0 else 0.0

    return {
        "total_deposits": total_deposits,
        "total_withdrawals": total_withdrawals,
        "net_flows": net_flows,
        "net_capital_invested": net_capital_invested,
        "simple_gain": simple_gain,
        "simple_return": simple_return,
    }


# External comment: Computes the Time-Weighted Rate of Return across sub-periods
def calculate_twr_return(
    starting_balance: float, 
    current_balance: float, 
    flows: List[Dict[str, Any]], 
    is_json_mode: bool
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Compounds chronological sub-period returns to derive the TWR % metric.
    """
    sorted_flows = sorted(flows, key=lambda x: x["date"])
    prev_start_value = starting_balance
    
    if not is_json_mode:
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
            end_value = prev_start_value

        # Compound the sub-period yield
        sub_period_return = (end_value - prev_start_value) / prev_start_value
        twr_product *= (1 + sub_period_return)

        flow_signed = flow_amount if flow_type == "deposit" else -flow_amount
        period_start_str = "2026-01-01" if i == 0 else sorted_flows[i-1]["date"]
        
        if not is_json_mode:
            print(f"{period_start_str:<12} | {flow_date:<12} | {prev_start_value:15,.2f} | {end_value:15,.2f} | {flow_signed:+12,.2f} | {sub_period_return*100:+9.2f}%")

        prev_start_value = end_value + flow_signed

    # Final sub-period evaluation
    final_start_date = sorted_flows[-1]["date"] if sorted_flows else "2026-01-01"
    sub_period_return = (current_balance - prev_start_value) / prev_start_value
    twr_product *= (1 + sub_period_return)
    
    if not is_json_mode:
        print(f"{final_start_date:<12} | {'Current':<12} | {prev_start_value:15,.2f} | {current_balance:15,.2f} | {'--':>12} | {sub_period_return*100:+9.2f}%")
        print("=" * 80)

    twr_return = (twr_product - 1) * 100
    return twr_return, sorted_flows


# External comment: Persists the performance JSON report and prints visual metrics
def save_and_print_report(report_data: Dict[str, Any], is_json_mode: bool) -> None:
    """
    Saves YTD statistics to disk and presents visual summary tables to stdout.
    """
    report_out_path = REPO_ROOT / "investment_screener/backend/data/ytd_performance_report.json"
    with open(report_out_path, "w") as f:
        json.dump(report_data, f, indent=2)

    if is_json_mode:
        print(json.dumps(report_data))
    else:
        print("\n" + "=" * 40)
        print("  YTD PERFORMANCE SUMMARY REPORT (CAD)")
        print("=" * 40)
        print(f"  Starting Balance (Jan 1):  ${report_data['starting_balance_cad']:,.2f} CAD")
        print(f"  Total Cash Deposits:       ${report_data['total_deposits_cad']:,.2f} CAD")
        print(f"  Total Cash Withdrawals:    ${report_data['total_withdrawals_cad']:,.2f} CAD")
        print(f"  Net Cash Flows:           {report_data['net_cash_flows_cad']:+,.2f} CAD")
        print(f"  Net Capital Invested:      ${report_data['net_capital_invested_cad']:,.2f} CAD")
        print(f"  Current Balance:           ${report_data['ending_balance_cad']:,.2f} CAD")
        print(f"  Dollar Value Change:       {report_data['dollar_gain_cad']:+,.2f} CAD")
        print("-" * 40)
        print(f"  Simple Net Return:         {report_data['simple_return_pct']:+.2f}%")
        print(f"  Time-Weighted Return (TWR): {report_data['time_weighted_return_pct']:+.2f}%")
        print("=" * 40 + "\n")
        print(f"✓ Saved YTD performance report to backend/data/ytd_performance_report.json")


# External comment: Orchestrates the calculation pipeline
def calculate_twr() -> None:
    """
    Main execution pipeline for loading, evaluating, and saving YTD statistics.
    """
    is_json_mode = "--json" in sys.argv
    flows_data = load_json(CASH_FLOWS_PATH)
    portfolio_data = load_json(PORTFOLIO_PATH)

    if not flows_data:
        if is_json_mode:
            print(json.dumps({"error": "cash_flows.json data is required."}))
        else:
            print("Error: cash_flows.json data is required.")
        sys.exit(1)

    starting_balance = flows_data.get("starting_balance_cad", 0.0)
    current_balance = (portfolio_data.get("totals") or {}).get("totalCAD", 0.0)
    flows = flows_data.get("cash_flows", [])

    if starting_balance <= 0:
        if is_json_mode:
            print(json.dumps({"error": "starting_balance_cad must be greater than 0."}))
        else:
            print("Error: starting_balance_cad must be greater than 0.")
        sys.exit(1)

    # 1. Simple Return Calculation
    simple_metrics = calculate_simple_metrics(starting_balance, current_balance, flows)

    # 2. Time-Weighted Return (TWR) Calculation
    twr_return, sorted_flows = calculate_twr_return(starting_balance, current_balance, flows, is_json_mode)

    # 3. Save and output
    report_data = {
        "starting_balance_cad": starting_balance,
        "ending_balance_cad": current_balance,
        "total_deposits_cad": simple_metrics["total_deposits"],
        "total_withdrawals_cad": simple_metrics["total_withdrawals"],
        "net_cash_flows_cad": simple_metrics["net_flows"],
        "net_capital_invested_cad": simple_metrics["net_capital_invested"],
        "dollar_gain_cad": simple_metrics["simple_gain"],
        "simple_return_pct": simple_metrics["simple_return"],
        "time_weighted_return_pct": twr_return,
        "sub_periods": sorted_flows
    }
    
    save_and_print_report(report_data, is_json_mode)


if __name__ == "__main__":
    calculate_twr()
