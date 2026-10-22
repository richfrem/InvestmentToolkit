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

Key Functions (Index):
    - level_inputs(): {pine input name: price} for a ticker from domain_model.sqlite
    - fill_level_inputs(): the indicator source with those values as input defaults

Key Input Dependencies:
    - domain_model.sqlite: price_level_set / price_level_tier, projection_version
"""
from __future__ import annotations

import re
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "domain_model.sqlite"


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
    return source
