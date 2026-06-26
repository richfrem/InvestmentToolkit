#!/usr/bin/env python3
"""
generate_portfolio_blueprint.py (Python Service)
=====================================

Purpose:
    Generates the "Portfolio Blueprint" section (Section IV) for the investment thesis document.
    Synthesizes target-portfolio.json (thesis targets) with portfolio.json (live holdings) to 
    produce an enriched, data-driven Markdown table grouped by sub-strategy.

Layer: Backend / Python Services / Report Generation

Usage Examples:
    # Preview section in stdout (dry-run)
    python3 generate_portfolio_blueprint.py

    # Update investment_thesis.md in-place
    python3 generate_portfolio_blueprint.py --write

    # Specify a custom thesis JSON file
    python3 generate_portfolio_blueprint.py --write --thesis-json data/theses/target-portfolio.json

Key Functions:
    - generate_section() - Constructs the primary Section IV Markdown content with live performance metrics
    - update_section_tables() - Rigorously scans the entire thesis document to enrich legacy tables with live data
    - build_actual_map() / build_thesis_map() - Normalize disparate data sources into unified maps for aggregation
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

THESIS_JSON   = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
PORTFOLIO_JSON = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
THESIS_MD     = REPO_ROOT / "investment_screener/backend/data/theses/investment_thesis.md"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from ticker_aliases import is_cash  # noqa: E402
from portfolio_io import load_portfolio_state, replace_block  # noqa: E402

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


def build_actual_map(portfolio: dict | list) -> tuple[dict, float]:
    """Build actual-position map from portfolio.json.

    Uses load_portfolio_state() so the total comes from totals.totalUSD
    (broker authoritative), never computed from shares×price.
    """
    import tempfile
    # Accept both list and dict; write to tmp for load_portfolio_state
    if isinstance(portfolio, list):
        data = portfolio
        total_ref: dict = {}
    else:
        data = portfolio.get("holdings", [])
        total_ref = portfolio.get("totals") or {}

    # Use portfolio_io for safe total resolution
    tmp = Path(tempfile.mktemp(suffix=".json"))
    tmp.write_text(json.dumps({"holdings": data, "totals": total_ref}))
    try:
        state = load_portfolio_state(tmp)
    finally:
        tmp.unlink(missing_ok=True)

    total = state["total_usd"]
    actual: dict = {}
    for h in data:
        sym = h.get("symbol") or h.get("ticker", "")
        if not sym:
            continue
        shares = float(h.get("shares") or 0)
        price  = float(h.get("price") or h.get("book_price") or 0)
        val    = shares * price
        actual[sym] = {
            "shares":    shares,
            "price":     price,
            "book":      float(h.get("book_price") or 0),
            "value":     round(val, 2),
            "actualPct": round(val / total * 100, 2) if total else 0,
            "name":      h.get("name", sym),
        }
    return actual, total


def build_thesis_map(thesis: dict) -> dict:
    """Returns {ticker: {subStrategyId, targetPct, role, thesisNote, thesisBreakers}}"""
    holdings = {}
    for h in thesis.get("holdings", []):
        ticker = h["ticker"]
        sid = h.get("subStrategyId", h.get("pillarId", "untracked"))
        # Map sub-strategies to avoid orphan sections or omissions
        if sid in ("preipo-access", "quantum-compute", "frontier-bets"):
            sid = "frontier-bets"
        elif sid == "other":
            sid = "untracked"
        
        holdings[ticker] = {
            "subStrategyId": sid,
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
    untracked = [s for s in actual_map if s not in thesis_map and not is_cash(s)]
    if untracked:
        groups.setdefault("untracked", []).extend(untracked)

    lines = []
    # Note: the "## IV. Portfolio Blueprint" header lives OUTSIDE the AUTO_UPDATE block.
    # generate_section() outputs only the block BODY so replace_block() can insert it cleanly.
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
    """Replace AUTO_UPDATE block in investment_thesis.md with regenerated content.

    Uses replace_block() so only the content between delimiters is touched.
    The '## IV. Portfolio Blueprint' header lives outside the block and is preserved.
    """
    content = path.read_text()
    updated = replace_block(content, "portfolio_blueprint", new_section)
    path.write_text(updated)
    print(f"✅ Updated Section IV: {path}")


def update_section_tables(content: str, current_data: dict, target_data: dict) -> str:
    """
    Find every holding table in the thesis — whether in the original 3-column format
    (| Ticker | Role | Conviction Note |) or the already-enriched 7-column format
    (| Ticker | Thesis Action | AI Signal | Actual % | Target % | Role | Conviction Note |)
    — and rebuild it with fresh live data.

    This runs on every --write call so the tables never go stale.
    """
    # Pattern 1: original 3-column format (first-time enrichment)
    pattern_3col = re.compile(
        r"(\| Ticker \| Role \| Conviction Note \|\n\| :--- \| :--- \| :--- \|\n)((?:\|[^\n]+\|\n?)+)",
        re.IGNORECASE
    )
    # Pattern 2: already-enriched 7-column format (re-enrichment on subsequent runs)
    pattern_7col = re.compile(
        r"(\| Ticker \| Thesis Action \| AI Signal \| Actual % \| Target % \| Role \| Conviction Note \|\n\| :--- \| :--- \| :--- \| ---: \| ---: \| :--- \| :--- \|\n)((?:\|[^\n]+\|\n?)+)",
        re.IGNORECASE
    )

    def get_ai_signal(ticker: str) -> str:
        proj_path = REPO_ROOT / f"investment_screener/backend/data/projections/{ticker}.json"
        if proj_path.exists():
            try:
                proj = load_json(proj_path)
                projs = proj if isinstance(proj, list) else [proj]
                ai = [p for p in projs if p.get("source") == "AI_AGENT"]
                if ai:
                    latest = max(ai, key=lambda x: x.get("savedAt", ""))
                    action = latest.get("aiThesis", {}).get("action")
                    if action:
                        return action
            except Exception:
                pass
        return "—"

    def build_enriched_row(ticker: str, role: str, conviction: str) -> str:
        # Strip bold markers for lookup
        t = ticker.strip("* ")
        actual  = current_data["holdings"].get(t, 0) or 0
        target  = target_data["holdings"].get(t, 0)  or 0
        action  = derive_action(t, actual, target)
        emoji   = ACTION_EMOJI.get(action, "")
        act_str = f"{actual:.2f}%" if actual else "—"
        tgt_str = f"{target:.2f}%" if target else "—"
        ai_sig  = get_ai_signal(t)
        return f"| **{t}** | {emoji} {action} | {ai_sig} | {act_str} | {tgt_str} | {role} | {conviction} |"

    new_header = "| Ticker | Thesis Action | AI Signal | Actual % | Target % | Role | Conviction Note |\n"
    new_sep    = "| :--- | :--- | :--- | ---: | ---: | :--- | :--- |\n"

    def rebuild_from_3col(m: re.Match) -> str:
        new_rows = []
        for line in m.group(2).splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) < 3:
                continue
            ticker, role, conviction = parts[0], parts[1], "|".join(parts[2:]).strip()
            new_rows.append(build_enriched_row(ticker, role, conviction))
        return new_header + new_sep + "\n".join(new_rows) + "\n"

    def rebuild_from_7col(m: re.Match) -> str:
        new_rows = []
        for line in m.group(2).splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) < 7:
                continue
            # 7-col layout: ticker | thesis_action | ai_signal | actual | target | role | conviction
            ticker, role, conviction = parts[0], parts[5], parts[6]
            new_rows.append(build_enriched_row(ticker, role, conviction))
        return new_header + new_sep + "\n".join(new_rows) + "\n"

    # Pattern 3: 6-column live format used in early thesis sections
    # Header: | Ticker | Action | Current % | Target % | Role | Conviction Note |
    pattern_6col = re.compile(
        r"(\| Ticker \| Action \| Current % \| Target % \| Role \| Conviction Note \|\n\| :--- \| :--- \| ---: \| ---: \| :--- \| :--- \|\n)((?:\|[^\n]+\|\n?)+)",
        re.IGNORECASE
    )

    def rebuild_from_6col(m: re.Match) -> str:
        header_6 = "| Ticker | Action | Current % | Target % | Role | Conviction Note |\n"
        sep_6    = "| :--- | :--- | ---: | ---: | :--- | :--- |\n"
        new_rows = []
        for line in m.group(2).splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) < 6:
                continue
            # layout: ticker | action | current | target | role | conviction
            ticker_raw, role, conviction = parts[0], parts[4], parts[5]
            t = ticker_raw.strip("* ")
            actual  = current_data["holdings"].get(t, 0) or 0
            target  = target_data["holdings"].get(t, 0)  or 0
            action  = derive_action(t, actual, target)
            emoji   = ACTION_EMOJI.get(action, "")
            act_str = f"{actual:.2f}%" if actual else "—"
            tgt_str = f"{target:.2f}%" if target else "—"
            new_rows.append(f"| **{t}** | {emoji} {action} | {act_str} | {tgt_str} | {role} | {conviction} |")
        return header_6 + sep_6 + "\n".join(new_rows) + "\n"

    content = pattern_6col.sub(rebuild_from_6col, content)
    content = pattern_7col.sub(rebuild_from_7col, content)
    content = pattern_3col.sub(rebuild_from_3col, content)
    return content


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

        # 3. Enrich early section tables with live data
        content = md_path.read_text()
        updated = update_section_tables(content, current_data, target_data)

        # 4. Sync header metadata from target-portfolio.json
        import datetime
        thesis_meta = load_json(THESIS_JSON)
        thesis_version = thesis_meta.get("name", "Investment Thesis")
        today = datetime.date.today().isoformat()

        # Find latest review file
        reviews_dir = REPO_ROOT / "PortfolioAnalysis" / "strategic-reviews"
        latest_review = ""
        if reviews_dir.exists():
            review_files = sorted(
                [f.name for f in reviews_dir.iterdir()
                 if f.suffix == ".md" and f.name[0].isdigit()],
                reverse=True
            )
            if review_files:
                latest_review = f"PortfolioAnalysis/strategic-reviews/{review_files[0]}"

        # Update title line
        updated = re.sub(r"^# Investment Thesis v[\d.]+", f"# {thesis_version}", updated, count=1, flags=re.MULTILINE)
        # Update Last Updated field
        updated = re.sub(r"(\| \*\*Last Updated\*\* \| )[\d-]+", rf"\g<1>{today}", updated)
        # Update Latest Review field
        if latest_review:
            updated = re.sub(r"(\| \*\*Latest Review\*\* \| )`[^`]+`", rf"\1`{latest_review}`", updated)

        md_path.write_text(updated)
        print(f"✅ Section tables enriched with live Action / Current % / Target %")
        print(f"✅ Header synced: {thesis_version} · Last Updated {today}")

        # 5. Regenerate current_positions blocks in all sub-strategy .md files
        print("\n── Updating sub-strategy current_positions blocks ──")
        sys.path.insert(0, str(Path(__file__).parent))
        from generate_sub_strategy_blocks import run as run_sub_blocks
        run_sub_blocks(Path(args.portfolio), Path(args.thesis_json))
    else:
        print(section)


if __name__ == "__main__":
    main()
