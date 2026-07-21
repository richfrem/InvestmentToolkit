"""Portfolio/account value calculations expressed against the relational model
(account_investment JOIN investment_price, GROUP BY account_id), not as Python
loops reconstructing the old JSON tree shape.

Per ADR-030: these are read-time-only queries. No table stores an account or
portfolio total -- every number here is computed fresh from account_investment/
investment_price on each call. Account boundaries are preserved first
(get_account_market_values' GROUP BY), and the portfolio total is always the
sum of those per-account results (get_portfolio_total_value), never an
independent flat query -- this is the direct fix for the bug class Task 0
found (RRSP holdings silently collapsing into TFSA).
"""

import sqlite3


def get_account_market_values(conn: sqlite3.Connection) -> dict[str, float]:
    """Market value per real account: SUM(quantity * price), grouped by account_id.

    Includes cash rows (asset_class='CASH' investments held via account_investment
    like any other position, per Wave 0's resolved decision 5) -- no special-casing,
    the JOIN treats them identically to equity positions.
    """
    # Deliberate inner JOIN (not LEFT JOIN): a position with an account_investment
    # row but no investment_price row yet (e.g. a symbol just synced from the
    # broker before its first price fetch) contributes zero to this total rather
    # than a fabricated price or a crash -- it simply drops out of the SUM until a
    # price is synced. This is intentional, not a bug: see
    # test_position_with_no_price_row_contributes_zero_but_still_appears_in_shares
    # in test_portfolio_repository.py, which also documents that the same symbol
    # still appears in load_portfolio_state_from_db()'s shares dict (LEFT JOIN),
    # so shares and total_usd can legitimately disagree on coverage for that symbol.
    cursor = conn.execute(
        """
        SELECT ai.account_id AS account_id, SUM(ai.quantity * ip.price) AS market_value
        FROM account_investment ai
        JOIN investment_price ip ON ip.investment_id = ai.investment_id
        GROUP BY ai.account_id;
        """
    )
    return {row[0]: row[1] for row in cursor.fetchall()}


def get_portfolio_total_value(conn: sqlite3.Connection) -> float:
    """Portfolio-wide total: the sum of get_account_market_values()'s own results.

    Deliberately not a separate flat SUM(quantity * price) query with no
    GROUP BY -- the portfolio total must always be traceable as a rollup of
    account-level totals, never a query that can silently ignore account
    boundaries.
    """
    return sum(get_account_market_values(conn).values())


def load_portfolio_state_from_db(conn: sqlite3.Connection) -> dict:
    """portfolio_io.py::load_portfolio_state()-compatible shape.

    shares/prices are aggregated across accounts by symbol (matching
    portfolio_io.py's own existing aggregation contract for its 7+ real
    callers); total_usd delegates to get_portfolio_total_value() so there is
    exactly one computation of the total in this codebase, not two.
    """
    cursor = conn.execute(
        """
        SELECT i.symbol AS symbol, SUM(ai.quantity) AS total_shares, MAX(ip.price) AS price
        FROM account_investment ai
        JOIN investment i ON i.investment_id = ai.investment_id
        LEFT JOIN investment_price ip ON ip.investment_id = ai.investment_id
        GROUP BY i.symbol;
        """
    )
    shares: dict[str, float] = {}
    prices: dict[str, float] = {}
    for symbol, total_shares, price in cursor.fetchall():
        if total_shares and total_shares > 0:
            shares[symbol] = total_shares
        if price and price > 0:
            prices[symbol] = price

    return {
        "shares": shares,
        "prices": prices,
        "total_usd": get_portfolio_total_value(conn),
        # PLACEHOLDER, not sourced FX data: portfolio_io.py's load_portfolio_state()
        # (the JSON-backed function this module replaces per Task 4's plan) reads
        # totals.exchangeRate from portfolio.json and only falls back to this same
        # 1.38 literal when that key is absent -- this module has no equivalent
        # totals/exchangeRate column to read from yet, so it always uses the
        # fallback. Real FX-rate sourcing is out of this task's scope: per
        # CLAUDE.md pitfall #27, it must be inferred from TradingView's own native
        # values (e.g. totalEquityCADCombined / totalEquityUSDCombined), never an
        # external FX API call. Wiring that in is a known gap for a later task.
        "exchange_rate": 1.38,
        "_totals_from_broker": False,  # per ADR-030: always computed, never stored/read from a broker column
    }
