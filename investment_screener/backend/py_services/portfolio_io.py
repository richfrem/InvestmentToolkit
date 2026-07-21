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
