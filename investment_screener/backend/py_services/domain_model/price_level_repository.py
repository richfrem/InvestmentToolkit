"""All ``price_level_set``/``price_level_tier`` table reads and writes live here.

Full-replace semantics, matching the source JSON's own full-object-rewrite pattern:
``update_price_levels.py`` always rewrites the whole ``priceLevels`` object, never
patches a single tier in place (confirmed against real data during Wave 2
investigation). ``target_entry_price`` becomes a ``tier_kind='TARGET_ENTRY'`` row,
kept distinct from buy tiers per spec s2.2 (confirmed real divergence, e.g. SNDK:
target 1350 vs. buy tiers 1048/1070).
"""

import sqlite3
import uuid


def replace_price_levels(
    conn: sqlite3.Connection,
    investment_id: str,
    schema_version: str | None,
    last_updated: str | None,
    last_updated_by: str | None,
    note: str | None,
    buy_tiers: list[dict],
    sell_tiers: list[dict],
    stop_loss: dict | None,
    target_entry_price: float | None,
) -> str:
    existing = conn.execute(
        "SELECT price_level_set_id FROM price_level_set WHERE investment_id = ?;",
        (investment_id,),
    ).fetchone()
    if existing:
        old_set_id = existing[0]
        conn.execute(
            "DELETE FROM price_level_tier WHERE price_level_set_id = ?;", (old_set_id,)
        )
        conn.execute(
            "DELETE FROM price_level_set WHERE price_level_set_id = ?;", (old_set_id,)
        )

    price_level_set_id = f"{investment_id}-pls-{uuid.uuid4().hex[:8]}"
    conn.execute(
        "INSERT INTO price_level_set "
        "(price_level_set_id, investment_id, schema_version, last_updated, "
        "last_updated_by, note) VALUES (?, ?, ?, ?, ?, ?);",
        (price_level_set_id, investment_id, schema_version, last_updated,
         last_updated_by, note),
    )

    def _insert_tier(tier_kind: str, tier: dict) -> None:
        tier_id = f"{price_level_set_id}-{tier_kind}-{tier.get('tier', uuid.uuid4().hex[:6])}"
        conn.execute(
            "INSERT INTO price_level_tier "
            "(tier_id, price_level_set_id, tier_kind, tier_number, price, action, "
            "trim_pct, order_type, basis, source, source_date, condition, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (tier_id, price_level_set_id, tier_kind, tier.get("tier", 0),
             tier.get("price"), tier.get("action"), tier.get("trimPct"),
             tier.get("orderType"), tier.get("basis"), tier.get("source"),
             tier.get("sourceDate"), tier.get("condition"), tier.get("status")),
        )

    for tier in buy_tiers:
        _insert_tier("BUY_TIER", tier)
    for tier in sell_tiers:
        _insert_tier("SELL_TIER", tier)
    if stop_loss:
        tier_id = f"{price_level_set_id}-STOP_LOSS"
        conn.execute(
            "INSERT INTO price_level_tier "
            "(tier_id, price_level_set_id, tier_kind, tier_number, price, basis, "
            "source, source_date, condition, status) "
            "VALUES (?, ?, 'STOP_LOSS', 0, ?, ?, ?, ?, ?, ?);",
            (tier_id, price_level_set_id, stop_loss.get("price"),
             stop_loss.get("basis"), stop_loss.get("source"),
             stop_loss.get("sourceDate"), stop_loss.get("type"),
             stop_loss.get("status")),
        )
    if target_entry_price is not None:
        tier_id = f"{price_level_set_id}-TARGET_ENTRY"
        conn.execute(
            "INSERT INTO price_level_tier "
            "(tier_id, price_level_set_id, tier_kind, tier_number, price) "
            "VALUES (?, ?, 'TARGET_ENTRY', 0, ?);",
            (tier_id, price_level_set_id, target_entry_price),
        )

    conn.commit()
    return price_level_set_id


def get_price_levels(conn: sqlite3.Connection, investment_id: str) -> dict | None:
    conn.row_factory = sqlite3.Row
    set_row = conn.execute(
        "SELECT * FROM price_level_set WHERE investment_id = ?;", (investment_id,)
    ).fetchone()
    if not set_row:
        return None
    set_row = dict(set_row)
    tiers = conn.execute(
        "SELECT * FROM price_level_tier WHERE price_level_set_id = ? ORDER BY tier_number;",
        (set_row["price_level_set_id"],),
    ).fetchall()
    tiers = [dict(t) for t in tiers]
    return {
        "price_level_set": set_row,
        "buy_tiers": [t for t in tiers if t["tier_kind"] == "BUY_TIER"],
        "sell_tiers": [t for t in tiers if t["tier_kind"] == "SELL_TIER"],
        "stop_loss": next((t for t in tiers if t["tier_kind"] == "STOP_LOSS"), None),
        "target_entry": next((t for t in tiers if t["tier_kind"] == "TARGET_ENTRY"), None),
    }
