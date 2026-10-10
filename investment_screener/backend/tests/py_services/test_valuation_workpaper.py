"""Valuation working documents: repository, command line (pipe flow), one-time importer, and a whole run.

These replace the per-stock JSON files that used to sit in temp/evaluations. Everything runs against
real temporary SQLite databases and real temporary folders; no mocks.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model import valuation_workpaper_repository as repo  # noqa: E402
from import_valuation_workpapers import import_workpapers, scan  # noqa: E402

CLI = PY / "valuation_workpaper.py"


@pytest.fixture
def conn(tmp_path):
    connection = initialize_db(str(tmp_path / "domain_model.sqlite"))
    yield connection
    connection.close()


def _cli(db, *args, stdin=None):
    return subprocess.run([sys.executable, str(CLI), "--db", str(db), *args], input=stdin, capture_output=True, text=True)


# ── repository ────────────────────────────────────────────────────────────────

def test_a_document_round_trips_and_the_symbol_is_upper_cased(conn):
    doc = {"price": 123.4, "financials": {"revenue": [1, 2, 3]}, "note": None}
    workpaper_id, created = repo.put_workpaper(conn, "mu", "raw", doc, "2026-09-01", "mu_raw.json")
    assert created and workpaper_id
    assert repo.get_latest_workpaper(conn, "MU", "raw") == doc
    assert repo.get_latest_workpaper(conn, "mu", "raw") == doc


def test_identical_content_is_stored_once_and_changed_content_is_a_new_version(conn):
    first, created_first = repo.put_workpaper(conn, "MU", "scenarios", {"bear": 1}, "2026-09-01")
    again, created_again = repo.put_workpaper(conn, "MU", "scenarios", {"bear": 1}, "2026-09-02")
    changed, created_changed = repo.put_workpaper(conn, "MU", "scenarios", {"bear": 2}, "2026-09-03")
    assert (created_first, created_again, created_changed) == (True, False, True)
    assert again == first and changed != first
    assert repo.get_latest_workpaper(conn, "MU", "scenarios") == {"bear": 2}


def test_key_order_does_not_make_a_different_document(conn):
    repo.put_workpaper(conn, "MU", "wacc", {"a": 1, "b": 2})
    _, created = repo.put_workpaper(conn, "MU", "wacc", {"b": 2, "a": 1})
    assert created is False


def test_the_newest_by_date_wins_and_symbols_and_stages_do_not_mix(conn):
    repo.put_workpaper(conn, "MU", "raw", {"v": "old"}, "2026-08-01")
    repo.put_workpaper(conn, "MU", "raw", {"v": "new"}, "2026-09-01")
    repo.put_workpaper(conn, "NVDA", "raw", {"v": "nvda"}, "2026-09-01")
    repo.put_workpaper(conn, "MU", "wacc", {"v": "wacc"}, "2026-09-01")
    assert repo.get_latest_workpaper(conn, "MU", "raw") == {"v": "new"}
    assert repo.get_latest_workpaper(conn, "NVDA", "raw") == {"v": "nvda"}
    assert repo.get_latest_workpaper(conn, "AMD", "raw") is None
    assert repo.list_stages(conn, "MU") == ["raw", "wacc"]
    assert [r["as_of"] for r in repo.list_workpapers(conn, "MU", "raw")] == ["2026-09-01", "2026-08-01"]


# ── command line (the pipe flow the skill steps use) ──────────────────────────

def test_put_echoes_the_document_and_get_returns_it(tmp_path):
    db = tmp_path / "domain_model.sqlite"
    put = _cli(db, "put", "--ticker", "MU", "--stage", "raw", stdin='{"price": 99.5}')
    assert put.returncode == 0 and json.loads(put.stdout) == {"price": 99.5}
    got = _cli(db, "get", "--ticker", "MU", "--stage", "raw")
    assert got.returncode == 0 and json.loads(got.stdout) == {"price": 99.5}


def test_put_rejects_input_that_is_not_json_and_get_reports_a_missing_document(tmp_path):
    db = tmp_path / "domain_model.sqlite"
    bad = _cli(db, "put", "--ticker", "MU", "--stage", "raw", stdin="not json")
    assert bad.returncode == 2 and "not JSON" in bad.stderr
    missing = _cli(db, "get", "--ticker", "MU", "--stage", "raw")
    assert missing.returncode == 1 and "no 'raw' document" in missing.stderr


def test_list_shows_metadata_without_the_payload(tmp_path):
    db = tmp_path / "domain_model.sqlite"
    _cli(db, "put", "--ticker", "MU", "--stage", "raw", "--as-of", "2026-09-01", stdin='{"big": [1,2,3]}')
    listing = json.loads(_cli(db, "list", "--ticker", "MU").stdout)
    assert listing[0]["stage"] == "raw" and listing[0]["as_of"] == "2026-09-01" and "payload_json" not in listing[0]


def test_a_valuation_run_hands_its_documents_through_the_database_not_files(tmp_path):
    """The run: raw -> scenarios -> dcf_result, each step reading the previous one with `get`; no file is created."""
    db = tmp_path / "domain_model.sqlite"
    before = set(tmp_path.iterdir())
    assert _cli(db, "put", "--ticker", "MU", "--stage", "raw", stdin='{"price": 100, "revenue": 5000}').returncode == 0
    raw = json.loads(_cli(db, "get", "--ticker", "MU", "--stage", "raw").stdout)
    scenarios = {"bear": raw["price"] * 0.7, "base": raw["price"] * 1.2, "bull": raw["price"] * 1.6}
    assert _cli(db, "put", "--ticker", "MU", "--stage", "scenarios", stdin=json.dumps(scenarios)).returncode == 0
    scenarios_back = json.loads(_cli(db, "get", "--ticker", "MU", "--stage", "scenarios").stdout)
    dcf = {"weightedFairValue": round(sum(scenarios_back.values()) / 3, 2)}
    assert _cli(db, "put", "--ticker", "MU", "--stage", "dcf_result", stdin=json.dumps(dcf)).returncode == 0
    assert json.loads(_cli(db, "get", "--ticker", "MU", "--stage", "dcf_result").stdout) == {"weightedFairValue": 116.67}
    new_files = {p.name for p in set(tmp_path.iterdir()) - before if not p.name.startswith("domain_model.sqlite")}
    assert not any(n.endswith(".json") for n in new_files)


# ── one-time importer ─────────────────────────────────────────────────────────

def _temp_tree(tmp_path):
    temp = tmp_path / "temp"
    (temp / "evaluations").mkdir(parents=True)
    old = time.mktime((2026, 9, 1, 12, 0, 0, 0, 0, -1))

    def write(rel, text):
        path = temp / rel
        path.write_text(text)
        os.utime(path, (old, old))

    write("mu_raw.json", '{"price": 1}')
    write("mu_dcf_out.json", '{"weightedFairValue": 2}')
    write("evaluations/NVDA_scenarios.json", '{"bear": 1}')
    write("evaluations/NVDA_dcf_0.10.json", '{"x": 1}')
    write("evaluations/ZZZZ_raw.json", "{}")
    write("brief.json", "{}")
    write("evaluations/MU_broken.json", "{not json")
    return temp


def _db_with_symbols(tmp_path, symbols=("MU", "NVDA")):
    db = tmp_path / "domain_model.sqlite"
    connection = initialize_db(str(db))
    for s in symbols:
        resolve_investment(connection, s)
    connection.close()
    return db


def test_scan_classifies_files_and_reports_what_it_skips(tmp_path):
    temp = _temp_tree(tmp_path)
    found = scan(temp, {"MU", "NVDA"})
    kinds = sorted((s, st) for _p, s, st, _a, _d in found["importable"])
    assert kinds == [("MU", "dcf_out"), ("MU", "raw"), ("NVDA", "dcf_0.10"), ("NVDA", "scenarios")]
    reasons = {p.name: why for p, why in found["skipped"]}
    assert "unknown ticker ZZZZ" in reasons["ZZZZ_raw.json"]
    assert "not <ticker>_<stage>" in reasons["brief.json"]
    assert "not JSON" in reasons["MU_broken.json"]


def test_dry_run_writes_nothing_write_loads_with_the_file_date_and_a_rerun_adds_nothing(tmp_path):
    temp, db = _temp_tree(tmp_path), _db_with_symbols(tmp_path)
    dry = import_workpapers(temp, db, dry_run=True)
    assert dry["importable"] == 4 and dry["created"] == 0
    connection = initialize_db(str(db))
    assert repo.list_workpapers(connection) == []
    connection.close()

    first = import_workpapers(temp, db, dry_run=False)
    assert first["created"] == 4 and first["already_present"] == 0
    connection = initialize_db(str(db))
    assert repo.get_latest_workpaper(connection, "MU", "raw") == {"price": 1}
    assert repo.list_workpapers(connection, "MU", "raw")[0]["as_of"] == "2026-09-01"
    assert repo.list_workpapers(connection, "MU", "raw")[0]["source"] == "mu_raw.json"
    connection.close()

    again = import_workpapers(temp, db, dry_run=False)
    assert again["created"] == 0 and again["already_present"] == 4
    assert (temp / "mu_raw.json").exists()  # the importer never moves or deletes files


def test_extra_symbols_let_analysed_but_untracked_tickers_in_and_other_prefixes_stay_out(tmp_path):
    temp, db = _temp_tree(tmp_path), _db_with_symbols(tmp_path)
    report = import_workpapers(temp, db, dry_run=False, extra_symbols={"zzzz"})
    assert report["created"] == 5
    connection = initialize_db(str(db))
    assert repo.get_latest_workpaper(connection, "ZZZZ", "raw") == {}
    connection.close()
    assert any("brief.json" in name for name, _why in report["skipped"])
