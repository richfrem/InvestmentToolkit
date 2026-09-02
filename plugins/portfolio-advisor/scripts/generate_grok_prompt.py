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

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (portfolio + thesis
      source of truth)
"""

import json
import sys
import argparse
import datetime
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parents[3]
DB_PATH     = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"
ETF_ANALYSIS_DIR = REPO_ROOT / "investment_screener/backend/data/etf_analysis"

sys.path.insert(0, str(Path(__file__).parent))
from portfolio_action import derive_action

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.projection_repository import get_latest_projection_by_source  # noqa: E402
from portfolio_io import load_portfolio_state, compute_weights, load_thesis_holdings  # noqa: E402


def _compute_current_from_db() -> dict:
    """Wave 3 replacement for validate_weights.compute_current(PORTFOLIO).

    Sources actual holdings from domain_model.sqlite via
    portfolio_io.load_portfolio_state() + compute_weights() (ADR-030), returning
    the same {"holdings": {ticker: pct}} shape the old compute_current() did.
    """
    state = load_portfolio_state(None)
    holdings = compute_weights(state["shares"], state["prices"], state["total_usd"])
    return {"total": round(sum(holdings.values()), 4), "holdings": holdings,
            "total_value": state["total_usd"]}


def get_dynamic_exclusions():
    """Build exclusion list dynamically by scanning etf_analysis directory and cash reserves."""
    exclusions = {'USD_CASH', 'PSU-U.TO', 'PSU.U.TO'}
    if ETF_ANALYSIS_DIR.exists():
        for p in ETF_ANALYSIS_DIR.glob('*.json'):
            exclusions.add(p.stem.upper())
    return exclusions


def load_dcf(ticker: str, db_path: Path | None = None) -> dict:
    """Return latest AI_AGENT DCF for ticker, or empty dict.

    Storage backend (Wave 1 Task 7B): reads `projection_version` via
    `domain_model.projection_repository`, not `projections/{TICKER}.json`
    directly (ADR-029). The original code filtered strictly by
    `source == "AI_AGENT"` with no fallback to other sources, so this uses
    `get_latest_projection_by_source` only.
    """
    conn = initialize_db(str(db_path or DB_PATH))
    try:
        row = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", (ticker,)
        ).fetchone()
        if row is None:
            return {}
        latest = get_latest_projection_by_source(conn, row[0], "AI_AGENT")
        if latest is None:
            return {}
        snapshot = json.loads(latest["snapshot_json"]) if latest.get("snapshot_json") else {}
        fv = latest.get("fair_value") or 0
        price = snapshot.get("price") or 0
        upside = round((fv - price) / price * 100, 1) if fv and price else None

        # Load projection scenarios and key risks for deep model intelligence
        scenarios_rows = conn.execute(
            """
            SELECT scenario_name, rationale, risks_json 
            FROM projection_scenario 
            WHERE projection_id = ?
            ORDER BY CASE scenario_name WHEN 'bear' THEN 1 WHEN 'base' THEN 2 WHEN 'bull' THEN 3 ELSE 4 END;
            """,
            (latest["projection_id"],)
        ).fetchall()

        scenarios_info = {}
        for s_name, s_rat, s_risks_raw in scenarios_rows:
            risks_list = []
            if s_risks_raw:
                try:
                    risks_list = json.loads(s_risks_raw)
                except Exception:
                    risks_list = [s_risks_raw]
            scenarios_info[s_name] = {
                "rationale": s_rat,
                "risks": risks_list
            }

        return {
            "action": latest.get("action", ""),
            "fairValue": fv,
            "price": price,
            "upside": upside,
            "savedAt": (latest.get("saved_at") or "")[:10],
            "scenarios": scenarios_info
        }
    except Exception:
        return {}
    finally:
        conn.close()


def _clean_markdown_text(text: str, max_chars: int = 120) -> str:
    """Normalize whitespace, sanitize markdown pipe characters, and truncate safely."""
    if not text:
        return ""
    cleaned = " ".join(str(text).split()).replace("|", "/")
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars - 1].rsplit(" ", 1)[0] + "…"


def derive_targeted_inquiry(ticker: str, holding: dict, dcf: dict) -> str:
    """Generate a targeted, model-informed inquiry pressure point for Grok to investigate."""
    inquiries = []
    try:
        # 1. Check for specific SA / DCF conflicts or agent rationale
        rationale = holding.get("agentRationale", "")
        if "DCF CONFLICT" in rationale or "SA/DCF" in rationale:
            inquiries.append("SA/DCF conflict: probe smart money / LP updates vs margin sustainability")
        elif holding.get("standingDecisionReason"):
            inquiries.append(f"Anchor thesis: {_clean_markdown_text(holding['standingDecisionReason'], 100)}")

        # 2. Extract Bear / Base case key risks from DCF scenarios
        scenarios = dcf.get("scenarios", {})
        bear_risks = scenarios.get("bear", {}).get("risks", []) if isinstance(scenarios, dict) else []
        base_risks = scenarios.get("base", {}).get("risks", []) if isinstance(scenarios, dict) else []

        def _first_risk_str(risks) -> str | None:
            if isinstance(risks, list) and risks:
                first = risks[0]
                if isinstance(first, str):
                    return _clean_markdown_text(first, 120)
                elif isinstance(first, dict):
                    return _clean_markdown_text(first.get("risk") or first.get("description") or str(first), 120)
            return None

        bear_risk_first = _first_risk_str(bear_risks)
        base_risk_first = _first_risk_str(base_risks)

        if bear_risk_first:
            inquiries.append(f"Bear risk to probe: {bear_risk_first}")
        elif base_risk_first:
            inquiries.append(f"Execution risk: {base_risk_first}")
        elif holding.get("thesisForInclusion"):
            inquiries.append(f"Verify thesis: {_clean_markdown_text(holding['thesisForInclusion'], 100)}")
        else:
            inquiries.append("Verify customer concentration, contract execution & guidance shifts")
    except Exception:
        inquiries = ["Verify customer concentration, contract execution & guidance shifts"]

    return " | ".join(inquiries)


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
    holdings_list = load_thesis_holdings(str(DB_PATH))
    current_data  = _compute_current_from_db()

    holdings_map = {h["ticker"]: h for h in holdings_list}
    target_data = {"holdings": {h["ticker"]: h["targetWeight"] for h in holdings_list}}
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
        role    = h.get("role", "watchlist")
        pillar  = h.get("pillarId", "")

        targeted_inquiry = derive_targeted_inquiry(ticker, h, dcf)

        if "DCF CONFLICT" in h.get("agentRationale", "") or "SA/DCF" in h.get("agentRationale", ""):
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
            targetedInquiry=targeted_inquiry,
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

    thesis_name    = "Investment Thesis"
    portfolio_val  = current_data["total_value"]

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
        "| Ticker | Actual% | Target% | Action | DCF Signal | Entry Price | Sizing context | Targeted Inquiries & Key Thesis Vulnerabilities |",
        "|--------|---------|---------|--------|------------|-------------|----------------|------------------------------------------------|"
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
            f"| {_action_emoji(r['action'])} | {dcf_label} | {entry_label} | {sizing} | {r['targetedInquiry']} |"
        )
    active_table = "\n".join(active_rows)

    # Initiate holdings table
    initiate_holdings_section = ""
    if initiate_list:
        init_rows = [
            "## 🟢 INITIATE Targets (targeted but not yet purchased)",
            "",
            "| Ticker | Target% | DCF Signal | Targeted Thesis Inquiries & Catalyst Gates |",
            "|--------|---------|------------|--------------------------------------------|"
        ]
        for r in initiate_list:
            dcf_label = _dcf_label(r["dcf"])
            init_rows.append(
                f"| **{r['ticker']}** | {r['target']:.1f}% | {dcf_label} "
                f"| {r['targetedInquiry']} |"
            )
        initiate_holdings_section = "\n".join(init_rows)

    # Exit holdings table
    exit_holdings_section = ""
    if exit_list:
        exit_rows = [
            "## 🔴 EXIT Positions (still held, target = 0%)",
            "",
            "| Ticker | Actual% | DCF Signal | Exit Reason & Reversal Watch |",
            "|--------|---------|------------|------------------------------|"
        ]
        for r in exit_list:
            dcf_label = _dcf_label(r["dcf"])
            exit_rows.append(
                f"| **{r['ticker']}** | {r['actual']:.1f}% | {dcf_label} "
                f"| Flagged for exit — {r['targetedInquiry']} |"
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
    parser.add_argument("--output", default=str(REPO_ROOT / "temp/grok-prompts/daily_grok_prompt.md"),
                        help="Write prompt to this file path instead of stdout.")
    parser.add_argument("--clipboard", action="store_true",
                        help="Copy output to macOS clipboard (requires pbcopy).")
    args = parser.parse_args()

    prompt = build_prompt(args.date)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(prompt + "\n")
        print(f"✅ Prompt written to {args.output}")

        # Create daily response placeholder
        placeholder_path = REPO_ROOT / f"temp/news-sweep-responses/grok/daily-{datetime.datetime.now().strftime('%b%d-%Y').lower()}.md"
        placeholder_path.parent.mkdir(parents=True, exist_ok=True)
        if not placeholder_path.exists():
            placeholder_path.write_text(f"# Grok Daily Sweep Response — {datetime.datetime.now().strftime('%Y-%m-%d')}\n\nPlease paste the raw Grok response below:\n\n---\n")
            print(f"[Response Placeholder Created at {placeholder_path}]")
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
