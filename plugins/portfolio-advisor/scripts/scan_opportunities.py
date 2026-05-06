#!/usr/bin/env python3
"""
scan_opportunities.py — Phase 1 data engine for /strategic-review.

Scans ALL projection files in the corpus, cross-references against live portfolio
and thesis targets, then outputs ranked tables for every action category:

  EXIT       — held positions with thesis target=0% (ranked by $ capital locked)
  SELL/TRIM  — held positions where DCF fair value < current price (ranked by downside)
  INITIATE   — unowned positions where DCF rates BUY/INITIATE (ranked by upside × confidence)
  ACCUMULATE — held but underweight vs thesis target, DCF agrees
  CONFLICTS  — held core positions where thesis says HOLD but DCF says SELL
  STALE      — analyses older than 90 days that need a refresh before acting

Output modes:
  --format markdown   Rich markdown tables (default) → paste into review file
  --format json       Machine-readable JSON → for other scripts to consume
  --format summary    One-paragraph executive summary

Usage (from repo root):
  python3 plugins/portfolio-advisor/scripts/scan_opportunities.py
  python3 plugins/portfolio-advisor/scripts/scan_opportunities.py --format json
  python3 plugins/portfolio-advisor/scripts/scan_opportunities.py --top 10 --format markdown
  python3 plugins/portfolio-advisor/scripts/scan_opportunities.py --category initiate
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

# ── Repo paths ──────────────────────────────────────────────────────────────────
REPO_ROOT      = Path(__file__).resolve().parents[3]
PORTFOLIO_PATH = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
THESIS_PATH    = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
PROJECTIONS    = REPO_ROOT / "investment_screener/backend/data/projections"
STALE_DAYS     = 90


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict | list:
    with open(path) as f:
        return json.load(f)


def load_portfolio(path: Path) -> dict:
    """Returns {TICKER: {shares, price, value, actualPct, bookPL}}"""
    raw = load_json(path)
    total = sum(h.get("shares", 0) * h.get("price", 0) for h in raw)
    out = {}
    for h in raw:
        ticker = h.get("symbol") or h.get("ticker", "")
        if not ticker or ticker == "USD_CASH":
            continue
        shares = h.get("shares", 0)
        price  = h.get("price", 0)
        value  = shares * price
        out[ticker] = {
            "shares":    shares,
            "price":     price,
            "value":     round(value, 2),
            "actualPct": round(value / total * 100, 2) if total else 0,
            "bookPL":    h.get("bookPL") or h.get("bookPl") or h.get("book_pl"),
            "currency":  h.get("currency", "USD"),
        }
    # Also store cash
    cash = next((h for h in raw if (h.get("symbol") or h.get("ticker","")) == "USD_CASH"), None)
    cash_value = cash.get("shares", 0) * cash.get("price", 1) if cash else 0
    out["_meta"] = {
        "totalValue": round(total, 2),
        "cashValue":  round(cash_value, 2),
        "cashPct":    round(cash_value / total * 100, 2) if total else 0,
    }
    return out


def load_thesis(path: Path) -> dict:
    """Returns {TICKER: {targetPct, pillarName, pillarId, thesisFor}}"""
    if not path.exists():
        return {}
    raw = load_json(path)
    out = {}
    
    # Map pillar IDs to names
    pillar_names = {}
    for pillar in raw.get("pillars", []):
        if "id" in pillar and "name" in pillar:
            pillar_names[pillar["id"]] = pillar["name"]
            
    for h in raw.get("holdings", []):
        ticker = h.get("ticker", "")
        if not ticker:
            continue
        pillar_id = h.get("pillarId", "")
        out[ticker] = {
            "targetPct":  h.get("targetWeight", 0),
            "pillarName": pillar_names.get(pillar_id, "Unclassified"),
            "pillarId":   pillar_id,
            "thesisFor":  h.get("thesisForInclusion", ""),
            "role":       h.get("role", ""),
        }
    return out


def load_projection(ticker: str) -> dict | None:
    """Load the most recent AI_AGENT projection for a ticker. Returns None if absent."""
    path = PROJECTIONS / f"{ticker}.json"
    if not path.exists():
        return None
    try:
        projections = load_json(path)
        ai = [p for p in projections if p.get("source") == "AI_AGENT"]
        if not ai:
            return None
        return max(ai, key=lambda x: x.get("savedAt", ""))
    except Exception:
        return None


def _days_old(date_str: str) -> int:
    if not date_str:
        return 999
    try:
        d = datetime.date.fromisoformat(date_str[:10])
        return (datetime.date.today() - d).days
    except Exception:
        return 999


def _proj_fields(proj: dict) -> dict:
    """Extract key fields from a projection entry."""
    th    = proj.get("aiThesis", {})
    sn    = proj.get("snapshot", {})
    alog  = proj.get("analyticsLog", {})
    fv    = th.get("fairValue", 0) or 0
    price = sn.get("price", 0) or th.get("currentPrice", 0) or 0
    upside = round((fv - price) / price * 100, 1) if price else 0
    conf   = float(alog.get("confidenceScore", 0) or 0)
    return {
        "action":      th.get("action", ""),
        "fairValue":   fv,
        "price":       price,
        "upside":      upside,
        "confidence":  round(conf, 2),
        "score":       round(upside * conf, 1),
        "thesis":      (th.get("thesis") or "")[:120],
        "analyzedAt":  (th.get("analyzedAt") or proj.get("savedAt") or "")[:10],
        "model":       th.get("model", ""),
        "stale":       _days_old((th.get("analyzedAt") or proj.get("savedAt") or "")) > STALE_DAYS,
    }


# ── Category scanners ──────────────────────────────────────────────────────────

def scan_exit(portfolio: dict, thesis: dict) -> list:
    """Held positions where thesis targetPct == 0 → EXIT queue."""
    results = []
    for ticker, pos in portfolio.items():
        if ticker == "_meta":
            continue
        t = thesis.get(ticker, {})
        if t.get("targetPct", -1) == 0 or (ticker not in thesis):
            proj = load_projection(ticker)
            pf = _proj_fields(proj) if proj else {}
            
            # If AI strongly disagrees with the EXIT (it's a BUY with upside),
            # this is a conflict, not dead weight. Route to scan_conflicts instead.
            if pf.get("action") in ("BUY", "ACCUMULATE", "INITIATE") and pf.get("upside", 0) > 10:
                continue

            results.append({
                "ticker":     ticker,
                "actualPct":  pos["actualPct"],
                "value":      pos["value"],
                "bookPL":     pos.get("bookPL"),
                "dcfAction":  pf.get("action", "N/A"),
                "dcfUpside":  pf.get("upside"),
                "fairValue":  pf.get("fairValue"),
                "price":      pos["price"],
                "confidence": pf.get("confidence"),
                "analyzedAt": pf.get("analyzedAt", ""),
                "stale":      pf.get("stale", True),
                "note":       "thesis EXIT" if ticker in thesis else "not in thesis",
            })
    # Sort by value desc (biggest capital locked first)
    results.sort(key=lambda x: x["value"], reverse=True)
    return results


def scan_trim(portfolio: dict, thesis: dict) -> list:
    """Held positions where actualPct > targetPct by >1pp AND DCF is SELL/TRIM."""
    results = []
    for ticker, pos in portfolio.items():
        if ticker == "_meta":
            continue
        t = thesis.get(ticker, {})
        target = t.get("targetPct", 0)
        actual = pos["actualPct"]
        if target == 0:
            continue  # that's EXIT, not TRIM
        drift = actual - target
        if drift <= 1.0:
            continue
        proj = load_projection(ticker)
        pf = _proj_fields(proj) if proj else {}
        dcf_action = pf.get("action", "")
        
        # DO NOT recommend trimming if the AI screams BUY or has massive upside
        if dcf_action in ("BUY", "ACCUMULATE", "INITIATE") and pf.get("upside", 0) > 10:
            continue
        results.append({
            "ticker":     ticker,
            "actualPct":  actual,
            "targetPct":  target,
            "drift":      round(drift, 2),
            "value":      pos["value"],
            "dcfAction":  dcf_action,
            "dcfUpside":  pf.get("upside"),
            "fairValue":  pf.get("fairValue"),
            "price":      pos["price"],
            "confidence": pf.get("confidence"),
            "pillar":     t.get("pillarName", ""),
            "analyzedAt": pf.get("analyzedAt", ""),
            "stale":      pf.get("stale", True),
        })
    results.sort(key=lambda x: x["drift"], reverse=True)
    return results


def scan_accumulate(portfolio: dict, thesis: dict) -> list:
    """Held positions underweight vs thesis target AND DCF is BUY/ACCUMULATE."""
    results = []
    for ticker, pos in portfolio.items():
        if ticker == "_meta":
            continue
        t = thesis.get(ticker, {})
        target = t.get("targetPct", 0)
        actual = pos["actualPct"]
        if target == 0 or actual >= target:
            continue
        gap = target - actual
        if gap < 0.5:
            continue  # within threshold
        proj = load_projection(ticker)
        pf = _proj_fields(proj) if proj else {}
        dcf_action = pf.get("action", "")
        # Only flag if DCF agrees it's worth adding
        if dcf_action not in ("BUY", "ACCUMULATE", "INITIATE", "MAINTAIN", ""):
            continue
        results.append({
            "ticker":     ticker,
            "actualPct":  actual,
            "targetPct":  target,
            "gap":        round(gap, 2),
            "value":      pos["value"],
            "dcfAction":  dcf_action,
            "dcfUpside":  pf.get("upside"),
            "fairValue":  pf.get("fairValue"),
            "price":      pos["price"],
            "score":      pf.get("score", 0),
            "confidence": pf.get("confidence"),
            "pillar":     t.get("pillarName", ""),
            "analyzedAt": pf.get("analyzedAt", ""),
            "stale":      pf.get("stale", True),
        })
    results.sort(key=lambda x: x["score"] if x["score"] else 0, reverse=True)
    return results


def scan_initiate(portfolio: dict, thesis: dict, top: int = 15) -> list:
    """Unowned tickers in projections with BUY/INITIATE rating, ranked by upside × confidence."""
    held = set(portfolio.keys()) - {"_meta"}
    results = []
    if not PROJECTIONS.exists():
        return results
    for fname in PROJECTIONS.iterdir():
        if fname.suffix != ".json":
            continue
        ticker = fname.stem
        if ticker in held:
            continue
        proj = load_projection(ticker)
        if not proj:
            continue
        pf = _proj_fields(proj)
        if pf["action"] not in ("BUY", "INITIATE", "ACCUMULATE"):
            continue
        if pf["upside"] <= 0:
            continue
        t = thesis.get(ticker, {})
        results.append({
            "ticker":     ticker,
            "inThesis":   ticker in thesis,
            "targetPct":  t.get("targetPct", 0),
            "pillar":     t.get("pillarName", "Unclassified"),
            "dcfAction":  pf["action"],
            "dcfUpside":  pf["upside"],
            "fairValue":  pf["fairValue"],
            "price":      pf["price"],
            "score":      pf["score"],
            "confidence": pf["confidence"],
            "thesis":     pf["thesis"],
            "analyzedAt": pf["analyzedAt"],
            "stale":      pf["stale"],
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top]


def scan_conflicts(portfolio: dict, thesis: dict) -> list:
    """Finds two types of conflicts:
       1) Core holdings (targetPct > 0) where DCF says SELL
       2) Zero-weight holdings (targetPct == 0) where DCF screams BUY"""
    results = []
    for ticker, pos in portfolio.items():
        if ticker == "_meta":
            continue
        t = thesis.get(ticker, {})
        target = t.get("targetPct", 0)
        
        proj = load_projection(ticker)
        if not proj:
            continue
        pf = _proj_fields(proj)
        
        is_conflict = False
        conflict_type = ""
        
        if target > 0 and pf["action"] in ("SELL", "EXIT", "TRIM"):
            is_conflict = True
            conflict_type = "Thesis OVERWEIGHT vs AI SELL"
        elif target == 0 and pf["action"] in ("BUY", "ACCUMULATE", "INITIATE") and pf["upside"] > 10:
            is_conflict = True
            conflict_type = "Thesis ZERO vs AI BUY"
            
        if not is_conflict:
            continue
            
        results.append({
            "ticker":      ticker,
            "actualPct":   pos["actualPct"],
            "targetPct":   target,
            "dcfAction":   pf["action"],
            "dcfUpside":   pf["upside"],
            "fairValue":   pf["fairValue"],
            "price":       pos["price"],
            "confidence":  pf["confidence"],
            "pillar":      t.get("pillarName", "Unclassified"),
            "thesis":      pf.get("thesis", ""),
            "analyzedAt":  pf["analyzedAt"],
            "conflictType": conflict_type,
            "stale":       pf["stale"],
        })
    results.sort(key=lambda x: abs(x["dcfUpside"] or 0), reverse=True)
    return results


def scan_stale(portfolio: dict, thesis: dict) -> list:
    """All held or thesis-targeted tickers with analyses older than STALE_DAYS."""
    all_tickers = set(portfolio.keys()) - {"_meta"}
    all_tickers |= set(thesis.keys())
    results = []
    for ticker in sorted(all_tickers):
        proj = load_projection(ticker)
        if not proj:
            results.append({"ticker": ticker, "analyzedAt": "never", "daysOld": 999, "hasProjection": False})
            continue
        pf = _proj_fields(proj)
        days = _days_old(pf["analyzedAt"])
        if days > STALE_DAYS:
            results.append({
                "ticker":       ticker,
                "analyzedAt":   pf["analyzedAt"],
                "daysOld":      days,
                "hasProjection": True,
                "dcfAction":    pf["action"],
            })
    results.sort(key=lambda x: x["daysOld"], reverse=True)
    return results


# ── Formatters ─────────────────────────────────────────────────────────────────

def _stale_flag(row: dict) -> str:
    return " ⚠️" if row.get("stale") else ""


def fmt_exit_table(rows: list) -> str:
    if not rows:
        return "_No EXIT-flagged positions found._\n"
    lines = ["| Ticker | Actual% | Value | P&L | DCF | Downside | Conf | Note |",
             "|--------|---------|-------|-----|-----|----------|------|------|"]
    for r in rows:
        pl  = f"{r['bookPL']:+.1f}%" if r.get("bookPL") is not None else "—"
        up  = f"{r['dcfUpside']:+.0f}%" if r.get("dcfUpside") is not None else "N/A"
        fv  = f"${r['fairValue']:,.0f}" if r.get("fairValue") else "N/A"
        conf= f"{r['confidence']:.2f}" if r.get("confidence") else "—"
        sf  = _stale_flag(r)
        lines.append(f"| {r['ticker']}{sf} | {r['actualPct']}% | ${r['value']:,.0f} | {pl} | {r['dcfAction']} {fv} | {up} | {conf} | {r['note']} |")
    return "\n".join(lines) + "\n"


def fmt_trim_table(rows: list) -> str:
    if not rows:
        return "_No TRIM candidates found._\n"
    lines = ["| Ticker | Actual% | Target% | Drift | DCF | Downside | Value | Pillar |",
             "|--------|---------|---------|-------|-----|----------|-------|--------|"]
    for r in rows:
        up  = f"{r['dcfUpside']:+.0f}%" if r.get("dcfUpside") is not None else "N/A"
        sf  = _stale_flag(r)
        lines.append(f"| {r['ticker']}{sf} | {r['actualPct']}% | {r['targetPct']}% | +{r['drift']}pp | {r['dcfAction']} | {up} | ${r['value']:,.0f} | {r['pillar']} |")
    return "\n".join(lines) + "\n"


def fmt_accumulate_table(rows: list) -> str:
    if not rows:
        return "_No ACCUMULATE candidates found._\n"
    lines = ["| Ticker | Actual% | Target% | Gap | DCF | Upside | Conf | Pillar |",
             "|--------|---------|---------|-----|-----|--------|------|--------|"]
    for r in rows:
        up  = f"{r['dcfUpside']:+.0f}%" if r.get("dcfUpside") is not None else "N/A"
        conf= f"{r['confidence']:.2f}" if r.get("confidence") else "—"
        sf  = _stale_flag(r)
        lines.append(f"| {r['ticker']}{sf} | {r['actualPct']}% | {r['targetPct']}% | {r['gap']}pp | {r['dcfAction']} | {up} | {conf} | {r['pillar']} |")
    return "\n".join(lines) + "\n"


def fmt_initiate_table(rows: list) -> str:
    if not rows:
        return "_No unowned BUY-rated opportunities found._\n"
    lines = ["| Rank | Ticker | In Thesis | Upside | FV | Price | Conf | Analyzed | Key Thesis |",
             "|------|--------|-----------|--------|-----|-------|------|----------|------------|"]
    for i, r in enumerate(rows, 1):
        in_t = f"✅ {r['targetPct']}% target" if r["inThesis"] else "❌ not in thesis"
        sf   = _stale_flag(r)
        fv   = f"${r['fairValue']:,.0f}" if r.get("fairValue") else "N/A"
        pr   = f"${r['price']:,.0f}" if r.get("price") else "N/A"
        lines.append(f"| {i} | {r['ticker']}{sf} | {in_t} | +{r['dcfUpside']}% | {fv} | {pr} | {r['confidence']} | {r['analyzedAt']} | {r['thesis']}... |")
    return "\n".join(lines) + "\n"


def fmt_conflicts_table(rows: list) -> str:
    if not rows:
        return "_No thesis/DCF conflicts found._\n"
    lines = ["| Ticker | Conflict Type | Actual% | Target% | DCF | Upside/Downside | FV | Conf | Pillar | Thesis (truncated) |",
             "|--------|---------------|---------|---------|-----|-----------------|----|------|--------|--------------------|"]
    for r in rows:
        up  = f"{r['dcfUpside']:+.0f}%" if r.get("dcfUpside") is not None else "N/A"
        fv  = f"${r['fairValue']:,.0f}" if r.get("fairValue") else "N/A"
        conf= f"{r['confidence']:.2f}" if r.get("confidence") else "—"
        sf  = _stale_flag(r)
        th  = (r['thesis'][:80] + "...") if len(r['thesis']) > 80 else r['thesis']
        lines.append(f"| {r['ticker']}{sf} | {r['conflictType']} | {r['actualPct']}% | {r['targetPct']}% | {r['dcfAction']} | {up} | {fv} | {conf} | {r['pillar']} | {th} |")
    return "\n".join(lines) + "\n"


def fmt_summary(data: dict) -> str:
    meta   = data.get("_meta", {})
    exits  = data.get("exit", [])
    trims  = data.get("trim", [])
    accs   = data.get("accumulate", [])
    inits  = data.get("initiate", [])
    confs  = data.get("conflicts", [])

    exit_cap = sum(r["value"] for r in exits)
    trim_pp  = sum(r["drift"] for r in trims)
    top3_init = ", ".join(f"{r['ticker']} (+{r['dcfUpside']}%)" for r in inits[:3])

    return (
        f"**Portfolio scan summary (as of {datetime.date.today()})**\n\n"
        f"- **EXIT queue:** {len(exits)} positions, ~${exit_cap:,.0f} locked capital "
        f"({round(exit_cap / meta.get('totalValue', 1) * 100, 1)}% of portfolio)\n"
        f"- **TRIM candidates:** {len(trims)} positions drifted overweight by avg "
        f"{round(trim_pp / len(trims), 1) if trims else 0}pp\n"
        f"- **ACCUMULATE:** {len(accs)} held positions underweight vs thesis with DCF upside\n"
        f"- **INITIATE (best unowned):** {top3_init or 'none found'}\n"
        f"- **Thesis/DCF conflicts:** {len(confs)} core holdings where DCF disagrees with thesis\n"
        f"- **Available cash:** ${meta.get('cashValue', 0):,.0f} "
        f"({meta.get('cashPct', 0)}% of portfolio)\n"
    )


def fmt_markdown(data: dict) -> str:
    meta  = data.get("_meta", {})
    date  = datetime.date.today().isoformat()
    out   = [f"<!-- scan_opportunities.py output — {date} -->\n"]

    out.append("## 🚀 Top Profit Opportunities — Unowned BUY-Rated Stocks\n")
    out.append(fmt_initiate_table(data.get("initiate", [])))

    out.append("\n## 🚨 EXIT Queue — Capital Locked in Dead Weight\n")
    out.append(f"> Total capital locked: ~${sum(r['value'] for r in data.get('exit', [])):,.0f}\n\n")
    out.append(fmt_exit_table(data.get("exit", [])))

    out.append("\n## ✂️ TRIM — Overweight vs Thesis Target\n")
    out.append(fmt_trim_table(data.get("trim", [])))

    out.append("\n## 🔵 ACCUMULATE — Underweight with DCF Upside\n")
    out.append(fmt_accumulate_table(data.get("accumulate", [])))

    out.append("\n## ⚔️ Strategic Conflicts — Thesis vs DCF Disagree\n")
    out.append(fmt_conflicts_table(data.get("conflicts", [])))

    stale = data.get("stale", [])
    if stale:
        out.append(f"\n## ⚠️ Stale Analyses (>{STALE_DAYS} days) — Run /evaluate-stock to refresh\n")
        tickers = ", ".join(f"`{r['ticker']}` ({r['daysOld']}d)" for r in stale[:10])
        out.append(f"{tickers}\n")

    out.append("\n## 💰 Portfolio Summary\n")
    out.append(f"- Total value: ${meta.get('totalValue', 0):,.0f}\n")
    out.append(f"- Available cash: ${meta.get('cashValue', 0):,.0f} ({meta.get('cashPct', 0)}%)\n")

    return "\n".join(out)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scan DCF corpus and portfolio for action priorities.")
    parser.add_argument("--format", choices=["markdown", "json", "summary"], default="markdown")
    parser.add_argument("--top", type=int, default=15, help="Max rows for INITIATE table")
    parser.add_argument("--category", choices=["exit", "trim", "accumulate", "initiate", "conflicts", "stale", "all"],
                        default="all")
    parser.add_argument("--portfolio", default=str(PORTFOLIO_PATH))
    parser.add_argument("--thesis",    default=str(THESIS_PATH))
    args = parser.parse_args()

    portfolio = load_portfolio(Path(args.portfolio))
    thesis    = load_thesis(Path(args.thesis))
    meta      = portfolio.pop("_meta", {})

    data = {
        "_meta":     meta,
        "exit":      scan_exit(portfolio, thesis)      if args.category in ("exit", "all")      else [],
        "trim":      scan_trim(portfolio, thesis)      if args.category in ("trim", "all")      else [],
        "accumulate":scan_accumulate(portfolio, thesis) if args.category in ("accumulate","all") else [],
        "initiate":  scan_initiate(portfolio, thesis, args.top) if args.category in ("initiate","all") else [],
        "conflicts": scan_conflicts(portfolio, thesis) if args.category in ("conflicts","all")  else [],
        "stale":     scan_stale(portfolio, thesis)     if args.category in ("stale", "all")     else [],
    }

    if args.format == "json":
        print(json.dumps(data, indent=2, default=str))
    elif args.format == "summary":
        print(fmt_summary(data))
    else:
        print(fmt_markdown(data))


if __name__ == "__main__":
    main()
