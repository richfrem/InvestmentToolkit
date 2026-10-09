#!/usr/bin/env python3
"""
update_price_levels.py — Tiered buy/sell price level manager for portfolio holdings.

Derives structured price tiers from DCF projections and stores them in domain_model.sqlite
(price_level_set / price_level_tier). The priceLevelSnapshot (next buy/sell tier and
proximity flags) is computed from those tables and the stored price, never stored separately.

Derivation formulas (source=dcf):
  buyTier[1].price  = round(base_fv * 0.75, 2)   # 25% margin of safety
  buyTier[2].price  = round(bear_fv * 1.05, 2)   # just above bear scenario
  sellTier[1].price = base_fv                     # trim 30% at base fair value
  sellTier[2].price = bull_fv                     # trim 50% at bull fair value
  sellTier[3].price = round(bull_fv * 1.20, 2)   # exit 100% at 20% above bull
  stopLoss.price    = round(bear_fv * 0.95, 2)   # thesis breaker

Sanity guard: buyTier[2] and stopLoss (bear-derived) are written with
status='suppressed' when more than 50% below the stored current price
(investment_price), e.g. a $3.44 stop on a $26 stock. Never clamped.

Usage:
  python3 update_price_levels.py --ticker GOOG --source dcf --write
  python3 update_price_levels.py --ticker GOOG --source dcf --dry-run
  python3 update_price_levels.py --all --source dcf --dry-run
  python3 update_price_levels.py --all --write --db /path/to/domain_model.sqlite

Key Functions (Index):
  - derive_tiers_from_dcf(): the tier formulas
  - compute_proximity_flags(): flags for a price against stored levels
  - load_latest_projection(): the latest AI_AGENT projection scenarios
  - compute_price_level_snapshot_from_db(): next tiers and flags from SQLite
  - derive_and_write(): one ticker
  - derive_and_write_all(): every thesis holding; reports updated, skipped and failed

Key Input Dependencies:
  - investment_screener/backend/data/domain_model.sqlite (projections, prices, thesis holdings)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / 'investment_screener/backend/data/domain_model.sqlite'

sys.path.insert(0, str(REPO_ROOT / 'investment_screener/backend/py_services'))
from domain_model.db_client import initialize_db
from domain_model.projection_repository import get_latest_projection_by_source, get_projection_scenarios
from domain_model.investment_repository import resolve_investment
from domain_model.price_level_repository import replace_price_levels, get_price_levels
from domain_model.investment_price_repository import get_investment_price
from portfolio_io import load_thesis_holdings

MAX_BEAR_LEVEL_DISTANCE = 0.50  # bear-derived levels further than this below price are suppressed


def _suppress_if_far_below(level: dict, current_price: float | None) -> dict:
    """Mark a bear-derived level 'suppressed' when it sits >50% below the current price.

    A stop or accumulation level that far away (e.g. a $3.44 stop on a $26
    stock) has no protective or actionable meaning; it is kept for audit but
    never emitted as active. Clamping is deliberately not done: a clamped
    level would be a number with no analytical basis.
    """
    if not current_price or current_price <= 0:
        return level
    if level['price'] < current_price * (1 - MAX_BEAR_LEVEL_DISTANCE):
        level['status'] = 'suppressed'
        level['basis'] += (
            f" — SUPPRESSED: >50% below current price ${current_price:.2f}; "
            "bear scenario too far out to act as a level"
        )
    return level


def derive_tiers_from_dcf(
    bear_fv: float,
    base_fv: float,
    bull_fv: float,
    source_date: str,
    note: str = '',
    current_price: float | None = None,
) -> dict:
    """Returns complete priceLevels dict derived from bear, base, and bull scenario prices.

    When current_price is given, bear-derived levels (buyTier 2, stopLoss) more
    than MAX_BEAR_LEVEL_DISTANCE below it are returned with status 'suppressed'.
    """
    levels = _derive_raw_tiers(bear_fv, base_fv, bull_fv, source_date, note)
    _suppress_if_far_below(levels['buyTiers'][1], current_price)
    _suppress_if_far_below(levels['stopLoss'], current_price)
    return levels


def _derive_raw_tiers(bear_fv: float, base_fv: float, bull_fv: float, source_date: str, note: str) -> dict:
    """Builds the unguarded priceLevels dict from the fixed DCF multipliers."""
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

    Reads `projection_version` / `projection_scenario` through
    `domain_model.projection_repository.get_latest_projection_by_source`, strictly
    `AI_AGENT` with no fallback to other sources.

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


def _load_current_price(ticker: str, db_path: Path | None = None) -> float | None:
    """Reads the stored current price for ticker from investment_price, or None."""
    conn = initialize_db(str(db_path or DB_PATH))
    try:
        row = get_investment_price(conn, resolve_investment(conn, ticker))
        return row['price'] if row else None
    finally:
        conn.close()


def derive_and_write(
    ticker: str,
    source: str = 'dcf',
    note: str = '',
    dry_run: bool = False,
    db_path: Path | None = None
) -> dict:
    """Derive price levels for a ticker and store them in domain_model.sqlite (unless dry_run).

    Raises:
        ValueError: No AI_AGENT projection, or one without bear/base/bull scenario prices.
    """
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
    current_price = _load_current_price(ticker, db_path)
    price_levels = derive_tiers_from_dcf(bear_fv, base_fv, bull_fv, today, note, current_price=current_price)
    for level in [*price_levels['buyTiers'], price_levels['stopLoss']]:
        if level.get('status') == 'suppressed':
            print(f"WARNING: {ticker} {level['basis']}", file=sys.stderr)
    
    # Store the whole priceLevels set (replace semantics). Any existing targetEntryPrice, a
    # separate TARGET_ENTRY row this script never sets, is read back and carried through.
    # Watchlist and new tickers get levels too, so the write is not gated on holding a position.
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

    # The priceLevelSnapshot is derived from price_level_tier and investment_price at read
    # time (see compute_price_level_snapshot_from_db) and returned, not stored.
    price_level_snapshot = None
    if not dry_run:
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

def derive_and_write_all(source: str = 'dcf', dry_run: bool = False, db_path: Path | None = None) -> dict:
    """Derive price levels for every thesis holding in domain_model.sqlite.

    Returns:
        {"updated": [derive_and_write results], "skipped": [{"ticker", "reason"}] for holdings
        with no usable projection, "failed": [{"ticker", "reason"}] for unexpected errors}.

    Raises:
        ValueError: The database has no thesis holdings (nothing to iterate is an error, not
            an empty success).
    """
    dbp = db_path or DB_PATH
    holdings = load_thesis_holdings(str(dbp))
    if not holdings:
        raise ValueError(f"no thesis holdings in {dbp}; set target weights first")
    out: dict = {"updated": [], "skipped": [], "failed": []}
    for holding in holdings:
        ticker = holding["ticker"]
        try:
            out["updated"].append(derive_and_write(ticker, source=source, dry_run=dry_run, db_path=dbp))
        except ValueError as e:
            out["skipped"].append({"ticker": ticker, "reason": str(e)})
        except Exception as e:  # keep going: one bad ticker must not stop the batch, but it is reported
            out["failed"].append({"ticker": ticker, "reason": f"{type(e).__name__}: {e}"})
    return out

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Update structured price levels from DCF.")
    parser.add_argument('--ticker', type=str, help="Specific ticker to update")
    parser.add_argument('--all', action='store_true', help="Update every thesis holding in domain_model.sqlite")
    parser.add_argument('--source', type=str, default='dcf', choices=['dcf', 'ta', 'news', 'earnings', '13f', 'manual'])
    parser.add_argument('--note', type=str, default='', help="Optional note to persist with price levels")
    parser.add_argument('--write', action='store_true', help="Persist updates to domain_model.sqlite (default is dry-run)")
    parser.add_argument('--dry-run', action='store_true', help="Dry run only")
    parser.add_argument('--db', type=str, default=None, help="Path to domain_model.sqlite (default: the real database)")
    args = parser.parse_args()
    db = Path(args.db) if args.db else None
    
    is_dry = not args.write or args.dry_run
    
    if args.ticker:
        try:
            res = derive_and_write(args.ticker, source=args.source, note=args.note, dry_run=is_dry, db_path=db)
            print(json.dumps(res, indent=2))
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif args.all:
        try:
            out = derive_and_write_all(source=args.source, dry_run=is_dry, db_path=db)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Updated {len(out['updated'])} tickers, skipped {len(out['skipped'])}, failed {len(out['failed'])}. Dry run: {is_dry}")
        for item in out['skipped'] + out['failed']:
            print(f"  {item['ticker']}: {item['reason']}", file=sys.stderr)
        if out['failed']:
            sys.exit(1)
    else:
        parser.print_help()
