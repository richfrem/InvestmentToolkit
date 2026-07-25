"""
Tests for update_targets.py — Wave 8 cutover to domain_model.sqlite.

Real bug this replaces: load()/save() read/wrote target-portfolio.json
directly; the canonical target-weight editor tool used during conversation
(via /calibrate-targets, /thesis-review) would have kept editing a file no
longer read by the live app once portfolio.json-style retirement extended
to this domain.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "plugins/portfolio-advisor/scripts"
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PY_SERVICES))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
from domain_model.pillar_repository import resolve_pillar  # noqa: E402
import update_targets  # noqa: E402


def _seed(db_path):
    conn = initialize_db(str(db_path))
    resolve_pillar(conn, "compute", "Compute", target_weight=40.0)
    nvda_id = resolve_investment(conn, "NVDA", asset_class="EQUITY")
    update_investment_fields(conn, nvda_id, target_weight=10.0, pillar_id="compute", lifecycle_status="accumulate")
    conn.close()


def test_load_reads_from_sqlite_not_json(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    _seed(db_path)
    monkeypatch.setattr(update_targets, "DB_PATH", db_path)

    data = update_targets.load()
    assert data["holdings"][0]["ticker"] == "NVDA"
    assert data["holdings"][0]["targetWeight"] == 10.0


def test_save_writes_target_weight_to_investment(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    _seed(db_path)
    monkeypatch.setattr(update_targets, "DB_PATH", db_path)

    data = update_targets.load()
    data["holdings"][0]["targetWeight"] = 100.0
    update_targets.save(data)

    conn = initialize_db(str(db_path))
    row = conn.execute("SELECT target_weight FROM investment WHERE symbol = 'NVDA';").fetchone()
    conn.close()
    assert row[0] == 100.0


def test_apply_set_then_save_round_trips_normalized_weight(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    _seed(db_path)
    monkeypatch.setattr(update_targets, "DB_PATH", db_path)

    data = update_targets.load()
    data = update_targets.apply_set(data, ["NVDA=50"], dry_run=False)
    data = update_targets.normalize(data)
    update_targets.save(data)

    conn = initialize_db(str(db_path))
    row = conn.execute("SELECT target_weight FROM investment WHERE symbol = 'NVDA';").fetchone()
    conn.close()
    assert row[0] == 100.0  # only holding -> normalizes to 100%


def test_apply_add_creates_new_investment_row(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    _seed(db_path)
    monkeypatch.setattr(update_targets, "DB_PATH", db_path)

    data = update_targets.load()
    data = update_targets.apply_add(data, ["AMD=5"], "AMD Inc", "compute", "sa-asi-race", "", dry_run=False)
    update_targets.save(data)

    conn = initialize_db(str(db_path))
    row = conn.execute("SELECT target_weight, pillar_id FROM investment WHERE symbol = 'AMD';").fetchone()
    conn.close()
    assert row is not None
    assert row[0] == 5.0
    assert row[1] == "compute"


def test_no_longer_references_target_portfolio_json():
    src = (SCRIPT_DIR / "update_targets.py").read_text()
    assert "target-portfolio.json" not in src
