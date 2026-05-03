#!/usr/bin/env python3
"""
generate_portfolio_blueprint.py — Generate Section IV: Portfolio Blueprint
for investment_thesis.md by combining target-portfolio.json (thesis targets)
with portfolio.json (actual broker holdings).

Groups holdings by subStrategyId. Shows actual %, target %, P&L, and
thesis-for-inclusion. Writes the section directly into investment_thesis.md
(replaces everything between the Section IV header and the next ## header).

Usage:
  python3 generate_portfolio_blueprint.py              # dry-run, print to stdout
  python3 generate_portfolio_blueprint.py --write      # update investment_thesis.md in place
  python3 generate_portfolio_blueprint.py --write --thesis-id target-portfolio
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

THESIS_JSON   = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
PORTFOLIO_JSON = REPO_ROOT / "investment_screener/frontend/src/data/portfolio.json"
THESIS_MD     = REPO_ROOT / "plugins/thesis-balancer/references/investment_thesis.md"

SUB_STRATEGY_NAMES = {
    "sa-asi-race":       "Sub-Strategy 1 — Situational Awareness / ASI Race",
    "datacenter-infra":  "Sub-Strategy 2 — Data Center Physical Infrastructure",
    "sovereign-finance": "Sub-Strategy 3 — Sovereign Finance",
    "quality-saas":      "Sub-Strategy 4 — Quality SaaS Resilience",
    "frontier-bets":     "Sub-Strategy 5 — Applied AI / Frontier Bets",
    "cash":              "Strategic Reserve",
    "untracked":         "Untracked / Thesis Pending",
}

ACTION_EMOJI = {
    "INITIATE":   "🟢",
    "ACCUMULATE": "🔵",
    "MAINTAIN":   "⚪",
    "TRIM":       "🟡",
    "EXIT":       "🔴",
    "WATCHLIST":  "👁️",
}


def load_json(path: Path) -> dict | list:
    with open(path) as f:
        return json.load(f)


def build_actual_map(portfolio: list) -> tuple[dict, float]:
    total = sum(h["shares"] * h["price"] for h in portfolio)
    actual = {}
    for h in portfolio:
        val = h["shares"] * h["price"]
        actual[h["symbol"]] = {
            "shares":    h["shares"],
            "price":     h["price"],
            "book":      h.get("book_price", 0),
            "value":     round(val, 2),
            "actualPct": round(val / total * 100, 2) if total else 0,
            "pnl":       round((h["price"] - h.get("book_price", h["price"])) / h.get("book_price", h["price"]) * 100, 1)
                         if h.get("book_price", 0) > 0 else 0,
            "name":      h.get("name", h["symbol"]),
        }
    return actual, total


def build_thesis_map(thesis: dict) -> dict:
    """Returns {ticker: {subStrategyId, targetPct, role, thesisNote, thesisBreakers}}"""
    holdings = {}
    for h in thesis.get("holdings", []):
        ticker = h["ticker"]
        holdings[ticker] = {
            "subStrategyId": h.get("subStrategyId", h.get("pillarId", "untracked")),
            "targetPct":     h.get("targetWeight", h.get("targetPct", 0)),
            "role":          h.get("role", ""),
            "thesisNote":    h.get("thesisForInclusion", h.get("thesisNote", "")),
            "thesisBreakers": h.get("thesisBreakers", []),
        }
    return holdings


def assign_action(actual_pct: float, target_pct: float, existing_action: str = "") -> str:
    if existing_action == "EXIT":
        return "EXIT"
    held = actual_pct > 0
    delta = target_pct - actual_pct
    if not held:
        return "INITIATE" if target_pct > 0 else "WATCHLIST"
    if delta > 0.5:
        return "ACCUMULATE"
    if delta < -0.5:
        return "TRIM"
    return "MAINTAIN"


def generate_section(thesis_map: dict, actual_map: dict, total_value: float) -> str:
    today = date.today().isoformat()

    # Group by sub-strategy
    groups: dict[str, list] = {}
    for ticker, t in thesis_map.items():
        sid = t["subStrategyId"]
        groups.setdefault(sid, []).append(ticker)

    # Add untracked holdings (in portfolio but not in thesis)
    untracked = [s for s in actual_map if s not in thesis_map and s != "USD_CASH"]
    if untracked:
        groups.setdefault("untracked", []).extend(untracked)

    lines = []
    lines.append("## IV. Portfolio Blueprint")
    lines.append("")
    lines.append(f"*Generated {today} from `target-portfolio.json` × `portfolio.json` (Questrade live sync).*")
    lines.append(f"*Total portfolio value: ${total_value:,.0f}. Run `python3 plugins/thesis-balancer/scripts/generate_portfolio_blueprint.py --write` to refresh.*")
    lines.append("")

    order = ["sa-asi-race", "datacenter-infra", "sovereign-finance", "quality-saas", "frontier-bets", "cash", "untracked"]
    for sid in order:
        if sid not in groups:
            continue
        tickers = groups[sid]
        section_name = SUB_STRATEGY_NAMES.get(sid, sid)
        lines.append(f"### {section_name}")
        lines.append("")
        lines.append("| Ticker | Action | Actual % | Target % | P&L | Conviction |")
        lines.append("| :--- | :--- | ---: | ---: | ---: | :--- |")

        # Sort: EXIT last, then by actual pct descending
        def sort_key(t):
            a = actual_map.get(t, {})
            th = thesis_map.get(t, {})
            is_exit = 1 if th.get("role") == "EXIT" else 0
            return (is_exit, -a.get("actualPct", 0))

        for ticker in sorted(tickers, key=sort_key):
            a = actual_map.get(ticker, {})
            th = thesis_map.get(ticker, {})
            actual_pct = a.get("actualPct", 0.0)
            target_pct = th.get("targetPct", 0.0)
            pnl = a.get("pnl", 0.0)
            action = assign_action(actual_pct, target_pct, th.get("role", "").upper())
            emoji = ACTION_EMOJI.get(action, "")
            note = th.get("thesisNote") or a.get("name", ticker)
            pnl_str = f"+{pnl:.1f}%" if pnl >= 0 else f"{pnl:.1f}%"
            actual_str = f"{actual_pct:.2f}%" if actual_pct else "—"
            target_str = f"{target_pct:.2f}%" if target_pct else "—"

            lines.append(f"| **{ticker}** | {emoji} {action} | {actual_str} | {target_str} | {pnl_str} | {note} |")

        lines.append("")

    return "\n".join(lines)


def update_thesis_md(new_section: str, path: Path) -> None:
    content = path.read_text()
    # Replace from ## IV. ... up to the next ## heading
    pattern = r"(## IV\. Portfolio Blueprint.*?)(?=\n## |\Z)"
    replacement = new_section + "\n\n---\n\n"
    updated, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count == 0:
        # Section doesn't exist yet — append before ## V
        updated = re.sub(r"(\n## V\.)", "\n\n" + new_section + "\n\n---\n\n## V.", content, count=1)
    path.write_text(updated)
    print(f"✅ Updated: {path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Portfolio Blueprint section for investment_thesis.md")
    parser.add_argument("--write", action="store_true", help="Write updated section into investment_thesis.md")
    parser.add_argument("--portfolio", default=str(PORTFOLIO_JSON))
    parser.add_argument("--thesis-json", default=str(THESIS_JSON))
    parser.add_argument("--thesis-md", default=str(THESIS_MD))
    args = parser.parse_args()

    thesis_json = load_json(Path(args.thesis_json))
    portfolio   = load_json(Path(args.portfolio))

    actual_map, total_value = build_actual_map(portfolio)
    thesis_map = build_thesis_map(thesis_json)

    section = generate_section(thesis_map, actual_map, total_value)

    if args.write:
        update_thesis_md(section, Path(args.thesis_md))
    else:
        print(section)


if __name__ == "__main__":
    main()
