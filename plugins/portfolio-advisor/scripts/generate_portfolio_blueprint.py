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
THESIS_MD     = REPO_ROOT / "plugins/portfolio-advisor/references/investment_thesis.md"

SUB_STRATEGY_NAMES = {
    "sa-asi-race":       "Sub-Strategy 1 — SA / ASI Race (Aschenbrenner Framework)",
    "cybersecurity":     "Sub-Strategy 2 — AI-Native Cybersecurity",
    "sovereign-finance": "Sub-Strategy 3 — Sovereign Finance",
    "quality-saas":      "Sub-Strategy 4 — Quality SaaS Resilience",
    "frontier-bets":     "Sub-Strategy 5 — Applied AI / Frontier Bets",
    "cash":              "Strategic Reserve",
    "untracked":         "Untracked / Thesis Pending",
}

from portfolio_action import derive_action, ACTION_EMOJI


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


def assign_action(ticker: str, actual_pct: float, target_pct: float, existing_action: str = "") -> str:
    return derive_action(ticker, actual_pct, target_pct)


def generate_section(thesis_map: dict, actual_map: dict, total_value: float) -> str:
    today = date.today().isoformat()

    # ── Import shared weight computation from validate_weights ──────────────
    sys.path.insert(0, str(Path(__file__).parent))
    from validate_weights import compute_current, compute_target
    current_data = compute_current(PORTFOLIO_JSON)
    target_data  = compute_target(THESIS_JSON)

    # Group by sub-strategy
    groups: dict[str, list] = {}
    for ticker, t in thesis_map.items():
        sid = t["subStrategyId"]
        groups.setdefault(sid, []).append(ticker)

    # Untracked: held but not in thesis
    untracked = [s for s in actual_map if s not in thesis_map and s not in ("USD_CASH",)]
    if untracked:
        groups.setdefault("untracked", []).extend(untracked)

    lines = []
    lines.append("## IV. Portfolio Blueprint")
    lines.append("")
    lines.append(f"*Generated {today} · Source: `validate_weights.py` × `target-portfolio.json` × `portfolio.json` (Questrade live)*")
    lines.append(f"*Portfolio value: ${total_value:,.0f}. Refresh: `python3 plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py --write`*")
    lines.append("")

    grand_actual = 0.0
    grand_target = 0.0

    order = ["sa-asi-race", "cybersecurity", "sovereign-finance", "quality-saas", "frontier-bets", "cash", "untracked"]
    for sid in order:
        if sid not in groups:
            continue
        tickers = groups[sid]
        section_name = SUB_STRATEGY_NAMES.get(sid, sid)
        lines.append(f"### {section_name}")
        lines.append("")
        lines.append("| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |")
        lines.append("| :--- | :--- | :--- | ---: | ---: | ---: | :--- |")

        def sort_key(t):
            ap = current_data["holdings"].get(t, 0) or 0
            th = thesis_map.get(t, {})
            is_exit = 1 if th.get("role") == "EXIT" else 0
            return (is_exit, -ap)

        sub_actual = 0.0
        sub_target = 0.0

        for ticker in sorted(tickers, key=sort_key):
            a          = actual_map.get(ticker, {})
            th         = thesis_map.get(ticker, {})
            actual_pct = current_data["holdings"].get(ticker, 0.0) or 0.0
            target_pct = target_data["holdings"].get(ticker, 0.0) or 0.0
            action     = assign_action(ticker, actual_pct, target_pct, th.get("role", "").upper())
            emoji      = ACTION_EMOJI.get(action, "")
            note       = th.get("thesisNote") or a.get("name", ticker)
            actual_str = f"{actual_pct:.2f}%" if actual_pct else "—"
            target_str = f"{target_pct:.2f}%" if target_pct else "—"
            
            # Fetch DCF projection for AI Signal & Upside
            proj_path = REPO_ROOT / f"investment_screener/backend/data/projections/{ticker}.json"
            ai_signal = "—"
            upside_str = "—"
            if proj_path.exists():
                try:
                    proj = load_json(proj_path)
                    thesis_obj = proj.get("aiThesis", {})
                    if thesis_obj:
                        fv = thesis_obj.get("fairValue")
                        curr_price = a.get("price") or thesis_obj.get("currentPrice")
                        if fv and curr_price and curr_price > 0:
                            upside = ((fv - curr_price) / curr_price) * 100
                            upside_str = f"+{upside:.1f}%" if upside >= 0 else f"{upside:.1f}%"
                        ai_action = thesis_obj.get("action")
                        if ai_action:
                            ai_signal = ai_action
                except Exception:
                    pass

            sub_actual += actual_pct
            sub_target += target_pct

            lines.append(f"| **{ticker}** | {emoji} {action} | {ai_signal} | {actual_str} | {target_str} | {upside_str} | {note} |")

        # Sub-strategy subtotal row
        delta = sub_target - sub_actual
        delta_str = (f"+{delta:.2f}pp" if delta > 0 else f"{delta:.2f}pp") if sub_actual or sub_target else "—"
        lines.append(f"| **Subtotal** | | **{sub_actual:.2f}%** | **{sub_target:.2f}%** | {delta_str} | |")
        lines.append("")

        grand_actual += sub_actual
        grand_target += sub_target

    # Overall totals
    grand_delta = grand_target - grand_actual
    grand_delta_str = f"+{grand_delta:.2f}pp" if grand_delta >= 0 else f"{grand_delta:.2f}pp"
    lines.append("### Portfolio Totals")
    lines.append("")
    lines.append("| | Actual % | Target % | Delta |")
    lines.append("| :--- | ---: | ---: | ---: |")
    lines.append(f"| **All holdings** | **{grand_actual:.2f}%** | **{grand_target:.2f}%** | {grand_delta_str} |")
    lines.append(f"| *Validate* | `python3 plugins/portfolio-advisor/scripts/validate_weights.py --mode both` | | |")
    lines.append("")

    return "\n".join(lines)


def update_thesis_md(new_section: str, path: Path) -> None:
    content = path.read_text()
    pattern = r"(## IV\. Portfolio Blueprint.*?)(?=\n## |\Z)"
    replacement = new_section + "\n\n---\n\n"
    updated, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count == 0:
        updated = re.sub(r"(\n## V\.)", "\n\n" + new_section + "\n\n---\n\n## V.", content, count=1)
    path.write_text(updated)
    print(f"✅ Updated Section IV: {path}")


def update_section_tables(content: str, current_data: dict, target_data: dict) -> str:
    """
    Find every '| Ticker | Role | Conviction Note |' table in the thesis and
    rebuild it with Action / Current % / Target % columns prepended after Ticker.
    Uses the canonical derive_action() — same logic as the frontend.
    """
    # Match table header + separator + all data rows (stops at blank line or non-table line)
    table_pattern = re.compile(
        r"(\| Ticker \| Role \| Conviction Note \|\n\| :--- \| :--- \| :--- \|\n)((?:\|[^\n]+\|\n?)+)",
        re.IGNORECASE
    )

    def rebuild_table(m: re.Match) -> str:
        rows_block = m.group(2)
        new_header = "| Ticker | Thesis Action | AI Signal | Actual % | Target % | Role | Conviction Note |\n"
        new_sep    = "| :--- | :--- | :--- | ---: | ---: | :--- | :--- |\n"
        new_rows = []
        for line in rows_block.splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) < 3:
                new_rows.append(line)
                continue
            ticker, role, conviction = parts[0], parts[1], "|".join(parts[2:]).strip()
            actual  = current_data["holdings"].get(ticker, 0) or 0
            target  = target_data["holdings"].get(ticker, 0)  or 0
            action  = derive_action(ticker, actual, target)
            emoji   = ACTION_EMOJI.get(action, "")
            act_str = f"{actual:.2f}%" if actual else "—"
            tgt_str = f"{target:.2f}%" if target else "—"
            
            # Fetch AI Signal
            proj_path = REPO_ROOT / f"investment_screener/backend/data/projections/{ticker}.json"
            ai_signal = "—"
            if proj_path.exists():
                try:
                    proj = load_json(proj_path)
                    ai_action = proj.get("aiThesis", {}).get("action")
                    if ai_action:
                        ai_signal = ai_action
                except Exception:
                    pass
            
            new_rows.append(f"| **{ticker}** | {emoji} {action} | {ai_signal} | {act_str} | {tgt_str} | {role} | {conviction} |")
        return new_header + new_sep + "\n".join(new_rows) + "\n"

    return table_pattern.sub(rebuild_table, content)


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
        md_path = Path(args.thesis_md)
        # 1. Load weights via validate_weights for accuracy
        sys.path.insert(0, str(Path(__file__).parent))
        from validate_weights import compute_current, compute_target
        current_data = compute_current(PORTFOLIO_JSON)
        target_data  = compute_target(THESIS_JSON)

        # 2. Update Section IV (blueprint)
        update_thesis_md(section, md_path)

        # 3. Enrich early section tables (Ticker | Role | Conviction Note) with live data
        content = md_path.read_text()
        updated = update_section_tables(content, current_data, target_data)
        md_path.write_text(updated)
        print(f"✅ Section tables enriched with live Action / Current % / Target %")
    else:
        print(section)


if __name__ == "__main__":
    main()
