"""Tests for update_thesis.py, which edits the thesis in domain_model.sqlite only.

Purpose:
    Weights, roles, thesis text, pillar targets and thesis breakers are read from and written to
    the database through the repositories; every write records one portfolio_change_log entry;
    --dry-run and a failed validation write nothing; --patch is an input file only; the
    retired JSON thesis file and the old role names are gone.

Key Input Dependencies: none (each test builds a real temporary SQLite database).
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "plugins/portfolio-advisor/scripts/update_thesis.py"
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import get_investment, resolve_investment, update_investment_fields  # noqa: E402
from domain_model.pillar_repository import list_pillars, resolve_pillar  # noqa: E402
from domain_model.portfolio_change_log_repository import list_change_log  # noqa: E402
from domain_model.thesis_breaker_repository import list_breakers  # noqa: E402

MANUAL = {"id": "ndr-floor", "type": "manual", "operator": "<", "threshold": 115, "status": "OK",
          "statusSetAt": "2026-07-01", "reviewCadenceDays": 90, "note": "NDR floor"}
AUTO = {"id": "rsi-low", "type": "auto", "metric": "rsi", "operator": "<", "threshold": 30, "horizon": 3}


def _db(tmp_path):
    """Two pillars (60 / 40) and two holdings, AAPL 60 in pillar ai and MSFT 40 in pillar sw."""
    path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(path))
    resolve_pillar(conn, "ai", "AI", 60.0)
    resolve_pillar(conn, "sw", "Software", 40.0)
    for symbol, weight, pillar in (("AAPL", 60.0, "ai"), ("MSFT", 40.0, "sw")):
        update_investment_fields(conn, resolve_investment(conn, symbol), target_weight=weight, pillar_id=pillar,
                                 lifecycle_status="accumulate", thesis_for_inclusion=f"{symbol} thesis")
    conn.close()
    return path


def _run(db, *args):
    return subprocess.run(["python3", str(SCRIPT), "--db", str(db), *args], capture_output=True, text=True, cwd=str(REPO_ROOT))


def _state(db):
    conn = initialize_db(str(db))
    out = {
        "weights": {s: get_investment(conn, resolve_investment(conn, s))["target_weight"] for s in ("AAPL", "MSFT")},
        "roles": {s: get_investment(conn, resolve_investment(conn, s))["lifecycle_status"] for s in ("AAPL", "MSFT")},
        "log": list_change_log(conn),
        "pillars": {p["pillar_id"]: p["target_weight"] for p in list_pillars(conn)},
    }
    conn.close()
    return out


def test_patch_rebalances_two_holdings_and_logs_one_change(tmp_path):
    """A patch moving 10 points from AAPL to MSFT is saved and recorded once, with the note."""
    db = _db(tmp_path)
    patch = tmp_path / "patch.json"
    patch.write_text(json.dumps({"holdings": [{"ticker": "AAPL", "targetWeight": 50.0}, {"ticker": "MSFT", "targetWeight": 50.0}]}))
    before = patch.read_text()
    r = _run(db, "--patch", str(patch), "--note", "Strategic review: rebalance")
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    state = _state(db)
    assert state["weights"] == {"AAPL": 50.0, "MSFT": 50.0}
    assert [e["note"] for e in state["log"]] == ["Strategic review: rebalance"]
    assert patch.read_text() == before  # the patch file is input only


def test_dry_run_writes_nothing(tmp_path):
    """--dry-run shows the diff and leaves weights and the change log alone."""
    db = _db(tmp_path)
    patch = tmp_path / "patch.json"
    patch.write_text(json.dumps({"holdings": [{"ticker": "AAPL", "targetWeight": 50.0}, {"ticker": "MSFT", "targetWeight": 50.0}]}))
    r = _run(db, "--patch", str(patch), "--dry-run")
    assert r.returncode == 0 and "DRY RUN" in r.stdout
    state = _state(db)
    assert state["weights"] == {"AAPL": 60.0, "MSFT": 40.0} and state["log"] == []


def test_weights_not_summing_to_100_fail_and_write_nothing(tmp_path):
    """Moving only AAPL to 70 leaves a 110 total: exit 1, no change, no log entry."""
    db = _db(tmp_path)
    r = _run(db, "--holding", "AAPL", "--target", "70")
    assert r.returncode == 1 and "Validation failed" in r.stdout
    state = _state(db)
    assert state["weights"]["AAPL"] == 60.0 and state["log"] == []


def test_role_uses_the_database_vocabulary(tmp_path):
    """--role trim is saved; the old core / hedge / reserve / speculative names are rejected by the parser."""
    db = _db(tmp_path)
    ok = _run(db, "--holding", "AAPL", "--role", "trim", "--note", "trim AAPL")
    assert ok.returncode == 0, f"{ok.stdout}\n{ok.stderr}"
    assert _state(db)["roles"]["AAPL"] == "trim"
    for old in ("core", "hedge", "reserve", "speculative"):
        bad = _run(db, "--holding", "AAPL", "--role", old)
        assert bad.returncode == 2 and "invalid choice" in bad.stderr


def test_thesis_text_is_saved_and_logged(tmp_path):
    """--thesis updates thesis_for_inclusion and records a change."""
    db = _db(tmp_path)
    r = _run(db, "--holding", "MSFT", "--thesis", "Cloud and AI distribution")
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    conn = initialize_db(str(db))
    assert get_investment(conn, "MSFT")["thesis_for_inclusion"] == "Cloud and AI distribution"
    assert len(list_change_log(conn)) == 1
    conn.close()


def test_pillar_targets_are_saved_when_they_still_sum_to_100(tmp_path):
    """Setting ai to 45 alone fails; patching ai 45 and sw 55 passes and is saved."""
    db = _db(tmp_path)
    assert _run(db, "--pillar", "ai", "--target", "45").returncode == 1
    patch = tmp_path / "p.json"
    patch.write_text(json.dumps({"pillars": [{"id": "ai", "targetWeight": 45.0}, {"id": "sw", "targetWeight": 55.0}]}))
    r = _run(db, "--patch", str(patch), "--note", "pillar shift")
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    assert _state(db)["pillars"] == {"ai": 45.0, "sw": 55.0}


def test_unknown_ticker_and_pillar_fail_with_a_message(tmp_path):
    """Unknown names are errors listing what exists."""
    db = _db(tmp_path)
    assert "not found" in _run(db, "--holding", "ZZZZ", "--target", "5").stderr
    assert "not found" in _run(db, "--pillar", "nope", "--target", "5").stderr


def test_breaker_add_status_and_remove_are_saved_and_logged(tmp_path):
    """--set-breaker, --set-breaker-status and --remove-breaker go through thesis_breaker and each log a change."""
    db = _db(tmp_path)
    assert _run(db, "--holding", "AAPL", "--set-breaker", json.dumps(MANUAL), "--note", "add").returncode == 0
    assert _run(db, "--holding", "AAPL", "--set-breaker", json.dumps(AUTO), "--note", "add auto").returncode == 0
    conn = initialize_db(str(db))
    assert {b["id"] for b in list_breakers(conn, "AAPL")} == {"ndr-floor", "rsi-low"}
    conn.close()

    r = _run(db, "--holding", "AAPL", "--set-breaker-status", "ndr-floor", "--status", "TRIGGERED", "--note", "Q2 NDR 108%")
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    conn = initialize_db(str(db))
    floor = next(b for b in list_breakers(conn, "AAPL") if b["id"] == "ndr-floor")
    conn.close()
    assert floor["status"] == "TRIGGERED" and "Q2 NDR 108%" in floor["note"] and "NDR floor" in floor["note"]

    assert _run(db, "--holding", "AAPL", "--remove-breaker", "rsi-low", "--note", "drop").returncode == 0
    conn = initialize_db(str(db))
    assert [b["id"] for b in list_breakers(conn, "AAPL")] == ["ndr-floor"]
    assert len(list_change_log(conn)) == 4
    conn.close()


def test_invalid_breaker_is_rejected_and_nothing_is_written(tmp_path):
    """A breaker with a bad operator is an error with no change-log entry."""
    db = _db(tmp_path)
    r = _run(db, "--holding", "AAPL", "--set-breaker", json.dumps({**AUTO, "operator": "!="}))
    assert r.returncode == 1 and "operator" in r.stderr
    conn = initialize_db(str(db))
    assert list_breakers(conn, "AAPL") == [] and list_change_log(conn) == []
    conn.close()


def test_list_prints_pillars_and_holdings_from_sqlite(tmp_path):
    """--list shows the database content."""
    r = _run(_db(tmp_path), "--list")
    assert r.returncode == 0 and "AAPL" in r.stdout and "Software" in r.stdout or "sw" in r.stdout


def test_script_has_no_file_path_or_old_role():
    """The source has no THESIS_PATH and none of the old role names."""
    source = SCRIPT.read_text()
    assert "THESIS_PATH" not in source
    assert '"core"' not in source and '"speculative"' not in source
