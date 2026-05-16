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
    """Open TV order dialog, fill it, screenshot it, then submit."""
    # Step 1: Navigate chart to the ticker so the overlay shows the right Buy/Sell
    nav_js = f"""
import {{ evaluate, connect }} from './connection.js';
await connect();
const result = await evaluate(`(function() {{
    try {{
        var api = window.TradingViewApi;
        if (!api || !api._activeChartWidgetWV) return JSON.stringify({{ switched: false, reason: 'API not available' }});
        var widget = api._activeChartWidgetWV.value();
        // Try _chartWidget.model().mainSeries().setChartSymbol()
        if (widget && widget._chartWidget) {{
            var model = widget._chartWidget.model && widget._chartWidget.model();
            if (model && model.mainSeries) {{
                var series = model.mainSeries();
                if (series && series.setChartSymbol) {{
                    series.setChartSymbol({json.dumps(ticker)});
                    return JSON.stringify({{ switched: true, method: 'setChartSymbol' }});
                }}
            }}
        }}
        // Fallback: use _activateChart or symbol input field
        var symbolInput = document.querySelector('[class*="symbolInput"], [data-name*="symbol"]');
        if (symbolInput) {{
            symbolInput.value = {json.dumps(ticker)};
            symbolInput.dispatchEvent(new Event('input', {{bubbles: true}}));
            return JSON.stringify({{ switched: true, method: 'input-field' }});
        }}
        return JSON.stringify({{ switched: false, reason: 'No usable setSymbol method found' }});
    }} catch(e) {{
        return JSON.stringify({{ switched: false, error: e.message }});
    }}
}})()`);
process.stdout.write(result + '\\n');
process.exit(0);
"""
    try:
        nav = _run_node(nav_js, timeout=10)
        if isinstance(nav, dict) and nav.get("error"):
            log.warning(f"Chart navigation: {nav['error']}")
    except Exception as e:
        log.warning(f"Chart nav failed (non-fatal): {e}")

    # Brief pause after symbol switch
    import time; time.sleep(1.5)

    # Step 2: Open dialog, fill form, screenshot
    exec_js = f"""
import {{ executeOrder }} from './core/trading.js';
try {{
    const result = await executeOrder({{
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
    return _run_node(exec_js, timeout=30)


def submit_order() -> dict:
    """Click the submit button — call only after HITL approval."""
    js = """
import { confirmAndSubmit } from './core/trading.js';
try {
    const result = await confirmAndSubmit();
    process.stdout.write(JSON.stringify(result) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
"""
    return _run_node(js, timeout=15)


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

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--submit", action="store_true",
                      help="Re-opens dialog if needed, fills form, then clicks submit")

    args = parser.parse_args()

    # --preflight and --execute require the full set; --submit re-fills so also needs them
    if not args.submit:
        for req in ("ticker", "action", "shares", "order_type", "account"):
            if getattr(args, req) is None:
                parser.error(f"--{req.replace('_','-')} is required for --preflight/--execute")

    if args.order_type in ("limit", "stop_limit") and args.limit_price is None and not args.submit:
        parser.error("--limit-price is required for limit/stop_limit orders")

    # ── preflight ──────────────────────────────────────────────────────────
    if args.preflight:
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
        portfolio_path = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "data", "portfolio.json"))
        if os.path.exists(portfolio_path):
            import time as _time
            age_minutes = (_time.time() - os.path.getmtime(portfolio_path)) / 60
            card["dataFreshnessMinutes"] = round(age_minutes, 1)
            if age_minutes > 60:
                card["_freshnessWarning"] = (
                    f"portfolio.json is {age_minutes:.0f} min old — prices may be stale. "
                    "Run /tv-portfolio-sync before placing orders."
                )

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
            result = submit_order()
        except RuntimeError as e:
            print(json.dumps({"error": str(e)}, indent=2))
            sys.exit(1)

        if "error" in result:
            print(json.dumps(result, indent=2))
            sys.exit(1)

        output = {
            "status": "submitted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": result,
        }
        print(json.dumps(output, indent=2))

        print("\n⏳ Syncing portfolio.json...")
        if sync_portfolio():
            print("✓ portfolio.json updated.")
        else:
            print("⚠️  Portfolio sync failed — retry manually.")
        sys.exit(0)


if __name__ == "__main__":
    main()
