import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402

EXPECTED_TABLES = {
    "account",
    "investment",
    "account_investment",
    "investment_price",
    "strategy_pillar",
    "sub_strategy",
    "price_level_set",
    "price_level_tier",
    "alert",
    "investment_note",
    "projection_version",
    "projection_scenario",
    "trade_log_entry",
    "order_execution",
    "cash_flow",
    "cash_flow_baseline",
    "portfolio_policy",
}


def test_initialize_db_creates_every_v32_table(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    actual_tables = {row[0] for row in cursor.fetchall()}
    missing = EXPECTED_TABLES - actual_tables
    assert not missing, f"Missing tables: {missing}"


def test_initialize_db_enforces_foreign_keys(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    cursor = conn.execute("PRAGMA foreign_keys;")
    assert cursor.fetchone()[0] == 1


def test_initialize_db_is_idempotent(tmp_path):
    db_path = str(tmp_path / "domain_model_test.sqlite")
    conn1 = initialize_db(db_path)
    conn1.close()
    conn2 = initialize_db(db_path)  # must not raise on re-open of existing file
    cursor = conn2.execute("SELECT COUNT(*) FROM investment;")
    assert cursor.fetchone()[0] == 0


def test_investment_symbol_unique_constraint_enforced(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    conn.execute(
        "INSERT INTO investment (investment_id, symbol, asset_class, currency, updated_at) "
        "VALUES ('aapl-1', 'AAPL', 'EQUITY', 'USD', '2026-07-19T00:00:00Z');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO investment (investment_id, symbol, asset_class, currency, updated_at) "
            "VALUES ('aapl-2', 'AAPL', 'EQUITY', 'USD', '2026-07-19T00:00:00Z');"
        )


def test_account_investment_unique_account_plus_investment_enforced(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    conn.execute(
        "INSERT INTO account (account_id, account_name, account_type) VALUES ('TFSA', 'TFSA', 'TFSA');"
    )
    conn.execute(
        "INSERT INTO investment (investment_id, symbol, asset_class, currency, updated_at) "
        "VALUES ('aapl-1', 'AAPL', 'EQUITY', 'USD', '2026-07-19T00:00:00Z');"
    )
    conn.execute(
        "INSERT INTO account_investment "
        "(account_investment_id, account_id, investment_id, quantity, last_synced_at) "
        "VALUES ('TFSA:aapl-1', 'TFSA', 'aapl-1', 10, '2026-07-19T00:00:00Z');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO account_investment "
            "(account_investment_id, account_id, investment_id, quantity, last_synced_at) "
            "VALUES ('TFSA:aapl-1-dup', 'TFSA', 'aapl-1', 5, '2026-07-19T01:00:00Z');"
        )


def test_projection_version_unique_investment_plus_version_enforced(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    conn.execute(
        "INSERT INTO investment (investment_id, symbol, asset_class, currency, updated_at) "
        "VALUES ('aapl-1', 'AAPL', 'EQUITY', 'USD', '2026-07-19T00:00:00Z');"
    )
    conn.execute(
        "INSERT INTO projection_version (projection_id, investment_id, version, saved_at) "
        "VALUES ('p1', 'aapl-1', 1, '2026-07-19T00:00:00Z');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO projection_version (projection_id, investment_id, version, saved_at) "
            "VALUES ('p2', 'aapl-1', 1, '2026-07-19T01:00:00Z');"
        )


def test_projection_scenario_unique_projection_plus_scenario_name_enforced(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    conn.execute(
        "INSERT INTO investment (investment_id, symbol, asset_class, currency, updated_at) "
        "VALUES ('aapl-1', 'AAPL', 'EQUITY', 'USD', '2026-07-19T00:00:00Z');"
    )
    conn.execute(
        "INSERT INTO projection_version (projection_id, investment_id, version, saved_at) "
        "VALUES ('p1', 'aapl-1', 1, '2026-07-19T00:00:00Z');"
    )
    conn.execute(
        "INSERT INTO projection_scenario (scenario_id, projection_id, scenario_name) "
        "VALUES ('s1', 'p1', 'base');"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO projection_scenario (scenario_id, projection_id, scenario_name) "
            "VALUES ('s2', 'p1', 'base');"
        )


def test_expected_indexes_exist(tmp_path):
    conn = initialize_db(str(tmp_path / "domain_model_test.sqlite"))
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index';")
    actual_indexes = {row[0] for row in cursor.fetchall()}
    expected_indexes = {
        "idx_investment_pillar",
        "idx_investment_lifecycle",
        "idx_account_investment_account",
        "idx_account_investment_investment",
        "idx_projection_investment",
        "idx_projection_scenario_projection",
        "idx_alert_investment",
        "idx_investment_note_investment",
    }
    missing = expected_indexes - actual_indexes
    assert not missing, f"Missing indexes: {missing}"
