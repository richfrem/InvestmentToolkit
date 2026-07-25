#!/usr/bin/env python3
"""
generate_review_json.py (Python Service)
=====================================

Purpose:
    Generates a dated `PortfolioAnalysisRecommendations.json` by comparing the current thesis targets 
    against live brokerage holdings. This JSON powers the Portfolio Analysis UI modal and 
    tracks proposed, approved, and applied rebalancing actions.

Layer: Backend / Python Services / Rebalancing

Usage Examples:
    python3 generate_review_json.py --date 2026-05-11
    python3 generate_review_json.py --dry-run

Key Functions:
    - generate() - Primary orchestrator that computes deltas, assigns action urgency, and structures the final JSON payload
    - _urgency() - Logic for classifying rebalance actions into URGENT, NORMAL, or LOW priority based on delta magnitude and action type
    - main() - CLI wrapper for persistence and interactive overwrite protection

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (investment,
      strategy_pillar tables -- sole source of truth)
"""

import json
import sys
import argparse
import datetime
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parents[3]
DB_PATH     = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"
REVIEWS_DIR = REPO_ROOT / "PortfolioAnalysis/strategic-reviews"

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from portfolio_action import derive_action
from portfolio_io import load_portfolio_state, compute_weights, load_target_weights  # noqa: E402


def _compute_current_from_db() -> dict:
    """Wave 3 replacement for validate_weights.compute_current(PORTFOLIO).

    Sources shares/prices/total from portfolio_io.load_portfolio_state()
    (domain_model.sqlite, ADR-030) and derives per-ticker weight % via
    portfolio_io.compute_weights(). Returns the same {"holdings": {...}} shape
    the old compute_current() returned so downstream code is unchanged.
    """
    state = load_portfolio_state(None)
    holdings = compute_weights(state["shares"], state["prices"], state["total_usd"])
    return {"total": round(sum(holdings.values()), 4), "holdings": holdings,
            "total_value": state["total_usd"]}


def _urgency(action: str, delta_abs: float) -> str:
    if action in ("EXIT", "INITIATE") and delta_abs > 3:
        return "URGENT"
    if action in ("EXIT", "INITIATE") or delta_abs > 1.5:
        return "NORMAL"
    return "LOW"


def _load_investments_from_db(db_path: Path) -> dict:
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import list_investments

    conn = initialize_db(str(db_path))
    try:
        rows = list_investments(conn)
    finally:
        conn.close()
    return {row["symbol"]: row for row in rows}


def _load_pillars_from_db(db_path: Path) -> list[dict]:
    from domain_model.db_client import initialize_db
    from domain_model.pillar_repository import list_pillars

    conn = initialize_db(str(db_path))
    try:
        rows = list_pillars(conn)
    finally:
        conn.close()
    return rows


def generate(date_str: str, db_path: Path = DB_PATH) -> dict:
    # _compute_current_from_db() always reads the real domain_model.sqlite --
    # portfolio_io.load_portfolio_state()'s own path parameter is documented
    # as unused (established contract shared by its 7+ existing callers).
    current_data  = _compute_current_from_db()
    target_data   = load_target_weights(str(db_path))
    holdings_map  = _load_investments_from_db(db_path)

    active   = []
    maintain = []

    for ticker, h in holdings_map.items():
        actual  = current_data["holdings"].get(ticker, 0)
        target  = target_data.get(ticker, 0)
        action  = derive_action(ticker, actual, target)
        delta   = round(target - actual, 4)

        # Skip WATCHLIST (both actual=0 and target=0, nothing to do)
        if action == "WATCHLIST":
            continue

        # REVIEW means actual significantly > target → treat as TRIM
        if action == "REVIEW":
            action = "TRIM"

        entry = {
            "ticker":            ticker,
            "pillarId":          h.get("pillar_id") or "unknown",
            "role":              h.get("lifecycle_status") or "core",
            "currentTarget":     round(target, 4),
            "recommendedTarget": round(target, 4),
            "delta":             delta,
            "action":            action,
            "actualPct":         round(actual, 4),
            "actualDelta":       delta,
            "rationale":         h.get("agent_rationale") or "",
            "urgency":           _urgency(action, abs(delta)),
        }

        if action == "MAINTAIN":
            maintain.append(entry)
        else:
            active.append(entry)

    # Sort active: EXIT first, then INITIATE, ACCUMULATE, TRIM — by delta magnitude within group
    order = {"EXIT": 0, "INITIATE": 1, "ACCUMULATE": 2, "TRIM": 3}
    active.sort(key=lambda x: (order.get(x["action"], 9), -abs(x["delta"])))

    total_shifted = round(sum(abs(h["delta"]) for h in active), 2)
    urgent  = sum(1 for h in active if h["urgency"] == "URGENT")
    normal  = sum(1 for h in active if h["urgency"] == "NORMAL")
    low_cnt = sum(1 for h in active if h["urgency"] == "LOW")

    pillar_list = [
        {
            "id":                p["pillar_id"],
            "name":              p["name"],
            "currentTarget":     round(p.get("target_weight") or 0, 2),
            "recommendedTarget": round(p.get("target_weight") or 0, 2),
            "delta":             0.0,
            "note":              "Current target from investment.target_weight (domain_model.sqlite)",
        }
        for p in _load_pillars_from_db(db_path)
    ]

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
         f"{datetime.datetime.now().microsecond // 1000:03d}Z"

    return {
        "reviewDate":             date_str,
        "reviewId":               f"{date_str}-PortfolioAnalysisRecommendations",
        "reviewFile":             f"PortfolioAnalysis/strategic-reviews/{date_str}-PortfolioAnalysisRecommendations.md",
        # thesisName/targetPortfolioVersion are document-level display
        # metadata only (no per-ticker business data) -- fixed descriptive
        # values, not read anywhere downstream but display.
        "thesisName":             "Investment Thesis",
        "targetPortfolioVersion": 1,
        "targetPortfolioFile":    "investment_screener/backend/data/domain_model.sqlite",
        "status":                 "PROPOSED",
        "approvedAt":             None,
        "appliedAt":              None,
        "applyCommand":           "python3 plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py --write",
        "summary": {
            "holdingsWithChanges": len(active),
            "holdingsUnchanged":   len(maintain),
            "urgentActions":       urgent,
            "normalActions":       normal,
            "lowActions":          low_cnt,
            "totalWeightShifted":  total_shifted,
        },
        "pillars":          pillar_list,
        "holdings":         active,
        "holdingsUnchanged": maintain,
        "generatedAt":      ts,
        "recommendations":  [],
    }


def main():
    parser = argparse.ArgumentParser(description="Generate a dated portfolio review JSON.")
    parser.add_argument("--date", default=datetime.date.today().isoformat(),
                        help="Review date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print JSON to stdout instead of writing to file.")
    args = parser.parse_args()

    review = generate(args.date)

    if args.dry_run:
        print(json.dumps(review, indent=2))
        return

    out = REVIEWS_DIR / f"{args.date}-PortfolioAnalysisRecommendations.json"
    if out.exists():
        print(f"⚠️  File already exists: {out}")
        answer = input("Overwrite? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

    out.write_text(json.dumps(review, indent=2) + "\n")
    s = review["summary"]
    print(f"✅ Written: {out}")
    print(f"   thesisName: {review['thesisName']}")
    print(f"   Holdings: {s['holdingsWithChanges']} with changes, {s['holdingsUnchanged']} maintain")
    print(f"   Actions:  {s['urgentActions']} URGENT, {s['normalActions']} NORMAL, {s['lowActions']} LOW")
    print(f"   Total weight to shift: {s['totalWeightShifted']:.2f}pp")


if __name__ == "__main__":
    main()
