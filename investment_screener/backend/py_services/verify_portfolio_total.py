#!/usr/bin/env python3
"""
verify_portfolio_total.py - Python utility script.

Purpose:
    verify_portfolio_total.py — Audit script: TV live account totals vs our computed total.

Fetches Total Equity USD from every TradingView account via CDP (live, authoritative),
then computes what our single portfolio database (portfolio.json) says, and shows the diff.
Note: portfolio.json is the sole portfolio database for the web app and analytics,
and it stores the raw account-level breakdowns (TFSA vs RRSP vs Cash balances) inside
the tvSnapshot root key.

Usage:
    python3 verify_portfolio_total.py            # live TV + stored prices
    python3 verify_portfolio_total.py --live     # live TV + live yfinance prices

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Audits equity sum verification)

Layer:
    Backend / Python Services

Usage Examples:
    python3 verify_portfolio_total.py            # live TV + stored prices
    python3 verify_portfolio_total.py --live     # live TV + live yfinance prices

Key Functions (Index):
    - get_tv_totals_live()
    - get_tv_totals_cached()
    - compute_our_total()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
import sys
import json
import argparse
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Walk up to repo root (investment_screener/backend/py_services → repo root = 3 levels up)
REPO_ROOT  = SCRIPT_DIR.parents[2]
TV_CLIENT_DIR = REPO_ROOT / "plugins" / "tradingview" / "scripts"
sys.path.insert(0, str(TV_CLIENT_DIR))
from tv_client import run_node_module

DATA_DIR      = SCRIPT_DIR.parent / "data"
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"


# ── TV live totals ────────────────────────────────────────────────────────────

def get_tv_totals_live() -> dict:
    js = """
import { getAccountTotals } from './core/broker_data.js';
try {
    const data = await getAccountTotals();
    process.stdout.write(JSON.stringify(data) + '\\n');
    process.exit(0);
} catch(e) {
    process.stdout.write(JSON.stringify({ error: e.message }) + '\\n');
    process.exit(1);
}
"""
    return run_node_module(js, timeout=90)


def get_tv_totals_cached() -> dict:
    """Read totals from last TV sync raw cache inside portfolio.json."""
    if not PORTFOLIO_FILE.exists():
        return {"error": "Portfolio database (portfolio.json) not found — run a TV sync first."}
    with open(PORTFOLIO_FILE) as f:
        data = json.load(f)
    if not isinstance(data, dict) or "tvSnapshot" not in data:
        return {"error": "Raw TradingView sync cache (tvSnapshot) not found inside portfolio.json — run a TV sync first."}
    
    tv = data["tvSnapshot"]
    accounts = []
    grand_total = grand_mkt = grand_cash = 0
    for snap in tv.get("snapshots", []):
        bal = snap.get("balances") or {}
        equity = bal.get("totalEquityUSD") or 0
        mkt    = bal.get("marketValueUSD") or 0
        cash   = bal.get("cashUSD") or 0
        if equity == 0 and mkt == 0 and cash == 0:
            continue  # skip accounts with no data (e.g. empty Cash account)
        accounts.append({"accountType": snap.get("accountType"), "accountId": snap.get("accountId"),
                         "totalEquityUSD": equity, "marketValueUSD": mkt, "cashUSD": cash})
        grand_total += equity
        grand_mkt   += mkt
        grand_cash  += cash
    return {"accounts": accounts, "grandTotalUSD": grand_total,
            "grandMarketValueUSD": grand_mkt, "grandCashUSD": grand_cash,
            "timestamp": tv.get("timestamp", "unknown"), "source": "cached"}


# ── our computed total ────────────────────────────────────────────────────────

def compute_our_total(use_live_prices: bool = False) -> tuple:
    """
    Returns (total_usd, breakdown_list).
    breakdown_list: [{symbol, shares, price, value, price_source}]
    """
    if not PORTFOLIO_FILE.exists():
        return 0.0, []

    with open(PORTFOLIO_FILE) as f:
        data = json.load(f)

    if isinstance(data, dict):
        positions = data.get("holdings", [])
    else:
        positions = data

    live_quotes: dict = {}
    if use_live_prices:
        tickers = [p["symbol"] for p in positions
                   if p.get("symbol") and p["symbol"] != "USD_CASH"]
        if tickers:
            result = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "fetch_quotes.py"), ",".join(tickers)],
                capture_output=True, text=True, timeout=45,
            )
            if result.returncode == 0:
                live_quotes = json.loads(result.stdout)

    total = 0.0
    breakdown = []
    for p in positions:
        sym    = p.get("symbol") or p.get("ticker", "?")
        shares = p.get("shares", 0) or 0
        if sym == "USD_CASH":
            price  = 1.0
            source = "cash"
        elif use_live_prices and sym in live_quotes and live_quotes[sym].get("price"):
            price  = live_quotes[sym]["price"]
            source = "yfinance-live"
        else:
            price  = p.get("price") or p.get("book_price") or 0
            source = "stored" if p.get("price") else "book_price"
        val = shares * price
        total += val
        breakdown.append({"symbol": sym, "shares": shares, "price": price, "value": val, "source": source})

    return total, breakdown


# ── report ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Audit portfolio total vs TradingView")
    parser.add_argument("--live", action="store_true",
                        help="Fetch TV totals live (requires TV running). Default: use last sync cache.")
    parser.add_argument("--live-prices", action="store_true",
                        help="Also refresh yfinance prices for our computed total.")
    args = parser.parse_args()

    # TV totals
    if args.live:
        print("Fetching LIVE account totals from TradingView via CDP…")
        tv = get_tv_totals_live()
    else:
        print("Reading cached TV totals from last sync (portfolio.json tvSnapshot)…")
        tv = get_tv_totals_cached()

    if "error" in tv:
        print(f"❌  TV error: {tv['error']}", file=sys.stderr)
        sys.exit(1)

    # Our total
    label = "live yfinance prices" if args.live_prices else "stored portfolio.json prices"
    print(f"Computing our portfolio total ({label})…\n")
    our_total, breakdown = compute_our_total(use_live_prices=args.live_prices)

    tv_total = tv.get("grandTotalUSD", 0)
    diff     = our_total - tv_total
    diff_pct = (diff / tv_total * 100) if tv_total else 0

    # ── TV account breakdown ──────────────────────────────────────────────────
    source_tag = tv.get("source", "live")
    ts         = tv.get("timestamp", "")
    print(f"{'TV Account Totals':} [{source_tag}  {ts[:19]}]")
    print(f"{'Account':<10} {'Market Value USD':>18} {'Cash USD':>12} {'Total Equity USD':>18}")
    print("─" * 62)
    for acct in tv.get("accounts", []):
        print(f"{acct['accountType']:<10} ${acct['marketValueUSD']:>17,.2f} ${acct['cashUSD']:>11,.2f} ${acct['totalEquityUSD']:>17,.2f}")
    print("─" * 62)
    print(f"{'GRAND TOTAL':<10} ${tv.get('grandMarketValueUSD',0):>17,.2f} ${tv.get('grandCashUSD',0):>11,.2f} ${tv_total:>17,.2f}")

    # ── comparison ────────────────────────────────────────────────────────────
    print()
    print(f"{'Our computed total:':<30} ${our_total:>10,.2f} USD")
    print(f"{'TV total equity:':<30} ${tv_total:>10,.2f} USD")
    print(f"{'Difference (ours − TV):':<30} ${diff:>+10,.2f} USD  ({diff_pct:+.2f}%)")
    print()

    if abs(diff) < 25:
        print("✅  PASS — within $25 tolerance")
    elif abs(diff) < 200:
        print(f"⚠   WARN — ${abs(diff):,.2f} gap (likely stale prices; run Refresh)")
    else:
        print(f"❌  FAIL — ${abs(diff):,.2f} gap")
        # Find the biggest contributors missing price
        no_price = [(b["symbol"], b["shares"]) for b in breakdown
                    if b["source"] == "book_price" and b["symbol"] != "USD_CASH"]
        if no_price:
            print(f"\n   Positions missing live price (using book_price):")
            for sym, shares in no_price:
                print(f"     {sym}: {shares} shares")

    # ── per-position breakdown ────────────────────────────────────────────────
    print()
    print(f"{'Symbol':<10} {'Shares':>8} {'Price':>12} {'Value':>12} {'Source'}")
    print("─" * 60)
    for b in sorted(breakdown, key=lambda x: -x["value"]):
        print(f"{b['symbol']:<10} {b['shares']:>8.3f} ${b['price']:>11.4f} ${b['value']:>11.2f}  {b['source']}")
    print("─" * 60)
    print(f"{'TOTAL':<10} {' ':>8} {' ':>12} ${our_total:>11.2f}")


if __name__ == "__main__":
    main()
