"""Tests for fetch_broker_data.py --compare: the baseline is the positions stored in domain_model.sqlite.

Purpose:
    The stored positions (summed across accounts per symbol) are the baseline a live TradingView
    read is compared against; the retired --promote option and every reference to the old
    portfolio file are gone.

Key Input Dependencies: none (each test builds a real temporary SQLite database).
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "plugins/tradingview/scripts/fetch_broker_data.py"
sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

import fetch_broker_data as fbd  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402


def _seed(tmp_path):
    """TFSA holds 30 AAPL and 10 MSFT; RRSP holds 10 AAPL."""
    db = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db))
    now = "2026-10-09T00:00:00Z"
    for account in ("TFSA", "RRSP"):
        upsert_account(conn, account, account, account)
    for account, symbol, qty in (("TFSA", "AAPL", 30), ("TFSA", "MSFT", 10), ("RRSP", "AAPL", 10)):
        investment_id = resolve_investment(conn, symbol, asset_class="EQUITY", currency="USD")
        upsert_account_investment(conn, account, investment_id, qty, 100.0, qty * 100.0, "USD", now)
        upsert_investment_price(conn, investment_id, price=100.0, currency="USD", fetched_at=now)
    conn.close()
    return db


def test_stored_positions_are_summed_across_accounts_per_symbol(tmp_path):
    """AAPL is 30 + 10 = 40 shares; MSFT is 10."""
    stored = fbd.fetch_stored_positions(_seed(tmp_path))
    assert {h["symbol"]: h["shares"] for h in stored["holdings"]} == {"AAPL": 40, "MSFT": 10}


def test_missing_database_has_no_baseline(tmp_path):
    """No database means no baseline (None), never a file fallback."""
    assert fbd.fetch_stored_positions(tmp_path / "absent.sqlite") is None


def test_compare_reports_matches_mismatches_and_one_sided_symbols(tmp_path):
    """A live read with AAPL 40, MSFT 12 and NVDA 5 against the stored book."""
    stored = fbd.fetch_stored_positions(_seed(tmp_path))
    tv = {"positions": [
        {"symbol": "AAPL", "quantity": 40}, {"symbol": "MSFT", "quantity": 12}, {"symbol": "NVDA", "quantity": 5},
    ]}
    report = fbd.compare_snapshots(tv, stored)
    assert [r["symbol"] for r in report["matched"]] == ["AAPL"]
    assert [(r["symbol"], r["tv_qty"], r["qt_qty"]) for r in report["qty_mismatch"]] == [("MSFT", 12, 10)]
    assert [r["symbol"] for r in report["tv_only"]] == ["NVDA"]
    assert report["qt_only"] == []


def test_promote_option_is_gone():
    """--promote did nothing; a stale caller now fails loudly."""
    r = subprocess.run([sys.executable, str(SCRIPT), "--promote"], capture_output=True, text=True)
    assert r.returncode == 2 and "unrecognized arguments" in r.stderr


def test_source_names_no_retired_portfolio_file():
    """The script no longer mentions portfolio.json."""
    assert "portfolio.json" not in SCRIPT.read_text()
