#!/usr/bin/env python3
"""
generate_grok_prompt.py — Build a live Grok/X.com news-sweep prompt from
target-portfolio.json and portfolio.json.

Each run reflects the *current* targets, actions, and DCF signals — no stale
ticker lists or copy-paste drift.

Usage (run from repo root):
    python3 plugins/portfolio-advisor/scripts/generate_grok_prompt.py
    python3 plugins/portfolio-advisor/scripts/generate_grok_prompt.py --output /tmp/grok_prompt.md
    python3 plugins/portfolio-advisor/scripts/generate_grok_prompt.py --clipboard

Output:
    A structured Grok prompt ready to paste into x.com/i/grok
    Optionally written to --output path or copied to clipboard.
"""

import json
import sys
import argparse
import datetime
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parents[3]
THESIS_JSON = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
PORTFOLIO   = REPO_ROOT / "investment_screener/frontend/src/data/portfolio.json"
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
    lines.append(f"# Portfolio X.com / Grok News Sweep — {date_str}")
    lines.append(f"**Thesis:** {thesis_name}  |  **Portfolio value:** ~${portfolio_val:,}  |  **Date:** {date_str}")
    lines.append("")
    lines.append("You are reviewing a concentrated AI/ASI infrastructure portfolio.")
    lines.append("Search X.com (recent posts, news, earnings, filings, analyst notes) for the")
    lines.append("latest on **each ticker listed below**. For every position return:")
    lines.append("")
    lines.append("1. **News** — Any material development in the last 7 days")
    lines.append("2. **Thesis Impact** — Strengthened / Weakened / Unchanged")
    lines.append("3. **Action** — Accumulate / Trim / Exit / Initiate / Maintain")
    lines.append("4. **Target Change** — Specific % recommendation or 'no change'")
    lines.append("")
    lines.append("Output as a structured markdown table:")
    lines.append("| Ticker | Current% | Target% | News | Thesis Impact | Action | Target Change |")
    lines.append("|--------|----------|---------|------|---------------|--------|---------------|")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Active held positions ──────────────────────────────────────────────
    lines.append("## 🔵 Active Holdings (currently owned + targeted)")
    lines.append("")
    lines.append("| Ticker | Actual% | Target% | Action | DCF Signal | Watch For |")
    lines.append("|--------|---------|---------|--------|------------|-----------|")
    for r in active_held:
        dcf_label = _dcf_label(r["dcf"])
        watch = r["watch"]
        lines.append(
            f"| **{r['ticker']}** | {r['actual']:.1f}% | {r['target']:.1f}% "
            f"| {_action_emoji(r['action'])} | {dcf_label} | {watch} |"
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
                f"| Confirm still want to initiate |"
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
                f"| Flagged for exit — check for any positive reversal |"
            )
        lines.append("")

    # ── SA LP cross-check ──────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## SA LP Cross-Check")
    lines.append("")
    lines.append("Also check: any new **Situational Awareness LP** (Aschenbrenner fund) disclosures,")
    lines.append("13F filings, or position changes posted on X. Their top Q4 2025 positions were:")
    lines.append("INTC (calls), CRWV (calls + common), CORZ, BE, LITE, SNDK, PSIX, IREN.")
    lines.append("Flag any position changes that conflict with or reinforce the portfolio above.")
    lines.append("")

    # ── Instructions ──────────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## Output Instructions")
    lines.append("")
    lines.append("Return a **single structured table** with all active holdings + initiates + exits.")
    lines.append("Prioritize: tier-1 contract wins, earnings surprises, regulatory events, thesis breakers.")
    lines.append("Flag SA/DCF conflicts explicitly (where the news supports one but not the other).")
    lines.append("For each target change, give a specific % (e.g., '↑ to 5.5%') not just 'add more'.")
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
