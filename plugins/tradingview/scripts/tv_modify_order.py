#!/usr/bin/env python3
"""
tv_modify_order.py (CLI)
=====================================

Purpose:
    Modify the limit price (and optionally quantity) of a Working or Inactive order
    in TradingView via CDP. Clicks the pencil (✏) button on the order row, fills the
    modify form using keyboard events (required to trigger React onChange), then clicks
    the Confirm / Send Order button. Two-step: modifyOrder() fills the form;
    submitModify() confirms.

Layer: Backend / Brokerage Automation

Usage Examples:
    # Modify price only (preferred — UUID is unique):
    python3 plugins/tradingview/scripts/tv_modify_order.py \
        --order-id 292b5304-0c3d-42c2-02c0-290f6d322c12 \
        --new-price 47.00

    # With ticker/action hints for row matching:
    python3 plugins/tradingview/scripts/tv_modify_order.py \
        --order-id 292b5304-0c3d-42c2-02c0-290f6d322c12 \
        --ticker INTC --action buy --new-price 47.00

    # Modify price and quantity:
    python3 plugins/tradingview/scripts/tv_modify_order.py \
        --order-id <uuid> --new-price 47.00 --new-shares 5

    # JSON output (for piping):
    python3 plugins/tradingview/scripts/tv_modify_order.py \
        --order-id <uuid> --new-price 47.00 --json

CLI Arguments:
    --order-id      TradingView order UUID (required)
    --new-price     New limit price (required)
    --new-shares    New share quantity (optional)
    --ticker        Ticker hint for row matching (optional)
    --action        Side hint: buy or sell (optional)
    --json          Output raw JSON instead of human-readable text

Output:
    Human-readable: "✅ Order <id>… modified → $47.00"
    JSON: { "modified": true, "modifyResult": {...}, "submitResult": {...} }

Key Functions:
    - modify_order() - Calls modifyOrder() + submitModify() in trading.js
    - main()         - CLI entry point

Script Dependencies:
    - plugins/tradingview/node/core/trading.js (modifyOrder, submitModify exports)
    - TradingView Desktop running with --remote-debugging-port=9222

Consumed by:
    - skills/modify-order/SKILL.md (via symlink)
    - investment_screener/backend/src/routes/trading.ts (PUT /api/trading/modify)
"""

import sys
import os
import json
import argparse
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
TV_NODE_DIR = os.path.join(REPO_ROOT, "plugins", "tradingview", "node")


def _run_node(js: str, timeout: int = 30) -> dict:
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


def modify_order(order_id: str, new_price: float, new_shares: int | None = None,
                 ticker: str | None = None, action: str | None = None) -> dict:
    """
    Modify a TradingView order's limit price (and optionally quantity).

    Calls modifyOrder() to fill the edit form, then submitModify() to confirm.

    Args:
        order_id:   TV order UUID to modify.
        new_price:  New limit price to set.
        new_shares: New share quantity (pass None to leave unchanged).
        ticker:     Ticker hint for DOM row matching.
        action:     Side hint ("Buy" or "Sell").

    Returns:
        { "modified": bool, "modifyResult": dict, "submitResult": dict }
        or { "modified": false, "error": str }
    """
    js = f"""
import {{ modifyOrder, submitModify }} from './core/trading.js';
try {{
    const modify = await modifyOrder({{
        orderId: {json.dumps(order_id)},
        ticker: {json.dumps(ticker)},
        action: {json.dumps(action)},
        newLimitPrice: {json.dumps(new_price)},
        newShares: {json.dumps(new_shares)},
    }});
    const submit = await submitModify({{
        ticker: {json.dumps(ticker)},
        action: {json.dumps(action)},
        newPrice: {json.dumps(new_price)},
        orderId: {json.dumps(order_id)},
    }});
    process.stdout.write(JSON.stringify({{ modified: true, modifyResult: modify, submitResult: submit }}) + '\\n');
    process.exit(0);
}} catch(e) {{
    process.stdout.write(JSON.stringify({{ modified: false, error: e.message }}) + '\\n');
    process.exit(1);
}}
"""
    return _run_node(js, timeout=30)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Modify a TradingView order via CDP")
    parser.add_argument("--order-id", required=True, help="TradingView order UUID")
    parser.add_argument("--new-price", type=float, required=True, help="New limit price")
    parser.add_argument("--new-shares", type=int, default=None, help="New quantity (optional)")
    parser.add_argument("--ticker", default=None, help="Ticker hint for row matching")
    parser.add_argument("--action", default=None, choices=["buy", "sell", "Buy", "Sell"],
                        help="Side hint for row matching")
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Output raw JSON (default: human-readable)")
    args = parser.parse_args()

    action = args.action.capitalize() if args.action else None

    try:
        result = modify_order(
            order_id=args.order_id,
            new_price=args.new_price,
            new_shares=args.new_shares,
            ticker=args.ticker,
            action=action,
        )
    except Exception as e:
        print(json.dumps({"modified": False, "error": str(e)}))
        sys.exit(1)

    if args.json_out:
        print(json.dumps(result, indent=2))
        return

    if result.get("modified"):
        print(f"✅ Order {args.order_id[:8]}… modified → ${args.new_price:.2f}")
        submit = result.get("submitResult", {})
        if submit.get("clicked"):
            print(f"   Confirmed: {submit['clicked']}")
        if submit.get("priceMatch") is False:
            print("   ⚠️  Broker panel may need a moment to refresh — verify in TV.")
    else:
        print(f"❌ Modify failed: {result.get('error', 'unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
