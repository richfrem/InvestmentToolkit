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

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Internal state database)
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

import os
import sys
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

def _find_scripts_dir() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if (candidate / "tv_client.py").exists():
            return candidate
        if (candidate / "scripts" / "tv_client.py").exists():
            return candidate / "scripts"
    raise ImportError("tv_client.py not found — check plugin installation or set TV_CDP_DIR.")

sys.path.insert(0, str(_find_scripts_dir()))
from tv_client import run_node_module

REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
BACKEND_SRC = os.path.abspath(os.path.join(REPO_ROOT, "investment_screener", "backend", "src"))
DATA_DIR = os.path.abspath(os.path.join(REPO_ROOT, "investment_screener", "backend", "data"))


sys.path.insert(0, BACKEND_SRC)

# Cross-directory import of the real Task 5E risk-gate composition +
# post-trade validation. This script's real file lives in
# plugins/tradingview/scripts/, not next to order_risk_gates.py/
# portfolio_io.py/ticker_aliases.py (investment_screener/backend/py_services/)
# — mirrors data_window_validator.py's own reverse sys.path-insert pattern
# for reaching tv_client.py from the other direction.
PY_SERVICES_DIR = os.path.join(REPO_ROOT, "investment_screener", "backend", "py_services")
sys.path.insert(0, PY_SERVICES_DIR)
from order_risk_gates import (  # noqa: E402
    build_portfolio_state_for_order,
    check_risk_gates,
    log_order_execution,
    validate_trade_execution,
    wait_for_trade_log_entry,
)
from portfolio_io import load_portfolio_state  # noqa: E402
from ticker_aliases import normalize_ticker  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

PORTFOLIO_PATH = os.environ.get(
    "PLACE_ORDER_PORTFOLIO_PATH",
    os.path.join(DATA_DIR, "portfolio.json"),
)
DATA_FRESHNESS_LIMIT_MINUTES = 60


def _check_market_hours() -> dict | None:
    """Returns a warning dict if NYSE is closed (holiday or outside hours), else None.

    Uses pandas_market_calendars when available; falls back to weekday + rough ET hours.

    Reads PLACE_ORDER_NOW_OVERRIDE (ISO 8601 UTC timestamp) when set, so tests can pin
    "now" to a known in-hours/out-of-hours moment instead of being coupled to the real
    wall clock. Unset in production — defaults to datetime.now(timezone.utc).
    """
    from datetime import datetime, timezone, timedelta
    now_override = os.environ.get("PLACE_ORDER_NOW_OVERRIDE")
    if now_override:
        print(
            f"⚠️  PLACE_ORDER_NOW_OVERRIDE is set ({now_override}) — market-hours check is "
            "using a fake timestamp, not the real clock. Unset this env var for real trading.",
            file=sys.stderr,
        )
        now_utc = datetime.fromisoformat(now_override)
    else:
        now_utc = datetime.now(timezone.utc)
    # Approximate EDT offset (UTC-4). Close enough for an advisory gate.
    now_et = now_utc + timedelta(hours=-4)

    try:
        import pandas_market_calendars as mcal  # type: ignore
        nyse = mcal.get_calendar("NYSE")
        schedule = nyse.schedule(
            start_date=now_et.strftime("%Y-%m-%d"),
            end_date=now_et.strftime("%Y-%m-%d"),
        )
        if schedule.empty:
            return {
                "marketClosed": True,
                "reason": (
                    f"NYSE is closed today ({now_et.strftime('%Y-%m-%d')}) — holiday or weekend. "
                    "Day orders will queue as Inactive and attempt to fill at the next regular session open. "
                    "Pass --ack-closed to place anyway."
                ),
            }
        market_open = schedule.iloc[0]["market_open"].to_pydatetime()
        market_close = schedule.iloc[0]["market_close"].to_pydatetime()
        if not (market_open <= now_utc <= market_close):
            return {
                "marketClosed": True,
                "reason": (
                    f"NYSE is currently closed (now {now_et.strftime('%H:%M')} ET; hours 09:30–16:00 ET). "
                    "Day orders placed now will queue as Inactive for the next session open. "
                    "Pass --ack-closed to place anyway."
                ),
            }
        return None
    except ImportError:
        # Fallback: weekday + rough ET hours only (no holiday detection)
        if now_et.weekday() >= 5:
            return {
                "marketClosed": True,
                "reason": (
                    f"Weekend — NYSE is closed. Day orders will queue for Monday's open. "
                    "Pass --ack-closed to place anyway."
                ),
            }
        now_h = now_et.hour + now_et.minute / 60.0
        if not (9.5 <= now_h <= 16.0):
            return {
                "marketClosed": True,
                "reason": (
                    f"Outside NYSE hours (now {now_et.strftime('%H:%M')} ET; hours 09:30–16:00 ET). "
                    "Day orders will queue for the next open. "
                    "Pass --ack-closed to place anyway."
                ),
            }
        return None


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
    return run_node_module(js)


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
    return run_node_module(exec_js, timeout=45)


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
    return run_node_module(js, timeout=30)


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
    return run_node_module(js, timeout=15)


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
    return run_node_module(js, timeout=20)


# ── portfolio sync ────────────────────────────────────────────────────────────

def sync_portfolio() -> bool:
    """Reconcile and refresh portfolio.json after order fill.
    Priority:
      1. Express API  /api/portfolio/sync-tv/apply  (backend running)
      2. fetch_broker_data.py --snapshot             (direct CDP — always available)
      3. QuestradeDataEngine.py                      (legacy REST fallback)
    """
    import urllib.request

    # 1. Express API (authoritative when backend is up)
    try:
        req = urllib.request.Request("http://localhost:3001/api/portfolio/sync-tv/apply", data=b"{}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode())
            if res_data.get("success") and res_data.get("tvAvailable"):
                print("✓ Sync complete: portfolio.json updated via Express API.")
                return True
    except Exception as e:
        print(f"⚠️  Express API unavailable ({e}). Falling back to direct CDP snapshot...")

    # 2. Direct fetch_broker_data.py --snapshot (works without backend, uses live TV CDP)
    snapshot_script = os.path.abspath(os.path.join(SCRIPT_DIR, "fetch_broker_data.py"))
    if os.path.exists(snapshot_script):
        result = subprocess.run(
            [sys.executable, snapshot_script, "--snapshot"],
            capture_output=True, text=True, timeout=90,
        )
        if result.returncode == 0:
            print("✓ Sync complete: portfolio.json updated via direct CDP snapshot (cash + holdings refreshed).")
            return True
        print(f"⚠️  Direct CDP snapshot failed ({result.stderr.strip()[:120]}). Falling back to Questrade...")

    # 3. Legacy Questrade REST API
    engine_path = os.path.abspath(os.path.join(BACKEND_SRC, "QuestradeDataEngine.py"))
    cache_dir   = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
    portfolio_path = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "data", "portfolio.json"))
    result = subprocess.run(
        [sys.executable, engine_path, "--cache-dir",
         os.path.join(cache_dir, "backend"), "--output", portfolio_path],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("✓ Sync complete: portfolio.json updated via Questrade REST API.")
        return True
    print("⚠️  Portfolio sync failed — retry manually with /tv-portfolio-sync.")
    return False



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
    parser.add_argument("--shares", default=None, type=float)
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
    parser.add_argument("--ack-closed", action="store_true", dest="ack_closed",
                        help="Acknowledge that the market is closed and place the order anyway (Day orders queue as Inactive)")
    parser.add_argument("--override-risk-gates", action="store_true", dest="override_risk_gates",
                        help="Place the order despite a failed risk gate (will be logged as OVERRIDDEN).")

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
        # Market hours gate — warn/block if NYSE is closed (holiday or after hours)
        ack_closed = getattr(args, 'ack_closed', False)
        market_status = _check_market_hours()
        if market_status and market_status.get("marketClosed") and not ack_closed:
            print(json.dumps({"error": "MARKET_CLOSED_BLOCKED", "details": market_status}, indent=2))
            print(f"\n🚫 {market_status['reason']}")
            sys.exit(5)

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

        # ── risk gates (Task 5E-6 composite: mrc, cluster_variance, ────────
        # breaker_veto, size, balance, data_readiness) ─────────────────────
        # Market orders have no card-level price (costEstimate is only
        # populated for limit orders per trading.js's real preflight()
        # contract) — fall back to the last-synced portfolio.json price for
        # this ticker; if that's also unavailable, use 0.0. Every gate
        # already degrades gracefully ("can't evaluate, don't block") on
        # missing price/value data, so this fallback is a safe, intentional
        # degradation, not a new failure mode.
        if args.limit_price is not None:
            order_price = args.limit_price
        else:
            try:
                _state = load_portfolio_state(Path(PORTFOLIO_PATH))
                order_price = _state["prices"].get(normalize_ticker(args.ticker.upper()), 0.0)
            except Exception:
                order_price = 0.0

        order_dict = {
            "ticker": args.ticker.upper(),
            "side": args.action.upper(),
            "shares": args.shares,
            "price": order_price,
        }

        portfolio_state = build_portfolio_state_for_order()
        gate_result = check_risk_gates(order_dict, portfolio_state)
        card["riskGates"] = gate_result
        if not gate_result["passed"]:
            if not args.override_risk_gates:
                print(json.dumps({"error": "RISK_GATES_BLOCKED", "details": gate_result}, indent=2))
                print(f"\n🚫 Risk gate(s) failed: {'; '.join(gate_result['reasons'])}")
                print("   Pass --override-risk-gates to place anyway (will be logged as OVERRIDDEN).")
                log_order_execution(order_dict, gate_result, decision="BLOCKED")
                sys.exit(6)
            else:
                print(f"\n⚠️  Risk gate(s) overridden: {'; '.join(gate_result['reasons'])}")
                log_order_execution(order_dict, gate_result, decision="OVERRIDDEN")

        # ── market hours advisory (already acked at this point) ─────────
        if market_status and market_status.get("marketClosed"):
            card["_marketClosedWarning"] = market_status["reason"]

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

        if card.get("_marketClosedWarning"):
            print(f"\n⚠️  MARKET CLOSED (acked): {card['_marketClosedWarning']}")
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

            # ── post-trade validation (Task 5E-7) ────────────────────────
            # --ticker/--action/--shares may be omitted on a --submit call
            # that's just re-clicking an already-filled dialog (see the
            # re-open guard above) — skip validation entirely when there's
            # nothing to validate against, rather than erroring.
            if args.ticker and args.action and args.shares:
                post_trade_order = {
                    "ticker": args.ticker.upper(),
                    "side": args.action.upper(),
                    "shares": args.shares,
                    "price": args.limit_price or 0.0,
                }
                matched_entry = wait_for_trade_log_entry(
                    post_trade_order,
                    account=args.account.upper() if args.account else None,
                )
                validation = validate_trade_execution(post_trade_order, matched_entry)
                print(f"\n📋 Post-trade validation: {validation['reason']}")
                if validation["slippage_flagged"]:
                    print(f"   ⚠️  {validation['reason']}")
                log_order_execution(
                    post_trade_order,
                    {"passed": True, "gates": [], "reasons": []},
                    decision="EXECUTED",
                    trade_execution_result=validation,
                )
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
