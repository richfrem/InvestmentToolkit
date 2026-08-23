#!/usr/bin/env python3
"""
tv_thesis_overlay.py — Generate and inject Pine Script Thesis Overlay into TradingView.

Reads fundamental valuation price levels (Fair Value from projection table,
Target Entry from price_level_tier, Thesis Breaker status from investment table)
from domain_model.sqlite, switches the active TradingView chart to TICKER,
validates the active chart symbol (Pitfall #7), lints the generated Pine Script (Pitfall #26),
and injects it via CDP.

Usage:
    python3 plugins/tradingview/scripts/tv_thesis_overlay.py --ticker NVDA [--dry-run]
"""

import os
import sys
import argparse
import json
import sqlite3
from typing import Dict, Any, Optional

# Resolve imports when executed directly or via symlink
SCRIPTS_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, "../../../"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tv_client import tv_call, validate_cdp_installation
from pine_linter import PineLinter
from investment_screener.backend.py_services.ticker_aliases import normalize_ticker

DEFAULT_DB_PATH = os.path.join(
    PROJECT_ROOT, "investment_screener/backend/data/domain_model.sqlite"
)


def resolve_ticker_levels(symbol: str, db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """
    Resolve valuation levels across investment, projection, and price_level_tier tables.
    """
    norm_symbol = normalize_ticker(symbol)
    result = {
        "symbol": norm_symbol,
        "name": norm_symbol,
        "fair_value": None,
        "target_entry": None,
        "stop_loss": None,
        "breaker_status": None,
        "action": None,
    }

    if not os.path.exists(db_path):
        return result

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # 1. Investment table
        inv = conn.execute(
            "SELECT investment_id, name, thesis_breaker_status FROM investment WHERE symbol = ?;",
            (norm_symbol,),
        ).fetchone()

        investment_id = inv["investment_id"] if inv else norm_symbol
        if inv:
            result["name"] = inv["name"] or norm_symbol
            result["breaker_status"] = inv["thesis_breaker_status"]

        # 2. Projection table (latest version)
        proj = conn.execute(
            "SELECT fair_value, action FROM projection_version WHERE investment_id = ? ORDER BY version DESC LIMIT 1;",
            (investment_id,),
        ).fetchone()
        if proj:
            result["fair_value"] = proj["fair_value"]
            result["action"] = proj["action"]

        # 3. Price level tier table (Target Entry and Stop Loss)
        tiers = conn.execute(
            """
            SELECT plt.tier_kind, plt.price
            FROM price_level_tier plt
            JOIN price_level_set pls ON plt.price_level_set_id = pls.price_level_set_id
            WHERE pls.investment_id = ?;
            """,
            (investment_id,),
        ).fetchall()

        for t in tiers:
            kind = t["tier_kind"]
            price = t["price"]
            if kind == "TARGET_ENTRY" and result["target_entry"] is None:
                result["target_entry"] = price
            elif kind == "STOP_LOSS" and result["stop_loss"] is None:
                result["stop_loss"] = price

    finally:
        conn.close()

    return result


def generate_pine_script_content(levels: Dict[str, Any]) -> str:
    """
    Generate clean Pine Script v6 code with horizontal plot lines and table overlay.
    """
    symbol = levels["symbol"]
    fv = levels.get("fair_value")
    entry = levels.get("target_entry")
    stop = levels.get("stop_loss")
    action = levels.get("action") or "MONITOR"
    breaker = levels.get("breaker_status") or "OK"

    lines = [
        "//@version=6",
        f'indicator("AI Thesis Overlay - {symbol}", overlay=true)',
        "",
        "// === Valuation Level Inputs ===",
        f"fairValue = input.float({fv if fv is not None else 0.0}, title='Fair Value', inline='fv')",
        f"targetEntry = input.float({entry if entry is not None else 0.0}, title='Target Entry', inline='entry')",
        f"stopLoss = input.float({stop if stop is not None else 0.0}, title='Stop Loss / Breaker', inline='stop')",
        "",
        "// === Plot Lines ===",
        "plot(fairValue > 0 ? fairValue : na, title='Fair Value', color=color.new(color.green, 20), style=plot.style_linebr, linewidth=2)",
        "plot(targetEntry > 0 ? targetEntry : na, title='Target Entry', color=color.new(color.blue, 20), style=plot.style_linebr, linewidth=2)",
        "plot(stopLoss > 0 ? stopLoss : na, title='Stop Loss', color=color.new(color.red, 20), style=plot.style_linebr, linewidth=2)",
        "",
        "// === Dashboard Status Badge ===",
        "var table infoTable = table.new(position.top_right, 2, 4, bgcolor=color.new(color.black, 40), border_color=color.gray, border_width=1)",
        "if barstate.islast",
        f"    table.cell(infoTable, 0, 0, 'Ticker', text_color=color.white, text_size=size.small)",
        f"    table.cell(infoTable, 1, 0, '{symbol}', text_color=color.yellow, text_size=size.small)",
        f"    table.cell(infoTable, 0, 1, 'Action', text_color=color.white, text_size=size.small)",
        f"    table.cell(infoTable, 1, 1, '{action}', text_color=color.green, text_size=size.small)",
        f"    table.cell(infoTable, 0, 2, 'Breaker', text_color=color.white, text_size=size.small)",
        f"    table.cell(infoTable, 1, 2, '{breaker}', text_color=color.aqua, text_size=size.small)",
        "",
    ]
    return "\n".join(lines)


def switch_chart_symbol(symbol: str) -> bool:
    """
    Ensure the active chart matches the requested symbol per Pitfall #7.
    """
    norm_symbol = normalize_ticker(symbol)
    res = tv_call("chart", "symbol", norm_symbol)
    if isinstance(res, dict) and res.get("error"):
        print(f"❌ Failed to switch symbol to {norm_symbol}: {res['error']}", file=sys.stderr)
        return False
    return True


def apply_overlay(symbol: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Main orchestration flow for injecting thesis levels.
    """
    levels = resolve_ticker_levels(symbol)
    pine_code = generate_pine_script_content(levels)

    # Save to temp file for linting
    temp_dir = os.path.join(PROJECT_ROOT, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_pine = os.path.join(temp_dir, f"ai_thesis_{levels['symbol']}.pine")

    with open(temp_pine, "w", encoding="utf-8") as f:
        f.write(pine_code)

    # Run Pine Linter (Pitfall #26)
    linter = PineLinter(temp_pine)
    if not linter.lint():
        return {
            "success": False,
            "error": f"Generated Pine Script failed linting: {linter.errors}",
        }

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "levels": levels,
            "pine_file": temp_pine,
        }

    # Verify CDP runtime
    cdp_status = validate_cdp_installation()
    if not cdp_status.get("installed"):
        return {"success": False, "error": f"TradingView CDP engine not ready: {cdp_status.get('issues')}"}

    # Step 1: Switch chart symbol (Pitfall #7)
    if not switch_chart_symbol(levels["symbol"]):
        return {"success": False, "error": f"Could not switch active chart to {levels['symbol']}"}

    # Step 2: Inject Pine Script via Node CLI
    inject_res = tv_call("pine", "inject", "--file", temp_pine)
    return {
        "success": True,
        "symbol": levels["symbol"],
        "levels": levels,
        "inject_result": inject_res,
    }


def main():
    parser = argparse.ArgumentParser(description="Inject AI Thesis Overlay onto TradingView chart")
    parser.add_argument("--ticker", "-t", required=True, help="Stock ticker symbol (e.g. NVDA)")
    parser.add_argument("--dry-run", action="store_true", help="Generate and lint without injecting")
    args = parser.parse_args()

    res = apply_overlay(args.ticker, dry_run=args.dry_run)
    print(json.dumps(res, indent=2))
    if not res.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
