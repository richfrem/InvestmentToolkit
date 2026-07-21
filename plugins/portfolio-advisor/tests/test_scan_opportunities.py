"""Tests for scan_opportunities.py's Wave 1 Task 7B rewire of `load_projection`/
`scan_initiate` onto domain_model.sqlite (ADR-029). All tests run against a
`tmp_path`-backed SQLite database via `initialize_db` — never the real
`data/domain_model.sqlite` file.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
from domain_model.pillar_repository import resolve_pillar  # noqa: E402
from domain_model.projection_repository import save_projection_version  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402

import scan_opportunities  # noqa: E402


class TestLoadPortfolioReadsSqlite:
    """Wave 3 Task 6: load_portfolio() must read domain_model.sqlite, never
    portfolio.json."""

    def test_computes_shares_price_value_and_book_pl(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        conn = initialize_db(str(db_path))
        upsert_account(conn, "TFSA", "TFSA", "TFSA")
        aapl_id = resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")
        cash_id = resolve_investment(conn, "USD_CASH", asset_class="CASH", currency="USD")
        upsert_investment_price(conn, aapl_id, price=110.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_investment_price(conn, cash_id, price=1.0, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_account_investment(
            conn, "TFSA", aapl_id, quantity=10, average_cost=100.0,
            book_value=1000.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
        upsert_account_investment(
            conn, "TFSA", cash_id, quantity=200.0, average_cost=1.0,
            book_value=200.0, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
        conn.close()

        result = scan_opportunities.load_portfolio(db_path)

        assert "USD_CASH" not in result  # cash excluded from per-ticker rows
        assert result["AAPL"]["shares"] == 10
        assert result["AAPL"]["price"] == 110.0
        assert result["AAPL"]["value"] == 1100.0
        assert result["AAPL"]["bookPL"] == 10.0  # (1100-1000)/1000 * 100
        assert result["AAPL"]["currency"] == "USD"
        assert result["_meta"]["totalValue"] == 1300.0
        assert result["_meta"]["cashValue"] == 200.0

    def test_missing_db_returns_empty(self, tmp_path):
        assert scan_opportunities.load_portfolio(tmp_path / "missing.sqlite") == {}


def test_load_thesis_reads_from_sqlite_not_json(tmp_path):
    """Wave 2 rewire: thesis fields must come from investment.target_weight
    et al. via the domain-model repository, not target-portfolio.json."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        resolve_pillar(conn, "ai-compute", "AI Compute")
        nvda_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
        update_investment_fields(
            conn, nvda_id,
            pillar_id="ai-compute", target_weight=5.5, lifecycle_status="accumulate",
            thesis_for_inclusion="Highest-conviction BUY.",
        )
        # Watchlist-only row (no pillar_id) must be excluded.
        wl_id = resolve_investment(conn, "ZZZZ", asset_class="EQUITY")
        update_investment_fields(conn, wl_id, is_watchlisted=True)
    finally:
        conn.close()

    thesis = scan_opportunities.load_thesis(db_path)
    assert thesis["NVDA"] == {
        "targetPct": 5.5,
        "pillarName": "AI Compute",
        "pillarId": "ai-compute",
        "thesisFor": "Highest-conviction BUY.",
        "role": "accumulate",
    }
    assert "ZZZZ" not in thesis


def test_load_thesis_missing_db_returns_empty(tmp_path):
    assert scan_opportunities.load_thesis(tmp_path / "does_not_exist.sqlite") == {}


def test_load_projection_returns_none_when_no_ai_agent_row(tmp_path):
    """Original code filtered strictly by source == AI_AGENT with no fallback —
    an ETF_ANALYSIS-only ticker must still return None."""
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "DXYZ", asset_class="ETF")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
            fair_value=40.0, action="INITIATE", source="ETF_ANALYSIS",
        )
    finally:
        conn.close()

    assert scan_opportunities.load_projection("DXYZ", db_path=db_path) is None


def test_load_projection_returns_latest_ai_agent_fields(tmp_path):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-06-01T00:00:00Z",
            fair_value=300.0, action="ACCUMULATE", source="AI_AGENT",
            snapshot_json='{"price": 250.0}',
        )
    finally:
        conn.close()

    proj = scan_opportunities.load_projection("NVDA", db_path=db_path)
    assert proj is not None
    assert proj["aiThesis"]["fairValue"] == 300.0
    assert proj["aiThesis"]["action"] == "ACCUMULATE"
    assert proj["snapshot"]["price"] == 250.0


def test_scan_initiate_finds_unowned_buy_rated_ticker(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "AMD", asset_class="EQUITY")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-06-01T00:00:00Z",
            fair_value=200.0, action="BUY", source="AI_AGENT",
            snapshot_json='{"price": 150.0}',
        )
    finally:
        conn.close()

    monkeypatch.setattr(scan_opportunities, "DB_PATH", db_path)

    portfolio = {"_meta": {"totalValue": 1000}}
    results = scan_opportunities.scan_initiate(portfolio, {}, top=5)

    assert len(results) == 1
    assert results[0]["ticker"] == "AMD"
    assert results[0]["dcfAction"] == "BUY"


def test_scan_initiate_excludes_held_tickers(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    conn = initialize_db(str(db_path))
    try:
        investment_id = resolve_investment(conn, "AMD", asset_class="EQUITY")
        save_projection_version(
            conn, investment_id, version=1, saved_at="2026-06-01T00:00:00Z",
            fair_value=200.0, action="BUY", source="AI_AGENT",
            snapshot_json='{"price": 150.0}',
        )
    finally:
        conn.close()

    monkeypatch.setattr(scan_opportunities, "DB_PATH", db_path)

    portfolio = {"_meta": {"totalValue": 1000}, "AMD": {"shares": 1, "price": 150.0}}
    results = scan_opportunities.scan_initiate(portfolio, {}, top=5)

    assert results == []
