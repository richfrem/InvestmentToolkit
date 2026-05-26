#!/usr/bin/env python3
"""
fetch_broker_data.py (Python Utility)
======================================

Purpose:
    Broker-agnostic portfolio data fetcher. Reads accounts, positions, balances,
    and orders from TradingView's broker panel via CDP DOM (primary), with optional
    Questrade REST API as a secondary source for cross-validation.

    Note: The portfolio transition period is complete. TradingView CDP is now the
    canonical runtime source of truth. All positions are consolidated across accounts
    and written to the single portfolio database, portfolio.json. The raw account-specific
    broker telemetry is stored inside the tvSnapshot root key of portfolio.json.

Layer: Backend / py_services / Broker

Usage Examples:
    # Inspect broker panel DOM (for selector discovery):
    python3 investment_screener/backend/py_services/fetch_broker_data.py --inspect

    # Fetch from TradingView CDP:
    python3 investment_screener/backend/py_services/fetch_broker_data.py --positions --source tv
    python3 investment_screener/backend/py_services/fetch_broker_data.py --balances --source tv
    python3 investment_screener/backend/py_services/fetch_broker_data.py --accounts --source tv
    python3 investment_screener/backend/py_services/fetch_broker_data.py --snapshot --source tv

    # Consolidated snapshot written to portfolio.json tvSnapshot key:
    python3 investment_screener/backend/py_services/fetch_broker_data.py --snapshot

    # Cross-validate TV vs Questrade (diff side-by-side):
    python3 investment_screener/backend/py_services/fetch_broker_data.py --compare

    # Once validated, promote consolidated TV snapshot directly into portfolio.json holdings:
    python3 investment_screener/backend/py_services/fetch_broker_data.py --snapshot --promote

Key Functions:
    - fetch_tv()        - Reads all data from TradingView broker panel via CDP
    - fetch_questrade() - Reads from Questrade REST API (requires .questrade_cache)
    - compare()         - Diffs TV vs Questrade positions and balances
    - write_snapshot()  - Writes tvSnapshot inside portfolio.json (or promotes positions with --promote)
"""

import sys
import os
import json
import argparse
import subprocess
from datetime import datetime, timezone
from typing import Optional

# ── path bootstrap ──────────────────────────────────────────────────────────

import os
import sys
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tv_client import run_node_module

REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
BACKEND_SRC = os.path.abspath(os.path.join(REPO_ROOT, "investment_screener", "backend", "src"))
DATA_DIR = os.path.abspath(os.path.join(REPO_ROOT, "investment_screener", "backend", "data"))

sys.path.insert(0, BACKEND_SRC)


# ── Node.js runner ────────────────────────────────────────────────────────────


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
    return run_node_module(js)


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
    return run_node_module(js, timeout=15)


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
    return run_node_module(js, timeout=20)


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
    return run_node_module(js, timeout=15)


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
    return run_node_module(js, timeout=30)


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
    return run_node_module(js, timeout=15)


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
    """Write snapshot to portfolio.json under tvSnapshot key (or promoted)."""
    path = os.path.join(DATA_DIR, "portfolio.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    data = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            pass

    if not isinstance(data, dict):
        data = {"holdings": data}

    if promote:
        print(f"⚠  Promoting TV snapshot directly to portfolio.json holdings.")
        tv_pos = snapshot.get("positions", [])
        # Aggregate by symbol
        agg = {}
        for p in tv_pos:
            sym = p.get("symbol")
            if not sym:
                continue
            if sym not in agg:
                agg[sym] = {"symbol": sym, "shares": p.get("quantity", 0), "book_price": p.get("avgFillPrice", 0)}
            else:
                agg[sym]["shares"] += p.get("quantity", 0)
        data["holdings"] = list(agg.values())
        data["tvSnapshot"] = snapshot
    else:
        print(f"✓ Saving raw TradingView snapshot to portfolio.json under tvSnapshot key.")
        data["tvSnapshot"] = snapshot

    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch broker data from TradingView CDP or Questrade")
    parser.add_argument("--source", choices=["tv", "questrade", "auto", "compare"], default="tv")
    parser.add_argument("--accounts",  action="store_true")
    parser.add_argument("--balances",  action="store_true")
    parser.add_argument("--positions", action="store_true")
    parser.add_argument("--orders",    action="store_true")
    parser.add_argument("--snapshot",  action="store_true", help="Full snapshot → portfolio.json tvSnapshot")
    parser.add_argument("--compare",   action="store_true", help="Diff TV vs Questrade positions")
    parser.add_argument("--inspect",   action="store_true", help="Dump broker panel DOM for debugging")
    parser.add_argument("--promote",   action="store_true", help="Promote TV positions to portfolio.json holdings list")
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
        print("Fetching TradingView positions across ALL accounts via CDP...")
        snapshot = fetch_tv_snapshot()
        if "error" in snapshot:
            print(f"❌ TV error: {snapshot['error']}", file=sys.stderr)
            sys.exit(1)

        # Aggregate positions by symbol across all accounts (sum quantities)
        agg: dict = {}
        for pos in snapshot.get("positions", []):
            sym = pos.get("symbol")
            if not sym:
                continue
            if sym not in agg:
                agg[sym] = dict(pos)
            else:
                # Same symbol in multiple accounts — sum qty, keep first avgFillPrice
                agg[sym]["quantity"] = (agg[sym].get("quantity") or 0) + (pos.get("quantity") or 0)

        tv = {"positions": list(agg.values())}
        acct_counts = {}
        for p in snapshot.get("positions", []):
            at = p.get("accountType", "?")
            acct_counts[at] = acct_counts.get(at, 0) + 1
        print(f"   TV: {len(tv['positions'])} unique symbols across {len(snapshot.get('accounts', []))} accounts {acct_counts}")

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
        accts = snapshot.get("accounts", [])
        snaps = snapshot.get("snapshots", [])
        for s in snaps:
            n = len(s.get("positions", []))
            print(f"   {s.get('accountType','?')} ({s.get('accountId','?')}): {n} positions")
        print(f"✓ {len(snapshot.get('positions', []))} total positions across {len(accts)} accounts")
        print(f"✓ Written to {path}")
        print()
        print(json.dumps(snapshot, indent=indent))


if __name__ == "__main__":
    main()
