"""Tests for lock_and_normalize_targets.py, which reads and writes target weights in domain_model.sqlite.

Purpose:
    Zero, lock and adjust named tickers, rescale the remaining unlocked weights so the book sums
    to 100%, persist only with --write (plus one portfolio_change_log entry), and fail loudly on
    unknown tickers, an over-100 lock total, a missing database or no instructions.

Key Input Dependencies: none (each test builds a real temporary SQLite database).
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "investment_screener" / "backend" / "py_services" / "lock_and_normalize_targets.py"

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
    return subprocess.run(["python3", str(SCRIPT_PATH), *args], capture_output=True, text=True, cwd=str(REPO_ROOT))


def _weights(db_path: Path, symbols) -> dict:
    conn = initialize_db(str(db_path))
    out = {s: get_investment(conn, resolve_investment(conn, s))["target_weight"] for s in symbols}
    conn.close()
    return out


BOOK = {"AAPL": 40.0, "MSFT": 30.0, "GOOG": 20.0, "INTC": 10.0}


def test_no_instructions_fails_and_says_what_to_pass(tmp_path):
    """Running with nothing to change exits 1 and names the options."""
    r = _run("--db", str(_make_db(tmp_path, BOOK)))
    assert r.returncode == 1 and "--zeros" in r.stderr


def test_zero_lock_adjust_and_normalize_writes_to_sqlite_and_logs(tmp_path):
    """INTC to 0, GOOG locked at 25, MSFT adjusted to 15: AAPL absorbs the rest (60) and one change is logged."""
    db_path = _make_db(tmp_path, BOOK)
    r = _run("--zeros", "INTC", "--locks", "GOOG=25.0", "--adjusts", "MSFT=15.0", "--write", "--db", str(db_path))
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    assert _weights(db_path, BOOK) == {"AAPL": 60.0, "MSFT": 15.0, "GOOG": 25.0, "INTC": 0.0}
    conn = initialize_db(str(db_path))
    log = list_change_log(conn)
    conn.close()
    assert len(log) == 1 and "lock_and_normalize_targets" in log[0]["note"]


def test_dry_run_changes_nothing(tmp_path):
    """Without --write the weights and the change log stay as they were."""
    db_path = _make_db(tmp_path, BOOK)
    r = _run("--zeros", "INTC", "--db", str(db_path))
    assert r.returncode == 0 and "DRY RUN" in r.stdout
    assert _weights(db_path, BOOK) == BOOK
    conn = initialize_db(str(db_path))
    assert list_change_log(conn) == []
    conn.close()


def test_unknown_ticker_fails_loudly_and_writes_nothing(tmp_path):
    """A lock on a ticker the database does not know is an error, not a silent skip."""
    db_path = _make_db(tmp_path, BOOK)
    r = _run("--locks", "ZZZZ=5", "--write", "--db", str(db_path))
    assert r.returncode == 1 and "ZZZZ" in r.stderr
    assert _weights(db_path, BOOK) == BOOK


def test_locks_over_100_fail(tmp_path):
    """Locked weights above 100 are rejected before anything is written."""
    db_path = _make_db(tmp_path, BOOK)
    r = _run("--locks", "AAPL=70", "MSFT=40", "--write", "--db", str(db_path))
    assert r.returncode == 1 and "exceeds 100" in r.stderr
    assert _weights(db_path, BOOK) == BOOK


def test_missing_database_fails_and_is_not_created(tmp_path):
    """A missing database is reported, never created as a side effect."""
    missing = tmp_path / "absent.sqlite"
    r = _run("--zeros", "AAPL", "--db", str(missing))
    assert r.returncode == 1 and "not found" in r.stderr
    assert not missing.exists()


def test_retired_target_file_option_is_gone():
    """--target-file no longer exists, so a stale caller fails loudly."""
    r = _run("--target-file", "x.json", "--zeros", "AAPL")
    assert r.returncode == 2 and "unrecognized arguments" in r.stderr


def test_script_never_names_a_retired_file():
    """The source mentions neither portfolio.json nor target-portfolio.json."""
    source = SCRIPT_PATH.read_text()
    assert "portfolio.json" not in source and "target-portfolio.json" not in source
