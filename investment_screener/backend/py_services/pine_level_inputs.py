#!/usr/bin/env python3
"""
pine_level_inputs.py - Fill the ai-ta-levels indicator's action inputs from stored price levels.

Purpose:
    The TradingView chart and the Stock Analysis page must show the same levels. The page reads
    price_level_tier; this module writes those same rows (and the saved DCF fair value) into the
    indicator's input defaults before injection, so the chart draws them. A level that is not
    stored stays 0.0, and the indicator draws nothing for it.

Layer: Backend / Python Services

Usage Examples:
    from pine_level_inputs import fill_level_inputs
    source = fill_level_inputs(pine_source, "VRT")
    python3 pine_level_inputs.py --draw HOOD     # switch the chart to HOOD and draw its stored levels
    python3 pine_level_inputs.py --follow        # keep running: redraw the levels of whichever stock the chart shows

Key Functions (Index):
    - level_inputs(): {pine input name: price} for a ticker from domain_model.sqlite
    - fill_level_inputs(): the indicator source with those values as input defaults
    - input_titles(): {pine input name: input title}, read from the indicator source
    - ticker_input_title(): title of the input that names the ticker the levels belong to
    - known_symbol(): True when the database already has the symbol (so drawing never creates one)
    - draw_levels(): set the chart indicator's inputs, and its ticker tag, to a ticker's stored levels (no Pine Editor)
    - follow_step() / follow(): redraw the levels whenever the chart's symbol changes

Key Input Dependencies:
    - domain_model.sqlite: price_level_set / price_level_tier, projection_version
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "domain_model.sqlite"
INDICATOR = Path(__file__).resolve().parents[3] / "plugins/tradingview/.apm/skills/operating-tradingview-charts/assets/pinescript-indicators/ai-ta-levels.pine"
INDICATOR_NAME = "AI TA Levels"   # matches the chart study name of the saved script (any version suffix)
TICKER_INPUT = "levels_for"       # the string input naming the ticker the levels belong to
LEVEL_INPUTS = ("target_fair", "target_buy1", "target_buy", "target_buy3",
                "target_trim1", "target_trim2", "target_trim3", "target_stop")


def level_inputs(symbol: str, db_path: str | Path | None = None) -> dict[str, float]:
    """Stored levels as ai-ta-levels input values: fair value, buy tiers 1-3, trim tiers 1-3, stop."""
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import resolve_investment
    from domain_model.price_level_repository import get_price_levels
    from domain_model.projection_repository import get_latest_projection_by_source

    conn = initialize_db(str(db_path or DB_PATH))
    try:
        inv = resolve_investment(conn, symbol.upper())
        out: dict[str, float] = {}
        proj = get_latest_projection_by_source(conn, inv, "AI_AGENT")
        if proj and proj.get("fair_value"):
            out["target_fair"] = float(proj["fair_value"])
        levels = get_price_levels(conn, inv) or {}
        active = lambda rows: sorted((r for r in rows or [] if (r.get("status") or "active") == "active"),
                                     key=lambda r: r.get("tier_number") or 0)
        buys, sells = active(levels.get("buy_tiers")), active(levels.get("sell_tiers"))
        for name, rows, i in (("target_buy1", buys, 0), ("target_buy", buys, 1), ("target_buy3", buys, 2),
                              ("target_trim1", sells, 0), ("target_trim2", sells, 1), ("target_trim3", sells, 2)):
            if len(rows) > i and rows[i].get("price"):
                out[name] = float(rows[i]["price"])
        stop = levels.get("stop_loss")
        if stop and (stop.get("status") or "active") == "active" and stop.get("price"):
            out["target_stop"] = float(stop["price"])
        return out
    finally:
        conn.close()


def fill_level_inputs(source: str, symbol: str, db_path: str | Path | None = None) -> str:
    """Return `source` with each `target_* = input.float(0.0, ...)` default set from storage."""
    for name, value in level_inputs(symbol, db_path).items():
        source = re.sub(rf"^({name}\s*=\s*input\.float\()\s*[0-9.]+", rf"\g<1>{value:.2f}", source, count=1, flags=re.M)
    return re.sub(rf'^({TICKER_INPUT}\s*=\s*input\.string\()"[^"]*"', rf'\g<1>"{symbol.upper()}"', source, count=1, flags=re.M)


def input_titles(source: str | None = None) -> dict[str, str]:
    """{pine input variable: input title} for the level inputs, read from the indicator source."""
    source = source if source is not None else INDICATOR.read_text()
    out = {}
    for name in LEVEL_INPUTS:
        m = re.search(rf'^{name}\s*=\s*input\.float\([^,]+,\s*"([^"]+)"', source, flags=re.M)
        if m:
            out[name] = m.group(1)
    return out


def ticker_input_title(source: str | None = None) -> str | None:
    """The title of the "levels for ticker" input, read from the indicator source."""
    source = source if source is not None else INDICATOR.read_text()
    m = re.search(rf'^{TICKER_INPUT}\s*=\s*input\.string\([^,]+,\s*"([^"]+)"', source, flags=re.M)
    return m.group(1) if m else None


def known_symbol(symbol: str, db_path: str | Path | None = None) -> bool:
    """True when the database already has `symbol` (read-only: drawing a chart must never create a stock)."""
    try:
        conn = sqlite3.connect(f"file:{db_path or DB_PATH}?mode=ro", uri=True)
    except sqlite3.Error:
        return False
    try:
        return conn.execute("SELECT 1 FROM investment WHERE symbol = ?", (symbol,)).fetchone() is not None
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def draw_levels(symbol: str, db_path: str | Path | None = None, switch: bool = True) -> dict:
    """Set the AI TA Levels indicator's inputs to `symbol`'s stored levels (and tag them with it).

    With `switch` (the default) the chart is first switched to `symbol`; the follower passes
    switch=False because the chart is already showing it. Levels that are not stored, and
    symbols the database does not know, are set to 0 so stale lines disappear.

    Returns the CDP result: {success, study, set, missing} or {success: False, error}.
    The indicator must already be on the chart layout (Indicators -> My scripts); it stays
    there across symbol changes.
    """
    from pine_script_manager import tv_call
    from ticker_aliases import normalize_ticker

    stored = normalize_ticker(symbol.upper())   # PSU.U, PSU-U and PSU-U.TO are one fund
    values = level_inputs(stored, db_path) if known_symbol(stored, db_path) else {}
    by_title: dict[str, float | str] = {title: round(values.get(name, 0.0), 2) for name, title in input_titles().items()}
    tag_title = ticker_input_title()
    if tag_title:
        by_title[tag_title] = symbol.upper()   # the indicator draws these levels only on this ticker
    if switch:
        switched = tv_call("chart", "symbol", symbol.upper())
        if not (isinstance(switched, dict) and switched.get("success")):
            return {"success": False, "error": f"chart switch failed: {switched}"}
    return tv_call("chart", "setInputs", "--name", INDICATOR_NAME, "--values", json.dumps(by_title, ensure_ascii=False))


def follow_step(current: str | None, last: str | None, draw=None) -> str | None:
    """One poll of the follower: draw when the chart's symbol changed, return the symbol now drawn.

    A failed draw returns `last` unchanged so the next poll retries it.
    """
    if not current or current == last:
        return last
    draw = draw or (lambda symbol: draw_levels(symbol, switch=False))
    result = draw(current)
    if isinstance(result, dict) and result.get("success"):
        return current
    print(f"levels not drawn for {current}: {result}", file=sys.stderr)
    return last


def follow(interval: float = 1.5, db_path: str | Path | None = None) -> None:
    """Redraw the stored levels of whichever stock the chart shows, until interrupted."""
    from pine_script_manager import tv_call

    last: str | None = None
    print("Following the chart symbol; Ctrl+C to stop.", flush=True)
    while True:
        shown = tv_call("chart", "getSymbol")
        current = shown.get("symbol") if isinstance(shown, dict) and shown.get("success") else None
        drawn = follow_step(current, last, lambda symbol: draw_levels(symbol, db_path, switch=False))
        if drawn != last:
            print(f"levels drawn for {drawn}", flush=True)
        last = drawn
        time.sleep(interval)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Draw stored levels on the AI TA Levels indicator.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--draw", metavar="TICKER", help="Switch the chart to TICKER and draw its stored levels")
    group.add_argument("--follow", action="store_true", help="Keep running and redraw the levels whenever the chart's symbol changes")
    parser.add_argument("--db", default=None, help="Path to domain_model.sqlite (default: the real database)")
    args = parser.parse_args()
    if args.follow:
        try:
            follow(db_path=args.db)
        except KeyboardInterrupt:
            return 0
    result = draw_levels(args.draw, args.db)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if isinstance(result, dict) and result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
