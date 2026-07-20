import json
import subprocess
import sys
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "investment_screener" / "backend" / "py_services" / "lock_and_normalize_targets.py"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import get_investment, resolve_investment  # noqa: E402


def test_lock_and_normalize_missing_required_args():
    """Test that running the script without args fails and prints help/error."""
    r = subprocess.run(
        ["python3", str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )
    assert r.returncode != 0


def test_lock_and_normalize_happy_path(tmp_path):
    """Test locking and normalizing targets using a temporary target-portfolio.json file.

    Wave 2 Task 10 producer cutover: ``--write`` now persists rescaled
    targetWeight values via the domain-model repository (investment.target_weight)
    instead of rewriting target-portfolio.json in place.
    """
    dummy_portfolio = {
        "holdings": [
            {"ticker": "AAPL", "targetWeight": 40.0, "role": "core"},
            {"ticker": "MSFT", "targetWeight": 30.0, "role": "core"},
            {"ticker": "GOOG", "targetWeight": 20.0, "role": "core"},
            {"ticker": "INTC", "targetWeight": 10.0, "role": "core"}
        ]
    }
    target_file = tmp_path / "target-portfolio.json"
    target_file.write_text(json.dumps(dummy_portfolio))
    db_path = tmp_path / "domain_model.sqlite"
    original_mtime = target_file.stat().st_mtime_ns

    # Run script to set INTC=0, lock GOOG=25.0, adjust MSFT=15.0, and normalize AAPL
    # Sum of locked + adjusts = GOOG(25.0) + MSFT(15.0) = 40.0
    # Remaining for AAPL = 60.0%
    r = subprocess.run(
        [
            "python3", str(SCRIPT_PATH),
            "--target-file", str(target_file),
            "--zeros", "INTC",
            "--locks", "GOOG=25.0",
            "--adjusts", "MSFT=15.0",
            "--write",
            "--db", str(db_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )

    assert r.returncode == 0, f"Script failed: {r.stdout}\n{r.stderr}"

    # target-portfolio.json must NOT be touched by the new write path.
    assert target_file.stat().st_mtime_ns == original_mtime

    conn = initialize_db(str(db_path))
    holdings_dict = {}
    for ticker in ("AAPL", "MSFT", "GOOG", "INTC"):
        investment_id = resolve_investment(conn, ticker)
        holdings_dict[ticker] = get_investment(conn, investment_id)["target_weight"]
    conn.close()

    assert holdings_dict["INTC"] == 0.0
    assert holdings_dict["GOOG"] == 25.0
    assert holdings_dict["MSFT"] == 15.0
    assert holdings_dict["AAPL"] == 60.0
    assert round(sum(holdings_dict.values()), 4) == 100.0


def test_lock_and_normalize_dry_run_does_not_touch_db(tmp_path):
    dummy_portfolio = {
        "holdings": [
            {"ticker": "AAPL", "targetWeight": 50.0, "role": "core"},
            {"ticker": "MSFT", "targetWeight": 50.0, "role": "core"},
        ]
    }
    target_file = tmp_path / "target-portfolio.json"
    target_file.write_text(json.dumps(dummy_portfolio))
    db_path = tmp_path / "domain_model.sqlite"

    r = subprocess.run(
        ["python3", str(SCRIPT_PATH), "--target-file", str(target_file), "--db", str(db_path)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, f"Script failed: {r.stdout}\n{r.stderr}"
    assert not db_path.exists()
