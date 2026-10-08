"""Purpose: the standing-decision CLI records, replaces and clears decisions with a dated source.

Layer: Tests. Uses a real SQLite database and the real CLI subprocess.
Key Functions: set, replace, clear, dry-run and unknown-ticker cases.
Key Input Dependencies: set_standing_decision.py; domain_model repositories.
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "investment_screener/backend/py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import get_investment, resolve_investment, update_investment_fields  # noqa: E402

SCRIPT = ROOT / "plugins/portfolio-advisor/scripts/set_standing_decision.py"


def run(db, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--db", str(db), "--json", *args], capture_output=True, text=True)


def seeded(tmp_path):
    db = tmp_path / "db.sqlite"
    conn = initialize_db(str(db))
    inv = resolve_investment(conn, "IREN")
    update_investment_fields(conn, inv, standing_decision_type="HOLD_AT_TARGET", standing_decision_reason="Hold at target.",
                             standing_decision_source="user 2026-06-21")
    conn.close()
    return db


def decision(db, symbol="IREN"):
    row = get_investment(initialize_db(str(db)), symbol)
    return {key: row[f"standing_decision_{key}"] for key in ("type", "reason", "source", "review")}


def test_setting_a_decision_replaces_the_old_one_and_stamps_today(tmp_path):
    db = seeded(tmp_path)
    result = run(db, "--ticker", "iren", "--type", "trim on strength", "--reason", "Trim above $45.", "--review", "After Q1 results")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["before"]["type"] == "HOLD_AT_TARGET" and report["after"]["type"] == "TRIM_ON_STRENGTH"
    assert decision(db) == {"type": "TRIM_ON_STRENGTH", "reason": "Trim above $45.",
                            "source": f"user {date.today().isoformat()}", "review": "After Q1 results"}


def test_clearing_removes_every_decision_field(tmp_path):
    db = seeded(tmp_path)
    assert run(db, "--ticker", "IREN", "--clear").returncode == 0
    assert decision(db) == {"type": None, "reason": None, "source": None, "review": None}


def test_dry_run_reports_the_change_without_writing(tmp_path):
    db = seeded(tmp_path)
    result = run(db, "--ticker", "IREN", "--clear", "--dry-run")
    assert json.loads(result.stdout)["dry_run"] is True
    assert decision(db)["type"] == "HOLD_AT_TARGET"


def test_unknown_tickers_and_incomplete_requests_are_refused(tmp_path):
    db = seeded(tmp_path)
    assert run(db, "--ticker", "NOPE", "--type", "HOLD", "--reason", "x").returncode == 1
    assert run(db, "--ticker", "IREN", "--type", "HOLD").returncode != 0          # reason is required
    assert run(db, "--ticker", "IREN", "--type", "HOLD", "--reason", "x", "--clear").returncode != 0
    assert get_investment(initialize_db(str(db)), "NOPE") is None                  # no investment is created
