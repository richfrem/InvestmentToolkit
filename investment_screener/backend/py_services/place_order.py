#!/usr/bin/env python3
"""
place_order.py (Python Utility)
=====================================

Purpose:
    Preflight-check and execute buy/sell orders via TradingView's built-in
    Questrade broker integration (automated via CDP DOM). Pre-flight checks
    broker connection, buying power, and account before showing a confirmation
    card. On --execute, drives the TradingView order dialog end-to-end,
    screenshots the filled form, and submits after HITL approval. Triggers
    a portfolio sync after execution to refresh portfolio.json.

Layer: Backend / py_services / Brokerage

Usage Examples:
    # Preflight — show card, no dialog opened:
    python3 investment_screener/backend/py_services/place_order.py \
        --ticker WYFI --action buy --shares 1 --order-type market \
        --account tfsa --preflight

    # Execute — fill TradingView order dialog and submit:
    python3 investment_screener/backend/py_services/place_order.py \
        --ticker WYFI --action buy --shares 1 --order-type market \
        --account tfsa --execute

    # Limit order:
    python3 investment_screener/backend/py_services/place_order.py \
        --ticker NVDA --action buy --shares 5 --order-type limit --limit-price 140.00 \
        --account tfsa --preflight

Key Functions:
    - preflight() - Checks TV broker status, buying power, returns confirmation card
    - execute_order() - Runs Node.js trading.js to fill + submit the TV order dialog
    - sync_portfolio() - Triggers QuestradeDataEngine sync after fill
"""

import sys
import os
import json
import argparse
import subprocess
import logging
from typing import Optional
from datetime import datetime, timezone

# ── path bootstrap ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
BACKEND_SRC = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "src"))
TV_NODE_DIR = os.path.join(REPO_ROOT, "plugins", "tradingview", "node")

sys.path.insert(0, BACKEND_SRC)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

PORTFOLIO_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "data", "portfolio.json"))
DATA_FRESHNESS_LIMIT_MINUTES = 60


def _check_data_freshness(ack_stale: bool = False) -> dict | None:
    """Returns a freshness warning dict if portfolio.json is stale, else None.
    If ack_stale is True, logs a warning but does not block."""
    if not os.path.exists(PORTFOLIO_PATH):
        return {"stale": True, "reason": "portfolio.json not found — run /tv-portfolio-sync first"}
    import time as _time
    age_minutes = (_time.time() - os.path.getmtime(PORTFOLIO_PATH)) / 60
    if age_minutes > DATA_FRESHNESS_LIMIT_MINUTES and not ack_stale:
        return {"stale": True, "age_minutes": round(age_minutes, 1),
                "reason": f"portfolio.json is {age_minutes:.0f} min old (limit {DATA_FRESHNESS_LIMIT_MINUTES} min). "
                          "Run /tv-portfolio-sync or pass --ack-stale to override."}
    return None

# ── Node.js runner ───────────────────────────────────────────────────────────

def _run_node(script_js: str, timeout: int = 30) -> dict:
    """Run inline Node.js ES module code in the tradingview/node context."""
    result = subprocess.run(
        ["node", "--input-type=module"],
        input=script_js,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=TV_NODE_DIR,
    )
    if result.returncode != 0 and not result.stdout.strip():
        stderr = result.stderr.strip()
        raise RuntimeError(f"Node.js error: {stderr[:500]}")
    # Try to parse JSON from stdout
    stdout = result.stdout.strip()
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        # Return raw output wrapped
        return {"raw": stdout, "stderr": result.stderr.strip()}


# ── preflight ────────────────────────────────────────────────────────────────

def preflight(ticker: str, action: str, shares: int, order_type: str,
              limit_price: Optional[float], account_type: str) -> dict:
    """Check broker status + buying power via CDP. Returns confirmation card."""
    js = f"""
import {{ preflight }} from './core/trading.js';
try {{
    const card = await preflight({{
        ticker: {json.dumps(ticker)},
        action: {json.dumps(action)},
        shares: {shares},
        orderType: {json.dumps(order_type.capitalize())},
        limitPrice: {json.dumps(limit_price)},
        accountType: {json.dumps(account_type.upper())},
    }});
    process.stdout.write(JSON.stringify(card) + '\\n');
    process.exit(0);
}} catch(e) {{
    process.stdout.write(JSON.stringify({{ error: e.message }}) + '\\n');
    process.exit(1);
}}
"""
    return _run_node(js)


# ── execute ──────────────────────────────────────────────────────────────────

def execute_order(ticker: str, action: str, shares: int, order_type: str,
                  limit_price: Optional[float], account_type: str) -> dict:
    """Switch TV chart to ticker, open order dialog, fill it, screenshot."""
    exec_js = f"""
import {{ executeOrder }} from './core/trading.js';
try {{
    const result = await executeOrder({{
        ticker: {json.dumps(ticker)},
        action: {json.dumps(action)},
        shares: {shares},
        orderType: {json.dumps(order_type)},
        limitPrice: {json.dumps(limit_price)},
        accountType: {json.dumps(account_type.upper())},
    }});
    process.stdout.write(JSON.stringify(result) + '\\n');
    process.exit(0);
}} catch(e) {{
    process.stdout.write(JSON.stringify({{ error: e.message }}) + '\\n');
    process.exit(1);
}}
"""
    return _run_node(exec_js, timeout=45)


def modify_order(tv_order_id: str, new_price: float, new_shares: Optional[int] = None,
                 ticker: Optional[str] = None, action: Optional[str] = None) -> dict:
    """
    Modify a Working/Inactive order's limit price (and optionally quantity) via CDP.

    Args:
        tv_order_id: TradingView order UUID.
        new_price:   New limit price.
        new_shares:  New quantity (None = leave unchanged).
        ticker:      Ticker hint for row matching.
        action:      Side hint ("Buy" or "Sell").

    Returns:
        { "modified": bool, "modifyResult": dict, "submitResult": dict }
    """
    js = f"""
import {{ modifyOrder, submitModify }} from './core/trading.js';
try {{
    const modify = await modifyOrder({{
        orderId: {json.dumps(tv_order_id)},
        ticker: {json.dumps(ticker)},
        action: {json.dumps(action)},
        newLimitPrice: {json.dumps(new_price)},
        newShares: {json.dumps(new_shares)},
    }});
    const submit = await submitModify({{
        ticker: {json.dumps(ticker)},
        action: {json.dumps(action)},
        newPrice: {json.dumps(new_price)},
        orderId: {json.dumps(tv_order_id)},
    }});
    process.stdout.write(JSON.stringify({{ modified: true, modifyResult: modify, submitResult: submit }}) + '\\n');
    process.exit(0);
}} catch(e) {{
    process.stdout.write(JSON.stringify({{ modified: false, error: e.message }}) + '\\n');
    process.exit(1);
}}
"""
    return _run_node(js, timeout=30)


def cancel_order(tv_order_id: str, ticker: Optional[str] = None,
                 action: Optional[str] = None, limit_price: Optional[float] = None) -> dict:
    """Cancel a Working/Inactive order in TradingView via CDP."""
    js = f"""
import {{ cancelOrder }} from './core/trading.js';
try {{
    const result = await cancelOrder({{
        orderId: {json.dumps(tv_order_id)},
        ticker: {json.dumps(ticker)},
        action: {json.dumps(action)},
        limitPrice: {json.dumps(limit_price)},
    }});
    process.stdout.write(JSON.stringify(result) + '\\n');
    process.exit(result.cancelled ? 0 : 1);
}} catch(e) {{
    process.stdout.write(JSON.stringify({{ error: e.message, cancelled: false }}) + '\\n');
    process.exit(1);
}}
"""
    return _run_node(js, timeout=15)


def submit_order(ticker: Optional[str] = None, action: Optional[str] = None,
                 limit_price: Optional[float] = None) -> dict:
    """Click the submit button — call only after HITL approval.
    Passes ticker/action/limitPrice to confirmAndSubmit so it can read the
    broker panel afterward and verify the order was registered."""
    js = f"""
import {{ confirmAndSubmit }} from './core/trading.js';
try {{
    const result = await confirmAndSubmit({{
        ticker: {json.dumps(ticker)},
        action: {json.dumps(action)},
        limitPrice: {json.dumps(limit_price)},
    }});
    process.stdout.write(JSON.stringify(result) + '\\n');
    process.exit(0);
}} catch(e) {{
    process.stdout.write(JSON.stringify({{ error: e.message }}) + '\\n');
    process.exit(1);
}}
"""
    return _run_node(js, timeout=20)


# ── portfolio sync ────────────────────────────────────────────────────────────

def sync_portfolio() -> bool:
    """Run QuestradeDataEngine to refresh portfolio.json after order fill."""
    engine_path = os.path.abspath(os.path.join(BACKEND_SRC, "QuestradeDataEngine.py"))
    cache_dir   = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
    portfolio_path = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "data", "portfolio.json"))
    result = subprocess.run(
        [sys.executable, engine_path, "--cache-dir",
         os.path.join(cache_dir, "backend"), "--output", portfolio_path],
        capture_output=True, text=True,
    )
    return result.returncode == 0


# ── terminal card ─────────────────────────────────────────────────────────────

def _format_card(card: dict) -> str:
    lines = [
        "",
        "╔══════════════════════════════════════════════════════╗",
        "║           ORDER CONFIRMATION REQUIRED                ║",
        "╠══════════════════════════════════════════════════════╣",
    ]
    w = 54

    def row(label: str, value: str, flag: str = "") -> str:
        combined = f"{label:<18}{value}"
        if flag:
            combined += f"  {flag}"
        return f"║  {combined:<{w}}║"

    lines.append(row("Via:", "TradingView (Questrade)"))
    lines.append(row("Ticker:", card.get("ticker", "?")))
    lines.append(row("Action:", card.get("action", "?").upper()))
    lines.append(row("Shares:", str(card.get("shares", "?"))))
    lines.append(row("Order Type:", card.get("priceDisplay", "?")))
    lines.append(row("Account:", f"{card.get('accountType','?')} (#{card.get('accountId','?')})"))
    lines.append(row("Cost Estimate:", card.get("costEstimateDisplay", "?")))

    coverage = card.get("coverage", {})
    sufficient = coverage.get("sufficient", True)
    flag = "✓ Sufficient" if sufficient else "✗ INSUFFICIENT"
    lines.append(row("Buying Power:", card.get("buyingPowerDisplay", "?"), flag))

    freshness = card.get("dataFreshnessMinutes")
    if freshness is not None:
        fresh_flag = "✓ Fresh" if freshness <= 60 else "⚠ STALE"
        lines.append(row("Data Age:", f"{freshness:.0f} min", fresh_flag))

    lines.append("╚══════════════════════════════════════════════════════╝")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

MAX_ORDER_VALUE_DEFAULT = 5_000.0  # USD — refuse orders above this without --allow-large

def main():
    parser = argparse.ArgumentParser(description="TradingView order placement with HITL confirmation")
    parser.add_argument("--ticker", default=None)
    parser.add_argument("--action", default=None, choices=["buy", "sell"])
    parser.add_argument("--shares", default=None, type=int)
    parser.add_argument("--order-type", default=None, choices=["market", "limit", "stop", "stop_limit"], dest="order_type")
    parser.add_argument("--limit-price", type=float, dest="limit_price")
    parser.add_argument("--account", default=None, help="rrsp, tfsa, margin")
    parser.add_argument("--output-json", default=None, dest="output_json")
    parser.add_argument("--max-order-value", type=float, default=MAX_ORDER_VALUE_DEFAULT,
                        dest="max_order_value",
                        help=f"Refuse orders whose cost estimate exceeds this value (default ${MAX_ORDER_VALUE_DEFAULT:,.0f})")
    parser.add_argument("--allow-large", action="store_true", dest="allow_large",
                        help="Bypass the max-order-value cap (requires explicit flag)")
    parser.add_argument("--ack-stale", action="store_true", dest="ack_stale",
                        help="Acknowledge stale portfolio data and proceed anyway (use with caution)")

    parser.add_argument("--order-id", default=None, dest="order_id",
                        help="TradingView order UUID (required for --cancel / --modify)")
    parser.add_argument("--new-price", type=float, default=None, dest="new_price",
                        help="New limit price (required for --modify)")
    parser.add_argument("--new-shares", type=int, default=None, dest="new_shares",
                        help="New share quantity (optional for --modify)")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--submit", action="store_true",
                      help="Re-opens dialog if needed, fills form, then clicks submit")
    mode.add_argument("--cancel", action="store_true",
                      help="Cancel an order in TradingView by order UUID")
    mode.add_argument("--modify", action="store_true",
                      help="Modify limit price of a Working/Inactive order by UUID")

    args = parser.parse_args()

    # --preflight and --execute require the full set; --submit re-fills so also needs them
    if not args.submit and not args.cancel and not args.modify:
        for req in ("ticker", "action", "shares", "order_type", "account"):
            if getattr(args, req) is None:
                parser.error(f"--{req.replace('_','-')} is required for --preflight/--execute")

    if args.order_type in ("limit", "stop_limit") and args.limit_price is None and not args.submit:
        parser.error("--limit-price is required for limit/stop_limit orders")

    # ── preflight ──────────────────────────────────────────────────────────
    if args.preflight:
        # Executable freshness gate — enforced in code, not just SKILL.md
        freshness = _check_data_freshness(ack_stale=getattr(args, 'ack_stale', False))
        if freshness and freshness.get("stale") and not getattr(args, 'ack_stale', False):
            print(json.dumps({"error": "DATA_STALE_BLOCKED", "details": freshness}, indent=2))
            print(f"\n🚫 {freshness['reason']}")
            sys.exit(4)

        try:
            card = preflight(args.ticker, args.action, args.shares,
                             args.order_type, args.limit_price, args.account)
        except RuntimeError as e:
            print(json.dumps({"error": str(e)}, indent=2))
            sys.exit(1)

        if "error" in card:
            print(json.dumps(card, indent=2))
            sys.exit(1)

        # ── data freshness gate ──────────────────────────────────────────
        # Warn if portfolio.json was not updated recently (stale prices).
        freshness = _check_data_freshness(ack_stale=args.ack_stale)
        card["stale"] = False
        if freshness and freshness.get("stale"):
            card["stale"] = True
            card["dataFreshnessMinutes"] = freshness.get("age_minutes")
            card["_freshnessWarning"] = freshness["reason"]
            if not args.ack_stale:
                print(json.dumps(card, indent=2))
                print(f"\n🚫 {freshness['reason']}")
                sys.exit(4)

        # ── max-order-value gate ─────────────────────────────────────────
        cost = card.get("costEstimate")
        if cost is not None and cost > args.max_order_value and not args.allow_large:
            card["_sizeWarning"] = (
                f"Order cost estimate ${cost:,.2f} exceeds safety cap ${args.max_order_value:,.0f}. "
                "Re-run with --allow-large to override."
            )

        print(_format_card(card))
        print()
        print(json.dumps(card, indent=2))
        if args.output_json:
            with open(args.output_json, "w") as f:
                json.dump(card, f, indent=2)

        if card.get("_sizeWarning"):
            print(f"\n🚫 {card['_sizeWarning']}")
            sys.exit(3)
        if card.get("_freshnessWarning"):
            print(f"\n⚠️  {card['_freshnessWarning']}")
        if card.get("_warning"):
            print(f"\n⚠️  {card['_warning']}")
            sys.exit(2)
        sys.exit(0)

    # ── execute (fill form + screenshot) ───────────────────────────────────
    if args.execute:
        # Re-check freshness at execute time — data may have gone stale since preflight
        freshness = _check_data_freshness(ack_stale=getattr(args, 'ack_stale', False))
        if freshness and freshness.get("stale") and not getattr(args, 'ack_stale', False):
            print(json.dumps({"error": "DATA_STALE_BLOCKED", "details": freshness}, indent=2))
            print(f"\n🚫 {freshness['reason']}")
            sys.exit(4)

        try:
            result = execute_order(args.ticker, args.action, args.shares,
                                   args.order_type, args.limit_price, args.account)
        except RuntimeError as e:
            print(json.dumps({"error": str(e)}, indent=2))
            sys.exit(1)

        if "error" in result:
            print(json.dumps(result, indent=2))
            sys.exit(1)

        output = {
            "status": "form_filled",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "screenshot": result.get("screenshot"),
            "submitButtonText": result.get("submitButtonText"),
            "dialogState": result.get("dialogState"),
        }
        print(json.dumps(output, indent=2))
        if result.get("screenshot"):
            print(f"\n📸 Screenshot saved: {result['screenshot']}")
        print(f"\n✅ Form filled: {result.get('submitButtonText', 'order ready')}")
        print("   Type CONFIRM to submit, or review the screenshot first.")
        if args.output_json:
            with open(args.output_json, "w") as f:
                json.dump(output, f, indent=2)
        sys.exit(0)

    # ── submit ─────────────────────────────────────────────────────────────
    if args.submit:
        # Re-open and re-fill the dialog if closed, then submit immediately.
        # This ensures the dialog is always in the expected state before clicking.
        if args.ticker and args.action and args.shares and args.order_type and args.account:
            try:
                print("⟳ Re-opening TradingView order dialog...")
                execute_order(args.ticker, args.action, args.shares,
                              args.order_type, args.limit_price, args.account)
            except RuntimeError as e:
                print(f"⚠️  Re-open failed: {e} — attempting submit anyway")
        try:
            result = submit_order(
                ticker=args.ticker,
                action=args.action,
                limit_price=args.limit_price,
            )
        except RuntimeError as e:
            print(json.dumps({"error": str(e)}, indent=2))
            sys.exit(1)

        if "error" in result:
            print(json.dumps(result, indent=2))
            sys.exit(1)

        tv_order_id = (result.get("brokerVerification") or {}).get("best", {}).get("orderId") or None
        output = {
            "status": "submitted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tvOrderId": tv_order_id,
            "result": result,
        }
        print(json.dumps(output, indent=2))

        print("\n⏳ Syncing portfolio.json...")
        if sync_portfolio():
            print("✓ portfolio.json updated.")
        else:
            print("⚠️  Portfolio sync failed — retry manually.")
        sys.exit(0)


    # ── modify ─────────────────────────────────────────────────────────────
    if args.modify:
        if not args.order_id:
            parser.error("--order-id is required for --modify")
        if args.new_price is None:
            parser.error("--new-price is required for --modify")
        action = args.action.capitalize() if args.action else None
        try:
            result = modify_order(args.order_id, args.new_price,
                                  new_shares=args.new_shares,
                                  ticker=args.ticker, action=action)
        except RuntimeError as e:
            print(json.dumps({"error": str(e), "modified": False}, indent=2))
            sys.exit(1)

        print(json.dumps(result, indent=2))
        if result.get("modified"):
            print(f"\n✅ Order modified in TradingView: {args.order_id[:8]}… → ${args.new_price:.2f}")
            sys.exit(0)
        else:
            print(f"\n⚠️  Modify failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    # ── cancel ─────────────────────────────────────────────────────────────
    if args.cancel:
        if not args.order_id:
            parser.error("--order-id is required for --cancel")
        try:
            result = cancel_order(args.order_id, ticker=args.ticker,
                                  action=args.action, limit_price=args.limit_price)
        except RuntimeError as e:
            print(json.dumps({"error": str(e), "cancelled": False}, indent=2))
            sys.exit(1)

        print(json.dumps(result, indent=2))
        if result.get("cancelled"):
            verified = "✓ verified" if result.get("verified") else "⚠ unverified (check TV manually)"
            print(f"\n✅ Order cancelled in TradingView: {result.get('orderId')} [{verified}]")
            sys.exit(0)
        else:
            print(f"\n⚠️  Cancel failed: {result.get('reason', 'Unknown error')}")
            sys.exit(1)


if __name__ == "__main__":
    main()
