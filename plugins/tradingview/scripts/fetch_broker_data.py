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

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Internal state database)
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
    # Use getAccountTotals() which switches to each account explicitly — unlike getBalances()
    # which reads whatever account is currently active and returns partial data when CASH is selected.
    js = """
import { getAccountTotals } from './core/broker_data.js';
try {
    const t = await getAccountTotals();
    const data = {
        cashUSD:                t.grandCashUSD,
        cashUSDCombined:        t.grandCashUSD,
        marketValueUSD:         t.grandMarketValueUSD,
        marketValueUSDCombined: t.grandMarketValueUSD,
        totalEquityUSD:         t.grandTotalUSD,
        totalEquityUSDCombined: t.grandTotalUSD,
        _perAccount:            t.accounts,
        timestamp:              t.timestamp,
    };
    process.stdout.write(JSON.stringify(data) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
"""
    return run_node_module(js, timeout=45)


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

def build_totals_from_balances(balances: dict, stored_exchange_rate: float) -> dict:
    """Pure transform: live TV account balances -> portfolio.json totals block.

    Marks totalSource='tv_authoritative' so the TS-side preserveAuthoritativeTotal()
    (portfolioSnapshot.ts) recognizes this as broker-authoritative and won't let a
    later price-refresh silently overwrite it with a shares*price approximation —
    both writers must agree on this convention, or the protection added there is
    incomplete.
    """
    cash_usd = balances.get("cashUSDCombined") or balances.get("cashUSD") or 0
    total_usd = balances.get("totalEquityUSDCombined") or balances.get("totalEquityUSD") or 0
    market_usd = balances.get("marketValueUSDCombined") or balances.get("marketValueUSD") or 0
    fx = stored_exchange_rate if stored_exchange_rate and stored_exchange_rate > 0 else 1.3795
    total_cad = round(total_usd * fx, 4)
    return {
        "holdingsUSD": market_usd,
        "cashUSD": cash_usd,
        "totalUSD": total_usd,
        "totalCAD": total_cad,
        "exchangeRate": fx,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "totalSource": "tv_authoritative",
    }


def write_snapshot(snapshot: dict, promote: bool = False, balances: Optional[dict] = None) -> str:
    """Write snapshot to portfolio.json — merges RRSP+TFSA positions and updates totals from live balances."""
    path = os.path.join(DATA_DIR, "portfolio.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    data: dict = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            pass

    if not isinstance(data, dict):
        data = {"holdings": data}

    data["tvSnapshot"] = snapshot

    # Smart-merge TV positions into holdings: aggregate RRSP + TFSA by symbol using
    # weighted-avg fill price, preserving all existing metadata (thesis, pillar, sector, etc.)
    tv_pos = snapshot.get("positions", [])
    if not tv_pos:
        # getPortfolio() returned no positions — likely getAccounts() failed (MutationObserver miss).
        # Abort the holdings merge entirely rather than silently preserving stale data.
        print("⚠  TV returned 0 positions — accounts dropdown may not have opened.", file=sys.stderr)
        print("   Holdings NOT updated. Re-run /tv-portfolio-sync or check TradingView broker panel.", file=sys.stderr)
        # Still write the tvSnapshot and updated totals, but skip holdings merge.
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path
    if tv_pos:
        # Hardcoded alias map — broker returns PSU.U.TO, canonical thesis uses PSU-U.TO.
        # Same fund (Purpose US Cash Fund), different display conventions.
        _ALIASES: dict = {"PSU.U.TO": "PSU-U.TO", "PSU.U": "PSU-U.TO"}
        _normalize = lambda x: _ALIASES.get(x, x)  # noqa: E731

        agg: dict = {}
        for p in tv_pos:
            sym = p.get("symbol")
            if not sym:
                continue
            sym = _normalize(sym)  # resolve broker alias (e.g. PSU.U.TO → PSU-U.TO)
            qty = p.get("quantity") or 0
            price = p.get("avgFillPrice") or 0
            if sym not in agg:
                agg[sym] = {"quantity": qty, "total_cost": qty * price}
            else:
                agg[sym]["quantity"] += qty
                agg[sym]["total_cost"] += qty * price

        tv_map = {
            sym: {"shares": v["quantity"], "book_price": round(v["total_cost"] / v["quantity"], 4) if v["quantity"] > 0 else 0}
            for sym, v in agg.items()
        }

        existing_holdings = data.get("holdings", [])
        existing_map = {h.get("symbol") or h.get("ticker", ""): h for h in existing_holdings}
        usd_cash = existing_map.pop("USD_CASH", None)

        merged = []
        for sym, tv in tv_map.items():
            if sym in existing_map:
                item = dict(existing_map[sym])
                item["shares"] = tv["shares"]
                item["book_price"] = tv["book_price"]
            else:
                item = {"symbol": sym, "shares": tv["shares"], "book_price": tv["book_price"]}
            merged.append(item)

        # Preserve USD_CASH, updating its value from live balances when available
        if usd_cash:
            cash_item = dict(usd_cash)
            if balances and not balances.get("error"):
                val = balances.get("cashUSDCombined") or balances.get("cashUSD") or usd_cash.get("shares", 0)
                cash_item["shares"] = val
                cash_item["market_value"] = val
            merged.append(cash_item)

        data["holdings"] = merged
        print(f"✓ Holdings merged: {len(merged)} symbols (RRSP + TFSA combined).")

    # Update totals from live balances — standalone getBalances() is reliable;
    # the embedded call inside getPortfolio() fails due to tab-switching state conflicts.
    if balances and not balances.get("error"):
        stored_fx = (data.get("totals") or {}).get("exchangeRate") or 1.3795
        data["totals"] = build_totals_from_balances(balances, stored_fx)
        print(f"✓ Totals updated: totalUSD=${data['totals']['totalUSD']:,.2f}  cashUSD=${data['totals']['cashUSD']:,.2f}")

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    # Refresh all thesis pages and role fields after every portfolio.json write.
    _run_portfolio_refresh()

    return path


def _run_portfolio_refresh() -> None:
    """Run refresh_all.py after any portfolio.json write to keep thesis pages current."""
    _repo_root = Path(SCRIPT_DIR).parents[2]
    refresh_script = _repo_root / "plugins/portfolio-advisor/scripts/refresh_all.py"
    if refresh_script.exists():
        subprocess.run([sys.executable, str(refresh_script)], check=False)
    else:
        print(f"⚠ refresh_all.py not found at {refresh_script}", file=sys.stderr)


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
        # Fetch balances first — getBalances() is unreliable after account-switching in getPortfolio()
        print("Fetching live balances from TradingView Account Summary...")
        balances: Optional[dict] = fetch_tv_balances()
        if balances.get("error"):
            print(f"⚠  Balance fetch failed: {balances['error']} — totals will not be updated.", file=sys.stderr)
            balances = None

        print("Fetching full portfolio snapshot from TradingView...")
        snapshot = fetch_tv_snapshot()
        if "error" in snapshot:
            print(f"❌ {snapshot['error']}", file=sys.stderr)
            print("   Is TradingView Desktop running with a broker connected?", file=sys.stderr)
            sys.exit(1)

        path = write_snapshot(snapshot, promote=args.promote, balances=balances)
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
