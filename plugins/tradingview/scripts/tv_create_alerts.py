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
PROJECTIONS_DIR = REPO_ROOT / "investment_screener" / "backend" / "data" / "projections"
TARGET_JSON_PATH = REPO_ROOT / "investment_screener" / "backend" / "data" / "theses" / "target-portfolio.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_latest_ai_entry(ticker: str) -> dict | None:
    """Load the latest AI_AGENT projection entry for a ticker."""
    proj_file = PROJECTIONS_DIR / f"{ticker.upper()}.json"
    if not proj_file.exists():
        return None

    try:
        with open(proj_file) as f:
            entries = json.load(f)
    except Exception:
        return None

    if not isinstance(entries, list) or not entries:
        return None

    ai_entries = [e for e in entries if e.get("source") == "AI_AGENT"]
    if not ai_entries:
        # Fall back to any entry if no AI_AGENT tagged entries
        ai_entries = entries

    return max(ai_entries, key=lambda x: x.get("savedAt", ""))


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


def get_tier_alert_levels(ticker: str, target_json: dict) -> list[tuple[str, float]]:
    """Extract (label, price) tuples from priceLevels blocks in target-portfolio.json.

    Returns richer tiered alerts: buy tiers, sell tiers with trim%, and stop loss.
    Returns empty list if no priceLevels block found for this ticker.
    Priority over DCF scenario prices when available.
    """
    holding = next(
        (h for h in target_json.get("holdings", [])
         if h.get("ticker", "").upper() == ticker.upper()),
        None
    )
    if not holding:
        return []

    price_levels = holding.get("priceLevels")
    if not price_levels:
        return []

    levels = []

    for tier in price_levels.get("buyTiers", []):
        if tier.get("status") != "active":
            continue
        price = tier.get("price")
        n = tier.get("tier", "?")
        if price and price > 0:
            label = f"{ticker} Buy Tier {n} — Accumulate at ${price:.2f}"
            levels.append((label, float(price)))

    for tier in price_levels.get("sellTiers", []):
        if tier.get("status") != "active":
            continue
        price = tier.get("price")
        n = tier.get("tier", "?")
        trim_pct = tier.get("trimPct")
        action = tier.get("action", "trim")
        if price and price > 0:
            if action == "exit" or trim_pct == 100:
                label = f"{ticker} Exit — Full position at ${price:.2f}"
            else:
                label = f"{ticker} Sell Tier {n} — Trim {trim_pct or 30}% at ${price:.2f}"
            levels.append((label, float(price)))

    stop = price_levels.get("stopLoss")
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

def get_all_tickers() -> list[str]:
    """Return all tickers that have projection JSON files."""
    return [p.stem for p in PROJECTIONS_DIR.glob("*.json")]


def process_ticker(ticker: str, dry_run: bool, target_json: dict | None = None) -> dict:
    """Create alerts for a single ticker. Returns a result summary dict.

    Priority: priceLevels tiers from target-portfolio.json (richer labels + trim%).
    Fallback: scenarioPrice levels from projection JSON.
    """
    # --- Primary source: priceLevels from target-portfolio.json ---
    tier_levels: list[tuple[str, float]] = []
    if target_json:
        tier_levels = get_tier_alert_levels(ticker, target_json)

    # --- Fallback source: DCF scenario prices from projections/ ---
    entry = load_latest_ai_entry(ticker)
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

    # Load target-portfolio.json once for priceLevels tier alerts
    target_json = None
    if TARGET_JSON_PATH.exists():
        try:
            with open(TARGET_JSON_PATH) as f:
                target_json = json.load(f)
        except Exception:
            pass  # proceed without tier alerts if file unreadable

    tickers = [args.ticker.upper()] if args.ticker else get_all_tickers()

    if not tickers:
        print(json.dumps({"error": "No projection files found"}))
        sys.exit(1)

    results = []
    for ticker in sorted(tickers):
        result = process_ticker(ticker, dry_run=args.dry_run, target_json=target_json)
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
