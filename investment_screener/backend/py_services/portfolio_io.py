#!/usr/bin/env python3
"""
portfolio_io.py - Python utility script.

Purpose:
    portfolio_io.py — Single source of truth for portfolio data I/O.

Safe primitives shared by ALL portfolio scripts (sync_portfolio_roles,
generate_portfolio_blueprint, refresh_all, etc.).

Critical invariant:
  load_portfolio_state() reads totals.totalUSD from portfolio.json as the
  authoritative denominator for weight calculations. It NEVER computes the
  portfolio total from shares×price (which differs from the broker-reported total
  when cash positions exist outside individual holdings).

Layer: Backend / py_services / Shared I/O

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Loads and saves portfolio)

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
import json
import re
import sys
from pathlib import Path
from typing import Any

# ── path bootstrap ──────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from ticker_aliases import normalize_ticker  # noqa: E402

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
    """Read portfolio.json and return a safe state dict.

    Uses totals.totalUSD as the authoritative denominator. Falls back to
    computing from shares×price only when totals key is absent (flat-list format).

    Args:
        portfolio_path: Path to portfolio.json.

    Returns:
        Dict with keys:
          - shares:       {symbol: float} — normalized ticker → share count
          - prices:       {symbol: float} — normalized ticker → last price
          - total_usd:    float           — broker-reported total (authoritative)
          - exchange_rate: float          — CAD→USD rate (default 1.38)
          - _totals_from_broker: bool     — True when total came from broker data
    """
    raw: Any = json.loads(portfolio_path.read_text())

    if isinstance(raw, list):
        holdings = raw
        totals: dict = {}
    else:
        holdings = raw.get("holdings", [])
        totals = raw.get("totals") or {}

    shares: dict[str, float] = {}
    prices: dict[str, float] = {}

    for h in holdings:
        sym = h.get("symbol") or h.get("ticker", "")
        sym = normalize_ticker(sym)
        if not sym:
            continue
        qty = float(h.get("shares") or 0)
        if qty <= 0:
            continue
        shares[sym] = shares.get(sym, 0.0) + qty

        price = float(h.get("price") or h.get("book_price") or 0)
        if price > 0:
            prices[sym] = price

    # Authoritative total: prefer broker-reported, fall back to computed
    broker_total = float(totals.get("totalUSD") or 0)
    if broker_total > 0:
        total_usd = broker_total
        from_broker = True
    else:
        total_usd = sum(shares.get(s, 0) * prices.get(s, 0) for s in shares)
        from_broker = False
        if total_usd == 0:
            print(
                "⚠ portfolio_io: could not determine portfolio total — "
                "run a TV sync first.",
                file=sys.stderr,
            )

    return {
        "shares":            shares,
        "prices":            prices,
        "total_usd":         total_usd,
        "exchange_rate":     float(totals.get("exchangeRate") or 1.38),
        "_totals_from_broker": from_broker,
    }


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
