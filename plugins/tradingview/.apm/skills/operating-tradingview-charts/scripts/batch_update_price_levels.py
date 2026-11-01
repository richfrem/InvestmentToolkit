#!/usr/bin/env python3
"""
batch_update_price_levels.py — Batch update the buy, trim and stop lines on every TradingView chart.
====================================================================================================

Purpose:
    Draws each stock's stored price levels (domain_model.sqlite) as horizontal lines on that
    stock's own TradingView chart. TradingView keeps a drawing with the symbol it was drawn on,
    so one batch run leaves every chart with its own levels; clicking through the watchlist
    shows the right lines on each stock with no background process.

    Indicator inputs cannot do this: they belong to the chart layout, so a batch that sets them
    leaves the last ticker's levels on every chart. After drawing, this script blanks the
    AI TA Levels indicator's level inputs so it neither draws a second set nor shows the
    "Levels are for X, not Y" warning.

    One run per ticker: switch the chart, remove the old level lines (only lines this tool drew,
    labelled "AI-L:", unless --all-lines), draw one labelled line per stored level, check that
    they are on the chart.

Layer:
    Plugins / TradingView / Operating TradingView Charts / Scripts

Usage Examples:
    # Recalculate levels in SQLite, then redraw every chart (the full refresh):
    python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --recalculate --sweep

    # Redraw every chart from the levels already stored:
    python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --sweep

    # See what would be removed and drawn, changing nothing:
    python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --sweep --dry-run

    # Also remove line drawings this tool did not draw (the owner's own lines):
    python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --sweep --all-lines

    # One ticker: recalculate, then redraw its chart:
    python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --ticker NFLX

Key Functions:
    - get_followed_tickers()     — active holdings and watchlisted symbols
    - batch_recalculate_levels() — recalculates and stores levels in domain_model.sqlite
    - build_level_plan()         — {ticker: [{price, label, color}]} from the stored levels
    - sync_chart_lines()         — draws the plan on every chart through the CDP engine

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (price_level_set / price_level_tier, projections)
    - investment_screener/backend/py_services/update_price_levels.py (level derivation)
    - investment_screener/backend/py_services/pine_level_inputs.py (stored levels reader, indicator input titles)
    - tradingview-cdp/core/level_lines.js (chart levelLines: switch, clear, draw, verify)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable, Dict, List, Optional

# Resolve project root and backend services directory
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "investment_screener").is_dir())
ENGINE_DIR = PROJECT_ROOT / "investment_screener/backend/py_services"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from pine_level_inputs import INDICATOR_NAME, input_titles, known_symbol, level_inputs, ticker_input_title
from update_price_levels import derive_and_write, derive_and_write_followed

# (pine input name, line label, colour) — the order lines are drawn in
LEVEL_LINES = (
    ("target_trim3", "Trim 3", "#ab47bc"),
    ("target_trim2", "Trim 2", "#fb8c00"),
    ("target_trim1", "Trim 1", "#fdd835"),
    ("target_fair", "DCF Fair Value", "#00bcd4"),
    ("target_buy1", "Buy 1", "#26a69a"),
    ("target_buy", "Buy 2", "#00e676"),
    ("target_buy3", "Buy 3", "#2962ff"),
    ("target_stop", "Stop", "#f44336"),
)
ALERT_TIERS = (
    ("target_buy1", "Buy 1"),
    ("target_trim1", "Trim 1"),
    ("target_fair", "DCF Fair Value"),
    ("target_stop", "Stop"),
)
SWEEP_TIMEOUT_PER_TICKER = 15   # seconds: symbol switch, settle, clear, draw, verify


def get_followed_tickers(db_path: str | Path | None = None) -> List[str]:
    """Retrieve all symbols in scope (active holdings and watchlisted stocks) from domain_model.sqlite.

    Args:
        db_path: Optional custom path to domain_model.sqlite.

    Returns:
        Sorted list of uppercase ticker symbols.
    """
    import review_cycle
    from domain_model.db_client import initialize_db

    db_file = str(db_path or (PROJECT_ROOT / "investment_screener/backend/data/domain_model.sqlite"))
    conn = initialize_db(db_file)
    try:
        items = review_cycle.in_scope(conn)
        return sorted({item["symbol"].upper() for item in items if item.get("symbol") and item["symbol"] != "CASH_USD"})
    finally:
        conn.close()


def batch_recalculate_levels(
    source: str = "combined",
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    """Recalculate and persist price levels in SQLite for all followed portfolio & watchlist names.

    Args:
        source: Tier derivation strategy ('combined', 'dcf', 'ta', etc.).
        dry_run: When True, computes tiers without committing to database.
        db_path: Optional path to domain_model.sqlite.

    Returns:
        Dictionary summary containing 'updated', 'skipped', and 'failed' lists.
    """
    dbp = Path(db_path) if db_path else None
    return derive_and_write_followed(source=source, dry_run=dry_run, db_path=dbp)


def build_level_plan(tickers: List[str], db_path: str | Path | None = None) -> Dict[str, List[Dict[str, Any]]]:
    """The lines to draw on each ticker's chart, read from its stored levels.

    Args:
        tickers: Ticker symbols.
        db_path: Optional path to domain_model.sqlite.

    Returns:
        {ticker: [{price, label, color}]}. A ticker with no stored levels gets an empty list,
        so its old level lines are still cleared.
    """
    plan: Dict[str, List[Dict[str, Any]]] = {}
    for ticker in tickers:
        sym = ticker.upper()
        values = level_inputs(sym, db_path) if known_symbol(sym, db_path) else {}
        plan[sym] = [
            {"price": round(values[name], 2), "label": label, "color": color}
            for name, label, color in LEVEL_LINES
            if values.get(name, 0) > 0
        ]
    return plan


def build_alert_plan(tickers: List[str], db_path: str | Path | None = None) -> List[Dict[str, Any]]:
    """Build alert creation tasks for key actionable levels across tickers.

    Args:
        tickers: Ticker symbols.
        db_path: Optional path to domain_model.sqlite.

    Returns:
        List of dicts: [{"symbol": sym, "price": price, "message": f"{sym}: {label} ${price:.2f}"}]
    """
    alerts: List[Dict[str, Any]] = []
    for ticker in tickers:
        sym = ticker.upper()
        values = level_inputs(sym, db_path) if known_symbol(sym, db_path) else {}
        for name, label in ALERT_TIERS:
            price = values.get(name, 0.0)
            if price > 0:
                p_round = round(price, 2)
                alerts.append({
                    "symbol": sym,
                    "price": p_round,
                    "message": f"{sym}: {label} ${p_round:.2f}",
                })
    return alerts


def sync_alerts(
    tickers: Optional[List[str]] = None,
    db_path: str | Path | None = None,
    dry_run: bool = False,
    clear: bool = False,
    call: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Synchronize audible price alerts in TradingView Desktop with visual chart lines.

    Args:
        tickers: Ticker symbols to alert on.
        db_path: Optional path to domain_model.sqlite.
        dry_run: Report what alerts would be created without submitting them.
        clear: When True, deletes existing alerts via CDP before recreating.
        call: CDP CLI caller (injectable for testing).

    Returns:
        Summary dict containing success, cleared, created_count, and failed list.
    """
    if call is None:
        from tv_client import tv_call as call

    cleared = False
    if clear and not dry_run:
        del_res = call("alert", "delete", "--all", timeout=20, enable_retry=False, enable_cache_fallback=False)
        cleared = bool(isinstance(del_res, dict) and del_res.get("success"))

    symbols = tickers if tickers is not None else get_followed_tickers(db_path)
    alerts = build_alert_plan(symbols, db_path)

    created: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "cleared": clear,
            "total_alerts": len(alerts),
            "alerts": alerts,
            "created_count": 0,
            "failed": [],
        }

    # Group alerts by symbol to minimize chart switches
    by_symbol: Dict[str, List[Dict[str, Any]]] = {}
    for a in alerts:
        by_symbol.setdefault(a["symbol"], []).append(a)

    for sym, sym_alerts in by_symbol.items():
        switch_target = f"TSX:{sym.replace('.TO', '')}" if sym.endswith(".TO") else sym
        call("chart", "symbol", switch_target, timeout=15, enable_retry=False, enable_cache_fallback=False)

        for item in sym_alerts:
            res = call(
                "alert", "create",
                "--price", f"{item['price']:.2f}",
                "--condition", "crossing",
                "--message", item["message"],
                timeout=15, enable_retry=False, enable_cache_fallback=False,
            )
            if isinstance(res, dict) and res.get("success"):
                created.append(item)
            else:
                err = res.get("error", str(res)) if isinstance(res, dict) else str(res)
                failed.append({"symbol": sym, "price": item["price"], "error": err})

    return {
        "success": len(failed) == 0,
        "cleared": cleared,
        "total_alerts": len(alerts),
        "created_count": len(created),
        "failed": failed,
    }


def _blank_indicator_values() -> Dict[str, Any]:
    """Indicator input titles -> blank value, so the indicator draws no levels and shows no warning."""
    values: Dict[str, Any] = {title: 0 for title in input_titles().values()}
    tag = ticker_input_title()
    if tag:
        values[tag] = ""
    return values


def sync_chart_lines(
    tickers: Optional[List[str]] = None,
    db_path: str | Path | None = None,
    dry_run: bool = False,
    all_lines: bool = False,
    call: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Draw every ticker's stored levels as lines on its own TradingView chart.

    Args:
        tickers: Ticker symbols; defaults to every holding and watchlist name.
        db_path: Optional path to domain_model.sqlite.
        dry_run: Report what would be removed and drawn; change nothing.
        all_lines: Also remove line drawings this tool did not draw.
        call: CDP CLI caller (defaults to tv_client.tv_call); injectable for tests.

    Returns:
        {success, total, synced: [tickers], failed: [{symbol, error}], indicator_blanked}.
    """
    if call is None:
        from tv_client import tv_call as call
    symbols = tickers if tickers is not None else get_followed_tickers(db_path)
    plan = build_level_plan(symbols, db_path)

    with tempfile.NamedTemporaryFile("w", suffix=".json", prefix="level_plan_", delete=False) as fh:
        json.dump(plan, fh)
        plan_path = fh.name
    try:
        args = ["chart", "levelLines", "--plan", plan_path]
        if dry_run:
            args.append("--dry-run")
        if all_lines:
            args.append("--all-lines")
        res = call(*args, timeout=30 + SWEEP_TIMEOUT_PER_TICKER * len(plan),
                   enable_retry=False, enable_cache_fallback=False)
    finally:
        Path(plan_path).unlink(missing_ok=True)

    res = res if isinstance(res, dict) else {"success": False, "error": str(res)}
    failed = res.get("failed")
    if failed is None:   # the engine call itself failed: no ticker was confirmed drawn
        failed = [{"symbol": s, "error": res.get("error", "levelLines call failed")} for s in plan]
    out = {
        "success": bool(res.get("success")) and not failed,
        "total": len(plan),
        "synced": res.get("synced", []),
        "failed": failed,
        "results": res.get("results", []),
        "indicator_blanked": False,
    }
    if not dry_run:
        blank = call("chart", "setInputs", "--name", INDICATOR_NAME, "--values", json.dumps(_blank_indicator_values()),
                     timeout=30, enable_cache_fallback=False)
        out["indicator_blanked"] = bool(isinstance(blank, dict) and blank.get("success"))
    return out


def _print_sync(res: Dict[str, Any], dry_run: bool) -> int:
    if dry_run:
        for r in res.get("results", []):
            if r.get("success"):
                print(f"  {r['symbol']}: would remove {r['wouldRemove']}, draw {r['wouldDraw']}"
                      f" (other line drawings on chart: {r['otherLines']})")
    print(f"\nChart lines {'checked' if dry_run else 'drawn'}: {len(res['synced'])}/{res['total']} tickers.")
    if not dry_run:
        print("AI TA Levels indicator inputs blanked." if res["indicator_blanked"]
              else "Note: AI TA Levels indicator not blanked (not on the chart?); it may still show its own levels.")
    if res["failed"]:
        print(f"FAILED ({len(res['failed'])}):", file=sys.stderr)
        for item in res["failed"]:
            print(f"  ✗ {item['symbol']}: {item['error']}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    """CLI entry point for batch updating TradingView price level lines."""
    parser = argparse.ArgumentParser(description="Batch update the buy, trim and stop lines on every TradingView chart.")
    parser.add_argument("--recalculate", action="store_true", help="Recalculate and store levels in SQLite for all followed names")
    parser.add_argument("--sweep", action="store_true", help="Redraw the stored levels as lines on every chart")
    parser.add_argument("--sync-alerts", action="store_true", help="Synchronize audible crossing alerts with visual chart lines")
    parser.add_argument("--clear-alerts", action="store_true", help="Clear all existing TradingView alerts before creating fresh ones")
    parser.add_argument("--ticker", type=str, help="Recalculate one ticker, then redraw its chart")
    parser.add_argument("--all-lines", action="store_true", help="Also remove line drawings this tool did not draw")
    parser.add_argument("--source", type=str, default="combined", choices=["combined", "dcf", "ta", "manual"],
                        help="Price level derivation source (default: combined)")
    parser.add_argument("--dry-run", action="store_true", help="Change neither the database nor the charts")
    parser.add_argument("--db", type=str, default=None, help="Path to domain_model.sqlite")
    args = parser.parse_args()
    dbp = Path(args.db) if args.db else None

    if args.ticker:
        sym = args.ticker.upper()
        print(f"Recalculating price levels for {sym} (source={args.source}, dry_run={args.dry_run})...")
        res = derive_and_write(sym, source=args.source, dry_run=args.dry_run, db_path=dbp)
        print(json.dumps(res, indent=2))
        rc = _print_sync(sync_chart_lines([sym], db_path=dbp, dry_run=args.dry_run, all_lines=args.all_lines), args.dry_run)
        if args.sync_alerts:
            print(f"Synchronizing price alerts for {sym}...")
            ares = sync_alerts([sym], db_path=dbp, dry_run=args.dry_run, clear=args.clear_alerts)
            print(f"Alerts created: {ares['created_count']}/{ares['total_alerts']} (cleared: {ares['cleared']}).")
            if ares["failed"]:
                for f in ares["failed"]:
                    print(f"  ✗ {f['symbol']} ${f['price']}: {f['error']}", file=sys.stderr)
        return rc

    rc = 0
    if args.clear_alerts and not args.sync_alerts and not args.dry_run:
        print("Clearing all TradingView alerts...")
        from tv_client import tv_call
        tv_call("alert", "delete", "--all", timeout=20, enable_retry=False, enable_cache_fallback=False)
        print("✓ All alerts cleared.")

    if args.recalculate or (not args.sweep and not args.sync_alerts):
        print(f"Batch recalculating price levels for all followed tickers (source={args.source}, dry_run={args.dry_run})...")
        res = batch_recalculate_levels(source=args.source, dry_run=args.dry_run, db_path=dbp)
        print(f"Completed: {len(res['updated'])} updated, {len(res['skipped'])} skipped, {len(res['failed'])} failed.")
        for item in res["failed"]:
            print(f"  ✗ {item['ticker']}: {item['reason']}", file=sys.stderr)
        rc = 1 if res["failed"] else 0

    if args.sweep:
        print("Drawing level lines on every chart...")
        rc = max(rc, _print_sync(sync_chart_lines(db_path=dbp, dry_run=args.dry_run, all_lines=args.all_lines), args.dry_run))

    if args.sync_alerts:
        print("Synchronizing audible price alerts with chart lines...")
        ares = sync_alerts(db_path=dbp, dry_run=args.dry_run, clear=args.clear_alerts)
        print(f"Alerts created: {ares['created_count']}/{ares['total_alerts']} (cleared: {ares['cleared']}).")
        if ares["failed"]:
            for f in ares["failed"]:
                print(f"  ✗ {f['symbol']} ${f['price']}: {f['error']}", file=sys.stderr)
            rc = max(rc, 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
