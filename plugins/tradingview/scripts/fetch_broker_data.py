#!/usr/bin/env python3
"""
fetch_broker_data.py (Python Utility)
======================================

Purpose:
    Broker-agnostic portfolio data fetcher. Reads accounts, positions, balances,
    and orders from TradingView's broker panel via CDP DOM (primary), with optional
    broker snapshot for cross-validation.

    Note: TradingView CDP is the canonical runtime source of truth. In --snapshot mode the
    consolidated per-account positions/cash are persisted to the domain model
    (domain_model.sqlite) ONLY. The raw snapshot is returned to the Node
    caller (BrokerSyncService.spawnFetchBroker) over stdout as a single JSON line
    (emit_snapshot_json); all progress output goes to stderr so stdout stays clean.

Layer: Backend / py_services / Broker

Usage Examples:
    # Inspect broker panel DOM (for selector discovery):
    python3 investment_screener/backend/py_services/fetch_broker_data.py --inspect

    # Fetch from TradingView CDP:
    python3 investment_screener/backend/py_services/fetch_broker_data.py --positions --source tv
    python3 investment_screener/backend/py_services/fetch_broker_data.py --balances --source tv
    python3 investment_screener/backend/py_services/fetch_broker_data.py --accounts --source tv
    python3 investment_screener/backend/py_services/fetch_broker_data.py --snapshot --source tv

    # Consolidated snapshot of all accounts, persisted to domain_model.sqlite:
    python3 investment_screener/backend/py_services/fetch_broker_data.py --snapshot

    # Diff the live TradingView positions against the positions stored in domain_model.sqlite:
    python3 investment_screener/backend/py_services/fetch_broker_data.py --compare

Key Functions:
    - fetch_tv_snapshot() - Reads every account's positions and balances from the TradingView broker panel via CDP
    - fetch_stored_positions() - The positions stored in domain_model.sqlite, summed per symbol
    - compare_snapshots() - Diffs live TV positions against the stored positions
    - write_snapshot()  - Persists the snapshot to domain_model.sqlite (SQLite only)
    - emit_snapshot_json() - Emits the snapshot as one JSON line on stdout (Node IPC return channel)

Key Input Dependencies:
    - TradingView Desktop on CDP port 9222 (broker panel: accounts, positions, balances)
    - investment_screener/backend/data/domain_model.sqlite (stored exchange rate; destination of the snapshot)

Key Output Dependencies:
    - domain_model.sqlite rows (account_investment, broker_reported_total, broker_exchange_rate)
    - In --snapshot mode, one JSON line on stdout (all progress output goes to stderr)
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
from tv_account_coverage import MAX_READS

REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
BACKEND_SRC = os.path.abspath(os.path.join(REPO_ROOT, "investment_screener", "backend", "src"))
DATA_DIR = os.path.abspath(os.path.join(REPO_ROOT, "investment_screener", "backend", "data"))
DOMAIN_MODEL_PY_SERVICES_DIR = os.path.abspath(
    os.path.join(REPO_ROOT, "investment_screener", "backend", "py_services")
)
DOMAIN_MODEL_DB_PATH = os.path.join(DATA_DIR, "domain_model.sqlite")

sys.path.insert(0, BACKEND_SRC)
sys.path.insert(0, DOMAIN_MODEL_PY_SERVICES_DIR)  # so `domain_model.*` resolves regardless of cwd

REAL_ACCOUNTS = {"TFSA", "RRSP", "CASH"}


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
        totalEquityCAD:         t.grandTotalCAD,
        totalEquityCADCombined: t.grandTotalCAD,
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


def fetch_complete_tv_snapshot(db_path: Optional[str] = None) -> tuple:
    """Read the portfolio snapshot, re-reading until every account that holds something is covered.

    Returns:
        (snapshot, missing_accounts). ``missing_accounts`` is empty for a complete read.
        An account whose switch failed counts as missing (tv_account_coverage.py).
    """
    from domain_model.db_client import initialize_db
    from tv_account_coverage import accounts_with_holdings, read_until_complete

    conn = initialize_db(db_path or DOMAIN_MODEL_DB_PATH)
    try:
        expected = accounts_with_holdings(conn) & REAL_ACCOUNTS
    finally:
        conn.close()
    return read_until_complete(
        fetch_tv_snapshot,
        lambda snap: [s.get("accountType") for s in snap.get("snapshots", []) if not s.get("error")],
        expected,
    )


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


# ── Broker source ──────────────────────────────────────────────────────────

def fetch_stored_positions(db_path: Optional[str] = None) -> Optional[dict]:
    """The positions stored in domain_model.sqlite, summed across accounts per symbol.

    This is the baseline ``--compare`` diffs a live TradingView read against.

    Args:
        db_path: Database to read; defaults to the real domain_model.sqlite.

    Returns:
        {"holdings": [{"symbol", "shares"}, ...]}, or None when the database does not exist.
    """
    path = str(db_path or DOMAIN_MODEL_DB_PATH)
    if not os.path.exists(path):
        return None
    from portfolio_io import load_portfolio_state
    state = load_portfolio_state(None, db_path=path)
    return {"holdings": [{"symbol": sym, "shares": qty} for sym, qty in state["shares"].items()]}


# ── compare ───────────────────────────────────────────────────────────────────

def compare_snapshots(tv: dict, qt: dict) -> dict:
    """
    Diff TV positions vs broker positions field-by-field.
    Returns a report with: matched, qty_mismatch, tv_only, qt_only rows.
    """
    tv_pos = {p["symbol"]: p for p in tv.get("positions", [])}
    qt_pos = {}

    # qt is {"holdings": [{symbol, shares, ...}]} (fetch_stored_positions)
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
    print("║         TV vs Broker — Position Diff              ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  TV positions:       {s['total_tv']:<33}║")
    print(f"║  broker positions:{s['total_qt']:<33}║")
    print(f"║  ✓ Matched:          {s['matched']:<33}║")
    print(f"║  ⚠ Qty mismatch:     {s['mismatched']:<33}║")
    print(f"║  TV only:            {s['tv_only']:<33}║")
    print(f"║  Broker only:     {s['qt_only']:<33}║")
    print("╚══════════════════════════════════════════════════════╝")

    if report["qty_mismatch"]:
        print("\n⚠  QUANTITY MISMATCHES:")
        for row in report["qty_mismatch"]:
            print(f"   {row['symbol']:<8}  TV={row['tv_qty']}  QT={row['qt_qty']}")

    if report["tv_only"]:
        print("\n📺  TV ONLY (not in the stored positions):")
        for row in report["tv_only"]:
            print(f"   {row['symbol']:<8}  qty={row['qty']}")

    if report["qt_only"]:
        print("\n🏦  Broker only (not found in TV):")
        for row in report["qt_only"]:
            print(f"   {row['symbol']:<8}  qty={row['qty']}")

    if s["mismatched"] == 0 and s["tv_only"] == 0 and s["qt_only"] == 0:
        print("\n✅  All positions match the stored positions.")
    else:
        print("\n❌  Discrepancies found between TradingView and the stored positions.")


# ── snapshot writer ───────────────────────────────────────────────────────────

def build_totals_from_balances(balances: dict, stored_exchange_rate: float) -> dict:
    """Pure transform: live TV account balances -> totals dict.

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


def _compute_exchange_rate_from_snapshot(snapshot: dict) -> Optional[float]:
    """Infer the live USD->CAD rate from TV's own native equity totals.

    Replicates investment_screener/backend/src/utils/helpers.ts::getLiveUsdCadRate()'s
    exact math: sum totalEquityCADCombined (falling back to totalEquityCAD) and
    totalEquityUSDCombined (falling back to totalEquityUSD) across every snapshot,
    then rate = totalCAD / totalUSD. Returns None when either sum is non-positive
    (no bogus rate written). Per CLAUDE.md pitfall #27 the rate is ALWAYS inferred
    from these native broker values, never an external FX API.
    """
    total_cad = 0.0
    total_usd = 0.0
    for snap in snapshot.get("snapshots", []):
        balances = snap.get("balances") or {}
        cad_combined = balances.get("totalEquityCADCombined")
        cad_fallback = balances.get("totalEquityCAD")
        cad = cad_combined if cad_combined is not None else (cad_fallback if cad_fallback is not None else 0)
        usd_combined = balances.get("totalEquityUSDCombined")
        usd_fallback = balances.get("totalEquityUSD")
        usd = usd_combined if usd_combined is not None else (usd_fallback if usd_fallback is not None else 0)
        total_cad += float(cad)
        total_usd += float(usd)
    if total_usd > 0 and total_cad > 0:
        return total_cad / total_usd
    return None


def _compute_exchange_rate_from_balances(balances: dict) -> Optional[float]:
    """Infer the live USD->CAD rate from the LIGHTWEIGHT --balances payload's
    already-summed top-level totals (no per-account loop needed -- unlike
    _compute_exchange_rate_from_snapshot, this payload's totalEquityCADCombined/
    totalEquityUSDCombined are already summed across every real account by
    fetch_tv_balances()). Falls back to the non-Combined fields when absent.
    Returns None when either total is non-positive (no bogus rate written).
    """
    cad_combined = balances.get("totalEquityCADCombined")
    cad_fallback = balances.get("totalEquityCAD")
    cad = cad_combined if cad_combined is not None else cad_fallback
    usd_combined = balances.get("totalEquityUSDCombined")
    usd_fallback = balances.get("totalEquityUSD")
    usd = usd_combined if usd_combined is not None else usd_fallback
    if cad is None or usd is None:
        return None
    cad = float(cad)
    usd = float(usd)
    if usd > 0 and cad > 0:
        return cad / usd
    return None


def refresh_exchange_rate_only(db_path: str = DOMAIN_MODEL_DB_PATH) -> Optional[float]:
    """Wave 3 Task 8 (price-refresh/exchange-rate sync gap): refresh JUST the
    stored USD->CAD rate, without a full broker sync.

    Calls fetch_tv_balances() (--balances -- a lightweight balance-only CDP
    fetch, far cheaper than --snapshot's full position sync), computes the
    rate from its already-summed top-level totals, and persists it via
    upsert_exchange_rate(). Callable as a CLI flag (--refresh-exchange-rate)
    and importable so routes/portfolio.ts's POST /refresh-prices can spawn it
    IN PARALLEL with the price fetch -- keeping the rate fresh on every price
    refresh, not just during a full --snapshot broker sync.

    Returns the computed rate, or None if the balance fetch failed or the
    totals were non-positive (no bogus rate written either way).
    """
    from domain_model.db_client import initialize_db
    from domain_model.exchange_rate_repository import upsert_exchange_rate

    balances = fetch_tv_balances()
    if not balances or balances.get("error"):
        return None

    rate = _compute_exchange_rate_from_balances(balances)
    if rate is None:
        return None

    conn = initialize_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    upsert_exchange_rate(conn, rate, now)
    return rate


def _persist_snapshot_to_db(
    snapshot: dict,
    db_path: str = DOMAIN_MODEL_DB_PATH,
    totals: Optional[dict] = None,
) -> int:
    """Persist a raw TV snapshot's real per-account positions/cash into
    account_investment rows -- mirrors migrate_portfolio_to_sqlite.py's
    per-holding write shape. Only the three real, seeded broker sub-accounts
    (TFSA/RRSP/CASH) are in scope; cash is written as a CASH_USD investment row
    via the same upsert_account_investment path as any equity position (Wave 0
    resolved decision 5), not a special-cased column. This is the SOLE
        persistence path in write_snapshot().

    ``totals`` (the broker-authoritative ``totals`` block built by build_totals_from_balances)
    is optional. When present with a positive ``totalUSD``, the broker's own
    last-reported total (totalUSD/totalCAD/totalSource) is captured in
    broker_reported_total (Wave 3 Task 8, tvSnapshot closure) -- the single fact
    verify_portfolio_total.py's reconciliation audit compares against the computed
    total. Never a substitute for get_portfolio_total_value(); only the audited-
    against comparison source.
    """
    from domain_model.db_client import initialize_db
    from domain_model.account_repository import upsert_account
    from domain_model.account_investment_repository import upsert_account_investment
    from domain_model.investment_repository import resolve_investment
    from domain_model.exchange_rate_repository import upsert_exchange_rate
    from domain_model.broker_reported_total_repository import upsert_broker_reported_total
    from ticker_aliases import normalize_ticker

    conn = initialize_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    written = 0
    for snap in snapshot.get("snapshots", []):
        account_id = snap.get("accountType")
        if account_id not in REAL_ACCOUNTS:
            continue
        upsert_account(conn, account_id, account_id, account_id)

        cash_usd = float((snap.get("balances") or {}).get("cashUSD") or 0)
        if cash_usd > 0:
            cash_investment_id = resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD")
            upsert_account_investment(
                conn, account_id, cash_investment_id, quantity=cash_usd,
                average_cost=1.0, book_value=cash_usd, currency="USD", last_synced_at=now,
            )

        for pos in snap.get("positions", []):
            quantity = float(pos.get("quantity") or 0)
            if quantity <= 0:
                continue  # closed/flattened position -- no noise row
            symbol = pos.get("symbol")
            if not symbol:
                continue
            symbol = normalize_ticker(symbol)
            investment_id = resolve_investment(conn, symbol, asset_class="EQUITY", currency="USD")
            upsert_account_investment(
                conn, account_id, investment_id, quantity=quantity,
                average_cost=pos.get("avgFillPrice"), book_value=None,
                currency="USD", last_synced_at=now,
            )
            written += 1

    # Wave 3 Task 8: store the single broker-reported FX fact (USD->CAD),
    # inferred from the SAME native TV totals helpers.ts::getLiveUsdCadRate() uses.
    # Only the scalar rate is stored (ADR-030 addendum) -- never a CAD total.
    rate = _compute_exchange_rate_from_snapshot(snapshot)
    if rate is not None:
        upsert_exchange_rate(conn, rate, now)

    # Wave 3 Task 8 (tvSnapshot closure): store the broker's own last-reported
    # total (totals.totalUSD/totalCAD/totalSource) for verify_portfolio_total.py's
    # reconciliation audit. Only the audited-against comparison source is stored,
    # never a substitute for the computed get_portfolio_total_value().
    if totals:
        total_usd = totals.get("totalUSD")
        if total_usd is not None and total_usd > 0:
            upsert_broker_reported_total(
                conn,
                float(total_usd),
                totals.get("totalCAD"),
                now,
                totals.get("totalSource"),
            )

    return written


def write_snapshot(snapshot: dict, balances: Optional[dict] = None) -> dict:
    """Persist a TV snapshot to the domain model (SQLite) — SQLite only.

    Persists per-account positions/cash (and the broker-reported total inferred from
    ``balances``) into SQLite, then runs the thesis refresh. The snapshot itself is
    returned to the Node caller as a single JSON line on stdout by
    ``emit_snapshot_json`` (see ``main``). Returns the ``totals`` block built from
    live balances (or ``{}``).
    """
    tv_pos = snapshot.get("positions", [])
    if not tv_pos:
        # getPortfolio() returned no positions — likely getAccounts() failed
        # (MutationObserver miss). Nothing safe to persist; surface loudly on
        # stderr and skip the DB write rather than writing empty/misleading rows.
        print("⚠  TV returned 0 positions — accounts dropdown may not have opened.", file=sys.stderr)
        print("   Holdings NOT updated. Re-run /tv-portfolio-sync or check TradingView broker panel.", file=sys.stderr)
        return {}

    # Build the broker-authoritative totals from live balances (used for the
    # broker_reported_total row and returned to callers). Progress → stderr so it
    # never contaminates the stdout JSON IPC channel.
    totals: dict = {}
    if balances and not balances.get("error"):
        totals = build_totals_from_balances(balances, 1.3795)
        print(
            f"✓ Totals computed: totalUSD=${totals['totalUSD']:,.2f}  cashUSD=${totals['cashUSD']:,.2f}",
            file=sys.stderr,
        )

    # Persist the real per-account positions/cash + broker-reported total to
    # domain_model.sqlite. Best-effort: a DB write failure must not crash the
    # sync — the stdout IPC emission still happens in main().
    try:
        written = _persist_snapshot_to_db(
            snapshot, db_path=DOMAIN_MODEL_DB_PATH, totals=totals or None
        )
        print(f"✓ Persisted {written} position(s) to domain_model.sqlite.", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠  Failed to persist snapshot to domain_model.sqlite: {exc}", file=sys.stderr)

    # Refresh all thesis pages and role fields after every sync.
    _run_portfolio_refresh()

    return totals


def emit_snapshot_json(snapshot: dict) -> None:
    """Emit the snapshot as a single compact JSON line on stdout — the stdout IPC
    return channel read by BrokerSyncService.ts.

    ALL human/progress output in the --snapshot path goes to stderr, so stdout
    carries only this one line; the Node caller (BrokerSyncService.spawnFetchBroker)
    parses the last non-empty stdout line as JSON. Compact (no indent) keeps it a
    single line, robust against any stray earlier stdout output.
    """
    sys.stdout.write(json.dumps(snapshot) + "\n")
    sys.stdout.flush()


def _run_portfolio_refresh() -> None:
    """Run refresh_all.py after any broker sync to keep thesis pages current."""
    _repo_root = Path(SCRIPT_DIR).parents[2]
    refresh_script = _repo_root / "plugins/portfolio-advisor/scripts/refresh_all.py"
    if refresh_script.exists():
        # Redirect the child's stdout to OUR stderr so refresh_all.py's progress
        # output can never contaminate the stdout JSON IPC channel emitted by
        # emit_snapshot_json (which runs after this).
        subprocess.run([sys.executable, str(refresh_script)], check=False, stdout=sys.stderr)
    else:
        print(f"⚠ refresh_all.py not found at {refresh_script}", file=sys.stderr)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch broker data from TradingView CDP or Broker")
    parser.add_argument("--source", choices=["tv", "broker", "auto", "compare"], default="tv")
    parser.add_argument("--accounts",  action="store_true")
    parser.add_argument("--balances",  action="store_true")
    parser.add_argument("--positions", action="store_true")
    parser.add_argument("--orders",    action="store_true")
    parser.add_argument("--snapshot",  action="store_true", help="Full snapshot → domain_model.sqlite + JSON on stdout")
    parser.add_argument("--compare",   action="store_true", help="Diff live TV positions against the stored positions in domain_model.sqlite")
    parser.add_argument("--inspect",   action="store_true", help="Dump broker panel DOM for debugging")
    parser.add_argument("--refresh-exchange-rate", action="store_true",
                         help="Lightweight balances-only USD->CAD rate refresh (no full snapshot sync)")
    parser.add_argument("--allow-partial", action="store_true",
                         help="Save a snapshot even when an account that holds positions was not read")
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

        print("Reading stored positions from domain_model.sqlite...")
        qt = fetch_stored_positions()
        if qt is None:
            print("❌ domain_model.sqlite not found — start the app once, then run broker sync.", file=sys.stderr)
            sys.exit(1)

        report = compare_snapshots(tv, qt)
        print_compare_report(report)
        print()
        print(json.dumps(report, indent=indent))
        return

    # ── balances-only exchange-rate refresh ───────────────────────────────────
    if args.refresh_exchange_rate:
        rate = refresh_exchange_rate_only()
        if rate is None:
            print("⚠  Could not refresh exchange rate (balance fetch failed or totals were non-positive).", file=sys.stderr)
            print(json.dumps({"error": "exchange_rate_refresh_failed"}, indent=indent))
            sys.exit(1)
        print(f"✓ Exchange rate refreshed: {rate}")
        print(json.dumps({"usd_to_cad_rate": rate}, indent=indent))
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
    if args.snapshot or not any([args.accounts, args.balances, args.positions, args.orders, args.compare, args.inspect, args.refresh_exchange_rate]):
        # Fetch balances first — getBalances() is unreliable after account-switching in getPortfolio()
        # NOTE: every human/progress line in this branch goes to stderr. stdout is
        # reserved exclusively for the final single-line JSON snapshot emitted by
        # emit_snapshot_json — it is the IPC return channel BrokerSyncService.ts
        # parses. Any
        # stray stdout print here would corrupt the caller's JSON.parse.
        print("Fetching live balances from TradingView Account Summary...", file=sys.stderr)
        balances: Optional[dict] = fetch_tv_balances()
        if balances.get("error"):
            print(f"⚠  Balance fetch failed: {balances['error']} — totals will not be updated.", file=sys.stderr)
            balances = None

        print("Fetching full portfolio snapshot from TradingView...", file=sys.stderr)
        snapshot, missing = fetch_complete_tv_snapshot()
        if "error" in snapshot:
            print(f"❌ {snapshot['error']}", file=sys.stderr)
            print("   Is TradingView Desktop running with a broker connected?", file=sys.stderr)
            sys.exit(1)
        if missing and not args.allow_partial:
            # A partial write left TFSA stale while reporting success (2026-10-08).
            print(f"❌ TradingView did not return {', '.join(missing)} after {MAX_READS} reads; nothing was saved, "
                  "so the stored positions are unchanged.", file=sys.stderr)
            print("   Open the broker panel's account dropdown once and run the sync again, "
                  "or pass --allow-partial if that account is really empty.", file=sys.stderr)
            sys.exit(3)
        if missing:
            print(f"⚠  Saving without {', '.join(missing)} (--allow-partial).", file=sys.stderr)

        write_snapshot(snapshot, balances=balances)
        accts = snapshot.get("accounts", [])
        snaps = snapshot.get("snapshots", [])
        for s in snaps:
            n = len(s.get("positions", []))
            print(f"   {s.get('accountType','?')} ({s.get('accountId','?')}): {n} positions", file=sys.stderr)
        print(f"✓ {len(snapshot.get('positions', []))} total positions across {len(accts)} accounts", file=sys.stderr)
        print("✓ Persisted to domain_model.sqlite", file=sys.stderr)

        # stdout IPC channel: the ONLY thing on stdout is this single JSON line.
        emit_snapshot_json(snapshot)


if __name__ == "__main__":
    main()
