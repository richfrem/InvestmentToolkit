#!/usr/bin/env python3
"""
generate_reports.py
===================
Generates daily/weekly portfolio reports from templates in plugins/portfolio-advisor/assets/templates/
Organizes holdings and watchlist tickers by sub-strategy, combines fundamentals, news, and technical analysis.
"""
import os
import sys
import json
import glob
from datetime import datetime

# Paths relative to project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DOMAIN_DB_PATH = os.path.join(PROJECT_ROOT, "investment_screener/backend/data/domain_model.sqlite")
DAILY_BRIEFS_DIR = os.path.join(PROJECT_ROOT, "investment_screener/backend/data/daily-briefs")
DAILY_REVIEWS_DIR = os.path.join(PROJECT_ROOT, "investment_screener/backend/data/history/reviews/daily")
WEEKLY_REVIEWS_DIR = os.path.join(PROJECT_ROOT, "investment_screener/backend/data/history/reviews/weekly")


def load_target_holdings_from_db(db_path=DOMAIN_DB_PATH):
    """Load target-portfolio-shaped holdings from the domain-model DB (Wave 2 rewire).

    Replaces the direct ``target-portfolio.json`` read. Returns the same
    ``{"holdings": [...]}`` shape the JSON file used to provide (ticker, name,
    subStrategyId, targetWeight, role, thesisForInclusion) so ``generate_report``'s
    body needs no further changes. Field mapping confirmed against
    ``migrate_target_portfolio_to_sqlite.py``'s write path: ``role`` ->
    ``lifecycle_status``, ``targetWeight`` -> ``target_weight``,
    ``thesisForInclusion`` -> ``thesis_for_inclusion``, ``subStrategyId`` ->
    ``sub_strategy_id``. Only rows with a ``pillar_id`` are included — the
    migration only sets ``pillar_id`` for real thesis holdings (watchlist-only
    rows get none), mirroring the original JSON read's implicit scope
    (``target_portfolio_data.get("holdings", [])`` only, not every investment).
    """
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "investment_screener/backend/py_services"))
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import list_investments

    if not os.path.exists(db_path):
        return {}

    conn = initialize_db(str(db_path))
    try:
        rows = list_investments(conn)
    finally:
        conn.close()

    holdings = []
    for row in rows:
        if row.get("pillar_id") is None:
            continue
        holdings.append({
            "ticker": row["symbol"],
            "name": row.get("name") or row["symbol"],
            "subStrategyId": row.get("sub_strategy_id") or "unassigned",
            "targetWeight": row.get("target_weight") or 0.0,
            "role": row.get("lifecycle_status") or "watchlist",
            "thesisForInclusion": row.get("thesis_for_inclusion") or "",
        })
    return {"holdings": holdings}


def load_portfolio_from_db(db_path=DOMAIN_DB_PATH):
    """Load actual-holdings-shaped portfolio data from domain_model.sqlite
    (Wave 3 Task 6 cutover — previously portfolio.json).

    Returns the same ``{"totals": {"totalUSD": ...}, "holdings": [{"symbol",
    "market_value"}, ...]}`` shape ``generate_report()`` expects, sourced from
    ``load_portfolio_state_from_db()`` (shares/prices aggregated across
    accounts) so the total is always ``get_portfolio_total_value()``, never a
    re-sum here.
    """
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "investment_screener/backend/py_services"))
    from domain_model.db_client import initialize_db
    from domain_model.portfolio_repository import load_portfolio_state_from_db

    if not os.path.exists(db_path):
        return {}

    conn = initialize_db(str(db_path))
    try:
        state = load_portfolio_state_from_db(conn)
    finally:
        conn.close()

    shares = state["shares"]
    prices = state["prices"]
    holdings = [
        {"symbol": sym, "market_value": shares[sym] * prices.get(sym, 0.0)}
        for sym in shares
    ]
    return {"totals": {"totalUSD": state["total_usd"]}, "holdings": holdings}


def load_latest_brief():
    """Finds and loads the latest daily brief JSON file."""
    files = glob.glob(os.path.join(DAILY_BRIEFS_DIR, "*.json"))
    if not files:
        return {}
    latest_file = max(files, key=os.path.getmtime)
    with open(latest_file) as f:
        return json.load(f)


def load_json(path):
    """Loads a JSON file if it exists, otherwise returns empty dict."""
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def generate_report(brief_data, target_portfolio_data, portfolio_data, template_path):
    """Compiles the template with the provided datasets."""
    with open(template_path) as f:
        template = f.read()

    # Extract general details
    date_str = brief_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    total_val = portfolio_data.get("totals", {}).get("totalUSD", brief_data.get("total_equity", 0.0))
    macro_reg = brief_data.get("macro_regime", {})
    macro_status = macro_reg.get("regime", "NEUTRAL")
    macro_score = macro_reg.get("score", 0)

    # Breadth and trend (Phase 3/4)
    market_reg = brief_data.get("market_regime", {})
    breadth_state = market_reg.get("breadth", {}).get("state", "UNKNOWN")

    # Map tickers to sub-strategy ID and details from target-portfolio
    ticker_details = {}
    sub_strategies = {}
    
    # Process target holdings
    for h in target_portfolio_data.get("holdings", []):
        t = h.get("ticker")
        sub_strat = h.get("subStrategyId", "unassigned")
        ticker_details[t] = {
            "name": h.get("name", t),
            "subStrategyId": sub_strat,
            "targetWeight": h.get("targetWeight", 0.0),
            "role": h.get("role", "watchlist"),
            "thesis": h.get("thesisForInclusion", "")
        }
        sub_strategies.setdefault(sub_strat, []).append(t)

    # Blend conviction scores and recommendations from the brief
    scores_by_ticker = {s.get("ticker"): s for s in brief_data.get("conviction_scores", [])}
    recs_by_ticker = {r.get("ticker"): r for r in brief_data.get("recommendations", [])}
    actual_holdings = {h.get("symbol"): h for h in portfolio_data.get("holdings", [])}

    # Group by sub-strategy and construct sections
    sub_strat_text = []
    rec_categories = {
        "ACCUMULATE": [],
        "INITIATE": [],
        "TRIM": [],
        "EXIT": [],
        "MAINTAIN": []
    }

    # Order sub-strategies for presentation
    for sub_strat_id, tickers in sorted(sub_strategies.items()):
        sub_strat_text.append(f"### Sub-Strategy: {sub_strat_id.upper()}\n")
        
        for t in sorted(tickers):
            details = ticker_details[t]
            score_info = scores_by_ticker.get(t, {})
            rec_info = recs_by_ticker.get(t, {})
            actual_info = actual_holdings.get(t, {})

            # Weights and drift
            target_w = details["targetWeight"]
            actual_w = score_info.get("actual_weight")
            if actual_w is None:
                actual_w = actual_info.get("market_value", 0.0) / total_val * 100 if total_val else 0.0
            drift = actual_w - target_w

            # Technical readings
            price = actual_info.get("price")
            if price is None:
                price = score_info.get("price", 0.0)
            rsi = score_info.get("rsi")
            adx = score_info.get("adx")
            vol_bias = score_info.get("vol_bias")

            # DCF values
            dcf_action = score_info.get("dcf_action", "N/A")
            pct_to_fv = score_info.get("pct_to_fv", 0.0)

            # Recommendations & Rationale
            action = rec_info.get("recommendation")
            if not action:
                action = "ACCUMULATE" if details["role"] == "accumulate" and macro_status == "RISK-ON" else "MAINTAIN"
            
            # Map action category
            cat = action.upper()
            if cat not in rec_categories:
                cat = "MAINTAIN"
            
            rationale = rec_info.get("rationale")
            if not rationale:
                rationale = f"DCF Action: {dcf_action} | Target Weight: {target_w:.2f}% | Actual Weight: {actual_w:.2f}%"

            ticker_row = (
                f"* **{t}** ({details['name']}) — Role: `{details['role']}`\n"
                f"  * Sizing: Actual Weight: `{actual_w:.2f}%` | Target: `{target_w:.2f}%` | Drift: `{drift:+.2f}%`\n"
                f"  * Technical: Price: `${price:,.2f}` | RSI: `{rsi or 'N/A'}` | ADX: `{adx or 'N/A'}` | Vol Bias: `{vol_bias or 'N/A'}`\n"
                f"  * DCF: Action: `{dcf_action}` | Upside: `{pct_to_fv:+.1f}%`\n"
                f"  * Verdict: **{action}** — {rationale}\n"
            )
            sub_strat_text.append(ticker_row)

            # Add to action lists
            rec_categories[cat].append(f"* **{t}**: {rationale} (Drift: {drift:+.2f}%)")

        sub_strat_text.append("\n" + "—" * 40 + "\n")

    # Executive summary bullet generation
    exec_bullets = []
    # Identify largest drifts
    all_drifts = []
    for t, details in ticker_details.items():
        score_info = scores_by_ticker.get(t, {})
        actual_info = actual_holdings.get(t, {})
        target_w = details["targetWeight"]
        actual_w = score_info.get("actual_weight")
        if actual_w is None:
            actual_w = actual_info.get("market_value", 0.0) / total_val * 100 if total_val else 0.0
        all_drifts.append((t, actual_w - target_w))
    
    all_drifts.sort(key=lambda x: abs(x[1]), reverse=True)
    top_drifts = [f"{t}({drift:+.2f}%)" for t, drift in all_drifts[:3] if abs(drift) > 0.5]
    if top_drifts:
        exec_bullets.append(f"* **Drift Alerts:** Key target deviations in {', '.join(top_drifts)}.")
    
    # Process triggers
    triggers = brief_data.get("thesis_breakers_triggered", [])
    if triggers:
        exec_bullets.append(f"* **⚠ Thesis Breakers:** Triggered events on {', '.join(triggers)}.")
    else:
        exec_bullets.append("* **Moat Integrity:** No active thesis breakers triggered this period.")

    # Earnings
    imminent = [e.get("ticker") for e in brief_data.get("earnings_flags", []) if e.get("flag") == "IMMINENT"]
    if imminent:
        exec_bullets.append(f"* **Earnings Check:** Imminent events within 7 days on {', '.join(imminent)}.")

    # Replace in template
    output = template.replace("{{DATE}}", date_str)
    output = output.replace("{{PORTFOLIO_VALUE}}", f"{total_val:,.2f}")
    output = output.replace("{{MACRO_REGIME}}", macro_status)
    output = output.replace("{{MACRO_SCORE}}", str(macro_score))
    output = output.replace("{{BREADTH_STATE}}", breadth_state)
    output = output.replace("{{EXEC_SUMMARY_BULLETS}}", "\n".join(exec_bullets))
    output = output.replace("{{SUB_STRATEGY_SECTION}}", "\n".join(sub_strat_text))

    for cat, list_vals in rec_categories.items():
        content = "\n".join(list_vals) if list_vals else "*(No tickers currently meet this action category)*"
        output = output.replace(f"{{{{RECOMMENDATION_{cat}}}}}", content)

    return output


def main():
    # Load authoritative inputs
    brief = load_latest_brief()
    target_portfolio = load_target_holdings_from_db()
    portfolio = load_portfolio_from_db()

    if not brief or not target_portfolio or not portfolio:
        print("Error: authoritative JSON inputs are missing or empty.")
        return

    # Templates
    daily_tmpl = os.path.join(PROJECT_ROOT, "plugins/portfolio-advisor/assets/templates/daily_report.md.template")
    weekly_tmpl = os.path.join(PROJECT_ROOT, "plugins/portfolio-advisor/assets/templates/weekly_report.md.template")

    os.makedirs(DAILY_REVIEWS_DIR, exist_ok=True)
    os.makedirs(WEEKLY_REVIEWS_DIR, exist_ok=True)

    date_str = brief.get("date", datetime.now().strftime("%Y-%m-%d"))

    # Daily Report
    if os.path.exists(daily_tmpl):
        daily_out = generate_report(brief, target_portfolio, portfolio, daily_tmpl)
        out_path = os.path.join(DAILY_REVIEWS_DIR, f"daily_confluence_scan_{date_str}.md")
        with open(out_path, "w") as f:
            f.write(daily_out)
        print(f"✅ Generated daily report: {out_path}")

    # Weekly Report
    if os.path.exists(weekly_tmpl):
        weekly_out = generate_report(brief, target_portfolio, portfolio, weekly_tmpl)
        out_path = os.path.join(WEEKLY_REVIEWS_DIR, f"weekly_confluence_scan_{date_str}.md")
        with open(out_path, "w") as f:
            f.write(weekly_out)
        print(f"✅ Generated weekly report: {out_path}")


if __name__ == "__main__":
    main()
