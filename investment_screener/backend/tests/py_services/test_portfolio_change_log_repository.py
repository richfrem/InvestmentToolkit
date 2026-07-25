import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.portfolio_change_log_repository import (  # noqa: E402
    add_change_log_entry,
    list_change_log,
)


def test_add_change_log_entry_appends_does_not_replace(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    add_change_log_entry(conn, "9.6", "2026-07-02", "First entry.", "2026-07-02T00:00:00Z")
    add_change_log_entry(conn, "9.8", "2026-07-05", "Second entry.", "2026-07-05T00:00:00Z")
    entries = list_change_log(conn)
    assert len(entries) == 2


def test_list_change_log_ordered_by_date_ascending(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    add_change_log_entry(conn, "10.8", "2026-07-10", "Later entry.", "2026-07-10T00:00:00Z")
    add_change_log_entry(conn, "9.6", "2026-07-02", "Earlier entry.", "2026-07-02T00:00:00Z")
    entries = list_change_log(conn)
    assert entries[0]["note"] == "Earlier entry."
    assert entries[1]["note"] == "Later entry."


def test_list_change_log_returns_empty_when_none(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    assert list_change_log(conn) == []
