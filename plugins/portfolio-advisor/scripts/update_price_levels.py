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
PROJ_DIR = REPO_ROOT / 'investment_screener/backend/data/projections'

# Import locked_write_json
sys.path.insert(0, str(REPO_ROOT / 'investment_screener/backend/py_services'))
try:
    from file_lock import locked_write_json
except ImportError:
    # Fallback if file_lock is not importable (e.g. running in testing environments with specific sys.path)
    def locked_write_json(file_path: Path, data: Any) -> None:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

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

def load_latest_projection(ticker: str, proj_dir: Path | None = None) -> dict | None:
    """Reads latest AI_AGENT projection entry for a given ticker."""
    pdir = proj_dir or PROJ_DIR
    pfile = pdir / f"{ticker.upper()}.json"
    if not pfile.exists():
        return None
    try:
        with open(pfile) as f:
            data = json.load(f)
        if isinstance(data, list):
            # find latest AI_AGENT entry by savedAt
            ai_entries = [e for e in data if e.get('source') == 'AI_AGENT']
            if not ai_entries:
                return None
            return max(ai_entries, key=lambda x: x.get('savedAt', ''))
        elif isinstance(data, dict):
            if data.get('source') == 'AI_AGENT':
                return data
            return None
    except Exception:
        return None
    return None

def derive_and_write(
    ticker: str,
    source: str = 'dcf',
    note: str = '',
    ta_overrides: dict | None = None,
    dry_run: bool = False,
    target_json_path: Path | None = None,
    portfolio_json_path: Path | None = None,
    proj_dir: Path | None = None
) -> dict:
    """Derives price levels for a ticker and updates the files."""
    tpath = target_json_path or TARGET_JSON
    ppath = portfolio_json_path or PORTFOLIO_JSON
    
    proj = load_latest_projection(ticker, proj_dir)
    if not proj:
        raise ValueError(f"No projection found for {ticker}")
        
    scenarios = proj.get('scenarios', {})
    if 'bear' not in scenarios or 'base' not in scenarios or 'bull' not in scenarios:
        raise ValueError(f"Incomplete scenarios in projection for {ticker}")
        
    bear_fv = scenarios['bear'].get('scenarioPrice') or scenarios['bear'].get('presentValue')
    base_fv = scenarios['base'].get('scenarioPrice') or scenarios['base'].get('presentValue')
    bull_fv = scenarios['bull'].get('scenarioPrice') or scenarios['bull'].get('presentValue')
    
    if bear_fv is None or base_fv is None or bull_fv is None:
        raise ValueError(f"Could not find scenarioPrice or presentValue in scenarios for {ticker}")
    
    today = datetime.now().strftime('%Y-%m-%d')
    price_levels = derive_tiers_from_dcf(bear_fv, base_fv, bull_fv, today, note)
    
    if ta_overrides:
        # Merge or append TA levels if provided
        pass
        
    # 1. Update target-portfolio.json
    target_data = {}
    holding_found = False
    if tpath.exists():
        with open(tpath) as f:
            target_data = json.load(f)
        
        for holding in target_data.get('holdings', []):
            if holding.get('ticker', '').upper() == ticker.upper():
                holding['priceLevels'] = price_levels
                holding_found = True
        
        if holding_found:
            target_data['updatedAt'] = datetime.now(timezone.utc).isoformat()
            if not dry_run:
                locked_write_json(tpath, target_data)
        else:
            print(f"Warning: Holding {ticker} not found in target portfolio holdings.")
            
    # 2. Update portfolio.json snapshot
    portfolio_data = {}
    current_price = 0.0
    snapshot_written = False
    if ppath.exists():
        with open(ppath) as f:
            portfolio_data = json.load(f)
            
        for acct in portfolio_data.get('accounts', []):
            for holding in acct.get('holdings', []):
                if holding.get('symbol', '').upper() == ticker.upper():
                    current_price = holding.get('price', 0.0)
                    
                    next_buy = next((t for t in price_levels['buyTiers'] if t.get('status') == 'active'), None)
                    next_sell = next((t for t in price_levels['sellTiers'] if t.get('status') == 'active'), None)
                    flags = compute_proximity_flags(current_price, price_levels)
                    
                    holding['priceLevelSnapshot'] = {
                        'nextBuyTier': next_buy,
                        'nextSellTier': next_sell,
                        'stopLoss': price_levels.get('stopLoss'),
                        'proximityFlags': flags
                    }
                    snapshot_written = True
                    
        if snapshot_written and not dry_run:
            locked_write_json(ppath, portfolio_data)
            
    return {
        'ticker': ticker,
        'dry_run': dry_run,
        'price_levels': price_levels,
        'snapshot_written': snapshot_written and not dry_run
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
