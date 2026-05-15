#!/usr/bin/env python3
"""
fetch_broker_data.py (Python Utility)
======================================

Purpose:
    Broker-agnostic portfolio data fetcher. Reads accounts, positions, balances,
    and orders from TradingView's broker panel via CDP DOM (primary), with optional
    Questrade REST API as a secondary source for cross-validation.

    During the transition period, TV data writes to portfolio_tv.json and Questrade
    data stays in portfolio.json. Use --source compare to diff them side-by-side and
    verify the TV scraper is accurate before making TV the canonical source.

Layer: Backend / py_services / Broker

Usage Examples:
    # Inspect broker panel DOM (for selector discovery):
    python3 investment_screener/backend/py_services/fetch_broker_data.py --inspect

    # Fetch from TradingView CDP:
    python3 investment_screener/backend/py_services/fetch_broker_data.py --positions --source tv
    python3 investment_screener/backend/py_services/fetch_broker_data.py --balances --source tv
    python3 investment_screener/backend/py_services/fetch_broker_data.py --accounts --source tv
    python3 investment_screener/backend/py_services/fetch_broker_data.py --snapshot --source tv

    # Full snapshot written to portfolio_tv.json (safe — does not overwrite portfolio.json):
    python3 investment_screener/backend/py_services/fetch_broker_data.py --snapshot

    # Cross-validate TV vs Questrade (diff side-by-side):
    python3 investment_screener/backend/py_services/fetch_broker_data.py --compare

    # Once validated, promote TV snapshot to portfolio.json:
    python3 investment_screener/backend/py_services/fetch_broker_data.py --snapshot --promote

Key Functions:
    - fetch_tv()        - Reads all data from TradingView broker panel via CDP
    - fetch_questrade() - Reads from Questrade REST API (requires .questrade_cache)
    - compare()         - Diffs TV vs Questrade positions and balances
    - write_snapshot()  - Writes portfolio_tv.json (or portfolio.json with --promote)
"""

import sys
import os
import json
import argparse
import subprocess
from datetime import datetime, timezone
from typing import Optional

# ── path bootstrap ──────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
BACKEND_SRC = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "src"))
TV_NODE_DIR = os.path.join(REPO_ROOT, "plugins", "tradingview", "node")
DATA_DIR    = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "data"))

sys.path.insert(0, BACKEND_SRC)


# ── Node.js runner ────────────────────────────────────────────────────────────

def _run_node(script_js: str, timeout: int = 30) -> dict:
    result = subprocess.run(
        ["node", "--input-type=module"],
        input=script_js,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=TV_NODE_DIR,
    )
    if result.returncode != 0 and not result.stdout.strip():
        raise RuntimeError(f"Node.js error: {result.stderr.strip()[:500]}")
    stdout = result.stdout.strip()
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"raw": stdout, "stderr": result.stderr.strip()}


# ── TradingView CDP source ────────────────────────────────────────────────────

def fetch_tv_accounts() -> list:
    js = """
import { getAccounts } from './core/broker_data.js';
try {
    const data = await getAccounts();
    process.stdout.write(JSON.stringify(data) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
"""
    return _run_node(js)


def fetch_tv_balances() -> dict:
    js = """
import { getBalances } from './core/broker_data.js';
try {
    const data = await getBalances();
    process.stdout.write(JSON.stringify(data) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
"""
    return _run_node(js, timeout=15)


def fetch_tv_positions() -> dict:
    js = """
import { getPositions } from './core/broker_data.js';
try {
    const data = await getPositions();
    process.stdout.write(JSON.stringify(data) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
"""
    return _run_node(js, timeout=20)


def fetch_tv_orders() -> list:
    js = """
import { getOrders } from './core/broker_data.js';
try {
    const data = await getOrders();
    process.stdout.write(JSON.stringify(data) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
"""
    return _run_node(js, timeout=15)


def fetch_tv_snapshot() -> dict:
    js = """
import { getPortfolio } from './core/broker_data.js';
try {
    const data = await getPortfolio();
    process.stdout.write(JSON.stringify(data) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
"""
    return _run_node(js, timeout=30)


def inspect_broker_panel() -> dict:
    js = """
import { inspectBrokerPanel } from './core/broker_data.js';
try {
    const data = await inspectBrokerPanel();
    process.stdout.write(JSON.stringify(data) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
"""
    return _run_node(js, timeout=15)


# ── Questrade source ──────────────────────────────────────────────────────────

def fetch_questrade_snapshot() -> Optional[dict]:
    """Read current portfolio.json as Questrade baseline."""
    portfolio_path = os.path.join(DATA_DIR, "portfolio.json")
    if not os.path.exists(portfolio_path):
        return None
    with open(portfolio_path) as f:
        return json.load(f)


# ── compare ───────────────────────────────────────────────────────────────────

def compare_snapshots(tv: dict, qt: dict) -> dict:
    """
    Diff TV positions vs Questrade positions field-by-field.
    Returns a report with: matched, qty_mismatch, tv_only, qt_only rows.
    """
    tv_pos = {p["symbol"]: p for p in tv.get("positions", [])}
    qt_pos = {}

    # portfolio.json is a top-level list of {symbol, shares, book_price, ...}
    if isinstance(qt, list):
        qt_holdings = qt
    else:
        qt_holdings = qt.get("holdings", qt.get("positions", []))
    for h in qt_holdings:
        sym = h.get("symbol") or h.get("ticker")
        if sym:
            qt_pos[sym] = {
                "symbol": sym,
                "quantity": h.get("shares") or h.get("openQuantity") or h.get("quantity"),
                "avgFillPrice": h.get("book_price") or h.get("averageEntryPrice") or h.get("avgFillPrice"),
            }

    all_syms = sorted(set(list(tv_pos.keys()) + list(qt_pos.keys())))

    matched, qty_mismatch, tv_only, qt_only = [], [], [], []

    for sym in all_syms:
        tv_p = tv_pos.get(sym)
        qt_p = qt_pos.get(sym)

        if tv_p and qt_p:
            tv_qty = tv_p.get("quantity")
            qt_qty = qt_p.get("quantity")
            if tv_qty is not None and qt_qty is not None and abs(tv_qty - qt_qty) > 0.01:
                qty_mismatch.append({
                    "symbol": sym,
                    "tv_qty": tv_qty,
                    "qt_qty": qt_qty,
                    "tv_avgFill": tv_p.get("avgFillPrice"),
                    "qt_avgFill": qt_p.get("avgFillPrice"),
                })
            else:
                matched.append({"symbol": sym, "qty": tv_qty, "avgFill": tv_p.get("avgFillPrice")})
        elif tv_p:
            tv_only.append({"symbol": sym, "qty": tv_p.get("quantity")})
        else:
            qt_only.append({"symbol": sym, "qty": qt_p.get("quantity")})

    return {
        "matched": matched,
        "qty_mismatch": qty_mismatch,
        "tv_only": tv_only,
        "qt_only": qt_only,
        "summary": {
            "total_tv": len(tv_pos),
            "total_qt": len(qt_pos),
            "matched": len(matched),
            "mismatched": len(qty_mismatch),
            "tv_only": len(tv_only),
            "qt_only": len(qt_only),
        },
    }


def print_compare_report(report: dict):
    s = report["summary"]
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║         TV vs Questrade — Position Diff              ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  TV positions:       {s['total_tv']:<33}║")
    print(f"║  Questrade positions:{s['total_qt']:<33}║")
    print(f"║  ✓ Matched:          {s['matched']:<33}║")
    print(f"║  ⚠ Qty mismatch:     {s['mismatched']:<33}║")
    print(f"║  TV only:            {s['tv_only']:<33}║")
    print(f"║  Questrade only:     {s['qt_only']:<33}║")
    print("╚══════════════════════════════════════════════════════╝")

    if report["qty_mismatch"]:
        print("\n⚠  QUANTITY MISMATCHES:")
        for row in report["qty_mismatch"]:
            print(f"   {row['symbol']:<8}  TV={row['tv_qty']}  QT={row['qt_qty']}")

    if report["tv_only"]:
        print("\n📺  TV ONLY (not in Questrade portfolio.json):")
        for row in report["tv_only"]:
            print(f"   {row['symbol']:<8}  qty={row['qty']}")

    if report["qt_only"]:
        print("\n🏦  QUESTRADE ONLY (not found in TV):")
        for row in report["qt_only"]:
            print(f"   {row['symbol']:<8}  qty={row['qty']}")

    if s["mismatched"] == 0 and s["tv_only"] == 0 and s["qt_only"] == 0:
        print("\n✅  All positions match — TV scraper validated. Safe to promote TV as primary source.")
    else:
        print("\n❌  Discrepancies found. Fix scraper before promoting TV as primary source.")


# ── snapshot writer ───────────────────────────────────────────────────────────

def write_snapshot(snapshot: dict, promote: bool = False) -> str:
    """Write snapshot to portfolio_tv.json (or portfolio.json with --promote)."""
    if promote:
        path = os.path.join(DATA_DIR, "portfolio.json")
        print(f"⚠  Writing to portfolio.json (promoted).")
    else:
        path = os.path.join(DATA_DIR, "portfolio_tv.json")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2)
    return path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch broker data from TradingView CDP or Questrade")
    parser.add_argument("--source", choices=["tv", "questrade", "auto", "compare"], default="tv")
    parser.add_argument("--accounts",  action="store_true")
    parser.add_argument("--balances",  action="store_true")
    parser.add_argument("--positions", action="store_true")
    parser.add_argument("--orders",    action="store_true")
    parser.add_argument("--snapshot",  action="store_true", help="Full snapshot → portfolio_tv.json")
    parser.add_argument("--compare",   action="store_true", help="Diff TV vs Questrade positions")
    parser.add_argument("--inspect",   action="store_true", help="Dump broker panel DOM for debugging")
    parser.add_argument("--promote",   action="store_true", help="Write to portfolio.json instead of portfolio_tv.json")
    parser.add_argument("--pretty",    action="store_true", default=True)
    args = parser.parse_args()

    indent = 2 if args.pretty else None

    # ── inspect ──────────────────────────────────────────────────────────────
    if args.inspect:
        result = inspect_broker_panel()
        print(json.dumps(result, indent=indent))
        return

    # ── compare ──────────────────────────────────────────────────────────────
    if args.compare or args.source == "compare":
        print("Fetching TradingView positions via CDP...")
        # Use positions directly (active account) — getPortfolio() multi-account iterate can fail
        pos_raw = fetch_tv_positions()
        tv = {"positions": pos_raw.get("positions", [])} if isinstance(pos_raw, dict) else {"positions": []}
        if "error" in pos_raw:
            print(f"❌ TV error: {pos_raw['error']}", file=sys.stderr)
            sys.exit(1)
        print(f"   TV: {len(tv.get('positions', []))} positions")

        print("Reading Questrade portfolio.json...")
        qt = fetch_questrade_snapshot()
        if qt is None:
            print("❌ portfolio.json not found — run Questrade sync first.", file=sys.stderr)
            sys.exit(1)

        report = compare_snapshots(tv, qt)
        print_compare_report(report)
        print()
        print(json.dumps(report, indent=indent))
        return

    # ── individual data types ─────────────────────────────────────────────────
    if args.accounts:
        result = fetch_tv_accounts()
        print(json.dumps(result, indent=indent))
        return

    if args.balances:
        result = fetch_tv_balances()
        print(json.dumps(result, indent=indent))
        return

    if args.positions:
        result = fetch_tv_positions()
        print(json.dumps(result, indent=indent))
        return

    if args.orders:
        result = fetch_tv_orders()
        print(json.dumps(result, indent=indent))
        return

    # ── snapshot ─────────────────────────────────────────────────────────────
    if args.snapshot or not any([args.accounts, args.balances, args.positions, args.orders, args.compare, args.inspect]):
        print("Fetching full portfolio snapshot from TradingView...")
        snapshot = fetch_tv_snapshot()
        if "error" in snapshot:
            print(f"❌ {snapshot['error']}", file=sys.stderr)
            print("   Is TradingView Desktop running with a broker connected?", file=sys.stderr)
            sys.exit(1)

        path = write_snapshot(snapshot, promote=args.promote)
        print(f"✓ {len(snapshot.get('positions', []))} positions, {len(snapshot.get('accounts', []))} accounts")
        print(f"✓ Written to {path}")
        print()
        print(json.dumps(snapshot, indent=indent))


if __name__ == "__main__":
    main()
