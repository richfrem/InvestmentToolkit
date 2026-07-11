"""
ticker_aliases.py — Canonical ticker normalization and special-symbol definitions.

Single source of truth for:
  - Ticker aliases (e.g. PSU.U → PSU-U.TO from the Questrade broker format)
  - Reserved cash symbols (USD_CASH — the internal sentinel for uninvested USD)

Import this module instead of scattering inline `if ticker == "USD_CASH"` checks.

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Maps ticker synonyms)
"""

# Questrade returns "PSU.U" without the exchange suffix; normalize to the TSX symbol.
# Add entries here when a new broker alias is discovered.
TICKER_ALIASES: dict[str, str] = {
    "PSU.U": "PSU-U.TO",
    "PSU.U.TO": "PSU-U.TO",
}

# Tickers that represent cash/liquidity reserves, not tradeable equities.
# These are excluded from valuation, drift, and opportunity scans.
CASH_SYMBOLS: frozenset[str] = frozenset({"USD_CASH"})

# Human-readable display names for reserved symbols.
CASH_DISPLAY_NAMES: dict[str, str] = {
    "USD_CASH": "US Dollar Cash",
}


def normalize_ticker(ticker: str) -> str:
    """Return the canonical ticker, resolving any broker aliases."""
    return TICKER_ALIASES.get(ticker, ticker)


def is_cash(ticker: str) -> bool:
    """Return True if the ticker represents a cash/liquidity position."""
    return ticker in CASH_SYMBOLS or ticker.endswith("_CASH")
