#!/usr/bin/env python3
"""
persist_valuation.py — Canonical valuation and price level persistence script.

Purpose:
    Safely and transactionally persists DCF valuations, scenarios, legal company names,
    standing decisions, and TradingView price levels into domain_model.sqlite
    (and intelligence.sqlite technical sweeps if technical data is provided).
    Automatically calculates and increments projection version numbers, preventing
    version conflicts or stale data regressions.

Layer:
    plugins/stock-valuation/scripts/

Usage:
    python3 persist_valuation.py --file payload.json
    python3 persist_valuation.py --payload '{"symbol": "NVDA", ...}'
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Resolve repository paths
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PY_SERVICES = _REPO_ROOT / "investment_screener/backend/py_services"
_TV_SCRIPTS = _REPO_ROOT / "plugins/tradingview/scripts"

sys.path.insert(0, str(_PY_SERVICES))
sys.path.insert(0, str(_TV_SCRIPTS))

from domain_model.db_client import initialize_db
from domain_model.investment_repository import resolve_investment, update_investment_fields
from domain_model.projection_repository import (
    get_latest_projection,
    save_projection_version,
    add_projection_scenario,
)
from domain_model.price_level_repository import replace_price_levels
from ticker_aliases import normalize_ticker


def persist_valuation(payload: dict, db_path: str | None = None) -> dict:
    raw_symbol = payload.get("symbol")
    if not raw_symbol:
        raise ValueError("Payload missing required 'symbol' field")

    symbol = normalize_ticker(raw_symbol)
    actual_db_path = db_path or str(_REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite")
    conn = initialize_db(actual_db_path)

    try:
        conn.execute("BEGIN IMMEDIATE")

        # 1. Ensure investment exists
        resolve_investment(conn, symbol)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Update legal company name if provided
        name = payload.get("name")
        if name:
            conn.execute("UPDATE investment SET name = ? WHERE symbol = ?;", (name, symbol))

        # 2. Update investment domain fields (lifecycle_status, standing_decision, etc.)
        inv_fields = {}
        for k in [
            "lifecycle_status",
            "target_weight",
            "target_action",
            "standing_decision_type",
            "standing_decision_reason",
            "standing_decision_source",
            "standing_decision_review",
            "pillar_id",
            "sub_strategy_id",
            "thesis_for_inclusion",
            "agent_rationale",
            "is_watchlisted",
            "sector",
            "industry",
        ]:
            if k in payload and payload[k] is not None:
                inv_fields[k] = payload[k]

        inv_fields["last_deep_analysis_at"] = payload.get("analyzed_at") or now_iso
        update_investment_fields(conn, symbol, **inv_fields)

        # 3. Handle Projection & Scenarios
        proj = payload.get("projection")
        new_version = None
        if proj and isinstance(proj, dict):
            latest_pv = get_latest_projection(conn, symbol)
            new_version = (latest_pv["version"] + 1) if latest_pv else 1

            fair_value = proj.get("fair_value") or proj.get("weightedFairValue")
            action = proj.get("action") or "HOLD"
            model = proj.get("model", "5yr_dcf_scenarios")
            rationale = proj.get("rationale", "")
            current_price = proj.get("current_price") or proj.get("currentPrice")
            upside_pct = proj.get("upside_pct") or proj.get("upsidePct")

            snapshot = {
                "ticker": symbol,
                "currentPrice": current_price,
                "weightedFairValue": fair_value,
                "upsidePct": upside_pct,
                "action": action,
                "discountRate": proj.get("discount_rate", 0.085),
                "horizon": proj.get("horizon", 5),
                "baseRevenue": proj.get("base_revenue") or proj.get("baseRevenue"),
                "baseShares": proj.get("base_shares") or proj.get("baseShares"),
            }
            analytics_log = {
                "valuationAction": action,
                "portfolioUrgency": proj.get("urgency", "NORMAL"),
                "conviction": proj.get("conviction", 8),
                "fairValue": fair_value,
                "upsidePct": upside_pct,
                "wacc": proj.get("discount_rate", 0.085),
            }

            proj_id = save_projection_version(
                conn=conn,
                investment_id=symbol,
                version=new_version,
                saved_at=now_iso,
                analyzed_at=payload.get("analyzed_at") or now_iso,
                model=model,
                fair_value=fair_value,
                action=action,
                rationale=rationale,
                snapshot_json=json.dumps(snapshot),
                analytics_log_json=json.dumps(analytics_log),
                source=proj.get("source", "AI_AGENT"),
            )

            # Insert scenarios (bear, base, bull)
            scenarios = proj.get("scenarios") or {}
            for sc_name, sc_data in scenarios.items():
                add_projection_scenario(
                    conn=conn,
                    projection_id=proj_id,
                    scenario_name=sc_name,
                    weight=sc_data.get("weight", 0.33),
                    growth_rate=sc_data.get("growthRate") or sc_data.get("growth_rate", 0.0),
                    net_margin=sc_data.get("netMargin") or sc_data.get("net_margin", 0.0),
                    exit_pe=sc_data.get("exitPE") or sc_data.get("exit_pe", 0.0),
                    scenario_price=sc_data.get("price") or sc_data.get("scenario_price", 0.0),
                    year5_revenue=sc_data.get("year5Revenue") or sc_data.get("year5_revenue"),
                    year5_net_income=sc_data.get("year5NetIncome") or sc_data.get("year5_net_income"),
                    year5_eps=sc_data.get("year5EPS") or sc_data.get("year5_eps"),
                )

        # 4. Handle TradingView Price Levels
        price_levels = payload.get("price_levels")
        if price_levels and isinstance(price_levels, dict):
            replace_price_levels(
                conn=conn,
                investment_id=symbol,
                schema_version=price_levels.get("schema_version", "1.0"),
                last_updated=now_iso,
                last_updated_by=price_levels.get("last_updated_by", "tradingview_cdp"),
                note=price_levels.get("note", "TradingView levels updated via persist_valuation"),
                buy_tiers=price_levels.get("buy_tiers", []),
                sell_tiers=price_levels.get("sell_tiers", []),
                stop_loss=price_levels.get("stop_loss"),
                target_entry_price=price_levels.get("target_entry_price"),
            )

        conn.commit()

        # 5. Technical sweep persistence if technicals provided
        technicals = payload.get("technicals")
        if technicals and isinstance(technicals, dict):
            try:
                from ta_sweep_single import persist_sweep
                tech_payload = {
                    "ticker": symbol,
                    "close": technicals.get("close", 0.0),
                    "emaFast": technicals.get("emaFast") or technicals.get("ema21", 0.0),
                    "emaMid": technicals.get("emaMid") or technicals.get("ema50", 0.0),
                    "emaSlow": technicals.get("emaSlow") or technicals.get("ema200", 0.0),
                    "adx": technicals.get("adx", 0.0),
                    "volBias": technicals.get("volBias", 0.0),
                    "atr": technicals.get("atr", 0.0),
                    "squeezeOn": technicals.get("squeezeOn", False),
                    "rsi": technicals.get("rsi", 50.0),
                }
                if proj:
                    tech_payload["dcf"] = {
                        "fairValue": proj.get("fair_value") or proj.get("weightedFairValue"),
                        "base": (proj.get("scenarios") or {}).get("base", {}).get("price", 0.0),
                        "bear": (proj.get("scenarios") or {}).get("bear", {}).get("price", 0.0),
                        "bull": (proj.get("scenarios") or {}).get("bull", {}).get("price", 0.0),
                    }
                persist_sweep(tech_payload)
            except Exception as e:
                # Non-fatal warning if intelligence.sqlite logger has issue
                print(f"Warning: Failed to persist technical sweep: {e}", file=sys.stderr)

        return {
            "status": "success",
            "symbol": symbol,
            "version": new_version,
            "fields_updated": list(inv_fields.keys()),
            "price_levels_updated": bool(price_levels),
            "projection_updated": bool(proj),
        }
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Canonical stock valuation and price level persistence")
    parser.add_argument("--payload", "-p", type=str, help="JSON string of valuation metadata")
    parser.add_argument("--file", "-f", type=str, help="Path to JSON file containing valuation metadata")
    parser.add_argument("--db", type=str, help="Optional custom path to domain_model.sqlite")
    parser.add_argument("--json", action="store_true", help="Output JSON response")
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

    result = persist_valuation(payload_data, db_path=args.db)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Successfully persisted valuation for {result['symbol']} (v{result['version']})")


if __name__ == "__main__":
    main()
