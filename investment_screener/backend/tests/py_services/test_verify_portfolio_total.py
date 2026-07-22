"""Tests for verify_portfolio_total.py — the ADR-030 reconciliation safeguard.

Covers the Wave 3 Task 6 cutover of compute_our_total() from portfolio.json
onto domain_model.sqlite: in stored-price mode the total must equal
get_portfolio_total_value() (never an independent shares*price re-sum), and
the per-position breakdown must still be derivable for the diff/reconciliation
report.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_verify_portfolio_total.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

import verify_portfolio_total as vpt  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.portfolio_repository import get_portfolio_total_value  # noqa: E402
from domain_model.broker_reported_total_repository import upsert_broker_reported_total  # noqa: E402


class TestGetTvTotalsCachedReadsSqlite:
    def test_returns_error_when_never_synced(self, tmp_path):
        result = vpt.get_tv_totals_cached(db_path=tmp_path / "missing.sqlite")
        assert "error" in result

    def test_reads_broker_reported_total_from_db(self, tmp_path):
        db_path = tmp_path / "domain_model.sqlite"
        conn = initialize_db(str(db_path))
        upsert_broker_reported_total(conn, 30373.98, 41900.0, "2026-07-20T00:00:00Z", "tv_authoritative")
        conn.close()
        result = vpt.get_tv_totals_cached(db_path=db_path)
        assert result["grandTotalUSD"] == 30373.98
        assert result["source"] == "tv_authoritative"

    def test_large_variance_fires_fail_path(self, tmp_path):
        """Computed (1950) vs broker-reported (5000) => $3050 gap must classify FAIL."""
        db_path, computed_total = _seed(tmp_path)
        conn = initialize_db(str(db_path))
        upsert_broker_reported_total(conn, 5000.0, None, "2026-07-20T00:00:00Z", "tv_authoritative")
        conn.close()
        tv = vpt.get_tv_totals_cached(db_path=db_path)
        our_total, _ = vpt.compute_our_total(use_live_prices=False, db_path=db_path)
        diff = our_total - tv["grandTotalUSD"]
        assert vpt.classify_reconciliation(diff) == "FAIL"

    def test_small_variance_passes(self, tmp_path):
        db_path, computed_total = _seed(tmp_path)  # 1950
        conn = initialize_db(str(db_path))
        upsert_broker_reported_total(conn, 1955.0, None, "2026-07-20T00:00:00Z", "tv_authoritative")
        conn.close()
        tv = vpt.get_tv_totals_cached(db_path=db_path)
        our_total, _ = vpt.compute_our_total(use_live_prices=False, db_path=db_path)
        assert vpt.classify_reconciliation(our_total - tv["grandTotalUSD"]) == "PASS"


def _seed(tmp_path):
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
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
    total = get_portfolio_total_value(conn)
    conn.close()
    return db_path, total


class TestComputeOurTotalReadsSqlite:
    def test_stored_price_total_matches_get_portfolio_total_value(self, tmp_path):
        db_path, expected_total = _seed(tmp_path)
        total, breakdown = vpt.compute_our_total(use_live_prices=False, db_path=db_path)
        assert total == expected_total == 1950.0
        assert {b["symbol"] for b in breakdown} == {"AAPL"}
        assert breakdown[0]["shares"] == 13  # aggregated across TFSA + RRSP

    def test_missing_db_returns_zero_and_empty(self, tmp_path):
        total, breakdown = vpt.compute_our_total(db_path=tmp_path / "missing.sqlite")
        assert total == 0.0
        assert breakdown == []

    def test_position_with_no_price_row_reported_as_no_price_source(self, tmp_path):
        db_path = tmp_path / "domain_model.sqlite"
        conn = initialize_db(str(db_path))
        upsert_account(conn, "TFSA", "TFSA", "TFSA")
        msft_id = resolve_investment(conn, "MSFT", asset_class="EQUITY", currency="USD")
        upsert_account_investment(
            conn, "TFSA", msft_id, quantity=5, average_cost=100.0,
            book_value=500.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
        conn.close()

        total, breakdown = vpt.compute_our_total(use_live_prices=False, db_path=db_path)
        assert total == 0.0  # no price row -> contributes $0, per get_account_market_values' INNER JOIN
        assert breakdown[0]["source"] == "no_price"
