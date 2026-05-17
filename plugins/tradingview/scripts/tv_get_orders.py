#!/usr/bin/env python3
"""
tv_get_orders.py (CLI)
=====================================

Purpose:
    Read Working and Inactive orders from TradingView's broker panel via CDP.
    Returns order rows as structured JSON (orderId + raw row text). Useful for
    verifying open orders, scripting order management, or checking what's live
    in the broker panel without opening TradingView manually.

Layer: Backend / Brokerage Automation

Usage Examples:
    # List all open orders (Working + Inactive):
    python3 plugins/tradingview/scripts/tv_get_orders.py

    # Filter by ticker:
    python3 plugins/tradingview/scripts/tv_get_orders.py --ticker INTC

    # JSON output (for piping to jq or other scripts):
    python3 plugins/tradingview/scripts/tv_get_orders.py --json

    # Working orders only:
    python3 plugins/tradingview/scripts/tv_get_orders.py --tab working

CLI Arguments:
    --ticker    Filter output to rows containing this ticker symbol (optional)
    --tab       Which broker panel tab to read: all | working | inactive (default: all)
    --json      Output raw JSON instead of human-readable table

Output:
    Human-readable: table of orderId + row text
    JSON: { "found": bool, "orders": [{ "orderId": "...", "text": "..." }, ...] }

Key Functions:
    - get_orders()  - Calls verifyOrderInBrokerPanel() in trading.js
    - main()        - CLI entry point; parses args, prints results

Script Dependencies:
    - plugins/tradingview/node/core/trading.js (verifyOrderInBrokerPanel export)
    - TradingView Desktop running with --remote-debugging-port=9222

Consumed by:
    - skills/get-orders/SKILL.md (via symlink)
"""

import sys
import os
import json
import argparse
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
TV_NODE_DIR = os.path.join(REPO_ROOT, "plugins", "tradingview", "node")


def _run_node(js: str, timeout: int = 15) -> dict:
    """
    Run inline Node.js ES module code in the tradingview/node context.

    Args:
        js:      ES module source code (run via --input-type=module).
        timeout: Seconds before subprocess is killed.

    Returns:
        Parsed JSON dict from stdout, or { "raw": ..., "stderr": ... } on decode failure.

    Raises:
        RuntimeError: If Node exits non-zero with no stdout.
    """
    result = subprocess.run(
        ["node", "--input-type=module"],
        input=js,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=TV_NODE_DIR,
    )
    if result.returncode != 0 and not result.stdout.strip():
        raise RuntimeError(f"Node error: {result.stderr.strip()[:500]}")
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return {"raw": result.stdout.strip(), "stderr": result.stderr.strip()}


def get_orders(ticker: str | None = None) -> dict:
    """
    Read all open orders (Working + Inactive) from TradingView's broker panel.

    Args:
        ticker: Optional ticker filter — only rows containing this symbol are returned.

    Returns:
        { "found": bool, "orders": [{ "orderId": str, "ticker": str, "side": str,
                                      "limitPrice": float, "status": str, "text": str }] }
    """
    js = f"""
import {{ listOpenOrders }} from './core/trading.js';
try {{
    const result = await listOpenOrders();
    const ticker = {json.dumps(ticker)};
    if (ticker && result.orders) {{
        result.orders = result.orders.filter(o => o.ticker && o.ticker.toUpperCase() === ticker.toUpperCase());
    }}
    process.stdout.write(JSON.stringify(result) + '\\n');
    process.exit(0);
}} catch(e) {{
    process.stdout.write(JSON.stringify({{ found: false, error: e.message }}) + '\\n');
    process.exit(1);
}}
"""
    return _run_node(js)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="List open orders from TradingView broker panel")
    parser.add_argument("--ticker", default=None, help="Filter by ticker symbol")
    parser.add_argument("--tab", default="all", choices=["all", "working", "inactive"],
                        help="Which broker panel tab to read (currently informational; all rows are returned)")
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Output raw JSON (default: human-readable table)")
    args = parser.parse_args()

    try:
        result = get_orders(ticker=args.ticker)
    except Exception as e:
        print(json.dumps({"found": False, "error": str(e)}))
        sys.exit(1)

    if args.json_out:
        print(json.dumps(result, indent=2))
        return

    orders = result.get("orders", [])
    if not orders:
        label = f" for {args.ticker}" if args.ticker else ""
        print(f"No orders found{label}.")
        return

    print(f"{'Order ID':<38}  Text")
    print("-" * 80)
    for o in orders:
        oid = o.get("orderId", "?")
        text = o.get("text", "")[:60]
        print(f"{oid:<38}  {text}")
    print(f"\n{len(orders)} order(s) found.")


if __name__ == "__main__":
    main()
