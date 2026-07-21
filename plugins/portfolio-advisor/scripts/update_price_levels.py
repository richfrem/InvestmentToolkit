#!/usr/bin/env python3
"""
update_price_levels.py — Tiered buy/sell price level manager for portfolio holdings.

Derives structured price tiers from DCF projections and writes them to:
  - target-portfolio.json: priceLevels block per holding
  - portfolio.json: priceLevelSnapshot (denormalized, read by skills at runtime)

Derivation formulas (source=dcf):
  buyTier[1].price  = round(base_fv * 0.75, 2)   # 25% margin of safety
  buyTier[2].price  = round(bear_fv * 1.05, 2)   # just above bear scenario
  sellTier[1].price = base_fv                     # trim 30% at base fair value
  sellTier[2].price = bull_fv                     # trim 50% at bull fair value
  sellTier[3].price = round(bull_fv * 1.20, 2)   # exit 100% at 20% above bull
  stopLoss.price    = round(bear_fv * 0.95, 2)   # thesis breaker

Usage:
  python3 update_price_levels.py --ticker GOOG --source dcf --write
  python3 update_price_levels.py --ticker GOOG --source dcf --dry-run
  python3 update_price_levels.py --all --source dcf --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET_JSON = REPO_ROOT / 'investment_screener/backend/data/theses/target-portfolio.json'
PORTFOLIO_JSON = REPO_ROOT / 'investment_screener/backend/data/portfolio.json'
DB_PATH = REPO_ROOT / 'investment_screener/backend/data/domain_model.sqlite'

# Import locked_write_json
sys.path.insert(0, str(REPO_ROOT / 'investment_screener/backend/py_services'))
try:
    from file_lock import locked_write_json
except ImportError:
    # Fallback if file_lock is not importable (e.g. running in testing environments with specific sys.path)
    def locked_write_json(file_path: Path, data: Any) -> None:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

from domain_model.db_client import initialize_db
from domain_model.projection_repository import get_latest_projection_by_source, get_projection_scenarios
from domain_model.investment_repository import resolve_investment
from domain_model.price_level_repository import replace_price_levels, get_price_levels
from domain_model.investment_price_repository import get_investment_price

def derive_tiers_from_dcf(bear_fv: float, base_fv: float, bull_fv: float, source_date: str, note: str = '') -> dict:
    """Returns complete priceLevels dict derived from bear, base, and bull scenario prices."""
    return {
        'schemaVersion': '1.0',
        'lastUpdated': source_date,
        'lastUpdatedBy': 'dcf',
        'note': note,
        'buyTiers': [
            {
                'tier': 1,
                'price': round(base_fv * 0.75, 2),
                'action': 'accumulate',
                'trimPct': None,
                'orderType': 'limit',
                'basis': 'DCF base FV x 0.75 — 25% margin of safety',
                'source': 'dcf',
                'sourceDate': source_date,
                'condition': None,
                'status': 'active'
            },
            {
                'tier': 2,
                'price': round(bear_fv * 1.05, 2),
                'action': 'accumulate_aggressive',
                'trimPct': None,
                'orderType': 'limit',
                'basis': 'DCF bear FV x 1.05 — aggressive accumulation zone',
                'source': 'dcf',
                'sourceDate': source_date,
                'condition': None,
                'status': 'active'
            }
        ],
        'sellTiers': [
            {
                'tier': 1,
                'price': round(base_fv, 2),
                'action': 'trim',
                'trimPct': 30,
                'orderType': 'limit',
                'basis': 'DCF base fair value',
                'source': 'dcf',
                'sourceDate': source_date,
                'condition': None,
                'status': 'active'
            },
            {
                'tier': 2,
                'price': round(bull_fv, 2),
                'action': 'trim',
                'trimPct': 50,
                'orderType': 'limit',
                'basis': 'DCF bull fair value',
                'source': 'dcf',
                'sourceDate': source_date,
                'condition': None,
                'status': 'active'
            },
            {
                'tier': 3,
                'price': round(bull_fv * 1.20, 2),
                'action': 'exit',
                'trimPct': 100,
                'orderType': 'limit',
                'basis': '20% above bull FV — thesis fully priced in',
                'source': 'dcf',
                'sourceDate': source_date,
                'condition': None,
                'status': 'active'
            }
        ],
        'stopLoss': {
            'price': round(bear_fv * 0.95, 2),
            'basis': 'DCF bear FV x 0.95 — thesis breaker',
            'source': 'dcf',
            'sourceDate': source_date,
            'type': 'thesis_breaker',
            'status': 'active'
        }
    }

def compute_proximity_flags(current_price: float, price_levels: dict | None) -> list[str]:
    """Computes proximity flags based on current price and price levels."""
    if not price_levels:
        return ['NO_PRICE_LEVELS']
    
    flags = []
    
    # Check buy tiers
    for tier in price_levels.get('buyTiers', []):
        if tier.get('status') != 'active':
            continue
        p = tier.get('price')
        if p and p > 0:
            # price within 2% below or equal/lower
            if current_price <= p and ((p - current_price) / p) <= 0.02:
                flags.append(f"AT_BUY_TIER_{tier['tier']}")

    # Check sell tiers
    for tier in price_levels.get('sellTiers', []):
        if tier.get('status') != 'active':
            continue
        p = tier.get('price')
        if p and p > 0:
            if current_price > p:
                flags.append(f"ABOVE_SELL_TIER_{tier['tier']}")
            elif abs(current_price - p) / p <= 0.02:
                flags.append(f"AT_SELL_TIER_{tier['tier']}")

    # Check stop loss
    stop = price_levels.get('stopLoss')
    if stop and stop.get('status') == 'active':
        p = stop.get('price')
        if p and p > 0:
            if current_price < p:
                flags.append('BELOW_STOP_LOSS')
            elif (current_price - p) / p <= 0.03:
                flags.append('AT_STOP_LOSS')
                
    return flags

def load_latest_projection(ticker: str, db_path: Path | None = None) -> dict | None:
    """Reads latest AI_AGENT projection entry for a given ticker.

    Storage backend (Wave 1 Task 7B): reads `projection_version`/
    `projection_scenario` via `domain_model.projection_repository`, not
    `projections/{TICKER}.json` directly (ADR-029). The original code filtered
    strictly by `source == 'AI_AGENT'` with no fallback to other sources, so
    this uses `get_latest_projection_by_source` only.

    Returns:
        `{"source": "AI_AGENT", "scenarios": {"bear"/"base"/"bull": {
        "scenarioPrice": float}}}`, or None if no AI_AGENT projection exists.
    """
    dbp = db_path or DB_PATH
    conn = initialize_db(str(dbp))
    try:
        row = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", (ticker.upper(),)
        ).fetchone()
        if row is None:
            return None
        entry = get_latest_projection_by_source(conn, row[0], "AI_AGENT")
        if entry is None:
            return None
        scenario_rows = get_projection_scenarios(conn, entry["projection_id"])
        scenarios = {
            r["scenario_name"]: {"scenarioPrice": r["scenario_price"]}
            for r in scenario_rows
        }
        return {"source": "AI_AGENT", "scenarios": scenarios}
    finally:
        conn.close()

def _tier_row_to_dict(row: dict) -> dict:
    """Maps a `price_level_tier` SQL row (snake_case columns) back to the
    JSON tier shape `compute_proximity_flags`/callers expect (camelCase,
    `tier` instead of `tier_number`)."""
    return {
        'tier': row.get('tier_number'),
        'price': row.get('price'),
        'action': row.get('action'),
        'trimPct': row.get('trim_pct'),
        'orderType': row.get('order_type'),
        'basis': row.get('basis'),
        'source': row.get('source'),
        'sourceDate': row.get('source_date'),
        'condition': row.get('condition'),
        'status': row.get('status'),
    }


def compute_price_level_snapshot_from_db(conn, investment_id: str) -> dict | None:
    """Computes the `priceLevelSnapshot` shape (nextBuyTier/nextSellTier/
    stopLoss/proximityFlags) entirely from already-migrated tables --
    `price_level_tier` (Wave 2 Task 9) for the tiers, `investment_price`
    (Wave 3 Task 1) for the current price. No new schema is needed: this
    denormalized cache was always fully derivable at read time from data
    this migration had already cut over, matching ADR-030's read-time-only
    principle for other derived views (e.g. portfolio totals). Returns None
    if there is no price_level_set or no current price for this investment.
    """
    levels = get_price_levels(conn, investment_id)
    if not levels:
        return None
    price_row = get_investment_price(conn, investment_id)
    if not price_row:
        return None
    current_price = price_row['price']

    buy_tiers = [_tier_row_to_dict(t) for t in levels['buy_tiers']]
    sell_tiers = [_tier_row_to_dict(t) for t in levels['sell_tiers']]
    stop_loss = _tier_row_to_dict(levels['stop_loss']) if levels['stop_loss'] else None
    price_levels = {'buyTiers': buy_tiers, 'sellTiers': sell_tiers, 'stopLoss': stop_loss}

    next_buy = next((t for t in buy_tiers if t.get('status') == 'active'), None)
    next_sell = next((t for t in sell_tiers if t.get('status') == 'active'), None)
    flags = compute_proximity_flags(current_price, price_levels)

    return {
        'nextBuyTier': next_buy,
        'nextSellTier': next_sell,
        'stopLoss': stop_loss,
        'proximityFlags': flags,
    }


def derive_and_write(
    ticker: str,
    source: str = 'dcf',
    note: str = '',
    ta_overrides: dict | None = None,
    dry_run: bool = False,
    target_json_path: Path | None = None,
    portfolio_json_path: Path | None = None,
    db_path: Path | None = None
) -> dict:
    """Derives price levels for a ticker and updates the files."""
    tpath = target_json_path or TARGET_JSON
    ppath = portfolio_json_path or PORTFOLIO_JSON

    proj = load_latest_projection(ticker, db_path)
    if not proj:
        raise ValueError(f"No projection found for {ticker}")

    scenarios = proj.get('scenarios', {})
    if 'bear' not in scenarios or 'base' not in scenarios or 'bull' not in scenarios:
        raise ValueError(f"Incomplete scenarios in projection for {ticker}")

    bear_fv = scenarios['bear'].get('scenarioPrice')
    base_fv = scenarios['base'].get('scenarioPrice')
    bull_fv = scenarios['bull'].get('scenarioPrice')
    
    if bear_fv is None or base_fv is None or bull_fv is None:
        raise ValueError(f"Could not find scenarioPrice or presentValue in scenarios for {ticker}")
    
    today = datetime.now().strftime('%Y-%m-%d')
    price_levels = derive_tiers_from_dcf(bear_fv, base_fv, bull_fv, today, note)
    
    if ta_overrides:
        # Merge or append TA levels if provided
        pass
        
    # 1. Persist priceLevels via the domain-model repository (Wave 2 Task 9 producer
    #    cutover) instead of rewriting target-portfolio.json in place. Full-object
    #    replace semantics preserved exactly: replace_price_levels() deletes and
    #    re-inserts the whole price_level_set for this investment, matching the old
    #    JSON write's "always rewrite the whole priceLevels block" behavior. Any
    #    pre-existing targetEntryPrice (a separate, TARGET_ENTRY-kind row this script
    #    never sets) is read back first and carried through unchanged so this write
    #    doesn't silently wipe it out.
    holding_found = False
    if tpath.exists():
        with open(tpath) as f:
            target_data = json.load(f)
        holding_found = any(
            h.get('ticker', '').upper() == ticker.upper() for h in target_data.get('holdings', [])
        )

    if holding_found:
        if not dry_run:
            dbp = db_path or DB_PATH
            conn = initialize_db(str(dbp))
            try:
                investment_id = resolve_investment(conn, ticker)
                existing = get_price_levels(conn, investment_id)
                existing_target_entry = (
                    existing['target_entry']['price'] if existing and existing.get('target_entry') else None
                )
                replace_price_levels(
                    conn,
                    investment_id,
                    schema_version=price_levels['schemaVersion'],
                    last_updated=price_levels['lastUpdated'],
                    last_updated_by=price_levels['lastUpdatedBy'],
                    note=price_levels['note'],
                    buy_tiers=price_levels['buyTiers'],
                    sell_tiers=price_levels['sellTiers'],
                    stop_loss=price_levels['stopLoss'],
                    target_entry_price=existing_target_entry,
                )
            finally:
                conn.close()
    else:
        print(f"Warning: Holding {ticker} not found in target portfolio holdings.")

    # 2. Compute the priceLevelSnapshot (Wave 3 Task 5.8 rewire).
    #
    # The prior code here iterated `portfolio_data.get('accounts', [])` looking
    # for `holdings[]` per account -- but real portfolio.json has no top-level
    # `accounts` key at all (its real shape is `{holdings, totals, tvSnapshot}`,
    # confirmed against portfolio.json.example and the real migrated file).
    # `portfolio_data.get('accounts', [])` therefore always returned `[]` in
    # production: `snapshot_written` was always False and this write path was
    # dead code, never actually persisting a priceLevelSnapshot anywhere. Since
    # this snapshot is fully derivable at read time from tables this wave has
    # already migrated (price_level_tier: Wave 2 Task 9; investment_price:
    # Wave 3 Task 1) -- see compute_price_level_snapshot_from_db's docstring --
    # there is no working portfolio.json write to "rewire": the equivalent data
    # already lives in SQLite via step 1's replace_price_levels() call above,
    # and this function now returns the same computed shape a caller reading
    # `res['price_level_snapshot']` would have gotten from the dead JSON path,
    # sourced correctly instead of from code that could never fire.
    price_level_snapshot = None
    if holding_found and not dry_run:
        dbp = db_path or DB_PATH
        conn = initialize_db(str(dbp))
        try:
            investment_id = resolve_investment(conn, ticker)
            price_level_snapshot = compute_price_level_snapshot_from_db(conn, investment_id)
        finally:
            conn.close()

    return {
        'ticker': ticker,
        'dry_run': dry_run,
        'price_levels': price_levels,
        'price_level_snapshot': price_level_snapshot,
        'snapshot_written': price_level_snapshot is not None,
    }

def derive_and_write_all(source: str = 'dcf', dry_run: bool = False) -> list[dict]:
    """Batch updates price levels for all holdings in target-portfolio.json."""
    results = []
    if not TARGET_JSON.exists():
        return results
    with open(TARGET_JSON) as f:
        target_data = json.load(f)
    for holding in target_data.get('holdings', []):
        ticker = holding.get('ticker')
        if ticker:
            try:
                res = derive_and_write(ticker, source=source, dry_run=dry_run)
                results.append(res)
            except Exception as e:
                print(f"Error updating {ticker}: {e}")
    return results

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Update structured price levels from DCF.")
    parser.add_argument('--ticker', type=str, help="Specific ticker to update")
    parser.add_argument('--all', action='store_true', help="Update all tickers in target portfolio")
    parser.add_argument('--source', type=str, default='dcf', choices=['dcf', 'ta', 'news', 'earnings', '13f', 'manual'])
    parser.add_argument('--note', type=str, default='', help="Optional note to persist with price levels")
    parser.add_argument('--write', action='store_true', help="Persist updates to files (default is dry-run)")
    parser.add_argument('--dry-run', action='store_true', help="Dry run only")
    args = parser.parse_args()
    
    is_dry = not args.write or args.dry_run
    
    if args.ticker:
        try:
            res = derive_and_write(args.ticker, source=args.source, note=args.note, dry_run=is_dry)
            print(json.dumps(res, indent=2))
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif args.all:
        results = derive_and_write_all(source=args.source, dry_run=is_dry)
        print(f"Batch updated {len(results)} tickers. Dry run: {is_dry}")
    else:
        parser.print_help()
