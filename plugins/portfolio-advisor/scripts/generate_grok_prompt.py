#!/usr/bin/env python3
"""
generate_grok_prompt.py (Python Service)
=====================================

Purpose:
    Generates a structured, live news-sweep prompt for Grok/X.com based on the current portfolio and thesis.
    Synthesizes target weights, actual positions, and DCF signals to identify priority research areas.

Layer: Backend / Python Services / AI Prompt Engineering

Usage Examples:
    python3 generate_grok_prompt.py --clipboard
    python3 generate_grok_prompt.py --output grok_prompt.md

Key Functions:
    - build_prompt() - Primary orchestrator that aggregates thesis, portfolio, and DCF data into a formatted Markdown prompt
    - load_dcf() - Retrieves the latest AI-generated valuation signals for inclusion in the prompt context
    - _action_emoji() - Utility for visual status indicators in the generated prompt table
"""

import json
import sys
import argparse
import datetime
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parents[3]
THESIS_JSON = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
PORTFOLIO   = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
PROJ_DIR    = REPO_ROOT / "investment_screener/backend/data/projections"
ETF_ANALYSIS_DIR = REPO_ROOT / "investment_screener/backend/data/etf_analysis"

sys.path.insert(0, str(Path(__file__).parent))
from validate_weights import compute_current, compute_target
from portfolio_action import derive_action


def get_dynamic_exclusions():
    """Build exclusion list dynamically by scanning etf_analysis directory and cash reserves."""
    exclusions = {'USD_CASH', 'PSU-U.TO', 'PSU.U.TO'}
    if ETF_ANALYSIS_DIR.exists():
        for p in ETF_ANALYSIS_DIR.glob('*.json'):
            exclusions.add(p.stem.upper())
    return exclusions


def load_dcf(ticker: str) -> dict:
    """Return latest AI_AGENT DCF for ticker, or empty dict."""
    path = PROJ_DIR / f"{ticker}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        projs = data if isinstance(data, list) else [data]
        ai = [p for p in projs if p.get("source") == "AI_AGENT"]
        if not ai:
            return {}
        latest = max(ai, key=lambda x: x.get("savedAt", ""))
        th = latest.get("aiThesis", {})
        sn = latest.get("snapshot", {})
        fv = th.get("fairValue", 0)
        price = sn.get("price", 0)
        upside = round((fv - price) / price * 100, 1) if fv and price else None
        return {
            "action": th.get("action", ""),
            "fairValue": fv,
            "price": price,
            "upside": upside,
            "savedAt": latest.get("savedAt", "")[:10],
        }
    except Exception:
        return {}


def _dcf_label(dcf: dict) -> str:
    if not dcf:
        return "No DCF"
    u = dcf.get("upside")
    a = dcf.get("action", "")
    return f"{a} {u:+.0f}%" if u is not None else a


def _action_emoji(action: str) -> str:
    return {
        "EXIT":      "🔴 EXIT",
        "INITIATE":  "🟢 INITIATE",
        "ACCUMULATE":"🔵 ACCUMULATE",
        "TRIM":      "🟡 TRIM",
        "REVIEW":    "🟡 REVIEW",
        "MAINTAIN":  "⚪ MAINTAIN",
        "WATCHLIST": "⬜ WATCHLIST",
    }.get(action, action)


def build_prompt(date_str: str) -> str:
    thesis       = json.loads(THESIS_JSON.read_text())
    current_data = compute_current(PORTFOLIO)
    target_data  = compute_target(THESIS_JSON)

    holdings_map = {h["ticker"]: h for h in thesis.get("holdings", [])}
    exclusions = get_dynamic_exclusions()

    # Classify holdings into groups
    active_held   = []   # have actual position AND target > 0
    initiate_list = []   # target > 0, actual = 0
    exit_list     = []   # target = 0, actual > 0
    watchlist     = []   # both 0

    for ticker, h in list(holdings_map.items()):
        if ticker.upper() in exclusions:
            continue
        actual  = current_data["holdings"].get(ticker, 0)
        target  = target_data["holdings"].get(ticker, 0)
        action  = derive_action(ticker, actual, target)
        dcf     = load_dcf(ticker)
        role    = h.get("role", "core")
        pillar  = h.get("pillarId", "")

        breakers = h.get("thesisBreakers", [])
        if breakers:
            watch = breakers[0][:60]
        elif "DCF CONFLICT" in h.get("agentRationale", "") or "SA/DCF" in h.get("agentRationale", ""):
            watch = "SA/DCF conflict — monitor for resolution"
        else:
            watch = "Execution + earnings"

        row = dict(
            ticker=ticker,
            actual=round(actual, 2),
            target=round(target, 2),
            action=action,
            dcf=dcf,
            role=role,
            pillar=pillar,
            watch=watch,
            agentRationale=h.get("agentRationale", ""),
        )

        if action == "WATCHLIST":
            watchlist.append(row)
        elif target == 0 and actual > 0:
            exit_list.append(row)
        elif actual == 0 and target > 0:
            initiate_list.append(row)
        else:
            active_held.append(row)

    # Sort active by target desc
    active_held.sort(key=lambda x: -x["target"])
    initiate_list.sort(key=lambda x: -x["target"])
    exit_list.sort(key=lambda x: -x["actual"])

    thesis_name    = thesis.get("name", "Investment Thesis")
    portfolio_val  = thesis.get("globalSettings", {}).get("portfolioValueUSD", 0)

    template_path = REPO_ROOT / "plugins/portfolio-advisor/assets/templates/daily_sweep.md.template"
    template = template_path.read_text()

    # Sizing deep dive logic
    num_parts = 3 + (1 if initiate_list else 0)
    deep_dive_part = 3 if initiate_list else 2
    
    initiate_section = ""
    if initiate_list:
        initiate_section = """### Part 2 — INITIATE Target Deep Dives

For **every INITIATE target** below, provide 3–5 sentences: recent momentum, valuation context
(current EV/EBITDA or P/S vs. historical), thesis fit, key risks, and conviction on initiating now."""

    # Active holdings table
    active_rows = [
        "| Ticker | Actual% | Target% | Action | DCF Signal | Entry Price | Sizing context |",
        "|--------|---------|---------|--------|------------|-------------|----------------|"
    ]
    for r in active_held:
        dcf_label = _dcf_label(r["dcf"])
        gap = round(r["target"] - r["actual"], 1)
        sizing = "Near target"
        if gap > 1.0:
            sizing = f"Under by {gap:.1f}pp — room to add"
        elif gap < -1.0:
            sizing = f"Over by {abs(gap):.1f}pp — trim candidate"
        entry = holdings_map[r["ticker"]].get("targetEntryPrice")
        entry_label = f"${entry:,.0f}" if entry else "—"
        active_rows.append(
            f"| **{r['ticker']}** | {r['actual']:.1f}% | {r['target']:.1f}% "
            f"| {_action_emoji(r['action'])} | {dcf_label} | {entry_label} | {sizing} |"
        )
    active_table = "\n".join(active_rows)

    # Initiate holdings table
    initiate_holdings_section = ""
    if initiate_list:
        init_rows = [
            "## 🟢 INITIATE Targets (targeted but not yet purchased)",
            "",
            "| Ticker | Target% | DCF Signal | Note |",
            "|--------|---------|------------|------|"
        ]
        for r in initiate_list:
            dcf_label = _dcf_label(r["dcf"])
            init_rows.append(
                f"| **{r['ticker']}** | {r['target']:.1f}% | {dcf_label} "
                f"| Deep dive required — initiate now or wait? |"
            )
        initiate_holdings_section = "\n".join(init_rows)

    # Exit holdings table
    exit_holdings_section = ""
    if exit_list:
        exit_rows = [
            "## 🔴 EXIT Positions (still held, target = 0%)",
            "",
            "| Ticker | Actual% | DCF Signal | Reason |",
            "|--------|---------|------------|--------|"
        ]
        for r in exit_list:
            dcf_label = _dcf_label(r["dcf"])
            exit_rows.append(
                f"| **{r['ticker']}** | {r['actual']:.1f}% | {dcf_label} "
                f"| Flagged for exit — any positive reversal? |"
            )
        exit_holdings_section = "\n".join(exit_rows)

    # Replacements
    prompt = template
    prompt = prompt.replace("{{DATE}}", date_str)
    prompt = prompt.replace("{{THESIS_NAME}}", thesis_name)
    prompt = prompt.replace("{{PORTFOLIO_VALUE}}", f"{portfolio_val:,}")
    prompt = prompt.replace("{{NUM_PARTS}}", str(num_parts))
    prompt = prompt.replace("{{INITIATE_SECTION}}", initiate_section)
    prompt = prompt.replace("{{DEEP_DIVE_PART}}", str(deep_dive_part))
    prompt = prompt.replace("{{QUESTIONS_PART}}", str(deep_dive_part + 1))
    prompt = prompt.replace("{{ACTIVE_HOLDINGS_TABLE}}", active_table)
    prompt = prompt.replace("{{INITIATE_HOLDINGS_SECTION}}", initiate_holdings_section)
    prompt = prompt.replace("{{EXIT_HOLDINGS_SECTION}}", exit_holdings_section)

    # Add SA LP check and footer
    footer = f"""
---

## SA LP Cross-Check

Check for new **Situational Awareness LP** (Aschenbrenner fund) disclosures,
13F filings, or X posts. Q4 2025 top positions: INTC (calls), CRWV (calls + common),
CORZ, BE, LITE, SNDK, PSIX, IREN. Flag any changes that conflict with or reinforce the portfolio.

---

## Output Format

Structure your response as Part 1 → Part {deep_dive_part + 1}.
Prioritize signal over completeness — if nothing material happened for a ticker, one line is enough.
Flag SA/DCF conflicts and valuation stretches explicitly.

_Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} from {thesis_name}_
"""
    return prompt + footer



def main():
    parser = argparse.ArgumentParser(description="Generate a Grok X.com portfolio sweep prompt.")
    parser.add_argument("--date", default=datetime.date.today().isoformat(),
                        help="Sweep date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--output", help="Write prompt to this file path instead of stdout.")
    parser.add_argument("--clipboard", action="store_true",
                        help="Copy output to macOS clipboard (requires pbcopy).")
    args = parser.parse_args()

    prompt = build_prompt(args.date)

    if args.output:
        Path(args.output).write_text(prompt + "\n")
        print(f"✅ Prompt written to {args.output}")
    elif args.clipboard:
        import subprocess
        subprocess.run(["pbcopy"], input=prompt.encode(), check=True)
        lines = prompt.count("\n") + 1
        print(f"✅ Prompt copied to clipboard ({lines} lines)")
        print("→ Paste into x.com/i/grok and send")
    else:
        print(prompt)


if __name__ == "__main__":
    main()
