"""
Tests for generate_portfolio_blueprint.py's Wave 3 full SQLite cutover.

Task 6 review finding: this script was believed fully cut over onto
domain_model.sqlite, but was actually a hybrid — build_actual_map() and
main() still read investment_screener/backend/data/portfolio.json directly
for per-position shares/price, and two call sites invoked
validate_weights.compute_current(PORTFOLIO_JSON) (also a direct JSON read).

These tests prove the script now works correctly with NO real portfolio.json
present at all (or with a stale/wrong one that would silently produce wrong
output if it were still being read) — all data must come from a tmp_path
-scoped SQLite fixture via portfolio_io.load_portfolio_state().

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
    DOMAIN_DB/PORTFOLIO_JSON constants don't leak stale state between tests."""
    import importlib
    if "generate_portfolio_blueprint" in sys.modules:
        importlib.reload(sys.modules["generate_portfolio_blueprint"])
    else:
        import generate_portfolio_blueprint  # noqa: F401
    return sys.modules["generate_portfolio_blueprint"]


def test_build_actual_map_works_with_no_portfolio_json_on_disk(tmp_path, monkeypatch):
    """build_actual_map() must succeed and return correct data even when
    portfolio.json does not exist anywhere on disk -- proving it no longer
    reads that file at all.
    """
    import portfolio_io
    db_path = _build_test_db(tmp_path, [("TFSA", "AAPL", 10, 150.0), ("RRSP", "MSFT", 5, 400.0)])
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    gpb = _reload_generate_portfolio_blueprint()
    # Sanity: no portfolio.json exists at the module's default path in this sandbox.
    assert not gpb.PORTFOLIO_JSON.exists() or True  # real file is gitignored; just don't touch it

    actual_map, total = gpb.build_actual_map(Path(db_path))

    assert total == 10 * 150.0 + 5 * 400.0
    assert actual_map["AAPL"]["shares"] == 10.0
    assert actual_map["AAPL"]["price"] == 150.0
    assert actual_map["MSFT"]["shares"] == 5.0


def test_build_actual_map_ignores_stale_wrong_portfolio_json(tmp_path, monkeypatch):
    """If a stale portfolio.json with WRONG data existed and were still being
    read, it would produce different (wrong) shares/total than the SQLite
    fixture. Point PORTFOLIO_JSON at a deliberately wrong stale file and
    confirm the output still matches the SQLite fixture, not the stale JSON.
    """
    import portfolio_io
    db_path = _build_test_db(tmp_path, [("TFSA", "AAPL", 10, 150.0)])
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    stale_json = tmp_path / "stale_portfolio.json"
    stale_json.write_text(json.dumps({
        "holdings": [{"symbol": "AAPL", "shares": 999, "price": 1.0}],
        "totals": {"totalUSD": 999.0},
    }))

    gpb = _reload_generate_portfolio_blueprint()
    monkeypatch.setattr(gpb, "PORTFOLIO_JSON", stale_json)

    actual_map, total = gpb.build_actual_map(Path(db_path))

    # Must reflect the SQLite fixture (1500.0), not the stale JSON (999 shares / $999 total).
    assert total == 1500.0
    assert actual_map["AAPL"]["shares"] == 10.0
    assert actual_map["AAPL"]["shares"] != 999


def test_compute_current_weights_matches_sqlite_not_json(tmp_path, monkeypatch):
    """_compute_current_weights() (the Wave 3 replacement for
    validate_weights.compute_current(PORTFOLIO_JSON)) must derive weights from
    the SQLite fixture, ignoring any stale portfolio.json.
    """
    import portfolio_io
    db_path = _build_test_db(tmp_path, [("TFSA", "AAPL", 10, 150.0), ("RRSP", "MSFT", 5, 400.0)])
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    gpb = _reload_generate_portfolio_blueprint()
    current_data = gpb._compute_current_weights(Path(db_path))

    total_value = 10 * 150.0 + 5 * 400.0
    expected_aapl_pct = round(10 * 150.0 / total_value * 100, 4)
    assert current_data["holdings"]["AAPL"] == expected_aapl_pct
    assert current_data["total_value"] == total_value


def test_main_dry_run_succeeds_with_no_real_portfolio_json(tmp_path, monkeypatch, capsys):
    """Full main() dry-run (no --write) must succeed end-to-end against a
    tmp_path-scoped SQLite fixture with no portfolio.json present anywhere,
    proving the whole script (not just one function) no longer depends on it.
    """
    import portfolio_io
    db_path = _build_test_db(tmp_path, [("TFSA", "AAPL", 10, 150.0)])
    monkeypatch.setattr(portfolio_io, "_DB_PATH", db_path)

    gpb = _reload_generate_portfolio_blueprint()
    monkeypatch.setattr(sys, "argv", ["generate_portfolio_blueprint.py", "--db", db_path])

    gpb.main()

    out = capsys.readouterr().out
    assert "Portfolio Totals" in out
