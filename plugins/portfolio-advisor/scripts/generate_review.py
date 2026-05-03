#!/usr/bin/env python3
"""
generate_review.py — Bootstrap a dated PortfolioAnalysisRecommendations.md from the
canonical template, pre-populating header metadata from live portfolio and thesis data.

Usage (run from repo root):
    python3 plugins/portfolio-advisor/scripts/generate_review.py [--date YYYY-MM-DD] [--dry-run]

Output:
    PortfolioAnalysis/strategic-reviews/YYYY-MM-DD-PortfolioAnalysisRecommendations.md

The generated file is a starting point for the /strategic-review agent skill.
All {{PLACEHOLDER}} tokens that require AI analysis are left as-is for the agent to fill.
"""

import json
import os
import sys
import argparse
import datetime
from pathlib import Path

# ── Paths (relative to repo root) ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]  # plugins/portfolio-advisor/scripts/ → repo root
TEMPLATE_PATH = REPO_ROOT / "plugins/portfolio-advisor/assets/templates/PortfolioAnalysisRecommendations.md"
PORTFOLIO_PATH = REPO_ROOT / "investment_screener/frontend/src/data/portfolio.json"
THESIS_PATH    = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
OUTPUT_DIR     = REPO_ROOT / "PortfolioAnalysis/strategic-reviews"
PROJECTIONS_DIR = REPO_ROOT / "investment_screener/backend/data/projections"


def load_json(path: Path) -> dict | list:
    with open(path) as f:
        return json.load(f)


def compute_portfolio_summary(portfolio: list) -> dict:
    """Derive key metrics from portfolio.json for header population."""
    holdings = [h for h in portfolio if h.get("symbol") != "USD_CASH"]
    cash = next((h for h in portfolio if h.get("symbol") == "USD_CASH"), None)

    total_value = sum(h.get("shares", 0) * h.get("price", 0) for h in portfolio)
    cash_value = cash.get("shares", 0) * cash.get("price", 1) if cash else 0
    cash_pct = round(cash_value / total_value * 100, 2) if total_value else 0

    return {
        "total_value": round(total_value, 0),
        "holding_count": len(holdings),
        "cash_value": round(cash_value, 0),
        "cash_pct": cash_pct,
    }


def compute_thesis_summary(thesis: dict, portfolio: list) -> dict:
    """Derive EXIT/INITIATE counts and thesis metadata."""
    held_tickers = {h["symbol"] for h in portfolio if h.get("shares", 0) > 0}

    all_thesis_holdings = []
    for pillar in thesis.get("pillars", []):
        for h in pillar.get("holdings", []):
            all_thesis_holdings.append(h)

    thesis_tickers = {h["ticker"] for h in all_thesis_holdings}
    target_zero = [h["ticker"] for h in all_thesis_holdings if h.get("targetWeight", 1) == 0]
    exit_flagged = [t for t in target_zero if t in held_tickers]
    initiate_targets = [t for t in thesis_tickers if t not in held_tickers and
                        any(h["ticker"] == t and h.get("targetWeight", 0) > 0 for h in all_thesis_holdings)]

    return {
        "thesis_name": thesis.get("name", "Investment Thesis"),
        "thesis_version": thesis.get("version", "?"),
        "exit_count": len(exit_flagged),
        "initiate_count": len(initiate_targets),
        "exit_tickers": exit_flagged,
        "initiate_tickers": initiate_targets,
    }


def scan_top_opportunities(portfolio: list, limit: int = 10) -> list:
    """Scan projections dir for unowned BUY-rated tickers, rank by upside × confidence."""
    if not PROJECTIONS_DIR.exists():
        return []

    held_tickers = {h["symbol"] for h in portfolio if h.get("shares", 0) > 0}
    opportunities = []

    for fname in PROJECTIONS_DIR.iterdir():
        if fname.suffix != ".json":
            continue
        ticker = fname.stem
        if ticker in held_tickers:
            continue

        try:
            projections = load_json(fname)
            ai = [p for p in projections if p.get("source") == "AI_AGENT"]
            if not ai:
                continue
            latest = max(ai, key=lambda x: x.get("savedAt", ""))
            th = latest.get("aiThesis", {})
            sn = latest.get("snapshot", {})
            fv = th.get("fairValue", 0)
            price = sn.get("price", 0) or th.get("currentPrice", 0)
            action = th.get("action", "")
            conf = latest.get("analyticsLog", {}).get("confidenceScore", 0) or 0
            analyzed_at = (th.get("analyzedAt") or "")[:10]

            if action in ("BUY", "INITIATE", "ACCUMULATE") and price > 0 and fv > 0:
                upside = round((fv - price) / price * 100, 1)
                opportunities.append({
                    "ticker": ticker,
                    "action": action,
                    "fairValue": fv,
                    "price": price,
                    "upside": upside,
                    "confidence": round(float(conf), 2),
                    "score": round(upside * float(conf), 1),
                    "analyzedAt": analyzed_at,
                    "keyThesis": (th.get("thesis") or "")[:100],
                })
        except Exception:
            continue

    opportunities.sort(key=lambda x: x["score"], reverse=True)
    return opportunities[:limit]


def build_opportunity_table(opportunities: list) -> str:
    """Render the opportunity leaderboard as a markdown table."""
    if not opportunities:
        return "_No unowned BUY-rated tickers found in projections corpus._"

    rows = ["| Rank | Ticker | Upside | Fair Value | Price | Conf | Analyzed | Key Thesis |",
            "|------|--------|--------|------------|-------|------|----------|------------|"]
    for i, o in enumerate(opportunities, 1):
        stale = " ⚠️" if o["analyzedAt"] and _days_old(o["analyzedAt"]) > 90 else ""
        row = (f"| {i} | {o['ticker']}{stale} | +{o['upside']}% | "
               f"${o['fairValue']:,.0f} | ${o['price']:,.0f} | {o['confidence']} | "
               f"{o['analyzedAt']} | {o['keyThesis']}... |")
        rows.append(row)
    return "\n".join(rows)


def _days_old(date_str: str) -> int:
    try:
        d = datetime.date.fromisoformat(date_str)
        return (datetime.date.today() - d).days
    except Exception:
        return 0


def populate_template(template: str, portfolio_summary: dict, thesis_summary: dict,
                      opportunities: list, date_str: str) -> str:
    """Replace all header-level {{PLACEHOLDERS}} we can fill from data."""
    total_value = portfolio_summary["total_value"]
    opp_table = build_opportunity_table(opportunities)

    # Capital calc: top-5 at 2% each
    top5_capital = round(total_value * 0.02 * min(5, len(opportunities)), 0)

    replacements = {
        "{{DATE}}":               date_str,
        "{{THESIS_NAME}}":        thesis_summary["thesis_name"],
        "{{THESIS_VERSION}}":     str(thesis_summary["thesis_version"]),
        "{{PORTFOLIO_VALUE_USD}}": f"{total_value:,.0f}",
        "{{HOLDING_COUNT}}":      str(portfolio_summary["holding_count"]),
        "{{EXIT_COUNT}}":         str(thesis_summary["exit_count"]),
        "{{INITIATE_COUNT}}":     str(thesis_summary["initiate_count"]),
        "{{CASH_VALUE}}":         f"{portfolio_summary['cash_value']:,.0f}",
        "{{CASH_PCT}}":           str(portfolio_summary["cash_pct"]),
        "{{TOP5_CAPITAL_REQUIRED}}": f"{top5_capital:,.0f}",
        # Leave AI-requiring fields for agent to fill:
        "{{FORMULA_SCORE}}":      "??",
        "{{FORMULA_STATUS}}":     "PENDING ANALYSIS",
        "{{ONE_LINE_STATUS}}":    "⏳ Run /strategic-review to populate this review.",
        "{{OVERALL_ASSESSMENT}}": "_Run /strategic-review to generate the overall assessment._",
        "{{TOP_CONVICTION_TICKERS}}": "_Pending Phase 3 conviction interview_",
        "{{LOW_CONVICTION_TICKERS}}": "_Pending Phase 3 conviction interview_",
        "{{CONVICTION_CHANGES}}": "_Pending Phase 3 conviction interview_",
        "{{TOTAL_REDEPLOY}}":     "??",
        "{{REDEPLOY_PCT}}":       "??",
        "<!-- {{OPPORTUNITY_ROWS}} -->": opp_table,
        "<!-- {{THEME_GAP_ROWS}} -->": "_Pending Phase 2 gap analysis_",
        "<!-- {{PILLAR_AUDIT_ROWS}} -->": "_Pending Step 2 pillar conviction audit_",
        "<!-- {{CHALLENGED_ROWS}} -->": "_Pending analysis_",
        "<!-- {{CONFIRMED_ROWS}} -->": "_Pending analysis_",
        "<!-- {{BREAKER_ROWS}} -->": "_Pending analysis_",
        "<!-- {{CONFLICT_BLOCKS}} -->": "_Pending analysis_",
        "<!-- {{PROPOSAL_BLOCKS}} -->": "_Pending analysis_",
        "<!-- {{EXIT_ROWS}} -->": "_Pending analysis_",
        "<!-- {{INITIATE_ROWS}} -->": "_Pending analysis_",
        "<!-- {{ACTION_LIST}} -->": "_Pending analysis_",
        "<!-- {{OPEN_QUESTIONS}} -->": "_Pending analysis — agent will populate after Phase 3 interview_",
        "{{EXIT_CAPITAL}}":       "??",
        "{{EXIT_PCT}}":           "??",
        "{{SOURCE_PORTFOLIO}}":   f"✅ Loaded — {portfolio_summary['holding_count']} holdings, ${total_value:,.0f}",
        "{{SOURCE_THESIS}}":      f"✅ Loaded — v{thesis_summary['thesis_version']}",
        "{{SOURCE_PROJECTIONS}}": f"✅ {len(opportunities)} unowned BUY candidates surfaced",
        "{{SOURCE_MISSING}}":     "⚠️ Run /strategic-review to check",
        "{{SOURCE_MEMORY}}":      "⚠️ Run /strategic-review to load",
        "{{SOURCE_WEIGHTS}}":     "⚠️ Run validate_weights.py to verify",
        "{{SOURCE_PILLARS}}":     "⚠️ Pending analysis",
        "{{SOURCE_SCORE}}":       "⚠️ Pending analysis",
    }

    result = template
    for token, value in replacements.items():
        result = result.replace(token, value)
    return result


def main():
    parser = argparse.ArgumentParser(description="Bootstrap a strategic review from the canonical template.")
    parser.add_argument("--date", default=datetime.date.today().isoformat(),
                        help="Review date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print output to stdout instead of writing to file.")
    args = parser.parse_args()

    # Load data
    if not TEMPLATE_PATH.exists():
        print(f"❌ Template not found: {TEMPLATE_PATH}", file=sys.stderr)
        sys.exit(1)
    if not PORTFOLIO_PATH.exists():
        print(f"❌ portfolio.json not found: {PORTFOLIO_PATH}", file=sys.stderr)
        sys.exit(1)

    template = TEMPLATE_PATH.read_text()
    portfolio = load_json(PORTFOLIO_PATH)
    thesis = load_json(THESIS_PATH) if THESIS_PATH.exists() else {}

    portfolio_summary = compute_portfolio_summary(portfolio)
    thesis_summary = compute_thesis_summary(thesis, portfolio)
    opportunities = scan_top_opportunities(portfolio)

    populated = populate_template(template, portfolio_summary, thesis_summary, opportunities, args.date)

    if args.dry_run:
        print(populated)
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{args.date}-PortfolioAnalysisRecommendations.md"

    if out_path.exists():
        print(f"⚠️  File already exists: {out_path}")
        answer = input("Overwrite? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

    out_path.write_text(populated)
    print(f"✅ Review scaffolded: {out_path}")
    print(f"   Holdings: {portfolio_summary['holding_count']} | "
          f"EXIT-flagged: {thesis_summary['exit_count']} | "
          f"INITIATE targets: {thesis_summary['initiate_count']}")
    print(f"   Opportunity scan: {len(opportunities)} unowned BUY candidates surfaced")
    print(f"\n→ Open the file, then run /strategic-review in Claude Code to populate it.")


if __name__ == "__main__":
    main()
