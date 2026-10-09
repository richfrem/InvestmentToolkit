"""Tests for system_health.py's data checks, which read domain_model.sqlite only.

Purpose:
    The synced-positions, target-weights and projections checks take their facts from the
    database (last_synced_at, investment.target_weight, projection_version), report an
    explicit state for an empty or missing database, and never look at retired JSON files.

Key Input Dependencies: none (each test builds a real temporary SQLite database).
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

import system_health  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
from domain_model.projection_repository import save_projection_version  # noqa: E402


@pytest.fixture
def db(tmp_path):
    """Path of an initialised, empty domain_model.sqlite."""
    path = tmp_path / "domain_model.sqlite"
    initialize_db(str(path)).close()
    return path


def _sync(db, age_minutes):
    """Sync."""
    conn = initialize_db(str(db))
    synced = (datetime.now(timezone.utc) - timedelta(minutes=age_minutes)).isoformat()
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    upsert_account_investment(conn, "TFSA", resolve_investment(conn, "AAPL"), 1, 1.0, 1.0, "USD", synced)
    conn.close()


def _targets(db, weights):
    """Targets."""
    conn = initialize_db(str(db))
    for symbol, weight in weights.items():
        update_investment_fields(conn, resolve_investment(conn, symbol), target_weight=weight)
    conn.close()


def test_fresh_sync_passes(db):
    """Positions synced minutes ago pass."""
    _sync(db, 5)
    result = system_health._check_synced_positions(db)
    assert result["status"] == "PASS" and result["age_minutes"] < 10


def test_old_sync_warns_with_the_age(db):
    """Positions synced two hours ago warn and say how old they are."""
    _sync(db, 120)
    result = system_health._check_synced_positions(db)
    assert result["status"] == "WARN" and 110 < result["age_minutes"] < 130
    assert "tv-portfolio-sync" in result["detail"]


def test_no_synced_positions_fails_with_the_fix(db):
    """An initialised database with no positions fails and names the sync command."""
    result = system_health._check_synced_positions(db)
    assert result["status"] == "FAIL" and "tv-portfolio-sync" in result["detail"]


def test_missing_database_fails_and_is_not_created(tmp_path):
    """A missing database is reported, not silently created by the check."""
    path = tmp_path / "absent.sqlite"
    assert system_health._check_synced_positions(path)["status"] == "FAIL"
    assert system_health._check_target_weights(path)["status"] == "FAIL"
    assert system_health._check_projections(path)["status"] == "FAIL"
    assert not path.exists()


def test_target_weights_summing_to_100_pass(db):
    """Weights that sum to 100 pass."""
    _targets(db, {"AAPL": 60.0, "MSFT": 40.0})
    result = system_health._check_target_weights(db)
    assert result["status"] == "PASS" and "100.0000" in result["detail"]


def test_target_weights_off_by_more_than_half_a_point_fail(db):
    """Weights summing to 60 fail and show the sum."""
    _targets(db, {"AAPL": 60.0})
    result = system_health._check_target_weights(db)
    assert result["status"] == "FAIL" and "60.0000" in result["detail"]


def test_no_target_weights_fail(db):
    """No weights at all fails with an explicit message, not a crash."""
    result = system_health._check_target_weights(db)
    assert result["status"] == "FAIL" and "no target weights" in result["detail"].lower()


def test_projections_missing_for_a_holding_warn_and_list_it(db):
    """A thesis holding without a projection version is listed as missing."""
    _targets(db, {"AAPL": 50.0, "MSFT": 50.0})
    conn = initialize_db(str(db))
    save_projection_version(conn, resolve_investment(conn, "AAPL"), 1, "2026-10-01T00:00:00Z")
    conn.close()
    result = system_health._check_projections(db)
    assert result["status"] == "WARN" and result["missing"] == ["MSFT"]
    assert result["detail"].startswith("1/2")


def test_projections_present_for_every_holding_pass(db):
    """Every thesis holding has a projection: pass."""
    _targets(db, {"AAPL": 100.0})
    conn = initialize_db(str(db))
    save_projection_version(conn, resolve_investment(conn, "AAPL"), 1, "2026-10-01T00:00:00Z")
    conn.close()
    assert system_health._check_projections(db)["status"] == "PASS"


def test_check_labels_describe_the_database_not_retired_files():
    """No check label or module text names a retired file."""
    labels = [name for name, _fn in system_health.CHECKS]
    assert "Synced positions" in labels and "portfolio.json" not in labels
    source = Path(system_health.__file__).read_text()
    assert "portfolio.json" not in source and "target-portfolio.json" not in source
