"""Tests for computed_snapshot_repository.py against a real temporary SQLite database."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model import computed_snapshot_repository as repo  # noqa: E402


@pytest.fixture
def conn(tmp_path):
    connection = initialize_db(str(tmp_path / "domain_model.sqlite"))
    yield connection
    connection.close()


def test_the_latest_snapshot_is_the_newest_one_saved(conn):
    repo.save_snapshot(conn, "risk_snapshot", {"v": 1}, computed_at="2026-10-01T00:00:00+00:00")
    repo.save_snapshot(conn, "risk_snapshot", {"v": 2}, computed_at="2026-10-02T00:00:00+00:00")
    assert repo.load_latest_snapshot(conn, "risk_snapshot") == {"v": 2}
    payload, computed_at = repo.load_latest_snapshot_with_time(conn, "risk_snapshot")
    assert payload == {"v": 2} and computed_at == "2026-10-02T00:00:00+00:00"


def test_no_snapshot_returns_none(conn):
    assert repo.load_latest_snapshot(conn, "rebalance_plan") is None
    assert repo.load_latest_snapshot_with_time(conn, "rebalance_plan") is None


def test_names_do_not_mix(conn):
    repo.save_snapshot(conn, "risk_snapshot", {"a": 1})
    repo.save_snapshot(conn, "market_regime", {"b": 2})
    assert repo.load_latest_snapshot(conn, "market_regime") == {"b": 2}
    assert repo.load_latest_snapshot(conn, "rebalance_plan") is None


def test_an_unknown_name_is_rejected(conn):
    with pytest.raises(ValueError):
        repo.save_snapshot(conn, "portfolio", {})
    with pytest.raises(ValueError):
        repo.load_latest_snapshot(conn, "portfolio")


def test_history_is_pruned_to_the_newest_rows_and_listed_oldest_first(conn):
    for i in range(5):
        repo.save_snapshot(conn, "risk_officer_override", {"i": i}, computed_at=f"2026-10-0{i + 1}T00:00:00+00:00", keep=3)
    assert repo.list_snapshots(conn, "risk_officer_override") == [{"i": 2}, {"i": 3}, {"i": 4}]


def test_a_payload_round_trips_nested_values(conn):
    payload = {"orders": [{"ticker": "NVDA", "shares": 3.5}], "warnings": [], "x": None}
    repo.save_snapshot(conn, "rebalance_plan", payload)
    assert repo.load_latest_snapshot(conn, "rebalance_plan") == payload
