"""
Tests for generate_portfolio_blueprint.py's SQLite data source.

These tests prove build_actual_map(), _compute_current_weights() and main()
take all holdings data from a tmp_path-scoped SQLite fixture via
portfolio_io.load_portfolio_state().

Test tier: Category C (sqlite + subprocess-free direct import).
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "plugins/portfolio-advisor/scripts"
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"

sys.path.insert(0, str(PY_SERVICES))
sys.path.insert(0, str(SCRIPT_DIR))


def _build_test_db(tmp_path, rows):
    """Build a throwaway domain_model.sqlite with (account, symbol, qty, price)
    rows, plus a matching `investment` row carrying a pillar_id/target_weight
    so build_thesis_map() picks it up. Returns the db path.
    """
    from domain_model.db_client import initialize_db
    from domain_model.account_repository import upsert_account
    from domain_model.investment_repository import resolve_investment
    from domain_model.investment_price_repository import upsert_investment_price
    from domain_model.account_investment_repository import upsert_account_investment

    db_path = str(tmp_path / "test.sqlite")
    conn = initialize_db(db_path)
    seen_accounts: set[str] = set()
    for account_id, symbol, qty, price in rows:
        if account_id not in seen_accounts:
            upsert_account(conn, account_id, account_id, account_id)
            seen_accounts.add(account_id)
        inv_id = resolve_investment(conn, symbol, asset_class="EQUITY", currency="USD")
        upsert_investment_price(conn, inv_id, price=price, currency="USD", fetched_at="2026-07-20T00:00:00Z")
        upsert_account_investment(
            conn, account_id, inv_id, quantity=qty, average_cost=price,
            book_value=qty * price, currency="USD", last_synced_at="2026-07-20T00:00:00Z",
        )
    conn.close()
    return db_path


def _reload_generate_portfolio_blueprint():
    """Import (or reimport) generate_portfolio_blueprint fresh so module-level
    DOMAIN_DB constant doesn't leak stale state between tests."""
    import importlib
    if "generate_portfolio_blueprint" in sys.modules:
        importlib.reload(sys.modules["generate_portfolio_blueprint"])
    else:
        import generate_portfolio_blueprint  # noqa: F401
    return sys.modules["generate_portfolio_blueprint"]


def test_build_actual_map_reads_the_sqlite_fixture(tmp_path, monkeypatch):
    """build_actual_map() returns shares and total from the SQLite fixture."""
    import portfolio_io
    db_path = _build_test_db(tmp_path, [("TFSA", "AAPL", 10, 150.0), ("RRSP", "MSFT", 5, 400.0)])
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    gpb = _reload_generate_portfolio_blueprint()

    actual_map, total = gpb.build_actual_map(Path(db_path))

    assert total == 10 * 150.0 + 5 * 400.0
    assert actual_map["AAPL"]["shares"] == 10.0
    assert actual_map["AAPL"]["price"] == 150.0
    assert actual_map["MSFT"]["shares"] == 5.0


def test_build_actual_map_reads_the_db_it_is_given_not_the_module_default(tmp_path):
    """The db_path argument is the database read; portfolio_io's default database is not consulted."""
    db_path = _build_test_db(tmp_path, [("TFSA", "AAPL", 10, 150.0)])
    gpb = _reload_generate_portfolio_blueprint()

    actual_map, total = gpb.build_actual_map(Path(db_path))

    assert total == 1500.0 and actual_map["AAPL"]["shares"] == 10.0


def test_module_has_no_portfolio_file_constant_or_cli_option():
    """The blueprint generator has no portfolio file path and no --portfolio option."""
    gpb = _reload_generate_portfolio_blueprint()
    assert not hasattr(gpb, "PORTFOLIO_JSON")
    assert "--portfolio" not in Path(gpb.__file__).read_text()


def test_compute_current_weights_matches_sqlite(tmp_path, monkeypatch):
    """_compute_current_weights() derives weights from the SQLite fixture."""
    import portfolio_io
    db_path = _build_test_db(tmp_path, [("TFSA", "AAPL", 10, 150.0), ("RRSP", "MSFT", 5, 400.0)])
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    gpb = _reload_generate_portfolio_blueprint()
    current_data = gpb._compute_current_weights(Path(db_path))

    total_value = 10 * 150.0 + 5 * 400.0
    expected_aapl_pct = round(10 * 150.0 / total_value * 100, 4)
    assert current_data["holdings"]["AAPL"] == expected_aapl_pct
    assert current_data["total_value"] == total_value


def test_main_dry_run_succeeds_against_the_sqlite_fixture(tmp_path, monkeypatch, capsys):
    """Full main() dry-run (no --write) succeeds end-to-end against a
    tmp_path-scoped SQLite fixture.
    """
    import portfolio_io
    db_path = _build_test_db(tmp_path, [("TFSA", "AAPL", 10, 150.0)])
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    gpb = _reload_generate_portfolio_blueprint()
    monkeypatch.setattr(sys, "argv", ["generate_portfolio_blueprint.py", "--db", db_path])

    gpb.main()

    out = capsys.readouterr().out
    assert "Portfolio Totals" in out
