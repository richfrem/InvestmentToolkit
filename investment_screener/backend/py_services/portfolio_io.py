#!/usr/bin/env python3
"""
portfolio_io.py - Python utility script.

Purpose:
    portfolio_io.py — Single source of truth for portfolio data I/O.

Safe primitives shared by ALL portfolio scripts (sync_portfolio_roles,
generate_portfolio_blueprint, refresh_all, etc.).

Critical invariant:
  load_portfolio_state() delegates to domain_model.portfolio_repository's
  SQLite-backed load_portfolio_state_from_db() (Wave 3 cutover). It NEVER
  computes the portfolio total from shares×price in this module — that
  computation lives exactly once, in portfolio_repository.py.

Layer: Backend / py_services / Shared I/O

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (Wave 3+; was
      portfolio.json prior to this cutover)

Layer:
    Backend / Python Services

Usage Examples:
    TBD

Key Functions (Index):
    - load_portfolio_state()
    - compute_weights()
    - replace_block()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
import re
import sys
from pathlib import Path
from typing import Any

# ── path bootstrap ──────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from ticker_aliases import normalize_ticker  # noqa: E402

# Wave 3 cutover: domain_model.sqlite is the sole source of truth for
# load_portfolio_state(). See domain_model/portfolio_repository.py.
_DB_PATH = str(_HERE / ".." / "data" / "domain_model.sqlite")

# ── constants ───────────────────────────────────────────────────────────────

ROLE_LABEL: dict[str, str] = {
    "accumulate": "ACCUMULATE ↑",
    "trim":       "TRIM ↓",
    "exit":       "EXIT ✕",
    "initiate":   "INITIATE ⊕",
    "watchlist":  "WATCHLIST",
    "monitor":    "MONITOR",
    "avoid":      "AVOID ✗",
}


# ── portfolio state loading ──────────────────────────────────────────────────

def load_portfolio_state(portfolio_path: Path) -> dict[str, Any]:
    """Read the portfolio state from domain_model.sqlite (Wave 3 cutover).

    ``portfolio_path`` is accepted for call-site compatibility with the 7+
    existing callers but is no longer read — SQLite (via
    ``domain_model.portfolio_repository.load_portfolio_state_from_db``) is the
    sole source of truth for this domain after Wave 3. This is a thin
    delegation, not a reimplementation: all aggregation/query logic lives in
    portfolio_repository.py.

    Args:
        portfolio_path: Retained for signature compatibility; unused.

    Returns:
        Dict with keys:
          - shares:       {symbol: float} — ticker → share count (aggregated across accounts)
          - prices:       {symbol: float} — ticker → last known price
          - total_usd:    float           — authoritative portfolio total
          - exchange_rate: float          — CAD→USD rate (default 1.38)
          - _totals_from_broker: bool     — True when total came from broker data
    """
    from domain_model.db_client import initialize_db
    from domain_model.portfolio_repository import load_portfolio_state_from_db

    conn = initialize_db(_DB_PATH)
    try:
        return load_portfolio_state_from_db(conn)
    finally:
        conn.close()


# ── target weight loading ────────────────────────────────────────────────────

def load_target_weights(db_path: str | None = None) -> dict[str, float]:
    """Read per-symbol target weights from ``investment.target_weight``.

    Wave 8: single canonical target-weight reader, replacing the several
    independent direct reads of target-portfolio.json's per-holding
    ``targetWeight`` field (generate_review_json.py's compute_target(),
    validate_weights.py's compute_target()/normalize_target(), etc.) that
    drifted out of sync with each other and with this same domain's already-
    migrated ``investment.target_weight`` column (mirrors
    portfolio_action.py's own ``_load_target_weights()``, promoted here so
    every consumer shares one implementation instead of each script keeping
    its own copy).

    Args:
        db_path: Optional override; defaults to the real domain_model.sqlite.

    Returns:
        {symbol: target_weight_pct} — only for symbols with a nonzero target.
    """
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import list_investments

    conn = initialize_db(db_path or _DB_PATH)
    try:
        rows = list_investments(conn)
    finally:
        conn.close()

    result: dict[str, float] = {}
    for row in rows:
        weight = row.get("target_weight") or 0
        if weight and weight > 0:
            result[row["symbol"]] = round(weight, 4)
    return result


def load_thesis_holdings(db_path: str | None = None) -> list[dict]:
    """Read the thesis holdings array from investment.* columns.

    Wave 8: single canonical thesis-holdings reader, replacing per-script
    direct reads of target-portfolio.json's `holdings` array (JSON shape:
    ticker/name/pillarId/subStrategyId/targetWeight/thesisForInclusion/role/
    agentRationale). Mirrors InvestmentRepository.ts's listThesisHoldings() --
    only rows with a non-null target_weight are thesis holdings.

    Args:
        db_path: Optional override; defaults to the real domain_model.sqlite.

    Returns:
        List of dicts with keys: ticker, name, pillarId, subStrategyId,
        targetWeight, thesisForInclusion, role, agentRationale.
    """
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import list_investments
    from domain_model.price_level_repository import get_price_levels

    resolved_db_path = db_path or _DB_PATH
    conn = initialize_db(resolved_db_path)
    try:
        rows = list_investments(conn)
        result = []
        for row in rows:
            if row.get("target_weight") is None:
                continue
            pl = get_price_levels(conn, row["symbol"])
            target_entry = pl["target_entry"]["price"] if pl and pl.get("target_entry") else None
            result.append({
                "ticker": row["symbol"],
                "name": row.get("name") or row["symbol"],
                "pillarId": row.get("pillar_id") or "other",
                "subStrategyId": row.get("sub_strategy_id"),
                "targetWeight": row.get("target_weight") or 0,
                "thesisForInclusion": row.get("thesis_for_inclusion") or "",
                "role": row.get("lifecycle_status") or "watchlist",
                "agentRationale": row.get("agent_rationale") or "",
                "targetEntryPrice": target_entry,
            })
        return result
    finally:
        conn.close()


# ── weight computation ───────────────────────────────────────────────────────

def compute_weights(
    shares: dict[str, float],
    prices: dict[str, float],
    total_usd: float,
) -> dict[str, float]:
    """Compute actual weight % per ticker.

    Args:
        shares:    {ticker: qty} from load_portfolio_state().
        prices:    {ticker: price} from load_portfolio_state().
        total_usd: authoritative denominator — must be the broker total, never
                   recomputed from shares×price inside this function.

    Returns:
        {ticker: weight_pct} — only for tickers that have both shares and price.
        Tickers with missing price are excluded (not counted as 0%).
    """
    if total_usd <= 0:
        return {}
    result: dict[str, float] = {}
    for sym, qty in shares.items():
        price = prices.get(sym)
        if price is None or price <= 0:
            continue
        result[sym] = round(qty * price / total_usd * 100, 4)
    return result


# ── auto-update block replacement ────────────────────────────────────────────

def replace_block(content: str, name: str, body: str) -> str:
    """Idempotently replace a named AUTO_UPDATE block in markdown content.

    Replaces everything between:
      <!-- AUTO_UPDATE_START: {name} -->
      <!-- AUTO_UPDATE_END: {name} -->

    Appends a new block if the delimiters don't exist yet.

    Args:
        content: Full .md file content.
        name:    Block identifier (e.g. "portfolio_blueprint").
        body:    New content to place inside the block.

    Returns:
        Updated content string.
    """
    start_tag = f"<!-- AUTO_UPDATE_START: {name} -->"
    end_tag   = f"<!-- AUTO_UPDATE_END: {name} -->"
    block     = f"{start_tag}\n{body.strip()}\n{end_tag}"

    pattern = (
        re.escape(start_tag)
        + r".*?"
        + re.escape(end_tag)
    )
    updated, count = re.subn(pattern, block, content, flags=re.DOTALL)
    if count == 0:
        updated = content.rstrip() + f"\n\n{block}\n"
    return updated


# ── CLI entrypoint ────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Query portfolio state and metadata.")
    parser.add_argument("--ticker", "-t", type=str, help="Check holding status and target weight for a specific ticker.")
    parser.add_argument("--pillars", action="store_true", help="List all strategy pillars and sub-strategies.")
    parser.add_argument("--json", action="store_true", help="Output in JSON format.")
    args = parser.parse_args()

    if args.pillars:
        from domain_model.pillar_repository import list_pillars, list_sub_strategies
        from domain_model.db_client import initialize_db
        conn = initialize_db(_DB_PATH)
        try:
            pillars = list_pillars(conn)
            sub_strats = list_sub_strategies(conn)
            data = {"pillars": pillars, "sub_strategies": sub_strats}
            if args.json:
                print(json.dumps(data, indent=2))
            else:
                print("Strategy Pillars:")
                for p in pillars:
                    print(f"  - {p['pillar_id']}: {p['name']} ({p.get('target_weight', 0)}%)")
                print("\nSub-Strategies:")
                for s in sub_strats:
                    print(f"  - {s['sub_strategy_id']} (Pillar: {s['pillar_id']}): {s['name']}")
        finally:
            conn.close()
        return

    if args.ticker:
        sym = normalize_ticker(args.ticker)
        state = load_portfolio_state(Path(_DB_PATH))
        shares = state.get("shares", {}).get(sym, 0.0)
        price = state.get("prices", {}).get(sym, 0.0)
        target_weights = load_target_weights()
        target_weight = target_weights.get(sym, 0.0)
        is_held = shares > 0
        
        info = {
            "ticker": sym,
            "shares": shares,
            "price": price,
            "market_value": round(shares * price, 2) if price else 0.0,
            "target_weight": target_weight,
            "is_held": is_held,
            "lifecycle_status": "core" if is_held else "watchlist",
            "permitted_actions": ["MAINTAIN", "ACCUMULATE", "TRIM", "EXIT"] if is_held else ["WATCHLIST", "INITIATE"],
        }
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            print(f"TICKER: {sym}")
            print(f"HOLDING STATUS: {'HELD' if is_held else 'NOT HELD'} (shares={shares}, market_value=${info['market_value']:,.2f})")
            print(f"TARGET WEIGHT: {target_weight}%")
            print(f"LIFECYCLE STATUS: {info['lifecycle_status']}")
            print(f"PERMITTED ACTIONS: {', '.join(info['permitted_actions'])}")
        return

    # Default: summary
    state = load_portfolio_state(Path(_DB_PATH))
    print(f"Portfolio Total USD: ${state.get('total_usd', 0.0):,.2f}")
    print(f"Total Holdings: {len(state.get('shares', {}))}")
    print(f"Cash USD: ${state.get('cash_usd', 0.0):,.2f}")


if __name__ == "__main__":
    main()

