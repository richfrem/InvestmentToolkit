import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    save_projection_version,
    get_latest_projection,
    list_projection_versions,
    add_projection_scenario,
    get_projection_scenarios,
)


def _seed_investment(conn):
    return resolve_investment(conn, "AAPL", asset_class="EQUITY", currency="USD")


def test_save_and_get_latest_projection(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
        fair_value=180.0, action="ACCUMULATE",
    )
    save_projection_version(
        conn, investment_id, version=2, saved_at="2026-07-10T00:00:00Z",
        fair_value=190.0, action="MAINTAIN",
    )
    latest = get_latest_projection(conn, investment_id)
    assert latest["version"] == 2
    assert latest["fair_value"] == 190.0
    assert latest["action"] == "MAINTAIN"


def test_save_projection_version_upserts_on_investment_and_version(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    id_1 = save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z", fair_value=180.0,
    )
    id_2 = save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T01:00:00Z", fair_value=185.0,
    )
    assert id_1 == id_2
    versions = list_projection_versions(conn, investment_id)
    assert len(versions) == 1
    assert versions[0]["fair_value"] == 185.0


def test_list_projection_versions_returns_all_ascending(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    save_projection_version(conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z")
    save_projection_version(conn, investment_id, version=2, saved_at="2026-07-10T00:00:00Z")
    versions = list_projection_versions(conn, investment_id)
    assert [v["version"] for v in versions] == [1, 2]


def test_projection_with_no_scenarios_block(tmp_path):
    """Legacy-format projections have no 'scenarios' block at all (confirmed real,
    apply_catalyst.py:176-179's 'legacy format' branch) — get_projection_scenarios must
    return an empty list, not raise, for a projection_id with zero scenario rows."""
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    projection_id = save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
    )
    assert get_projection_scenarios(conn, projection_id) == []


def test_add_and_get_projection_scenarios(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    projection_id = save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
    )
    add_projection_scenario(
        conn, projection_id, "bear", weight=0.2, growth_rate=5.0, net_margin=10.0,
        exit_pe=15.0, quality_multiplier=1.0, share_change=0.0, scenario_price=150.0,
    )
    add_projection_scenario(
        conn, projection_id, "base", weight=0.5, growth_rate=10.0, net_margin=15.0,
        exit_pe=20.0, quality_multiplier=1.0, share_change=0.0, scenario_price=180.0,
    )
    add_projection_scenario(
        conn, projection_id, "bull", weight=0.3, growth_rate=15.0, net_margin=20.0,
        exit_pe=25.0, quality_multiplier=1.2, share_change=-1.0, scenario_price=220.0,
    )
    scenarios = get_projection_scenarios(conn, projection_id)
    assert {s["scenario_name"] for s in scenarios} == {"bear", "base", "bull"}


def test_add_projection_scenario_upserts_on_projection_and_name(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    projection_id = save_projection_version(
        conn, investment_id, version=1, saved_at="2026-07-01T00:00:00Z",
    )
    add_projection_scenario(conn, projection_id, "bear", weight=0.2, scenario_price=150.0)
    add_projection_scenario(conn, projection_id, "bear", weight=0.25, scenario_price=155.0)
    scenarios = get_projection_scenarios(conn, projection_id)
    assert len(scenarios) == 1
    assert scenarios[0]["weight"] == 0.25
