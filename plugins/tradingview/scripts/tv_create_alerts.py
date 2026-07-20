#!/usr/bin/env python3
"""
tv_create_alerts.py - Create TradingView price alerts from DCF projection JSONs.

Usage:
    python3 tv_create_alerts.py                    # all holdings with projections
    python3 tv_create_alerts.py --ticker CRWV      # single ticker
    python3 tv_create_alerts.py --dry-run          # print what would be created

For each ticker, reads the latest AI_AGENT entry in the projection JSON and
creates alerts at the bear / base / bull scenarioPrice levels plus the
weighted fair value (aiThesis.fairValue).

CLI syntax (tradingview-cdp/cli.js):
    node <CLI> alert create --price PRICE --condition crossing --message MESSAGE

Requires TradingView Desktop running with --remote-debugging-port=9222.
Prints a warning and skips the ticker if TradingView is not reachable.
"""

import sys
import json
import argparse
from pathlib import Path

def _find_scripts_dir() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if (candidate / "tv_client.py").exists():
            return candidate
        if (candidate / "scripts" / "tv_client.py").exists():
            return candidate / "scripts"
    raise ImportError("tv_client.py not found — check plugin installation or set TV_CDP_DIR.")

sys.path.insert(0, str(_find_scripts_dir()))
from tv_client import TV_NODE_DIR, tv_call, is_tv_running

REPO_ROOT = TV_NODE_DIR.parent
DB_PATH = REPO_ROOT / "investment_screener" / "backend" / "data" / "domain_model.sqlite"

sys.path.insert(0, str(REPO_ROOT / "investment_screener" / "backend" / "py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    get_latest_projection,
    get_latest_projection_by_source,
    get_projection_scenarios,
    list_symbols_with_projections,
)
from domain_model.price_level_repository import get_price_levels  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_latest_ai_entry(ticker: str, db_path: Path = DB_PATH) -> dict | None:
    """Load the latest projection entry for a ticker, with its scenarios.

    Storage backend (Wave 2 Task 10 rewire): reads `projection_version` /
    `projection_scenario` via `domain_model.projection_repository`, not
    `projections/{TICKER}.json` (that directory was archived at the end of
    Wave 1 — see `730daddb refactor: archive projections/ after Wave 1
    SQLite cutover`, meaning this function always returned None from that
    point on until this rewire). Preserves the original fallback: prefer an
    AI_AGENT-sourced entry, else fall back to the latest entry from any source.
    """
    conn = initialize_db(str(db_path))
    try:
        row = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", (ticker.upper(),)
        ).fetchone()
        if row is None:
            return None
        investment_id = row[0]

        entry = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
        if entry is None:
            entry = get_latest_projection(conn, investment_id)
        if entry is None:
            return None

        scenario_rows = get_projection_scenarios(conn, entry["projection_id"])
        scenarios = {
            s["scenario_name"]: {"scenarioPrice": s.get("scenario_price")}
            for s in scenario_rows
        }

        return {
            "ticker": ticker.upper(),
            "savedAt": entry.get("saved_at", ""),
            "scenarios": scenarios,
            "aiThesis": {"fairValue": entry.get("fair_value")},
        }
    finally:
        conn.close()


def get_alert_levels(entry: dict) -> list[tuple[str, float]]:
    """
    Extract (label, price) tuples from a projection entry.

    Returns alerts for bear / base / bull scenarioPrice values and the
    weighted fair value. Skips any level where scenarioPrice is not computed.
    """
    levels = []
    ticker = entry.get("ticker", "UNKNOWN")
    scenarios = entry.get("scenarios", {})

    for scenario in ("bear", "base", "bull"):
        s = scenarios.get(scenario, {})
        price = s.get("scenarioPrice")
        if price and price > 0:
            label = f"{ticker} {scenario.capitalize()} ${price:.0f}"
            levels.append((label, float(price)))

    fair_value = entry.get("aiThesis", {}).get("fairValue")
    if fair_value and fair_value > 0:
        label = f"{ticker} DCF Fair Value ${fair_value:.0f}"
        levels.append((label, float(fair_value)))

    return levels


def get_tier_alert_levels(ticker: str, db_path: Path = DB_PATH) -> list[tuple[str, float]]:
    """Extract (label, price) tuples from investment.price_level_set/tier rows.

    Storage backend (Wave 2 Task 10 rewire): reads
    ``price_level_set``/``price_level_tier`` via
    ``domain_model.price_level_repository.get_price_levels`` instead of
    target-portfolio.json's ``holdings[].priceLevels`` block (ADR-029).

    Returns richer tiered alerts: buy tiers, sell tiers with trim%, and stop loss.
    Returns empty list if no price-level row exists for this ticker.
    Priority over DCF scenario prices when available.
    """
    conn = initialize_db(str(db_path))
    try:
        row = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", (ticker.upper(),)
        ).fetchone()
        if row is None:
            return []
        price_levels = get_price_levels(conn, row[0])
    finally:
        conn.close()

    if not price_levels:
        return []

    levels = []

    for tier in price_levels.get("buy_tiers", []):
        if tier.get("status") != "active":
            continue
        price = tier.get("price")
        n = tier.get("tier_number", "?")
        if price and price > 0:
            label = f"{ticker} Buy Tier {n} — Accumulate at ${price:.2f}"
            levels.append((label, float(price)))

    for tier in price_levels.get("sell_tiers", []):
        if tier.get("status") != "active":
            continue
        price = tier.get("price")
        n = tier.get("tier_number", "?")
        trim_pct = tier.get("trim_pct")
        action = tier.get("action", "trim")
        if price and price > 0:
            if action == "exit" or trim_pct == 100:
                label = f"{ticker} Exit — Full position at ${price:.2f}"
            else:
                label = f"{ticker} Sell Tier {n} — Trim {trim_pct or 30}% at ${price:.2f}"
            levels.append((label, float(price)))

    stop = price_levels.get("stop_loss")
    if stop and stop.get("status") == "active":
        price = stop.get("price")
        if price and price > 0:
            label = f"{ticker} ⚠️ Stop Loss — Thesis Breaker at ${price:.2f}"
            levels.append((label, float(price)))

    return levels


def create_alert(ticker: str, price: float, message: str, dry_run: bool = False) -> dict:
    """Create a single TradingView price alert."""
    if dry_run:
        return {"dry_run": True, "ticker": ticker, "price": price, "message": message}

    return tv_call(
        "alert", "create",
        "--price", str(price),
        "--condition", "crossing",
        "--message", message,
    )


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def get_all_tickers(db_path: Path = DB_PATH) -> list[str]:
    """Return all tickers that have at least one projection row in domain_model.sqlite.

    Storage backend (Wave 2 Task 10 rewire): replaces globbing the (now
    archived) ``projections/*.json`` directory with
    ``domain_model.projection_repository.list_symbols_with_projections``.
    """
    conn = initialize_db(str(db_path))
    try:
        return list_symbols_with_projections(conn)
    finally:
        conn.close()


def process_ticker(ticker: str, dry_run: bool, db_path: Path = DB_PATH) -> dict:
    """Create alerts for a single ticker. Returns a result summary dict.

    Priority: priceLevels tiers from domain_model.sqlite (richer labels + trim%).
    Fallback: scenarioPrice levels from the latest projection row.
    """
    # --- Primary source: price_level_set/tier rows ---
    tier_levels: list[tuple[str, float]] = get_tier_alert_levels(ticker, db_path)

    # --- Fallback source: DCF scenario prices from projection_version/scenario ---
    entry = load_latest_ai_entry(ticker, db_path)
    dcf_levels = get_alert_levels(entry) if entry else []

    # Use tier levels if available, otherwise fall back to DCF scenario levels
    levels = tier_levels if tier_levels else dcf_levels

    if not levels:
        return {
            "ticker": ticker,
            "status": "skipped",
            "reason": "no price levels or scenarioPrice values found",
        }

    created = []
    failed = []
    for label, price in levels:
        try:
            result = create_alert(ticker, price, label, dry_run=dry_run)
        except Exception as e:
            failed.append({"label": label, "price": price, "error": str(e)})
            continue

        # Task 5A-8: tv_call() (used inside create_alert()) no longer raises
        # on failure — it returns {"error": str, "data": ..., "cached": bool,
        # "timestamp": str} instead. Detect that shape explicitly so a failed
        # alert creation still routes to `failed` instead of `created`.
        if isinstance(result, dict) and result.get("error"):
            failed.append({"label": label, "price": price, "error": result["error"]})
        else:
            created.append({"label": label, "price": price, "result": result})

    return {
        "ticker": ticker,
        "status": "dry_run" if dry_run else "ok",
        "alerts_created": len(created),
        "alerts_failed": len(failed),
        "details": created + failed,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create TradingView price alerts from DCF projection JSONs."
    )
    parser.add_argument("--ticker", help="Single ticker to process (default: all)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without calling TradingView",
    )
    args = parser.parse_args()

    if not args.dry_run and not is_tv_running():
        print(
            "\nTradingView Desktop not detected on port 9222.\n"
            "Launch it with:  python3 plugins/tradingview/scripts/tv_launch.py\n"
            "Or manually:     open -a TradingView --args --remote-debugging-port=9222\n",
            file=sys.stderr,
        )
        sys.exit(1)

    tickers = [args.ticker.upper()] if args.ticker else get_all_tickers()

    if not tickers:
        print(json.dumps({"error": "No projection files found"}))
        sys.exit(1)

    results = []
    for ticker in sorted(tickers):
        result = process_ticker(ticker, dry_run=args.dry_run)
        results.append(result)

    # Summary table
    total_created = sum(r.get("alerts_created", 0) for r in results)
    total_skipped = sum(1 for r in results if r["status"] == "skipped")
    total_failed = sum(r.get("alerts_failed", 0) for r in results)

    output = {
        "results": results,
        "summary": {
            "tickers_processed": len(tickers) - total_skipped,
            "tickers_skipped": total_skipped,
            "alerts_created": total_created,
            "alerts_failed": total_failed,
            "dry_run": args.dry_run,
        },
    }

    print(json.dumps(output, indent=2))

    # Human-readable table to stderr for agent readability
    print("\nAlert Sync Summary:", file=sys.stderr)
    print(f"{'Ticker':<12} {'Status':<10} {'Created':<10} {'Failed'}", file=sys.stderr)
    print("-" * 42, file=sys.stderr)
    for r in results:
        ticker = r["ticker"]
        status = r["status"]
        created = r.get("alerts_created", "-")
        failed = r.get("alerts_failed", "-")
        reason = r.get("reason", "")
        if reason:
            print(f"{ticker:<12} {status:<10} {str(created):<10} {failed}  ({reason})", file=sys.stderr)
        else:
            print(f"{ticker:<12} {status:<10} {str(created):<10} {failed}", file=sys.stderr)


if __name__ == "__main__":
    main()
