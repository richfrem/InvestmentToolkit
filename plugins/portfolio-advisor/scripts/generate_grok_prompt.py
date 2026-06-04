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

sys.path.insert(0, str(Path(__file__).parent))
from validate_weights import compute_current, compute_target
from portfolio_action import derive_action


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

    # Classify holdings into groups
    active_held   = []   # have actual position AND target > 0
    initiate_list = []   # target > 0, actual = 0
    exit_list     = []   # target = 0, actual > 0
    watchlist     = []   # both 0

    for ticker, h in holdings_map.items():
        actual  = current_data["holdings"].get(ticker, 0)
        target  = target_data["holdings"].get(ticker, 0)
        action  = derive_action(ticker, actual, target)
        dcf     = load_dcf(ticker)
        role    = h.get("role", "core")
        pillar  = h.get("pillarId", "")

        # Build watch-for string from thesisBreakers (first one) or agentRationale hint
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

    lines = []
    lines.append(f"# Portfolio News Sweep — {date_str}")
    lines.append(f"**Thesis:** {thesis_name}  |  **Portfolio value:** ~${portfolio_val:,}  |  **Date:** {date_str}")
    lines.append("")
    lines.append("You are reviewing a concentrated AI/ASI infrastructure portfolio.")
    lines.append("Search X posts, earnings releases, filings, and analyst notes for **material updates only**")
    lines.append("from the **last 7–14 days**. Skip filler — only report developments that change conviction,")
    lines.append("sizing, or thesis alignment. Flag SA LP (Situational Awareness LP / Aschenbrenner fund) moves.")
    lines.append("")

    num_parts = 3 + (1 if initiate_list else 0)
    lines.append(f"Return your response in **{num_parts} parts**:")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Part 1 header ─────────────────────────────────────────────────────
    lines.append("### Part 1 — Sweep Table (every position)")
    lines.append("")
    lines.append("| Ticker | Current% | Target% | Key Catalyst/News (last 7–14 days) | Thesis Impact | Conviction (1–10) | Action | Target Change | Entry Price | Deep Dive? |")
    lines.append("|--------|----------|---------|------------------------------------|---------------|-------------------|--------|---------------|-------------|------------|")
    lines.append("")
    lines.append("**Conviction scale**: 1–3 = bearish / thesis challenged, 4–6 = neutral / hold, 7–10 = high conviction / add.")
    lines.append("**Entry Price**: for any ACCUMULATE/INITIATE action, suggest a GTC limit buy price (support level or DCF-based).")
    lines.append("Mark `[DD]` only for: earnings beat/miss >10%, major contract, regulatory shift, SA LP position change, or thesis breaker.")
    lines.append("For target changes give a specific % (e.g. `↑ to 5.5%`) — not just 'add more'.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Part 2 — INITIATE (only when targets exist) ───────────────────────
    if initiate_list:
        lines.append("### Part 2 — INITIATE Target Deep Dives")
        lines.append("")
        lines.append("For **every INITIATE target** below, provide 3–5 sentences: recent momentum, valuation context")
        lines.append("(current EV/EBITDA or P/S vs. historical), thesis fit, key risks, and conviction on initiating now.")
        lines.append("")
        lines.append("---")
        lines.append("")
        deep_dive_part = 3
    else:
        deep_dive_part = 2

    # ── Deep dives header ─────────────────────────────────────────────────
    lines.append(f"### Part {deep_dive_part} — Active Holdings Deep Dives (only [DD]-flagged)")
    lines.append("")
    lines.append("For each `[DD]` position: catalyst + thesis impact + conviction change + sizing recommendation.")
    lines.append("Include current valuation context (price vs. analyst PT range) where available.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Portfolio-level questions (always Part last) ──────────────────────
    lines.append(f"### Part {deep_dive_part + 1} — Portfolio-Level Questions")
    lines.append("")
    lines.append("Answer these for the portfolio as a whole:")
    lines.append("")
    lines.append("1. **Biggest risk right now** — what single development could most damage this portfolio?")
    lines.append("2. **Most mispriced position** — which holding looks most over- or under-valued vs. current thesis?")
    lines.append("3. **Top trim / add priorities this month** — 2–3 highest-conviction actions.")
    lines.append("4. **Macro pulse** — any developments in AI capex trends, power capacity, or rate sensitivity")
    lines.append("   that materially affect this portfolio's positioning?")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Active held positions ──────────────────────────────────────────────
    lines.append("## 🔵 Active Holdings (currently owned + targeted)")
    lines.append("")
    lines.append("| Ticker | Actual% | Target% | Action | DCF Signal | Entry Price | Sizing context |")
    lines.append("|--------|---------|---------|--------|------------|-------------|----------------|")
    for r in active_held:
        dcf_label = _dcf_label(r["dcf"])
        gap = round(r["target"] - r["actual"], 1)
        if gap > 1.0:
            sizing = f"Under by {gap:.1f}pp — room to add"
        elif gap < -1.0:
            sizing = f"Over by {abs(gap):.1f}pp — trim candidate"
        else:
            sizing = "Near target"
        entry = holdings_map[r["ticker"]].get("targetEntryPrice")
        entry_label = f"${entry:,.0f}" if entry else "—"
        lines.append(
            f"| **{r['ticker']}** | {r['actual']:.1f}% | {r['target']:.1f}% "
            f"| {_action_emoji(r['action'])} | {dcf_label} | {entry_label} | {sizing} |"
        )
    lines.append("")

    # ── Initiate targets ──────────────────────────────────────────────────
    if initiate_list:
        lines.append("## 🟢 INITIATE Targets (targeted but not yet purchased)")
        lines.append("")
        lines.append("| Ticker | Target% | DCF Signal | Note |")
        lines.append("|--------|---------|------------|------|")
        for r in initiate_list:
            dcf_label = _dcf_label(r["dcf"])
            lines.append(
                f"| **{r['ticker']}** | {r['target']:.1f}% | {dcf_label} "
                f"| Deep dive required — initiate now or wait? |"
            )
        lines.append("")

    # ── Exit positions ──────────────────────────────────────────────────
    if exit_list:
        lines.append("## 🔴 EXIT Positions (still held, target = 0%)")
        lines.append("")
        lines.append("| Ticker | Actual% | DCF Signal | Reason |")
        lines.append("|--------|---------|------------|--------|")
        for r in exit_list:
            dcf_label = _dcf_label(r["dcf"])
            lines.append(
                f"| **{r['ticker']}** | {r['actual']:.1f}% | {dcf_label} "
                f"| Flagged for exit — any positive reversal? |"
            )
        lines.append("")

    # ── SA LP cross-check ─────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## SA LP Cross-Check")
    lines.append("")
    lines.append("Check for new **Situational Awareness LP** (Aschenbrenner fund) disclosures,")
    lines.append("13F filings, or X posts. Q4 2025 top positions: INTC (calls), CRWV (calls + common),")
    lines.append("CORZ, BE, LITE, SNDK, PSIX, IREN. Flag any changes that conflict with or reinforce the portfolio.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Output Format")
    lines.append("")
    lines.append(f"Structure your response as Part 1 → Part {deep_dive_part + 1}.")
    lines.append("Prioritize signal over completeness — if nothing material happened for a ticker, one line is enough.")
    lines.append("Flag SA/DCF conflicts and valuation stretches explicitly.")
    lines.append("")
    lines.append(f"_Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} from {thesis_name}_")

    return "\n".join(lines)


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
