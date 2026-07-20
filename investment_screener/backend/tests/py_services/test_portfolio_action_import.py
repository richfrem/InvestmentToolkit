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


def test_portfolio_action_reads_target_weight_from_sqlite_not_json(tmp_path):
    """Target weights must come from investment.target_weight, not the JSON file.

    Seed the DB with weights that DIFFER from target_portfolio.test.json's
    values (60/40) to prove the JSON file is not the source of truth anymore.
    """
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    try:
        aapl_id = resolve_investment(conn, "AAPL")
        msft_id = resolve_investment(conn, "MSFT")
        update_investment_fields(conn, aapl_id, target_weight=10)
        update_investment_fields(conn, msft_id, target_weight=90)
    finally:
        conn.close()

    r = _run(CANONICAL_PATH, db_path)
    assert r.returncode == 0, f"Non-zero exit: {r.stderr}"
    data = json.loads(r.stdout)
    # AAPL: current 60% (from portfolio.test.json fixture) vs target 10% -> ratio 6 -> TRIM
    # MSFT: current 40% vs target 90% -> ratio 0.44 -> ACCUMULATE
    assert data["AAPL"] == "TRIM"
    assert data["MSFT"] == "ACCUMULATE"
