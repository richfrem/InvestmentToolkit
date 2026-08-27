#!/usr/bin/env python3
"""
test_questrade_price_refresh.py - Unit tests for Questrade live price refresh service.

Purpose:
    Validates that Questrade get_quotes responses correctly upsert into
    domain_model.sqlite's investment_price table, while safely excluding
    synthetic cash rows and non-USD-denominated investments this domain
    model cannot yet safely re-price from a Questrade quote.

Layer:
    Testing / Plugins / Questrade

Usage Examples:
    pytest plugins/questrade/tests/test_questrade_price_refresh.py
    python3 plugins/questrade/tests/test_questrade_price_refresh.py

Key Functions (Index):
    - test_refresh_writes_price_for_usd_equity()
    - test_refresh_skips_non_usd_currency()
    - test_refresh_excludes_cash_investments()
    - test_batch_symbols_splits_at_twenty()
    - test_refresh_handles_unresolvable_quote_gracefully()
    - test_refresh_upserts_not_duplicates()

Key Input Dependencies:
    - plugins/questrade/scripts/questrade_price_refresh.py
"""

import sys
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/questrade/scripts"))

from domain_model.db_client import initialize_db
from domain_model.investment_repository import resolve_investment
from domain_model.investment_price_repository import get_investment_price

from questrade_price_refresh import (
    _select_investments_for_quote_refresh,
    _batch_symbols,
    persist_quotes_to_prices,
)


def setup_in_memory_db() -> sqlite3.Connection:
    """Create in-memory SQLite db with full domain model schema."""
    return initialize_db(":memory:")


def test_refresh_writes_price_for_usd_equity():
    """Happy path: a real USD equity quote writes its lastPrice into investment_price."""
    conn = setup_in_memory_db()
    resolve_investment(conn, "BTDR", asset_class="EQUITY", currency="USD")

    quote = {
        "symbol": "BTDR", "currency": "USD",
        "lastPrice": 11.845, "bidPrice": 11.84, "askPrice": 11.85,
        "quoteTime": "2026-08-27T14:24:39Z",
    }
    written, skipped = persist_quotes_to_prices(
        conn,
        quotes_by_symbol={"BTDR": quote},
        investments_by_symbol={"BTDR": {"investment_id": "BTDR", "symbol": "BTDR", "currency": "USD"}},
    )

    assert written == 1
    assert skipped == []
    price_row = get_investment_price(conn, "BTDR")
    assert price_row["price"] == 11.845
    assert price_row["currency"] == "USD"

    print("✓ test_refresh_writes_price_for_usd_equity passed!")


def test_refresh_skips_non_usd_currency():
    """Guards against writing a Questrade quote price under investment_price's
    assumed-USD convention for a genuinely non-USD-denominated holding (e.g.
    DLR.TO, PSU-U.TO) — Questrade get_positions carries no currency signal to
    catch this upstream, so this must be enforced here. Also verifies the
    second-layer guard in persist_quotes_to_prices itself, in case a caller
    bypasses the selection filter."""
    conn = setup_in_memory_db()
    resolve_investment(conn, "DLR.TO", asset_class="EQUITY", currency="CAD")

    all_investments = _select_investments_for_quote_refresh(conn)
    assert "DLR.TO" not in {inv["symbol"] for inv in all_investments}

    # Second-layer guard: even if a caller force-includes it, it must not be written.
    quote = {"symbol": "DLR.TO", "currency": "CAD", "lastPrice": 14.50}
    written, skipped = persist_quotes_to_prices(
        conn,
        quotes_by_symbol={"DLR.TO": quote},
        investments_by_symbol={"DLR.TO": {"investment_id": "DLR.TO", "symbol": "DLR.TO", "currency": "CAD"}},
    )
    assert written == 0
    assert "DLR.TO" in skipped
    assert get_investment_price(conn, "DLR.TO") is None

    print("✓ test_refresh_skips_non_usd_currency passed!")


def test_refresh_excludes_cash_investments():
    """get_quotes would never resolve a synthetic symbol like CASH_USD anyway, but
    this skill must not even attempt to include it in a batch, for clarity/safety
    and to avoid wasting a symbol slot in the 20-per-call cap."""
    conn = setup_in_memory_db()
    resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD", name="US Dollar Cash")
    resolve_investment(conn, "BTDR", asset_class="EQUITY", currency="USD")

    eligible = _select_investments_for_quote_refresh(conn)
    symbols = {inv["symbol"] for inv in eligible}
    assert "CASH_USD" not in symbols
    assert "BTDR" in symbols

    print("✓ test_refresh_excludes_cash_investments passed!")


def test_batch_symbols_splits_at_twenty():
    """get_quotes caps at 20 symbols per call — verify the split boundary exactly."""
    twenty_four = [f"SYM{i}" for i in range(24)]
    batches = _batch_symbols(twenty_four, batch_size=20)
    assert len(batches) == 2
    assert len(batches[0]) == 20
    assert len(batches[1]) == 4

    exactly_twenty = [f"SYM{i}" for i in range(20)]
    assert _batch_symbols(exactly_twenty, batch_size=20) == [exactly_twenty]

    assert _batch_symbols([], batch_size=20) == []

    print("✓ test_batch_symbols_splits_at_twenty passed!")


def test_refresh_handles_unresolvable_quote_gracefully():
    """One bad quote (e.g. a halted security with no usable price field) must not
    abort the rest of the batch — mirrors _run_portfolio_refresh's 'one bad row
    doesn't kill the run' spirit elsewhere in this plugin."""
    conn = setup_in_memory_db()
    resolve_investment(conn, "BTDR", asset_class="EQUITY", currency="USD")
    resolve_investment(conn, "HALTED", asset_class="EQUITY", currency="USD")

    quotes = {
        "BTDR": {"symbol": "BTDR", "currency": "USD", "lastPrice": 11.845},
        "HALTED": {"symbol": "HALTED", "currency": "USD"},  # no lastPrice at all
    }
    investments = {
        "BTDR": {"investment_id": "BTDR", "symbol": "BTDR", "currency": "USD"},
        "HALTED": {"investment_id": "HALTED", "symbol": "HALTED", "currency": "USD"},
    }
    written, skipped = persist_quotes_to_prices(conn, quotes, investments)

    assert written == 1
    assert "HALTED" in skipped
    assert get_investment_price(conn, "BTDR")["price"] == 11.845
    assert get_investment_price(conn, "HALTED") is None

    print("✓ test_refresh_handles_unresolvable_quote_gracefully passed!")


def test_refresh_upserts_not_duplicates():
    """Re-confirms upsert_investment_price's ON CONFLICT behavior end-to-end
    through this new caller, catching any accidental future regression to a
    raw INSERT (investment_price is PRIMARY KEY(investment_id) — one row per
    symbol, last-write-wins)."""
    conn = setup_in_memory_db()
    resolve_investment(conn, "BTDR", asset_class="EQUITY", currency="USD")
    investments = {"BTDR": {"investment_id": "BTDR", "symbol": "BTDR", "currency": "USD"}}

    persist_quotes_to_prices(conn, {"BTDR": {"symbol": "BTDR", "currency": "USD", "lastPrice": 11.845}}, investments)
    persist_quotes_to_prices(conn, {"BTDR": {"symbol": "BTDR", "currency": "USD", "lastPrice": 12.10}}, investments)

    count = conn.execute("SELECT COUNT(*) FROM investment_price WHERE investment_id = 'BTDR'").fetchone()[0]
    assert count == 1
    assert get_investment_price(conn, "BTDR")["price"] == 12.10

    print("✓ test_refresh_upserts_not_duplicates passed!")


if __name__ == "__main__":
    test_refresh_writes_price_for_usd_equity()
    test_refresh_skips_non_usd_currency()
    test_refresh_excludes_cash_investments()
    test_batch_symbols_splits_at_twenty()
    test_refresh_handles_unresolvable_quote_gracefully()
    test_refresh_upserts_not_duplicates()
