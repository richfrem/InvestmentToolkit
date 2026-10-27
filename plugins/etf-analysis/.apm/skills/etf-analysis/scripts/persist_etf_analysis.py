#!/usr/bin/env python3
"""
persist_etf_analysis.py — etf-analysis plugin

Saves or updates an ETF analysis JSON to the data/etf_analysis/ directory.
If a file already exists for this ticker, appends the new analysis as a new
version (list of versions, same pattern as projections/).

Usage:
    python3 persist_etf_analysis.py < /tmp/DXYZ_etf.json
    python3 persist_etf_analysis.py --input /tmp/KOID_etf.json
    python3 persist_etf_analysis.py --input /tmp/HUMN_etf.json --dry-run
"""

import json
import sys
import uuid
import argparse
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / "investment_screener").exists():
            return parent
    return start.parents[3]


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
DATA_DIR = REPO_ROOT / "investment_screener" / "backend" / "data" / "etf_analysis"
DB_PATH = REPO_ROOT / "investment_screener" / "backend" / "data" / "domain_model.sqlite"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    get_latest_projection_by_source,
    list_projection_versions,
    save_projection_version,
    add_projection_scenario,
)


def _build_projection(data: dict, version: int) -> dict:
    """Synthesise a projection-format record from an ETF analysis so the
    Dashboard's AI Expert Thesis panel (backed by `projection_version` in
    domain_model.sqlite as of Wave 1 Task 7B — ADR-029) shows this analysis
    for every ETF that has been analysed."""
    snap = data.get("snapshot", {})
    price = snap.get("price", 0)
    ha = data.get("holdingsAnalysis", {})
    action = data.get("action", "HOLD")
    rationale_text = data.get("actionRationale", data.get("rationale", ""))

    # Build minimal bear/base/bull from action + alignment score
    alignment = ha.get("thesisAlignmentScore", 50)
    bear_price = round(price * 0.68, 2)   # -32% generic bear
    base_price = round(price * 1.15, 2)   # +15% generic base
    bull_price = round(price * 1.60, 2)   # +60% generic bull
    fair_value = round(0.35 * bear_price + 0.45 * base_price + 0.20 * bull_price, 2)

    top_holdings = ha.get("topHoldings", [])
    holdings_md = "\n".join(
        f"| {h.get('symbol','?')} | {h.get('holdingPct','?')}% | {h.get('alignment','?')} | {h.get('note','')} |"
        for h in top_holdings[:8]
    )

    full_rationale = (
        f"# {data.get('ticker', '')} — {data.get('name', 'ETF Analysis')}\n"
        f"## ETF Analysis — {data.get('fundType', 'THEMATIC_ETF')} (NOT a DCF)\n\n"
        f"{data.get('rationale', '')}\n\n"
        f"---\n\n"
        f"### Holdings (Top {len(top_holdings)})\n\n"
        f"| Symbol | Weight | Alignment | Note |\n"
        f"|--------|--------|-----------|------|\n"
        f"{holdings_md}\n\n"
        f"**Thesis Alignment Score: {alignment}/100**\n\n"
        f"---\n\n"
        f"### Action Rationale\n\n{rationale_text}\n\n"
        f"### Upside Catalysts\n\n"
        + "\n".join(f"- {c}" for c in data.get("upsideCatalysts", [])) + "\n\n"
        f"### Risks\n\n"
        + "\n".join(f"- {r}" for r in data.get("risks", [])) + "\n\n"
        + (f"### Entry Note\n\n{data.get('entryNote', '')}" if data.get("entryNote") else "")
    )

    return {
        "ticker": data["ticker"],
        "id": str(uuid.uuid4()),
        "source": "ETF_ANALYSIS",
        "schemaVersion": "1.2",
        "version": version,
        "savedAt": data.get("savedAt", data.get("updatedAt", "")),
        "updatedAt": data.get("updatedAt", data.get("savedAt", "")),
        "name": data.get("name", f"ETF Analysis — {data['ticker']}"),
        "rationale": data.get("rationale", ""),
        "snapshot": {
            "price": price,
            "currency": snap.get("currency", "USD"),
            "shares": 0, "revenue": 0, "lastActualPS": None,
            "fiscalPeriod": f"N/A — {data.get('fundType', 'ETF')}",
            "analystGrowthEstimate": None, "analystMarginEstimate": None,
        },
        "dataPreferences": {"growthBasis": "N/A", "marginBasis": "N/A"},
        "scenarios": {
            "bear": {
                "weight": 0.35, "growthRate": -20, "netMargin": 0, "exitPE": 0,
                "qualityMultiplier": 0.5, "shareChange": 0,
                "scenarioPrice": bear_price,
                "rationale": "Adverse scenario: thesis headwinds, sector rotation, macro weakness.",
                "year5Revenue": 0, "year5NetIncome": 0, "year5EPS": 0, "year5Shares": 0,
                "year5PriceUndiscounted": bear_price, "presentValue": bear_price,
            },
            "base": {
                "weight": 0.45, "growthRate": 5, "netMargin": 0, "exitPE": 0,
                "qualityMultiplier": 1.0, "shareChange": 0,
                "scenarioPrice": base_price,
                "rationale": "Base scenario: thesis plays out, moderate appreciation.",
                "year5Revenue": 0, "year5NetIncome": 0, "year5EPS": 0, "year5Shares": 0,
                "year5PriceUndiscounted": base_price, "presentValue": base_price,
            },
            "bull": {
                "weight": 0.20, "growthRate": 30, "netMargin": 0, "exitPE": 0,
                "qualityMultiplier": 1.5, "shareChange": 0,
                "scenarioPrice": bull_price,
                "rationale": "Bull scenario: thesis catalysts accelerate, strong re-rating.",
                "year5Revenue": 0, "year5NetIncome": 0, "year5EPS": 0, "year5Shares": 0,
                "year5PriceUndiscounted": bull_price, "presentValue": bull_price,
            },
        },
        "aiThesis": {
            "model": "Claude Sonnet 4.6",
            "fairValue": fair_value,
            "action": action,
            "analyzedAt": data.get("savedAt", data.get("updatedAt", "")),
            "rationale": full_rationale,
        },
        "globalSettings": {"discountRate": 10, "timeHorizon": 5},
        "analyticsLog": [],
    }


def _sync_projection_db(data: dict, next_version: int, db_path: Path, dry_run: bool = False) -> None:
    """Write/replace this ticker's ETF_ANALYSIS projection row in domain_model.sqlite.

    Storage backend (Wave 1 Task 7B): writes the `projection_version`/
    `projection_scenario` tables via `domain_model.projection_repository`, not
    `data/projections/{TICKER}.json` directly (ADR-029) — this was the second half
    of pitfall #8's "ETF dual-write" (the `data/etf_analysis/` versions file itself
    stays a plain JSON write; only the Dashboard-facing projection sync moved to
    SQLite). Mirrors the original file-based behavior of keeping only ONE
    ETF_ANALYSIS entry per ticker (old entries removed before the new one is
    appended): if a prior ETF_ANALYSIS row exists for this investment, its version
    number is reused (upsert replaces it in place); otherwise a new version number
    one past the investment's current MAX(version) is assigned so it never collides
    with an AI_AGENT-sourced row.
    """
    if dry_run:
        return
    conn = initialize_db(str(db_path))
    try:
        ticker = data["ticker"].upper()
        investment_id = resolve_investment(conn, ticker, asset_class="ETF")
        proj_record = _build_projection(data, next_version)

        existing_etf = get_latest_projection_by_source(conn, investment_id, "ETF_ANALYSIS")
        if existing_etf is not None:
            db_version = existing_etf["version"]
        else:
            all_versions = list_projection_versions(conn, investment_id)
            db_version = max((v["version"] for v in all_versions), default=0) + 1

        snapshot = proj_record["snapshot"]
        ai_thesis = proj_record["aiThesis"]
        projection_id = save_projection_version(
            conn, investment_id, version=db_version,
            saved_at=proj_record["savedAt"], analyzed_at=ai_thesis["analyzedAt"],
            model=ai_thesis["model"], fair_value=ai_thesis["fairValue"],
            action=ai_thesis["action"], rationale=ai_thesis["rationale"],
            snapshot_json=json.dumps(snapshot),
            analytics_log_json=json.dumps(proj_record["analyticsLog"]),
            source="ETF_ANALYSIS",
        )
        for name, scen in proj_record["scenarios"].items():
            add_projection_scenario(
                conn, projection_id, name,
                weight=scen.get("weight"), growth_rate=scen.get("growthRate"),
                net_margin=scen.get("netMargin"), exit_pe=scen.get("exitPE"),
                quality_multiplier=scen.get("qualityMultiplier"),
                share_change=scen.get("shareChange"), rationale=scen.get("rationale"),
                year5_revenue=scen.get("year5Revenue"), year5_net_income=scen.get("year5NetIncome"),
                year5_eps=scen.get("year5EPS"), scenario_price=scen.get("scenarioPrice"),
            )

        # Synchronize investment table state
        update_fields = {
            "target_action": ai_thesis.get("action"),
            "last_deep_analysis_at": ai_thesis.get("analyzedAt"),
        }
        if "agentRationale" in data:
            update_fields["agent_rationale"] = data["agentRationale"]
        elif "rationale" in data:
            update_fields["agent_rationale"] = data["rationale"]

        update_investment_fields(conn, investment_id, **update_fields)

        print(f"✅ Projection and investment record synced to domain_model.sqlite: {ticker} (version {db_version})")
    finally:
        conn.close()


def persist(data: dict, dry_run: bool = False, db_path: Path | None = None) -> str:
    ticker = data.get("ticker", "UNKNOWN").upper()
    out_path = DATA_DIR / f"{ticker}.json"

    existing = []
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
            if not isinstance(existing, list):
                existing = [existing]
        except Exception:
            existing = []

    next_version = max((e.get("version", 0) for e in existing), default=0) + 1
    data["version"] = next_version
    existing.append(data)

    if dry_run:
        print(f"[DRY RUN] Would write {ticker}.json  (version {next_version})")
        return str(out_path)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(existing, indent=2))
    print(f"✅ Written: {out_path}  (version {next_version})")

    # Also sync the Dashboard-facing projection (AI Expert Thesis panel reads
    # projection_version/projection_scenario in domain_model.sqlite — ADR-029,
    # Wave 1 Task 7B). Previously wrote data/projections/{ticker}.json directly.
    _sync_projection_db(data, next_version, db_path or DB_PATH, dry_run=dry_run)

    return str(out_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Input JSON file path (default: stdin)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.input:
        data = json.loads(Path(args.input).read_text())
    else:
        data = json.load(sys.stdin)

    persist(data, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
