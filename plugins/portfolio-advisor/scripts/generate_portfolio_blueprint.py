#!/usr/bin/env python3
"""
generate_portfolio_blueprint.py (Python Service)
=====================================

Purpose:
    Generates the "Portfolio Blueprint" section (Section IV) for the investment thesis document.
    Synthesizes thesis targets (domain_model.sqlite ``investment`` rows) with live holdings
    (domain_model.sqlite, via portfolio_io.load_portfolio_state()) to produce an enriched,
    data-driven Markdown table grouped by sub-strategy.

    Wave 3 full cutover: ALL portfolio data — per-position shares/price AND the
    authoritative total — is sourced from domain_model.sqlite. No portfolio.json
    read remains anywhere in this file.

Layer: Backend / Python Services / Report Generation

Usage Examples:
    # Preview section in stdout (dry-run)
    python3 generate_portfolio_blueprint.py

    # Update investment_thesis.md in-place
    python3 generate_portfolio_blueprint.py --write

    # Specify a custom domain_model.sqlite path
    python3 generate_portfolio_blueprint.py --write --db data/domain_model.sqlite

Key Functions:
    - generate_section() - Constructs the primary Section IV Markdown content with live performance metrics
    - update_section_tables() - Rigorously scans the entire thesis document to enrich legacy tables with live data
    - build_actual_map() / build_thesis_map() - Normalize disparate data sources into unified maps for aggregation

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (Wave 3+; portfolio.json is no longer read)
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

PORTFOLIO_JSON = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
THESIS_MD     = REPO_ROOT / "investment_screener/backend/data/theses/investment_thesis.md"
DOMAIN_DB     = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from ticker_aliases import is_cash  # noqa: E402
from portfolio_io import load_portfolio_state, compute_weights, replace_block  # noqa: E402


def _compute_current_weights(db_path: Path | None = None) -> dict:
    """Wave 3 replacement for validate_weights.compute_current(PORTFOLIO_JSON).

    Sources shares/prices/total exclusively from
    portfolio_io.load_portfolio_state() (SQLite-backed) and derives per-ticker
    weight % via portfolio_io.compute_weights() — the same total_usd
    denominator used everywhere else in this file, so this can never drift
    from build_actual_map()'s totals. Returns the same shape the retired
    validate_weights.compute_current() returned: {"total", "holdings",
    "total_value"}.
    """
    state = load_portfolio_state(db_path or DOMAIN_DB)
    holdings = compute_weights(state["shares"], state["prices"], state["total_usd"])
    return {
        "total": round(sum(holdings.values()), 4),
        "holdings": holdings,
        "total_value": state["total_usd"],
    }

SUB_STRATEGY_NAMES = {
    "sa-asi-race":         "Sub-Strategy 1 — SA / ASI Race (Aschenbrenner Framework)",
    "cybersecurity":       "Sub-Strategy 2 — AI-Native Cybersecurity",
    "sovereign-finance":   "Sub-Strategy 3 — Sovereign Finance",
    "quality-saas":        "Sub-Strategy 4 — Quality SaaS Resilience",
    "frontier-bets":       "Sub-Strategy 5 — Applied AI / Frontier Bets",
    "metabolic-rewriting": "Sub-Strategy 6 — Metabolic Reprogramming & Genetic Editing",
    "cash":                "Strategic Reserve",
    "untracked":           "Untracked / Thesis Pending",
}

from portfolio_action import derive_action, ACTION_EMOJI, _load_target_weights


def _resolve_investment_id(conn, ticker: str) -> str | None:
    """Look up investment_id for a symbol without inserting (read-only lookup)."""
    row = conn.execute("SELECT investment_id FROM investment WHERE symbol = ?;", (ticker,)).fetchone()
    return row[0] if row else None


def _get_latest_ai_projection(ticker: str, db_path: Path | None = None) -> dict | None:
    """Fetch the latest projection for ``ticker`` from the domain model DB, preferring
    the latest ``AI_AGENT``-sourced row and falling back to the latest row of any source.

    Storage backend (Wave 1 Task 7C): reads `projection_version` via
    `domain_model.projection_repository` instead of `projections/{TICKER}.json`
    (ADR-029). Mirrors `portfolio_action.py`'s `_load_ai_upside` — same
    AI_AGENT-preferred / any-source-fallback lookup, used here for both the AI
    signal action and the fair-value upside computation. Returns ``None`` on any
    lookup failure so callers fall back to "—" placeholders.
    """
    try:
        sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
        from domain_model.db_client import initialize_db
        from domain_model.projection_repository import get_latest_projection, get_latest_projection_by_source

        conn = initialize_db(str(db_path or DOMAIN_DB))
        try:
            investment_id = _resolve_investment_id(conn, ticker)
            if investment_id is None:
                return None
            entry = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
            if entry is None:
                entry = get_latest_projection(conn, investment_id)
            return entry
        finally:
            conn.close()
    except Exception:
        return None


def _get_latest_ai_agent_projection(ticker: str, db_path: Path | None = None) -> dict | None:
    """Fetch the latest ``AI_AGENT``-sourced projection for ``ticker``, strictly —
    no fallback to other sources. Returns ``None`` if no AI_AGENT row exists.

    Storage backend (Wave 1 Task 7C): reads `projection_version` via
    `domain_model.projection_repository` (ADR-029), replacing the prior
    `[p for p in projs if p.get("source") == "AI_AGENT"]` file-based filter.
    """
    try:
        sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
        from domain_model.db_client import initialize_db
        from domain_model.projection_repository import get_latest_projection_by_source

        conn = initialize_db(str(db_path or DOMAIN_DB))
        try:
            investment_id = _resolve_investment_id(conn, ticker)
            if investment_id is None:
                return None
            return get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
        finally:
            conn.close()
    except Exception:
        return None


def build_actual_map(db_path: Path | None = None) -> tuple[dict, float]:
    """Build actual-position map entirely from domain_model.sqlite.

    Wave 3 full cutover: shares, prices, and the authoritative total all come
    from portfolio_io.load_portfolio_state() (which delegates to
    domain_model.portfolio_repository.load_portfolio_state_from_db()). No
    portfolio.json read remains here — the ``db_path`` argument is passed
    through for signature compatibility/testability only; load_portfolio_state()
    itself always reads the module-level ``portfolio_io._DB_PATH``.
    """
    state = load_portfolio_state(db_path or DOMAIN_DB)

    shares_map = state["shares"]
    prices_map = state["prices"]
    total = state["total_usd"]

    actual: dict = {}
    for sym, shares in shares_map.items():
        if not sym:
            continue
        price = float(prices_map.get(sym) or 0)
        val   = float(shares) * price
        actual[sym] = {
            "shares":    float(shares),
            "price":     price,
            "book":      0.0,  # not exposed by load_portfolio_state(); unused downstream
            "value":     round(val, 2),
            "actualPct": round(val / total * 100, 2) if total else 0,
            "name":      sym,
        }
    return actual, total


def build_thesis_map(db_path: Path | None = None) -> dict:
    """Returns {ticker: {subStrategyId, targetPct, role, thesisNote, thesisBreakers}}

    Storage backend (Wave 2 rewire): reads per-investment thesis fields from
    ``investment`` via ``domain_model.investment_repository.list_investments``
    instead of ``target-portfolio.json`` holdings (ADR-029). Field mapping
    confirmed against ``migrate_target_portfolio_to_sqlite.py``'s write path:
    ``role`` -> ``lifecycle_status``, ``targetWeight`` -> ``target_weight``,
    ``thesisForInclusion`` -> ``thesis_for_inclusion``, ``subStrategyId`` ->
    ``sub_strategy_id``. ``thesisBreakers`` has no real-data usage (0/75 real
    holdings carry it as of this migration) and no list-shaped column exists
    on ``investment`` (only the scalar ``thesis_breaker_status``), so it is
    always returned as ``[]`` here — this mirrors the thesis_breakers.py /
    update_thesis.py exception rather than forcing a lossy scalar mapping.
    """
    sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import list_investments

    conn = initialize_db(str(db_path or DOMAIN_DB))
    try:
        rows = list_investments(conn)
    finally:
        conn.close()

    holdings = {}
    for row in rows:
        # Only rows that actually came from target-portfolio.json's holdings[]
        # array carry a pillar_id (migration write path only sets pillar_id
        # for real thesis holdings — watchlist-only rows get none). This
        # mirrors the original JSON read's implicit scope (thesis.holdings
        # only, not every watchlist/investment row).
        if row.get("pillar_id") is None:
            continue
        ticker = row["symbol"]
        sid = row.get("sub_strategy_id") or row.get("pillar_id") or "untracked"
        # Map sub-strategies to avoid orphan sections or omissions
        if sid in ("preipo-access", "quantum-compute", "frontier-bets"):
            sid = "frontier-bets"
        elif sid == "other":
            sid = "untracked"

        holdings[ticker] = {
            "subStrategyId": sid,
            "targetPct":     row.get("target_weight") or 0,
            "role":          row.get("lifecycle_status") or "",
            "thesisNote":    row.get("thesis_for_inclusion") or "",
            "thesisBreakers": [],
        }
    return holdings


def assign_action(ticker: str, actual_pct: float, target_pct: float, existing_action: str = "") -> str:
    return derive_action(ticker, actual_pct, target_pct)


def generate_section(thesis_map: dict, actual_map: dict, total_value: float) -> str:
    today = date.today().isoformat()

    # ── Current % and target % both sourced from domain_model.sqlite
    #    (Wave 3 full cutover — no portfolio.json read remains).
    current_data = _compute_current_weights(DOMAIN_DB)
    target_data  = {"holdings": _load_target_weights(DOMAIN_DB)}

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
    lines.append(f"*Generated {today} · Source: `domain_model.sqlite` (investment + account_investment, broker-synced live holdings)*")
    lines.append(f"*Portfolio value: ${total_value:,.0f}. Refresh: `python3 plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py --write`*")
    lines.append("")

    grand_actual = 0.0
    grand_target = 0.0

    order = ["sa-asi-race", "cybersecurity", "sovereign-finance", "quality-saas", "frontier-bets", "metabolic-rewriting", "cash", "untracked"]
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
            
            # Fetch DCF projection for AI Signal & Upside (domain_model.sqlite, ADR-029)
            ai_signal = "—"
            upside_str = "—"
            entry = _get_latest_ai_projection(ticker)
            if entry:
                fv = entry.get("fair_value")
                curr_price = a.get("price")
                if fv and curr_price and curr_price > 0:
                    upside = ((fv - curr_price) / curr_price) * 100
                    upside_str = f"+{upside:.1f}%" if upside >= 0 else f"{upside:.1f}%"
                ai_action = entry.get("action")
                if ai_action:
                    ai_signal = ai_action

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
        entry = _get_latest_ai_agent_projection(ticker)
        if entry:
            action = entry.get("action")
            if action:
                return action
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
    parser.add_argument("--thesis-md", default=str(THESIS_MD))
    parser.add_argument("--db", default=str(DOMAIN_DB), help="Path to domain_model.sqlite")
    args = parser.parse_args()

    # Wave 3 full cutover: portfolio data (per-position shares/price AND the
    # total) is sourced entirely from domain_model.sqlite via
    # portfolio_io.load_portfolio_state(). --portfolio is retained only for
    # CLI/back-compat and passthrough to generate_sub_strategy_blocks.run()
    # below; it is no longer read for shares/price/total here.
    actual_map, total_value = build_actual_map(Path(args.db))
    thesis_map = build_thesis_map(Path(args.db))

    section = generate_section(thesis_map, actual_map, total_value)

    if args.write:
        md_path = Path(args.thesis_md)
        # 1. Load weights: current % and target % both from sqlite
        current_data = _compute_current_weights(Path(args.db))
        target_data  = {"holdings": _load_target_weights(Path(args.db))}

        # 2. Update Section IV (blueprint)
        update_thesis_md(section, md_path)

        # 3. Enrich early section tables with live data
        content = md_path.read_text()
        updated = update_section_tables(content, current_data, target_data)

        # 4. Sync header metadata
        import datetime
        thesis_version = "Investment Thesis"
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
        run_sub_blocks(Path(args.db))
    else:
        print(section)


if __name__ == "__main__":
    main()
