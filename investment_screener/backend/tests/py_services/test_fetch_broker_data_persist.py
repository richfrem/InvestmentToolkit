"""
Tests fetch_broker_data.py's Wave 3 Task 5.7 rewire: write_snapshot() now also
persists the real snapshot's per-account positions/cash into domain_model.sqlite
via _persist_snapshot_to_db(), additive alongside the existing portfolio.json write.

fetch_broker_data.py is the real target of two symlinks
(investment_screener/backend/py_services/fetch_broker_data.py and
plugins/tradingview/skills/tv-portfolio-sync/scripts/fetch_broker_data.py) --
confirmed identical via `diff` before this rewire, so editing this one real file
rewires all three access paths together (not 3 independent write paths).
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "plugins/tradingview/scripts"
DOMAIN_MODEL_PY_SERVICES_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(DOMAIN_MODEL_PY_SERVICES_DIR))

import fetch_broker_data  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_investment_repository import list_account_investments  # noqa: E402
from domain_model.exchange_rate_repository import get_exchange_rate  # noqa: E402
from domain_model.broker_reported_total_repository import get_broker_reported_total  # noqa: E402

SNAPSHOT = {
    "accounts": [{"accountType": "TFSA", "accountId": "1"}],
    "snapshots": [
        {
            "accountType": "TFSA",
            "balances": {"cashUSD": 300.0},
            "positions": [{"symbol": "MSFT", "quantity": 4, "avgFillPrice": 410.0}],
        },
    ],
    "positions": [{"symbol": "MSFT", "quantity": 4, "avgFillPrice": 410.0, "accountType": "TFSA"}],
}


def test_persist_snapshot_to_db_writes_real_positions_and_cash(tmp_path):
    db_path = str(tmp_path / "test.sqlite")
    written = fetch_broker_data._persist_snapshot_to_db(SNAPSHOT, db_path=db_path)
    assert written == 1

    conn = initialize_db(db_path)
    rows = {r["investment_id"]: r for r in list_account_investments(conn, account_id="TFSA")}
    assert rows["MSFT"]["quantity"] == 4
    assert rows["MSFT"]["average_cost"] == 410.0
    assert rows["CASH_USD"]["quantity"] == 300.0


def test_persist_snapshot_to_db_computes_and_stores_exchange_rate(tmp_path):
    """A snapshot carrying TV's native CAD/USD equity totals must produce the
    inferred rate (sum CAD / sum USD across snapshots, exactly mirroring
    helpers.ts::getLiveUsdCadRate) in broker_exchange_rate."""
    db_path = str(tmp_path / "test.sqlite")
    snapshot = {
        "snapshots": [
            {"accountType": "TFSA",
             "balances": {"cashUSD": 100.0, "totalEquityCADCombined": 6900.0, "totalEquityUSDCombined": 5000.0},
             "positions": [{"symbol": "MSFT", "quantity": 1, "avgFillPrice": 400.0}]},
            {"accountType": "RRSP",
             "balances": {"totalEquityCADCombined": 1380.0, "totalEquityUSDCombined": 1000.0},
             "positions": []},
        ]
    }
    fetch_broker_data._persist_snapshot_to_db(snapshot, db_path=db_path)
    conn = initialize_db(db_path)
    # (6900 + 1380) / (5000 + 1000) = 8280 / 6000 = 1.38
    assert get_exchange_rate(conn) == 1.38


def test_persist_snapshot_to_db_no_totals_leaves_rate_unset(tmp_path):
    """A snapshot with no CAD/USD equity totals must NOT write a bogus rate row."""
    db_path = str(tmp_path / "test.sqlite")
    fetch_broker_data._persist_snapshot_to_db(SNAPSHOT, db_path=db_path)
    conn = initialize_db(db_path)
    assert get_exchange_rate(conn) is None


def test_persist_snapshot_to_db_stores_broker_reported_total(tmp_path):
    """When a totals block is threaded in, the broker's reported totalUSD/CAD/source
    lands in broker_reported_total for verify_portfolio_total.py's audit."""
    db_path = str(tmp_path / "test.sqlite")
    totals = {"totalUSD": 30373.98, "totalCAD": 41900.0, "totalSource": "tv_authoritative"}
    fetch_broker_data._persist_snapshot_to_db(SNAPSHOT, db_path=db_path, totals=totals)
    conn = initialize_db(db_path)
    row = get_broker_reported_total(conn)
    assert row["total_usd"] == 30373.98
    assert row["total_cad"] == 41900.0
    assert row["source"] == "tv_authoritative"


def test_persist_snapshot_to_db_no_totals_leaves_broker_total_unset(tmp_path):
    """No totals block (or no totalUSD) must NOT write a bogus broker_reported_total row."""
    db_path = str(tmp_path / "test.sqlite")
    fetch_broker_data._persist_snapshot_to_db(SNAPSHOT, db_path=db_path)
    conn = initialize_db(db_path)
    assert get_broker_reported_total(conn) is None


def test_write_snapshot_persists_broker_reported_total_from_balances(tmp_path, monkeypatch):
    """write_snapshot builds totals from live balances, then threads them into the
    DB persist so the broker's reported total is captured alongside positions."""
    monkeypatch.setattr(fetch_broker_data, "DATA_DIR", str(tmp_path))
    db_path = str(tmp_path / "domain_model.sqlite")
    monkeypatch.setattr(fetch_broker_data, "DOMAIN_MODEL_DB_PATH", db_path)
    monkeypatch.setattr(fetch_broker_data, "_run_portfolio_refresh", lambda: None)

    balances = {"totalEquityUSDCombined": 30373.98, "marketValueUSDCombined": 29000.0,
                "cashUSDCombined": 1373.98}
    fetch_broker_data.write_snapshot(SNAPSHOT, balances=balances)
    conn = initialize_db(db_path)
    row = get_broker_reported_total(conn)
    assert row["total_usd"] == 30373.98
    assert row["source"] == "tv_authoritative"


def test_persist_snapshot_to_db_skips_non_real_accounts_and_zero_qty(tmp_path):
    db_path = str(tmp_path / "test.sqlite")
    snapshot = {
        "snapshots": [
            {"accountType": "MARGIN", "balances": {"cashUSD": 50}, "positions": [{"symbol": "X", "quantity": 1}]},
            {"accountType": "RRSP", "balances": {}, "positions": [{"symbol": "Y", "quantity": 0}]},
        ]
    }
    written = fetch_broker_data._persist_snapshot_to_db(snapshot, db_path=db_path)
    assert written == 0

    conn = initialize_db(db_path)
    assert list_account_investments(conn, account_id="MARGIN") == []
    assert list_account_investments(conn, account_id="RRSP") == []


def test_write_snapshot_persists_to_sqlite_only(tmp_path, monkeypatch):
    """Wave 3 completion: write_snapshot is now SQLite-only. It persists the real
    per-account positions/cash to domain_model.sqlite and does NOT write
    portfolio.json anymore (the former IPC/holdings/totals JSON write is gone)."""
    monkeypatch.setattr(fetch_broker_data, "DATA_DIR", str(tmp_path))
    db_path = str(tmp_path / "domain_model.sqlite")
    monkeypatch.setattr(fetch_broker_data, "DOMAIN_MODEL_DB_PATH", db_path)
    monkeypatch.setattr(fetch_broker_data, "_run_portfolio_refresh", lambda: None)

    fetch_broker_data.write_snapshot(SNAPSHOT, balances=None)

    # portfolio.json must NOT be written anymore.
    assert not (tmp_path / "portfolio.json").exists()

    conn = initialize_db(db_path)
    rows = {r["investment_id"]: r for r in list_account_investments(conn, account_id="TFSA")}
    assert rows["MSFT"]["quantity"] == 4


def test_write_snapshot_never_touches_portfolio_json_even_with_balances(tmp_path, monkeypatch):
    """Even with a live balances payload (which formerly drove the totals/holdings
    JSON write), no portfolio.json is produced."""
    monkeypatch.setattr(fetch_broker_data, "DATA_DIR", str(tmp_path))
    db_path = str(tmp_path / "domain_model.sqlite")
    monkeypatch.setattr(fetch_broker_data, "DOMAIN_MODEL_DB_PATH", db_path)
    monkeypatch.setattr(fetch_broker_data, "_run_portfolio_refresh", lambda: None)

    balances = {"totalEquityUSDCombined": 30373.98, "marketValueUSDCombined": 29000.0,
                "cashUSDCombined": 1373.98}
    fetch_broker_data.write_snapshot(SNAPSHOT, balances=balances)
    assert not (tmp_path / "portfolio.json").exists()


def test_emit_snapshot_json_prints_single_json_line_to_stdout(capsys):
    """The stdout IPC channel: emit_snapshot_json prints the snapshot as one
    machine-parseable JSON line on stdout (and nothing else on stdout), so the
    Node caller can JSON.parse the last non-empty stdout line."""
    fetch_broker_data.emit_snapshot_json(SNAPSHOT)
    captured = capsys.readouterr()
    stdout_lines = [ln for ln in captured.out.splitlines() if ln.strip()]
    assert len(stdout_lines) == 1
    assert json.loads(stdout_lines[0]) == SNAPSHOT
