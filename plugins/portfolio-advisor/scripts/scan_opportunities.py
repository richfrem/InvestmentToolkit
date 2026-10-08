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
THESIS_PATH    = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
DB_PATH        = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from risk_reward import STALE_DAYS  # noqa: E402  (one staleness threshold for every surface)

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from ticker_aliases import is_cash  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    get_latest_projection_by_source,
    list_symbols_with_projections,
)
from domain_model.investment_repository import list_investments  # noqa: E402
from domain_model.pillar_repository import list_pillars  # noqa: E402
from domain_model.portfolio_repository import load_portfolio_state_from_db  # noqa: E402
from portfolio_io import compute_weights  # noqa: E402

try:
    from compute_conviction_scores import compute_all
except ImportError:
    compute_all = None


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_conviction_scores(db_path: Path | None = None) -> dict:
    """Return {ticker: ConvictionScore} mapping containing live technical momentum,
    ownership-aware bands, and composite scores from SQLite.
    """
    if compute_all is None:
        return {}
    try:
        intel_path = None
        if db_path:
            p = Path(db_path)
            if p.name == "domain_model.sqlite":
                sibling = p.parent / "intelligence.sqlite"
                if sibling.exists():
                    intel_path = str(sibling)
            else:
                intel_path = str(p)
        scores = compute_all(intel_path, domain_db_path=str(db_path or DB_PATH))
        return {s.ticker: s for s in scores}
    except Exception:
        return {}

def load_json(path: Path) -> dict | list:
    with open(path) as f:
        return json.load(f)


def _load_book_values_and_currency(conn) -> dict:
    """Return {symbol: {"book_value": sum(book_value), "currency": ...}}, aggregated
    across accounts — the account_investment/investment_price fields
    load_portfolio_state_from_db() doesn't carry (it only returns shares/prices).
    """
    cursor = conn.execute(
        """
        SELECT i.symbol AS symbol, SUM(ai.book_value) AS book_value,
               MAX(i.currency) AS currency
        FROM account_investment ai
        JOIN investment i ON i.investment_id = ai.investment_id
        GROUP BY i.symbol;
        """
    )
    return {
        row[0]: {"book_value": row[1], "currency": row[2] or "USD"}
        for row in cursor.fetchall()
    }


def load_portfolio(db_path: Path = DB_PATH) -> dict:
    """Returns {TICKER: {shares, price, value, actualPct, bookPL}}, sourced
    from domain_model.sqlite (Wave 3 Task 6 cutover — previously portfolio.json).

    ``value``/``actualPct``/``_meta.totalValue`` are derived from
    ``load_portfolio_state_from_db()`` (via ``portfolio_io.compute_weights``
    for the %), never an independent shares*price re-sum — per ADR-030.
    ``bookPL``/``currency`` have no equivalent in that shared shape, so they
    are sourced from a local account_investment/investment aggregate query.
    """
    if not Path(db_path).exists():
        return {}

    conn = initialize_db(str(db_path))
    try:
        state = load_portfolio_state_from_db(conn)
        book_info = _load_book_values_and_currency(conn)
    finally:
        conn.close()

    shares_map = state["shares"]
    prices_map = state["prices"]
    total = state["total_usd"]
    weights = compute_weights(shares_map, prices_map, total)

    out = {}
    for ticker, shares in shares_map.items():
        if not ticker or is_cash(ticker):
            continue
        price = prices_map.get(ticker, 0)
        value = shares * price
        info = book_info.get(ticker, {})
        book_value = info.get("book_value")
        book_pl = (
            round((value - book_value) / book_value * 100, 2)
            if book_value else None
        )
        out[ticker] = {
            "shares":    shares,
            "price":     price,
            "value":     round(value, 2),
            "actualPct": weights.get(ticker, 0),
            "bookPL":    book_pl,
            "currency":  info.get("currency", "USD"),
        }

    # Also store cash
    cash_symbols = [s for s in shares_map if is_cash(s)]
    cash_value = sum(shares_map[s] * prices_map.get(s, 1.0) for s in cash_symbols)
    out["_meta"] = {
        "totalValue": round(total, 2),
        "cashValue":  round(cash_value, 2),
        "cashPct":    round(cash_value / total * 100, 2) if total else 0,
    }
    return out


def load_thesis(db_path: Path | None = None) -> dict:
    """Returns {TICKER: {targetPct, pillarName, pillarId, thesisFor}}

    Storage backend (Wave 2 rewire): reads per-investment thesis fields from
    ``investment`` via ``domain_model.investment_repository.list_investments``,
    joined against ``strategy_pillar`` for the display name, instead of
    ``target-portfolio.json`` (ADR-029). Field mapping confirmed against
    ``migrate_target_portfolio_to_sqlite.py``'s write path: ``targetWeight`` ->
    ``target_weight``, ``pillarId`` -> ``pillar_id``, ``thesisForInclusion`` ->
    ``thesis_for_inclusion``, ``role`` -> ``lifecycle_status``. Only rows with a
    ``pillar_id`` are included, matching the original JSON read's implicit scope
    (``target_portfolio_data.get("holdings", [])`` only).
    """
    db_path = db_path or DB_PATH
    if not Path(db_path).exists():
        return {}

    conn = initialize_db(str(db_path))
    try:
        rows = list_investments(conn)
        pillar_names = {p["pillar_id"]: p["name"] for p in list_pillars(conn)}
    finally:
        conn.close()

    out = {}
    for row in rows:
        pillar_id = row.get("pillar_id")
        if pillar_id is None:
            continue
        ticker = row["symbol"]
        out[ticker] = {
            "targetPct":  row.get("target_weight") or 0,
            "pillarName": pillar_names.get(pillar_id, "Unclassified"),
            "pillarId":   pillar_id,
            "thesisFor":  row.get("thesis_for_inclusion") or "",
            "role":       row.get("lifecycle_status") or "",
        }
    return out


def load_projection(ticker: str, db_path: Path | None = None) -> dict | None:
    """Load the most recent AI_AGENT projection for a ticker. Returns None if absent.

    Storage backend (Wave 1 Task 7B): reads `projection_version` via
    `domain_model.projection_repository`, not `projections/{TICKER}.json`
    directly (ADR-029). The original code filtered strictly by
    `source == "AI_AGENT"` with no fallback to other sources (returns `None`
    if no AI_AGENT row exists), so this uses `get_latest_projection_by_source`
    only — no fallback to `get_latest_projection`, unlike consumers whose
    original code did fall back.
    """
    conn = initialize_db(str(db_path or DB_PATH))
    try:
        row = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", (ticker,)
        ).fetchone()
        if row is None:
            return None
        investment_id = row[0]
        entry = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
        if entry is None:
            return None
        return {
            "savedAt": entry.get("saved_at", ""),
            "aiThesis": {
                "fairValue": entry.get("fair_value"),
                "action": entry.get("action"),
                "analyzedAt": entry.get("analyzed_at"),
                "model": entry.get("model"),
            },
            "snapshot": json.loads(entry["snapshot_json"]) if entry.get("snapshot_json") else {},
            "analyticsLog": json.loads(entry["analytics_log_json"]) if entry.get("analytics_log_json") else {},
        }
    finally:
        conn.close()


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


def _enrich_with_scores(item: dict, ticker: str, scores: dict | None = None) -> None:
    """Enrich opportunity item with live technical momentum and conviction scoring."""
    sc = scores.get(ticker) if scores else None
    item["rsi"] = round(sc.rsi, 1) if (sc and sc.rsi is not None) else None
    item["adx"] = round(sc.adx, 1) if (sc and sc.adx is not None) else None
    item["volBias"] = round(sc.vol_bias, 1) if (sc and sc.vol_bias is not None) else None
    from recommendation import recommend_all
    rec = recommend_all(str(DB_PATH)).get(ticker, {})
    item["band"] = rec.get("action")
    item["dcfAction"] = rec.get("valuation")
    item["recommendation"] = rec
    item["convictionScore"] = sc.total if sc else None
    item["flags"] = sc.flags if sc else []


# ── Category scanners ──────────────────────────────────────────────────────────

def scan_exit(portfolio: dict, thesis: dict, scores: dict | None = None) -> list:
    """Held positions where thesis targetPct == 0 → EXIT queue."""
    from recommendation import recommend_all
    records = recommend_all(str(DB_PATH))
    results = []
    for ticker, pos in portfolio.items():
        if ticker == "_meta":
            continue
        t = thesis.get(ticker, {})
        if records.get(ticker, {}).get("action") == "EXIT":
            proj = load_projection(ticker)
            pf = _proj_fields(proj) if proj else {}
            

            item = {
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
            }
            _enrich_with_scores(item, ticker, scores)
            results.append(item)
    # Sort by value desc (biggest capital locked first)
    results.sort(key=lambda x: x["value"], reverse=True)
    return results


def scan_trim(portfolio: dict, thesis: dict, scores: dict | None = None) -> list:
    """Held positions where actualPct > targetPct by >1pp AND DCF is SELL/TRIM."""
    from recommendation import recommend_all
    records = recommend_all(str(DB_PATH))
    results = []
    for ticker, pos in portfolio.items():
        if ticker == "_meta":
            continue
        t = thesis.get(ticker, {})
        target = t.get("targetPct", 0)
        actual = pos["actualPct"]
        if records.get(ticker, {}).get("action") != "TRIM":
            continue
        drift = actual - target
        proj = load_projection(ticker)
        pf = _proj_fields(proj) if proj else {}
        dcf_action = records[ticker]["valuation"]
        item = {
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
        }
        _enrich_with_scores(item, ticker, scores)
        results.append(item)
    results.sort(key=lambda x: x["drift"], reverse=True)
    return results


def scan_accumulate(portfolio: dict, thesis: dict, scores: dict | None = None) -> list:
    """Held positions underweight vs thesis target AND DCF is BUY/ACCUMULATE."""
    from recommendation import recommend_all
    records = recommend_all(str(DB_PATH))
    results = []
    for ticker, pos in portfolio.items():
        if ticker == "_meta":
            continue
        t = thesis.get(ticker, {})
        target = t.get("targetPct", 0)
        actual = pos["actualPct"]
        if records.get(ticker, {}).get("action") != "ACCUMULATE":
            continue
        gap = target - actual
        proj = load_projection(ticker)
        pf = _proj_fields(proj) if proj else {}
        dcf_action = records[ticker]["valuation"]
        item = {
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
        }
        _enrich_with_scores(item, ticker, scores)
        results.append(item)
    results.sort(key=lambda x: x["score"] if x["score"] else 0, reverse=True)
    return results


def scan_initiate(portfolio: dict, thesis: dict, top: int = 15, scores: dict | None = None) -> list:
    """Unowned tickers in projections with BUY/INITIATE rating, ranked by upside × confidence."""
    held = set(portfolio.keys()) - {"_meta"}
    from recommendation import recommend_all
    records = recommend_all(str(DB_PATH))
    results = []
    conn = initialize_db(str(DB_PATH))
    try:
        all_tickers = list_symbols_with_projections(conn)
    finally:
        conn.close()
    for ticker in all_tickers:
        if ticker in held:
            continue
        proj = load_projection(ticker)
        if not proj:
            continue
        pf = _proj_fields(proj)
        if records.get(ticker, {}).get("action") != "INITIATE":
            continue
        if pf["upside"] <= 0:
            continue
        t = thesis.get(ticker, {})
        item = {
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
        }
        _enrich_with_scores(item, ticker, scores)
        results.append(item)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top]


def scan_conflicts(portfolio: dict, thesis: dict, scores: dict | None = None) -> list:
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
            
        item = {
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
        }
        _enrich_with_scores(item, ticker, scores)
        results.append(item)
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
    lines = ["| Ticker | Actual% | Value | P&L | DCF | RSI | Band | Downside | Conf | Note |",
             "|--------|---------|-------|-----|-----|-----|------|----------|------|------|"]
    for r in rows:
        pl  = f"{r['bookPL']:+.1f}%" if r.get("bookPL") is not None else "—"
        up  = f"{r['dcfUpside']:+.0f}%" if r.get("dcfUpside") is not None else "N/A"
        fv  = f"${r['fairValue']:,.0f}" if r.get("fairValue") else "N/A"
        conf= f"{r['confidence']:.2f}" if r.get("confidence") else "—"
        sf  = _stale_flag(r)
        rsi = f"{r['rsi']:.0f}" if r.get("rsi") is not None else "—"
        band= r.get("band") or "—"
        lines.append(f"| {r['ticker']}{sf} | {r['actualPct']}% | ${r['value']:,.0f} | {pl} | {r['dcfAction']} {fv} | {rsi} | {band} | {up} | {conf} | {r['note']} |")
    return "\n".join(lines) + "\n"


def fmt_trim_table(rows: list) -> str:
    if not rows:
        return "_No TRIM candidates found._\n"
    lines = ["| Ticker | Actual% | Target% | Drift | DCF | RSI | Band | Downside | Value | Pillar |",
             "|--------|---------|---------|-------|-----|-----|------|----------|-------|--------|"]
    for r in rows:
        up  = f"{r['dcfUpside']:+.0f}%" if r.get("dcfUpside") is not None else "N/A"
        sf  = _stale_flag(r)
        rsi = f"{r['rsi']:.0f}" if r.get("rsi") is not None else "—"
        band= r.get("band") or "—"
        lines.append(f"| {r['ticker']}{sf} | {r['actualPct']}% | {r['targetPct']}% | +{r['drift']}pp | {r['dcfAction']} | {rsi} | {band} | {up} | ${r['value']:,.0f} | {r['pillar']} |")
    return "\n".join(lines) + "\n"


def fmt_accumulate_table(rows: list) -> str:
    if not rows:
        return "_No ACCUMULATE candidates found._\n"
    lines = ["| Ticker | Actual% | Target% | Gap | DCF | RSI | Band | Score | Upside | Pillar |",
             "|--------|---------|---------|-----|-----|-----|------|-------|--------|--------|"]
    for r in rows:
        up  = f"{r['dcfUpside']:+.0f}%" if r.get("dcfUpside") is not None else "N/A"
        sf  = _stale_flag(r)
        rsi = f"{r['rsi']:.0f}" if r.get("rsi") is not None else "—"
        band= r.get("band") or "—"
        score = f"{r['convictionScore']:+d}" if r.get("convictionScore") is not None else "—"
        lines.append(f"| {r['ticker']}{sf} | {r['actualPct']}% | {r['targetPct']}% | {r['gap']}pp | {r['dcfAction']} | {rsi} | {band} | {score} | {up} | {r['pillar']} |")
    return "\n".join(lines) + "\n"


def fmt_initiate_table(rows: list) -> str:
    if not rows:
        return "_No unowned BUY-rated opportunities found._\n"
    lines = ["| Rank | Ticker | In Thesis | Upside | FV | Price | RSI | Band | Score | Conf | Key Thesis |",
             "|------|--------|-----------|--------|-----|-------|-----|------|-------|------|------------|"]
    for i, r in enumerate(rows, 1):
        in_t = f"✅ {r['targetPct']}% target" if r["inThesis"] else "❌ not in thesis"
        sf   = _stale_flag(r)
        fv   = f"${r['fairValue']:,.0f}" if r.get("fairValue") else "N/A"
        pr   = f"${r['price']:,.0f}" if r.get("price") else "N/A"
        rsi  = f"{r['rsi']:.0f}" if r.get("rsi") is not None else "—"
        band = r.get("band") or "—"
        score = f"{r['convictionScore']:+d}" if r.get("convictionScore") is not None else "—"
        lines.append(f"| {i} | {r['ticker']}{sf} | {in_t} | +{r['dcfUpside']}% | {fv} | {pr} | {rsi} | {band} | {score} | {r['confidence']} | {r['thesis']}... |")
    return "\n".join(lines) + "\n"


def fmt_conflicts_table(rows: list) -> str:
    if not rows:
        return "_No thesis/DCF conflicts found._\n"
    lines = ["| Ticker | Conflict Type | Actual% | Target% | DCF | RSI | Band | Upside/Downside | FV | Pillar | Thesis (truncated) |",
             "|--------|---------------|---------|---------|-----|-----|------|-----------------|----|--------|--------------------|"]
    for r in rows:
        up  = f"{r['dcfUpside']:+.0f}%" if r.get("dcfUpside") is not None else "N/A"
        fv  = f"${r['fairValue']:,.0f}" if r.get("fairValue") else "N/A"
        conf= f"{r['confidence']:.2f}" if r.get("confidence") else "—"
        sf  = _stale_flag(r)
        rsi = f"{r['rsi']:.0f}" if r.get("rsi") is not None else "—"
        band= r.get("band") or "—"
        th  = (r['thesis'][:80] + "...") if len(r['thesis']) > 80 else r['thesis']
        lines.append(f"| {r['ticker']}{sf} | {r['conflictType']} | {r['actualPct']}% | {r['targetPct']}% | {r['dcfAction']} | {rsi} | {band} | {up} | {fv} | {r['pillar']} | {th} |")
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
        out.append(f"\n## ⚠️ Stale Analyses (>{STALE_DAYS} days) — Run /update-stock-analysis to refresh\n")
        tickers = ", ".join(f"`{r['ticker']}` ({r['daysOld']}d)" for r in stale[:10])
        out.append(f"{tickers}\n")

    out.append("\n## 💰 Portfolio Summary\n")
    out.append(f"- Total value: ${meta.get('totalValue', 0):,.0f}\n")
    out.append(f"- Available cash: ${meta.get('cashValue', 0):,.0f} ({meta.get('cashPct', 0)}%)\n")

    return "\n".join(out)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    global DB_PATH
    parser = argparse.ArgumentParser(description="Scan DCF corpus and portfolio for action priorities.")
    parser.add_argument("--format", choices=["markdown", "json", "summary"], default="markdown")
    parser.add_argument("--top", type=int, default=15, help="Max rows for INITIATE table")
    parser.add_argument("--category", choices=["exit", "trim", "accumulate", "initiate", "conflicts", "stale", "all"],
                        default="all")
    parser.add_argument(
        "--portfolio", default=None,
        help="Legacy portfolio.json path, kept for CLI back-compat; no longer "
             "read. Holdings now come from --db (domain_model.sqlite).",
    )
    parser.add_argument(
        "--thesis", default=str(THESIS_PATH),
        help="Legacy target-portfolio.json path, kept for CLI back-compat; "
             "no longer read directly. Thesis fields now come from --db.",
    )
    parser.add_argument("--db", default=str(DB_PATH), help="Path to domain_model.sqlite")
    args = parser.parse_args()

    DB_PATH = Path(args.db)
    portfolio = load_portfolio(DB_PATH)
    thesis    = load_thesis(Path(args.db))
    scores    = load_conviction_scores(Path(args.db))
    meta      = portfolio.pop("_meta", {})

    data = {
        "_meta":     meta,
        "exit":      scan_exit(portfolio, thesis, scores=scores)      if args.category in ("exit", "all")      else [],
        "trim":      scan_trim(portfolio, thesis, scores=scores)      if args.category in ("trim", "all")      else [],
        "accumulate":scan_accumulate(portfolio, thesis, scores=scores) if args.category in ("accumulate","all") else [],
        "initiate":  scan_initiate(portfolio, thesis, args.top, scores=scores) if args.category in ("initiate","all") else [],
        "conflicts": scan_conflicts(portfolio, thesis, scores=scores) if args.category in ("conflicts","all")  else [],
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
