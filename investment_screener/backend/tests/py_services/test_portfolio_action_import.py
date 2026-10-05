"""
Tests that portfolio_action.py works when invoked via its py_services/ symlink path.
This is the exact path bridge.ts uses via spawnPythonScript().
A broken sys.path.insert (missing .resolve()) silently returns {} in production.

Wave 2 rewire: target weights are read from the domain-model sqlite DB
(investment.target_weight) instead of --target JSON — --target is still
accepted on the CLI for back-compat with the production caller (helpers.ts)
but is no longer read directly. Tests seed a temp DB via the repository layer
and point --db at it.
"""

import subprocess
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES_DIR = REPO_ROOT / "investment_screener/backend/tests/fixtures"
SYMLINK_PATH = REPO_ROOT / "investment_screener/backend/py_services/portfolio_action.py"
CANONICAL_PATH = REPO_ROOT / "plugins/portfolio-advisor/scripts/portfolio_action.py"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402


def _seed_db(db_path: Path) -> None:
    conn = initialize_db(str(db_path))
    try:
        aapl_id = resolve_investment(conn, "AAPL")
        msft_id = resolve_investment(conn, "MSFT")
        update_investment_fields(conn, aapl_id, target_weight=60)
        update_investment_fields(conn, msft_id, target_weight=40)
    finally:
        conn.close()


def _run(script_path: Path, db_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "python3", str(script_path),
            "--all",
            "--portfolio", str(FIXTURES_DIR / "portfolio.test.json"),
            "--target",   str(FIXTURES_DIR / "target_portfolio.test.json"),
            "--db",       str(db_path),
        ],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )


def test_portfolio_action_via_symlink_path(tmp_path):
    """py_services/ symlink path must work — this is how bridge.ts calls it."""
    db_path = tmp_path / "domain_model.sqlite"
    _seed_db(db_path)
    r = _run(SYMLINK_PATH, db_path)
    assert r.returncode == 0, f"Non-zero exit via symlink: {r.stderr}"
    data = json.loads(r.stdout)
    assert len(data) > 0, "Expected non-empty action map via symlink path"


def test_portfolio_action_via_canonical_path(tmp_path):
    """Canonical plugin path must also work."""
    db_path = tmp_path / "domain_model.sqlite"
    _seed_db(db_path)
    r = _run(CANONICAL_PATH, db_path)
    assert r.returncode == 0, f"Non-zero exit via canonical path: {r.stderr}"
    data = json.loads(r.stdout)
    assert len(data) > 0, "Expected non-empty action map via canonical path"


def test_portfolio_action_ignores_target_weight_and_reads_valuation_from_sqlite(tmp_path):
    """Recommendations come BEFORE targets: seed targets that point the opposite
    way to valuation and prove the action follows valuation only."""
    from domain_model.projection_repository import save_projection_version

    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    try:
        aapl_id = resolve_investment(conn, "AAPL")
        msft_id = resolve_investment(conn, "MSFT")
        update_investment_fields(conn, aapl_id, target_weight=90)  # would have meant ACCUMULATE
        update_investment_fields(conn, msft_id, target_weight=10)  # would have meant TRIM
        upsert_account(conn, "tfsa", "TFSA", "TFSA")
        for investment_id, quantity, fair_value in ((aapl_id, 60, 0.5), (msft_id, 40, 2.0)):
            upsert_account_investment(
                conn, "tfsa", investment_id, quantity, None, None, "USD", "2026-01-01T00:00:00Z",
            )
            upsert_investment_price(conn, investment_id, 1.0, "USD", "2026-01-01T00:00:00Z")
            save_projection_version(
                conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
                fair_value=fair_value, action="MAINTAIN", source="AI_AGENT",
                snapshot_json='{"price": 1.0}',
            )
    finally:
        conn.close()

    r = _run(CANONICAL_PATH, db_path)
    assert r.returncode == 0, f"Non-zero exit: {r.stderr}"
    data = json.loads(r.stdout)
    assert data["AAPL"] == "TRIM"        # price 2x fair value
    assert data["MSFT"] == "ACCUMULATE"  # price half of fair value
