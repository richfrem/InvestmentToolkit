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


DATA_DIR = Path(__file__).resolve().parents[5] / "investment_screener" / "backend" / "data" / "etf_analysis"
PROJ_DIR = Path(__file__).resolve().parents[5] / "investment_screener" / "backend" / "data" / "projections"


def _build_projection(data: dict, version: int) -> dict:
    """Synthesise a projection-format record from an ETF analysis so the
    Dashboard's loadAIThesis (which reads data/projections/) shows the
    AI Expert Thesis panel for every ETF that has been analysed."""
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


def persist(data: dict, dry_run: bool = False) -> str:
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

    # Also write/update data/projections/{ticker}.json so the Dashboard's
    # AI Expert Thesis panel shows this analysis automatically.
    PROJ_DIR.mkdir(parents=True, exist_ok=True)
    proj_path = PROJ_DIR / f"{ticker}.json"
    proj_existing = []
    if proj_path.exists():
        try:
            proj_existing = json.loads(proj_path.read_text())
            if not isinstance(proj_existing, list):
                proj_existing = [proj_existing]
            # Remove any previous ETF_ANALYSIS entries (keep user projections)
            proj_existing = [p for p in proj_existing if p.get("source") != "ETF_ANALYSIS"]
        except Exception:
            proj_existing = []

    proj_record = _build_projection(data, next_version)
    proj_existing.append(proj_record)
    proj_path.write_text(json.dumps(proj_existing, indent=2))
    print(f"✅ Projection synced: {proj_path}")

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
