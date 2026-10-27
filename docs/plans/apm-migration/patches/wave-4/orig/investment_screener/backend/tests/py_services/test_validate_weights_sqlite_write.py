"""Tests for validate_weights.py's target-weight modes, which read and write domain_model.sqlite only.

Purpose:
    --mode target and --normalize take weights from investment.target_weight; --normalize --write
    persists the rescaled weights and records one portfolio_change_log entry; without --write
    nothing is written; the retired --target / --portfolio options are gone.

Key Input Dependencies: none (each test builds a real temporary SQLite database).
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "plugins/portfolio-advisor/scripts/validate_weights.py"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import get_investment, resolve_investment, update_investment_fields  # noqa: E402
from domain_model.portfolio_change_log_repository import list_change_log  # noqa: E402


def _make_db(tmp_path: Path, weights: dict) -> Path:
    """A database whose investments carry the given target weights."""
    db_path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(db_path))
    for symbol, weight in weights.items():
        update_investment_fields(conn, resolve_investment(conn, symbol), target_weight=weight)
    conn.close()
    return db_path


def _run(*args):
    """Run."""
    return subprocess.run(["python3", str(SCRIPT_PATH), *args], capture_output=True, text=True, cwd=str(REPO_ROOT))


def test_normalize_write_persists_to_sqlite_and_logs_one_change(tmp_path):
    """Weights 30 + 30 rescale to 50 + 50 in the database and one change-log entry is recorded."""
    db_path = _make_db(tmp_path, {"AAPL": 30, "MSFT": 30})
    proc = _run("--normalize", "--write", "--db", str(db_path))
    assert proc.returncode == 0, proc.stderr
    conn = initialize_db(str(db_path))
    assert get_investment(conn, resolve_investment(conn, "AAPL"))["target_weight"] == 50.0
    assert get_investment(conn, resolve_investment(conn, "MSFT"))["target_weight"] == 50.0
    log = list_change_log(conn)
    conn.close()
    assert len(log) == 1 and "validate_weights" in log[0]["note"]
    assert json.loads(proc.stdout)["normalised_total"] == 100.0


def test_normalize_without_write_changes_nothing(tmp_path):
    """A dry run reports the new total but leaves weights and the change log untouched."""
    db_path = _make_db(tmp_path, {"AAPL": 30, "MSFT": 30})
    proc = _run("--normalize", "--db", str(db_path))
    assert proc.returncode == 0, proc.stderr
    conn = initialize_db(str(db_path))
    assert get_investment(conn, resolve_investment(conn, "AAPL"))["target_weight"] == 30.0
    assert list_change_log(conn) == []
    conn.close()
    assert json.loads(proc.stdout)["normalised_total"] == 100.0


def test_mode_target_reads_the_database(tmp_path):
    """--mode target sums investment.target_weight and ignores zero weights."""
    db_path = _make_db(tmp_path, {"AAPL": 60, "MSFT": 40, "ZERO": 0})
    proc = _run("--mode", "target", "--db", str(db_path))
    assert proc.returncode == 0, proc.stderr
    target = json.loads(proc.stdout)["target"]
    assert target == {"total": 100.0, "holdings": {"AAPL": 60.0, "MSFT": 40.0}}


def test_normalize_with_no_weights_fails_clearly(tmp_path):
    """No target weights anywhere: exit 1 with a message, no change-log entry."""
    db_path = _make_db(tmp_path, {})
    proc = _run("--normalize", "--write", "--db", str(db_path))
    assert proc.returncode == 1 and "nothing to normalize" in proc.stderr
    conn = initialize_db(str(db_path))
    assert list_change_log(conn) == []
    conn.close()


def test_retired_file_options_are_gone():
    """--target and --portfolio no longer exist, so a stale caller fails loudly."""
    for option in ("--target", "--portfolio"):
        proc = _run(option, "x.json")
        assert proc.returncode == 2 and "unrecognized arguments" in proc.stderr
