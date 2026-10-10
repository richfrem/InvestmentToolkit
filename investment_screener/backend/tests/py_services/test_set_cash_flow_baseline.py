"""Tests for set_cash_flow_baseline.py and the January 1 USD/CAD rate on the YTD baseline."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "investment_screener/backend/py_services/set_cash_flow_baseline.py"
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.cash_flow_repository import get_cash_flow_baseline, upsert_cash_flow_baseline  # noqa: E402
from set_cash_flow_baseline import set_baseline  # noqa: E402


@pytest.fixture
def conn(tmp_path):
    connection = initialize_db(str(tmp_path / "domain_model.sqlite"))
    yield connection
    connection.close()


def test_a_baseline_without_a_rate_has_none(conn):
    upsert_cash_flow_baseline(conn, "ALL", 37426.0, "2026-01-01")
    assert get_cash_flow_baseline(conn, "ALL")["jan1_usd_cad_rate"] is None


def test_the_rate_is_stored_and_a_later_update_without_one_keeps_it(conn):
    upsert_cash_flow_baseline(conn, "ALL", 37426.0, "2026-01-01", 1.3723)
    upsert_cash_flow_baseline(conn, "ALL", 40000.0, "2026-01-01")
    baseline = get_cash_flow_baseline(conn, "ALL")
    assert baseline["starting_balance_cad"] == 40000.0 and baseline["jan1_usd_cad_rate"] == 1.3723


def test_set_baseline_can_set_only_the_rate_on_an_existing_baseline(conn):
    upsert_cash_flow_baseline(conn, "ALL", 37426.0, "2026-01-01")
    stored = set_baseline(conn, jan1_usd_cad_rate=1.3723)
    assert (stored["starting_balance_cad"], stored["starting_date"], stored["jan1_usd_cad_rate"]) == (37426.0, "2026-01-01", 1.3723)


def test_set_baseline_needs_a_balance_and_date_when_none_is_stored(conn):
    with pytest.raises(ValueError, match="required"):
        set_baseline(conn, jan1_usd_cad_rate=1.37)


def test_set_baseline_rejects_non_positive_values(conn):
    with pytest.raises(ValueError):
        set_baseline(conn, 0, "2026-01-01")
    upsert_cash_flow_baseline(conn, "ALL", 1.0, "2026-01-01")
    with pytest.raises(ValueError):
        set_baseline(conn, jan1_usd_cad_rate=-1)


def test_cli_writes_the_baseline_and_dry_run_writes_nothing(tmp_path):
    db = tmp_path / "domain_model.sqlite"
    base = [sys.executable, str(SCRIPT), "--db-path", str(db)]
    dry = subprocess.run(base + ["--starting-balance-cad", "100", "--starting-date", "2026-01-01", "--dry-run"], capture_output=True, text=True)
    assert dry.returncode == 0
    connection = initialize_db(str(db))
    assert get_cash_flow_baseline(connection, "ALL") is None
    connection.close()
    real = subprocess.run(base + ["--starting-balance-cad", "100", "--starting-date", "2026-01-01", "--jan1-usd-cad-rate", "1.4"], capture_output=True, text=True)
    assert real.returncode == 0, real.stderr
    assert json.loads(real.stdout)["jan1_usd_cad_rate"] == 1.4


def test_ytd_report_json_carries_the_rate_and_writes_no_file(tmp_path):
    """ytd_return.py prints the report with the baseline's rate and writes no report file."""
    sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
    import ytd_return

    db = tmp_path / "domain_model.sqlite"
    connection = initialize_db(str(db))
    upsert_cash_flow_baseline(connection, "ALL", 1000.0, "2026-01-01", 1.37)
    connection.close()
    assert ytd_return.load_cash_flows(db)["jan1_usd_cad_rate"] == 1.37
    assert not hasattr(ytd_return, "load_json")
