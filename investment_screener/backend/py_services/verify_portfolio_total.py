#!/usr/bin/env python3
"""
verify_portfolio_total.py - Python utility script.

Purpose:
    verify_portfolio_total.py — Audit script: TV live account totals vs our computed total.

Fetches Total Equity USD from every TradingView account via CDP (live, authoritative),
then computes what our single portfolio database says, and shows the diff.

Per ADR-030 (Wave 3 Task 6 cutover), "our computed total" is
domain_model.sqlite's ``get_portfolio_total_value()`` — a live, read-time-only
rollup of account_investment x investment_price, never a stored total and
never independently re-summed here. The cached TV-side comparison total
(``get_tv_totals_cached()``) still reads portfolio.json's ``tvSnapshot`` root
key, since that raw broker-sync cache has no domain_model.sqlite equivalent
yet (out of this task's scope — it is the broker's own reported figure being
audited against, not the consumer side of this migration).

Usage:
    python3 verify_portfolio_total.py            # live TV + stored prices
    python3 verify_portfolio_total.py --live     # live TV + live yfinance prices

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (Audits equity sum
      verification; Wave 3 Task 6 cutover — previously portfolio.json)
    - investment_screener/backend/data/portfolio.json (tvSnapshot cache only —
      the broker-reported comparison side, not migrated)

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

sys.path.insert(0, str(SCRIPT_DIR))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.portfolio_repository import load_portfolio_state_from_db  # noqa: E402

DATA_DIR      = SCRIPT_DIR.parent / "data"
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
DB_PATH        = DATA_DIR / "domain_model.sqlite"


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

def compute_our_total(use_live_prices: bool = False, db_path: Path = DB_PATH) -> tuple:
    """
    Returns (total_usd, breakdown_list).
    breakdown_list: [{symbol, shares, price, value, price_source}]

    Per ADR-030 (Wave 3 Task 6 cutover): with stored prices (the default),
    ``total`` is ``load_portfolio_state_from_db()``'s own ``total_usd`` —
    i.e. ``get_portfolio_total_value()`` — never an independent shares*price
    re-sum here. ``--live-prices`` is this diagnostic's one intentional
    exception: it recomputes a *comparison* total using fresh yfinance quotes
    specifically to detect stale-price drift, and is reported as a distinct,
    clearly-labeled figure, not a silent substitute for the SQLite total.
    """
    if not db_path.exists():
        return 0.0, []

    conn = initialize_db(str(db_path))
    try:
        state = load_portfolio_state_from_db(conn)
    finally:
        conn.close()

    shares_map = state["shares"]
    prices_map = state["prices"]

    live_quotes: dict = {}
    if use_live_prices:
        tickers = [sym for sym in shares_map if sym and sym != "USD_CASH"]
        if tickers:
            result = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "fetch_quotes.py"), ",".join(tickers)],
                capture_output=True, text=True, timeout=45,
            )
            if result.returncode == 0:
                live_quotes = json.loads(result.stdout)

    total = 0.0
    breakdown = []
    for sym, shares in shares_map.items():
        if sym == "USD_CASH":
            price  = prices_map.get(sym, 1.0)
            source = "cash"
        elif use_live_prices and sym in live_quotes and live_quotes[sym].get("price"):
            price  = live_quotes[sym]["price"]
            source = "yfinance-live"
        elif sym in prices_map:
            price  = prices_map[sym]
            source = "stored"
        else:
            price  = 0
            source = "no_price"
        val = shares * price
        total += val
        breakdown.append({"symbol": sym, "shares": shares, "price": price, "value": val, "source": source})

    # Stored-price mode: total is the authoritative SQLite rollup
    # (get_portfolio_total_value(), via load_portfolio_state_from_db), never
    # this loop's own re-sum -- see ADR-030. Live-price mode is the
    # deliberate diagnostic exception described above.
    if not use_live_prices:
        total = state["total_usd"]

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
    label = "live yfinance prices" if args.live_prices else "stored domain_model.sqlite prices"
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
                    if b["source"] == "no_price" and b["symbol"] != "USD_CASH"]
        if no_price:
            print(f"\n   Positions missing a price row (contributing $0 to the total):")
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
