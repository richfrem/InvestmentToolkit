import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.portfolio_repository import (  # noqa: E402
    get_account_market_values,
    get_portfolio_total_value,
    load_portfolio_state_from_db,
)


def _seed_two_accounts(conn):
    """AAPL held in both TFSA (10 sh @ $150) and RRSP (3 sh @ $150) -- deliberately
    the exact shape Task 0 found real data has (same symbol, different accounts,
    different quantities), to guard against the RRSP-collapses-into-TFSA bug class.
    """
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    upsert_account(conn, "RRSP", "RRSP", "RRSP")
    aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
    upsert_investment_price(conn, aapl_id, price=150.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
    upsert_account_investment(
        conn, "TFSA", aapl_id, quantity=10, average_cost=140.0,
        book_value=1400.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
    )
    upsert_account_investment(
        conn, "RRSP", aapl_id, quantity=3, average_cost=140.0,
        book_value=420.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
    )
    return aapl_id


def test_get_account_market_values_keeps_accounts_separate(tmp_path):
    """The direct regression guard for Task 0's real finding: TFSA and RRSP must
    never be collapsed into a single figure before the account-level query returns.
    """
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_two_accounts(conn)
    values = get_account_market_values(conn)
    assert values == {"TFSA": 1500.0, "RRSP": 450.0}  # 10*150, 3*150 -- never summed together here


def test_get_portfolio_total_value_is_the_sum_of_account_values(tmp_path):
    """The portfolio total must be traceable as SUM(per-account values), not an
    independent flat query -- this is what "preserve account boundaries before
    rolling up" means concretely.
    """
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_two_accounts(conn)
    account_values = get_account_market_values(conn)
    total = get_portfolio_total_value(conn)
    assert total == sum(account_values.values()) == 1950.0


def test_get_portfolio_total_value_includes_cash_investment_rows(tmp_path):
    """Cash is a real INVESTMENT row (asset_class='CASH', Wave 0 resolved decision 5),
    held via account_investment like any other position -- it must count toward the
    account and portfolio totals the same way a stock position does.
    """
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_two_accounts(conn)
    cash_id = resolve_investment(conn, "CASH_USD", asset_class="CASH", currency="USD")
    upsert_investment_price(conn, cash_id, price=1.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
    upsert_account_investment(
        conn, "TFSA", cash_id, quantity=250.0, average_cost=1.0,
        book_value=250.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
    )
    account_values = get_account_market_values(conn)
    assert account_values["TFSA"] == 1750.0  # 1500 (AAPL) + 250 (cash)
    assert get_portfolio_total_value(conn) == 2200.0  # 1750 (TFSA) + 450 (RRSP)


def test_load_portfolio_state_from_db_returns_shares_prices_and_total(tmp_path):
    """The portfolio_io.py-compatible shape -- shares/prices aggregated across
    accounts by symbol (portfolio_io.py's own existing aggregation contract),
    total_usd delegated to get_portfolio_total_value() (single source of truth
    for the total, not a second independent computation)."""
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_two_accounts(conn)
    state = load_portfolio_state_from_db(conn)
    assert state["shares"]["AAPL"] == 13  # 10 (TFSA) + 3 (RRSP), aggregated by symbol across accounts
    assert state["prices"]["AAPL"] == 150.0
    assert state["total_usd"] == get_portfolio_total_value(conn) == 1950.0
    assert state["_totals_from_broker"] is False  # per ADR-030: always computed, never a stored broker column


def test_position_with_no_price_row_contributes_zero_but_still_appears_in_shares(tmp_path):
    """Finding 1 regression guard: a newly synced position (account_investment row
    exists) with no investment_price row yet (price not fetched) must NOT
    contribute to get_account_market_values()/get_portfolio_total_value() (inner
    JOIN excludes it), but MUST still appear in load_portfolio_state_from_db()'s
    shares dict (LEFT JOIN includes it) with no corresponding prices entry. This
    is intentional -- see the comment above get_account_market_values()'s query --
    not a bug, but previously undocumented and untested.
    """
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    _seed_two_accounts(conn)
    new_id = resolve_investment(conn, "NEWSYM", asset_class="EQUITY", currency="USD")
    # Deliberately no upsert_investment_price call for NEWSYM.
    upsert_account_investment(
        conn, "TFSA", new_id, quantity=5, average_cost=10.0,
        book_value=50.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
    )

    account_values = get_account_market_values(conn)
    assert account_values["TFSA"] == 1500.0  # unchanged -- NEWSYM contributes 0, not a phantom value
    assert get_portfolio_total_value(conn) == 1950.0  # unchanged

    state = load_portfolio_state_from_db(conn)
    assert state["shares"]["NEWSYM"] == 5  # still visible via LEFT JOIN
    assert "NEWSYM" not in state["prices"]  # no price row yet -- no fabricated price
    assert state["total_usd"] == 1950.0  # NEWSYM still contributes 0 to the total
