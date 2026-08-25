#!/usr/bin/env python3
"""
stock_intake_persist.py - Canonical atomic persistence engine for stock intake & valuation refresh.

Purpose:
    Canonical, versioned service script for onboarding/updating all analytical surfaces
    for a stock within a SINGLE unified SQLite transaction:
    1. Investment thesis & target weights (domain_model.sqlite investment)
    2. Technical Action Price Tiers (domain_model.sqlite price_level_tier)
    3. Valuation Modeler DCF projection (domain_model.sqlite projection_version & data/projections/{TICKER}.json)

Layer:
    Backend / py_services / Persistence
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from domain_model.db_client import initialize_db
from domain_model.investment_repository import update_investment_fields, resolve_investment
from domain_model.price_level_repository import replace_price_levels
from ticker_aliases import normalize_ticker

_DB_PATH = str(_HERE / ".." / "data" / "domain_model.sqlite")
_PROJ_DIR = _HERE / ".." / "data" / "projections"

def persist_intake_payload(payload: dict) -> dict:
    raw_symbol = payload.get("symbol")
    if not raw_symbol:
        raise ValueError("Payload missing required symbol")
        
    canonical = normalize_ticker(raw_symbol)
    conn = initialize_db(_DB_PATH)
    
    # 1. Begin explicit transaction for atomic multi-table integrity
    conn.execute("BEGIN IMMEDIATE")
    try:
        resolve_investment(conn, canonical)
        
        # A. Update investment table fields
        fields = {}
        for key in [
            "lifecycle_status", "target_weight", "target_action",
            "standing_decision_type", "standing_decision_reason",
            "standing_decision_source", "standing_decision_review",
            "pillar_id", "sub_strategy_id", "thesis_for_inclusion",
            "agent_rationale", "is_watchlisted", "sector", "industry",
            "last_deep_analysis_at"
        ]:
            if key in payload:
                fields[key] = payload[key]
                
        # Default last_deep_analysis_at to now if performing intake/refresh
        if "last_deep_analysis_at" not in fields:
            fields["last_deep_analysis_at"] = datetime.now(timezone.utc).isoformat()
                
        if fields:
            fields["updated_at"] = datetime.now(timezone.utc).isoformat()
            set_clause = ", ".join(f"{key} = ?" for key in fields)
            params = list(fields.values()) + [canonical]
            conn.execute(f"UPDATE investment SET {set_clause} WHERE investment_id = ?;", params)
            
        # B. Update price levels if provided
        pls = payload.get("price_levels")
        if pls and isinstance(pls, dict):
            now = datetime.now(timezone.utc).isoformat()
            replace_price_levels(
                conn=conn,
                investment_id=canonical,
                schema_version=pls.get("schema_version", "1.0"),
                last_updated=now,
                last_updated_by=pls.get("last_updated_by", "stock-intake-persist"),
                note=pls.get("note", "Updated technical levels"),
                buy_tiers=pls.get("buy_tiers", []),
                sell_tiers=pls.get("sell_tiers", []),
                stop_loss=pls.get("stop_loss"),
                target_entry_price=pls.get("target_entry_price")
            )
            
        # C. Commit database transaction
        conn.commit()
        
        # D. Atomic write-to-temp-then-rename for projection JSON file
        proj = payload.get("projection")
        if proj and isinstance(proj, dict):
            os.makedirs(_PROJ_DIR, exist_ok=True)
            proj_file = _PROJ_DIR / f"{canonical}.json"
            proj_data = [proj] if not isinstance(proj, list) else proj
            
            with tempfile.NamedTemporaryFile("w", dir=_PROJ_DIR, delete=False, suffix=".tmp") as tf:
                json.dump(proj_data, tf, indent=2)
                temp_name = tf.name
            os.replace(temp_name, proj_file)
                
        return {
            "status": "success",
            "symbol": canonical,
            "updated_fields": list(fields.keys()),
            "price_levels_updated": bool(pls),
            "projection_updated": bool(proj)
        }
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Comprehensive atomic persistence for stock analysis")
    parser.add_argument("--payload", "-p", type=str, help="JSON string of intake metadata")
    parser.add_argument("--file", "-f", type=str, help="Path to JSON file containing intake metadata")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    payload_data = None
    if args.payload:
        payload_data = json.loads(args.payload)
    elif args.file:
        with open(args.file, "r") as f:
            payload_data = json.load(f)
    else:
        parser.print_help()
        sys.exit(1)

    result = persist_intake_payload(payload_data)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Successfully updated all analytical surfaces for {result['symbol']}")

if __name__ == "__main__":
    main()
