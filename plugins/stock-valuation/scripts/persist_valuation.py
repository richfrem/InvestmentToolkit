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
    python3 persist_valuation.py --file payload.json --rate-audit rate_audit.json --db PATH
    python3 persist_valuation.py --payload '{"symbol": "NVDA", ...}'

Key Functions:
    _require_rate_match() — Require a finite decimal rate equal to the audit.
    _validate_model_rate_fields() — Check duplicated calculation metadata.
    validate_discount_rate_audit() — Check method/rate/arithmetic before a database write.
    attach_discount_rate_audit() — Add a calculator artifact without losing model metadata.
    _persist_projection(), _persist_outlook_note(), _persist_scenarios() — Domain transaction helpers.
    _persist_technicals() — Separate post-commit intelligence sweep.
    persist_valuation() — Version and persist valuation through domain repositories.
    main() — CLI entry point.

Key Input Dependencies:
    Reviewed valuation payload; optional wacc.py explicit-input audit; domain_model.sqlite.
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Connection

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
from wacc import compute_discount_rate


def _require_rate_match(rate: object, expected: dict, label: str) -> None:
    """Validate a decimal rate against the reproducible selected rate."""
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate):
        raise ValueError(f"{label} must be an explicit finite decimal rate")
    if not math.isclose(rate, expected["selectedRate"], rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError(f"{label} does not match discountRateAudit")


def _validate_model_rate_fields(model: dict, expected: dict, label: str) -> None:
    """Validate every present method/rate in a known calculator metadata object."""
    if "method" in model and model["method"] != expected["method"]:
        raise ValueError(f"{label} method does not match discountRateAudit")
    for key in ("discountRate", "discount_rate"):
        if key not in model:
            continue
        _require_rate_match(model[key], expected, f"{label}.{key}")


def validate_discount_rate_audit(projection: dict) -> None:
    """Reject inconsistent audited valuations before opening the database.

    This verifies reproducibility and method/rate agreement, not source validity
    or investment readiness. Legacy projections without audits retain their path.
    """
    model = projection.get("valuationModel") or {}
    audit = model.get("discountRateAudit")
    if audit is None:
        return
    if not isinstance(audit, dict):
        raise ValueError("discountRateAudit must be a calculator output object")
    expected = compute_discount_rate(audit.get("inputs") or {})
    for key in ("method", "asOf", "currency", "rateType", "components"):
        if audit.get(key) != expected[key]:
            raise ValueError(f"discountRateAudit {key} does not match its inputs")
    if model.get("method") != expected["method"]:
        raise ValueError("valuationModel method does not match discountRateAudit")
    _validate_model_rate_fields(model, expected, "valuationModel")
    if projection.get("model") in ("annual_fcff", "terminal_earnings", "annual_fcfe"):
        if projection["model"] != expected["method"]:
            raise ValueError("projection model does not match discountRateAudit")
    for parent, label in ((model, "valuationModel"), (projection, "projection")):
        for name, scenario in (parent.get("scenarios") or {}).items():
            _validate_model_rate_fields(scenario, expected, f"{label}.scenarios.{name}")
    _require_rate_match(audit.get("selectedRate"), expected, "selectedRate")
    _require_rate_match(projection.get("discount_rate", projection.get("discountRate")), expected, "discount_rate")
    _validate_model_rate_fields(projection, expected, "projection")


def attach_discount_rate_audit(payload: dict, audit: dict) -> None:
    """Attach a reviewed calculator artifact and preserve existing model fields."""
    projection = payload.get("projection")
    if not isinstance(projection, dict):
        raise ValueError("--rate-audit requires a projection payload")
    model = projection.setdefault("valuationModel", {})
    existing = model.get("discountRateAudit")
    if existing is not None and existing != audit:
        raise ValueError("Conflicting embedded and supplied discountRateAudit")
    model["discountRateAudit"] = audit
    validate_discount_rate_audit(projection)


def _persist_projection(conn: "Connection", symbol: str, proj: dict, payload: dict, now_iso: str) -> int:
    """Save projection metadata and delegate notes/scenarios inside the caller transaction."""
    latest_pv = get_latest_projection(conn, symbol)
    new_version = (latest_pv["version"] + 1) if latest_pv else 1

    fair_value = proj.get("fair_value", proj.get("weightedFairValue"))
    action = proj.get("action") or "HOLD"
    model = proj.get("model", "5yr_dcf_scenarios")
    rationale = proj.get("rationale", "")
    current_price = proj.get("current_price") or proj.get("currentPrice")
    upside_pct = proj.get("upside_pct", proj.get("upsidePct"))
    discount_rate = proj.get("discount_rate", proj.get("discountRate", 0.085))

    snapshot = {
        "ticker": symbol,
        "currentPrice": current_price,
        "weightedFairValue": fair_value,
        "upsidePct": upside_pct,
        "action": action,
        "discountRate": discount_rate,
        "horizon": proj.get("horizon", 5),
        "baseRevenue": proj.get("base_revenue") or proj.get("baseRevenue"),
        "baseShares": proj.get("base_shares") or proj.get("baseShares"),
        "researchReport": proj.get("researchReport"),
    }
    analytics_log = {
        "valuationAction": action,
        "portfolioUrgency": proj.get("urgency", "NORMAL"),
        "conviction": proj.get("conviction", 8),
        "fairValue": fair_value,
        "upsidePct": upside_pct,
        "wacc": discount_rate,
    }
    if "valuationModel" in proj:
        analytics_log["valuationModel"] = proj["valuationModel"]

    # Preserve and enforce outlookAudit in analytics_log
    if "outlookAudit" in proj:
        analytics_log["outlookAudit"] = proj["outlookAudit"]
    elif "outlookAudit" in payload:
        analytics_log["outlookAudit"] = payload["outlookAudit"]

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

    _persist_outlook_note(conn, symbol, analytics_log, now_iso)
    _persist_scenarios(conn, proj_id, proj)
    return new_version


def _persist_outlook_note(conn: "Connection", symbol: str, analytics_log: dict, now_iso: str) -> None:
    """Save the forward-outlook note in the same domain transaction."""
    audit = analytics_log.get("outlookAudit")
    if audit and isinstance(audit, dict):
        import uuid as _uuid
        calls_str = ", ".join(audit.get("callsAnalyzed", []))
        guidance = audit.get("guidanceDirection", "UNSPECIFIED")
        assessment = audit.get("strategicAssessment", "")
        risks = "; ".join(audit.get("adversarialRisks", [])) if audit.get("adversarialRisks") else "None recorded"
        backlog = audit.get("backlogPipeline", "None recorded")

        note_body = (
            f"## Forward Outlook Audit ({calls_str})\n"
            f"- Guidance Trajectory: {guidance}\n"
            f"- Contracted Backlog & Pipeline: {backlog}\n"
            f"- Strategic Assessment: {assessment}\n"
            f"- Adversarial Risks: {risks}"
        )
        note_id = f"{symbol}-audit-{_uuid.uuid4().hex[:8]}"
        has_call_material = any(
            marker in calls_str.lower()
            for marker in ("prepared remarks", "conference call", "call transcript")
        )
        note_type = "INVESTOR_CALL_TRANSCRIPT_ANALYSIS" if has_call_material else "EARNINGS_RELEASE_OUTLOOK"
        conn.execute(
            "INSERT INTO investment_note (note_id, investment_id, note_date, note_type, body, source) "
            "VALUES (?, ?, ?, ?, ?, 'persist_valuation::outlookAudit');",
            (note_id, symbol, now_iso, note_type, note_body)
        )


def _persist_scenarios(conn: "Connection", proj_id: str, proj: dict) -> None:
    """Save all scenario columns through the canonical projection repository."""
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
            scenario_price=sc_data.get("price", sc_data.get("scenario_price", sc_data.get("presentValue", 0.0))),
            quality_multiplier=sc_data.get("qualityMultiplier"),
            share_change=sc_data.get("shareChange"),
            rationale=sc_data.get("rationale"),
            risks_json=json.dumps(sc_data["risks"]) if "risks" in sc_data else None,
            year5_revenue=sc_data.get("year5Revenue") or sc_data.get("year5_revenue"),
            year5_net_income=sc_data.get("year5NetIncome") or sc_data.get("year5_net_income"),
            year5_eps=sc_data.get("year5EPS") or sc_data.get("year5_eps"),
        )


def _persist_technicals(payload: dict, proj: dict | None) -> None:
    """Write the separate intelligence sweep after domain commit; retain nonfatal warnings."""
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


def persist_valuation(payload: dict, db_path: str | None = None) -> dict:
    """Persist a reviewed payload; audited rates must agree before any mutation."""
    if isinstance(payload.get("projection"), dict):
        validate_discount_rate_audit(payload["projection"])
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
        new_version = _persist_projection(conn, symbol, proj, payload, now_iso) if isinstance(proj, dict) and proj else None

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

        _persist_technicals(payload, proj)

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


def main() -> None:
    """Read payload and optional rate audit, then call canonical persistence."""
    parser = argparse.ArgumentParser(description="Canonical stock valuation and price level persistence")
    parser.add_argument("--payload", "-p", type=str, help="JSON string of valuation metadata")
    parser.add_argument("--file", "-f", type=str, help="Path to JSON file containing valuation metadata")
    parser.add_argument("--db", type=str, help="Optional custom path to domain_model.sqlite")
    parser.add_argument("--rate-audit", type=Path, help="Attach and verify wacc.py explicit-input output")
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

    if args.rate_audit:
        attach_discount_rate_audit(payload_data, json.loads(args.rate_audit.read_text()))
    result = persist_valuation(payload_data, db_path=args.db)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Successfully persisted valuation for {result['symbol']} (v{result['version']})")


if __name__ == "__main__":
    main()
