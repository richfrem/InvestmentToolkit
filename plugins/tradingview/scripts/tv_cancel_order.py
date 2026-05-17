#!/usr/bin/env python3
"""
tv_cancel_order.py (CLI)
=====================================

Purpose:
    Cancel a Working or Inactive order in TradingView via CDP by locating the order
    row by UUID and clicking its × cancel button. Handles TV's secondary confirmation
    dialog ("Cancel order" / "Keep order") automatically. Does NOT modify the Trade Log;
    use POST /api/trading/cancel (backend route) for the full cancel + log update flow.

Layer: Backend / Brokerage Automation

Usage Examples:
    # Cancel by UUID (preferred):
    python3 plugins/tradingview/scripts/tv_cancel_order.py \
        --order-id 292b5304-0c3d-42c2-02c0-290f6d322c12

    # With hints for fallback row matching:
    python3 plugins/tradingview/scripts/tv_cancel_order.py \
        --order-id 292b5304-0c3d-42c2-02c0-290f6d322c12 \
        --ticker INTC --action buy --limit-price 47.00

    # JSON output (for piping):
    python3 plugins/tradingview/scripts/tv_cancel_order.py \
        --order-id <uuid> --json

CLI Arguments:
    --order-id      TradingView order UUID (required)
    --ticker        Ticker hint for fallback row matching (optional)
    --action        Side hint: buy or sell (optional)
    --limit-price   Price hint for fallback row matching (optional)
    --json          Output raw JSON instead of human-readable text

Output:
    Human-readable: "✅ Order <id>… cancelled (verified gone)"
    JSON: { "cancelled": true, "verified": true, "orderId": "...", "ticker": "..." }

Key Functions:
    - cancel_order() - Calls cancelOrder() in trading.js via Node.js subprocess
    - main()         - CLI entry point; parses args, calls cancel_order, prints result

Script Dependencies:
    - plugins/tradingview/node/core/trading.js (cancelOrder export)
    - TradingView Desktop running with --remote-debugging-port=9222

Consumed by:
    - skills/cancel-order/SKILL.md (via symlink)
    - investment_screener/backend/src/routes/trading.ts (POST /api/trading/cancel)
    - investment_screener/backend/py_services/place_order.py --cancel
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
        js: ES module source code as a string (run via --input-type=module).
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


def cancel_order(order_id: str, ticker: str | None = None,
                 action: str | None = None, limit_price: float | None = None) -> dict:
    """
    Cancel a Working or Inactive order in TradingView by UUID.

    Args:
        order_id:    TV order UUID to cancel.
        ticker:      Ticker hint for DOM row matching if UUID is not found directly.
        action:      Side hint ("Buy" or "Sell").
        limit_price: Price hint for row matching.

    Returns:
        { "cancelled": bool, "verified": bool, "orderId": str, "ticker": str }
    """
    js = f"""
import {{ cancelOrder }} from './core/trading.js';
try {{
    const result = await cancelOrder({{
        orderId: {json.dumps(order_id)},
        ticker: {json.dumps(ticker)},
        action: {json.dumps(action)},
        limitPrice: {json.dumps(limit_price)},
    }});
    process.stdout.write(JSON.stringify(result) + '\\n');
    process.exit(result.cancelled ? 0 : 1);
}} catch(e) {{
    process.stdout.write(JSON.stringify({{ cancelled: false, error: e.message }}) + '\\n');
    process.exit(1);
}}
"""
    return _run_node(js)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Cancel a TradingView order via CDP")
    parser.add_argument("--order-id", required=True, help="TradingView order UUID")
    parser.add_argument("--ticker", default=None, help="Ticker hint (for row matching)")
    parser.add_argument("--action", default=None, choices=["buy", "sell", "Buy", "Sell"],
                        help="Side hint")
    parser.add_argument("--limit-price", type=float, default=None, help="Price hint")
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Output raw JSON")
    args = parser.parse_args()

    action = args.action.capitalize() if args.action else None

    try:
        result = cancel_order(
            order_id=args.order_id,
            ticker=args.ticker,
            action=action,
            limit_price=args.limit_price,
        )
    except Exception as e:
        print(json.dumps({"cancelled": False, "error": str(e)}))
        sys.exit(1)

    if args.json_out:
        print(json.dumps(result, indent=2))
        return

    if result.get("cancelled"):
        verified = " (verified gone)" if result.get("verified") else ""
        print(f"✅ Order {args.order_id[:8]}… cancelled{verified}")
    else:
        print(f"❌ Cancel failed: {result.get('error', 'unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
