#!/usr/bin/env python3
"""
questrade_price_refresh.py - Python Service for Questrade live price refresh.

Purpose:
    Fetches live quotes for currently-held, USD-denominated, non-cash
    investments via Questrade's get_quotes MCP tool and writes them into
    domain_model.sqlite's investment_price table. An optional, user-triggered
    augment to the existing TradingView/yfinance pricing baseline (Rule #20)
    — fully separate from questrade_sync.py, which only syncs holdings/
    balances/cash and never touches investment_price.

Layer:
    Plugins / Questrade / Services

Usage Examples:
    # Direct payload sync from JSON file (skill stages {"quotes": {...}}):
    python3 plugins/questrade/scripts/questrade_price_refresh.py --payload payload.json

    # Dry-run validation:
    python3 plugins/questrade/scripts/questrade_price_refresh.py --payload payload.json --dry-run

Key Functions (Index):
    - _select_investments_for_quote_refresh() : Eligible investments for a live quote (USD, non-cash).
    - _batch_symbols()                        : Splits a symbol list into <=20-symbol get_quotes batches.
    - _extract_quote_price()                  : Pulls the live tradable price out of one quote entry.
    - persist_quotes_to_prices()              : Upserts investment_price rows from quotes, currency-checked.
    - main()                                  : CLI entrypoint for parsing JSON payloads.

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (Domain Database)
"""

import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Any

# ── path bootstrap ──────────────────────────────────────────────────────────
# _HERE resolves through the skills/questrade-refresh-prices/scripts/ symlink
# to this canonical file at plugins/questrade/scripts/ — parents[2] from there
# is repo root (see questrade_sync.py's own note on this exact bug).
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[2]
_PY_SERVICES = _REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(_PY_SERVICES))

from domain_model.investment_repository import list_investments  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402

_DEFAULT_DB_PATH = str(_REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite")


def _select_investments_for_quote_refresh(conn: sqlite3.Connection) -> list[dict]:
    """Return investment rows eligible for a live Questrade quote refresh.

    Excludes:
      - asset_class == 'CASH' (CASH_USD and any future synthetic cash rows —
        not real Questrade tickers, get_quotes would never resolve them).
      - currency != 'USD' (e.g. a genuinely CAD-denominated row like DLR.TO or
        PSU-U.TO). Questrade's get_positions carries no currency field, so
        questrade_sync.py cannot detect this upstream — see the
        "domain_model.sqlite account_id convention" section's sibling note in
        references/questrade-tool-schemas.md for the same class of gap.
    """
    return [
        inv
        for inv in list_investments(conn)
        if inv.get("asset_class") != "CASH" and inv.get("currency") == "USD"
    ]


def _batch_symbols(symbols: list[str], batch_size: int = 20) -> list[list[str]]:
    """Split a symbol list into <=batch_size chunks for get_quotes (20/call cap)."""
    return [symbols[i : i + batch_size] for i in range(0, len(symbols), batch_size)]


def _extract_quote_price(quote: dict) -> Optional[float]:
    """Pull the live tradable price out of one get_quotes response entry.

    Field name confirmed via a live call (2026-08-27, BTDR) — see
    references/questrade-tool-schemas.md's get_quotes response-shape section.
    Returns None for a halted/delisted security or any quote missing a usable
    lastPrice, rather than raising, so one bad symbol doesn't abort a batch.
    """
    price = quote.get("lastPrice")
    if price is None:
        return None
    try:
        return float(price)
    except (TypeError, ValueError):
        return None


def persist_quotes_to_prices(
    conn: sqlite3.Connection,
    quotes_by_symbol: dict[str, dict],
    investments_by_symbol: dict[str, dict],
) -> tuple[int, list[str]]:
    """Upsert one investment_price row per resolvable, currency-safe quote.

    Args:
        conn: Open SQLite connection to domain_model.sqlite.
        quotes_by_symbol: symbol -> raw get_quotes response entry.
        investments_by_symbol: symbol -> investment row (investment_id, symbol),
            used to resolve investment_id.

    Returns:
        (written_count, skipped_symbols) — skipped_symbols covers both
        currency-ineligible rows and rows with no usable quote price.

    Currency safety: the LIVE quote's own 'currency' field is the authoritative
    check here, not the stored investment.currency column — that column is
    unreliable (this domain model hardcodes currency='USD' on every investment
    row today, including genuinely CAD-denominated tickers like PSU-U.TO; see
    questrade-tool-schemas.md). Checking the stored value alone would let a
    mislabeled ticker's CAD price slip through under the USD label.
    """
    now = datetime.now(timezone.utc).isoformat()
    written = 0
    skipped: list[str] = []

    for symbol, quote in quotes_by_symbol.items():
        investment = investments_by_symbol.get(symbol)
        if investment is None or quote.get("currency") != "USD":
            skipped.append(symbol)
            continue

        price = _extract_quote_price(quote)
        if price is None:
            skipped.append(symbol)
            continue

        upsert_investment_price(
            conn=conn,
            investment_id=investment["investment_id"],
            price=price,
            currency="USD",
            fetched_at=now,
        )
        written += 1

    return written, skipped


def main() -> None:
    """CLI entry point for refreshing investment_price from a staged quotes JSON payload."""
    parser = argparse.ArgumentParser(description="Refresh live Questrade prices into domain_model.sqlite")
    parser.add_argument("--payload", type=str, required=True, help="Path to JSON payload file: {\"quotes\": {symbol: <get_quotes entry>}}")
    parser.add_argument("--db-path", type=str, default=_DEFAULT_DB_PATH, help="Path to SQLite database")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing to database")
    args = parser.parse_args()

    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"Error: Payload file not found at {payload_path}", file=sys.stderr)
        sys.exit(1)

    with open(payload_path) as f:
        data = json.load(f)

    quotes_by_symbol: dict[str, Any] = data.get("quotes", {})

    if args.dry_run:
        print(f"Dry run: Found {len(quotes_by_symbol)} quote(s) in payload.")
        return

    conn = sqlite3.connect(args.db_path)
    try:
        eligible = _select_investments_for_quote_refresh(conn)
        investments_by_symbol = {inv["symbol"]: inv for inv in eligible}
        written, skipped = persist_quotes_to_prices(conn, quotes_by_symbol, investments_by_symbol)
        print(f"✓ Successfully refreshed {written} price(s) in domain_model.sqlite")
        if skipped:
            print(f"⚠ Skipped {len(skipped)} symbol(s) (non-USD currency or no usable price): {skipped}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
