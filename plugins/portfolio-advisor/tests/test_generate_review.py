"""Tests for generate_review.py's compute_thesis_summary(), which reads
domain_model.sqlite (investment.target_weight via list_investments) and counts
EXIT/INITIATE holdings across all investments, not per pillar.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    resolve_investment,
    update_investment_fields,
)
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402

import generate_review as gr  # noqa: E402


class TestLoadPortfolioHoldingsFromDb:
    """Portfolio holdings for header population come from domain_model.sqlite."""

    def test_returns_symbol_shares_price_rows(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        conn = initialize_db(str(db_path))
        upsert_account(conn, "TFSA", "TFSA", "TFSA")
        aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
        upsert_investment_price(conn, aapl_id, price=200.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_account_investment(
            conn, "TFSA", aapl_id, quantity=5, average_cost=180.0,
            book_value=900.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
        conn.close()

        holdings = gr.load_portfolio_holdings_from_db(db_path)
        assert holdings == [{"symbol": "AAPL", "shares": 5, "price": 200.0}]

    def test_missing_db_returns_empty_list(self, tmp_path):
        assert gr.load_portfolio_holdings_from_db(tmp_path / "missing.sqlite") == []


def _make_db(tmp_path):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        exit_id = resolve_investment(conn, "EXITME")
        update_investment_fields(conn, exit_id, target_weight=0.0)
        init_id = resolve_investment(conn, "NEWCO")
        update_investment_fields(conn, init_id, target_weight=5.0)
        held_id = resolve_investment(conn, "HELD")
        update_investment_fields(conn, held_id, target_weight=10.0)
    finally:
        conn.close()
    return db_path


def test_compute_thesis_summary_reads_target_weight_from_sqlite(tmp_path):
    """EXIT and INITIATE lists come from investment.target_weight."""
    db_path = _make_db(tmp_path)
    portfolio = [
        {"symbol": "EXITME", "shares": 10},
        {"symbol": "HELD", "shares": 5},
    ]

    summary = gr.compute_thesis_summary(portfolio, db_path=db_path)

    assert summary["exit_count"] == 1
    assert summary["exit_tickers"] == ["EXITME"]
    assert summary["initiate_count"] == 1
    assert summary["initiate_tickers"] == ["NEWCO"]
    assert summary["thesis_name"] == "Investment Thesis"


def test_thesis_version_is_the_latest_change_log_version(tmp_path):
    """The version shown in the review is the newest portfolio_change_log version."""
    from domain_model.portfolio_change_log_repository import record_change
    db_path = _make_db(tmp_path)
    assert gr.compute_thesis_summary([], db_path=db_path)["thesis_version"] == "unversioned"
    conn = initialize_db(str(db_path))
    record_change(conn, "first")
    record_change(conn, "second")
    conn.close()
    assert gr.compute_thesis_summary([], db_path=db_path)["thesis_version"] == "2"


def test_held_ticker_with_no_target_is_not_exit_flagged(tmp_path):
    """A NULL target weight means no thesis, not a zero target, so it is not an EXIT."""
    db_path = _make_db(tmp_path)
    conn = initialize_db(str(db_path))
    resolve_investment(conn, "NOTARGET")
    conn.close()
    summary = gr.compute_thesis_summary([{"symbol": "NOTARGET", "shares": 3}], db_path=db_path)
    assert "NOTARGET" not in summary["exit_tickers"]


def test_no_thesis_holdings_fails_loudly(tmp_path):
    """An empty thesis is an error, never an empty review header."""
    import pytest
    db_path = tmp_path / "empty.sqlite"
    initialize_db(str(db_path)).close()
    with pytest.raises(ValueError, match="thesis"):
        gr.compute_thesis_summary([], db_path=db_path)


def test_missing_db_fails_loudly(tmp_path):
    """A missing database is an error."""
    import pytest
    with pytest.raises(ValueError, match="not found"):
        gr.compute_thesis_summary([], db_path=tmp_path / "missing.sqlite")


def test_module_has_no_json_thesis_path():
    """generate_review.py has no thesis file path or JSON loader."""
    assert not hasattr(gr, "THESIS_PATH") and not hasattr(gr, "load_json")
