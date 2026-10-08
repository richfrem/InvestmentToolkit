#!/usr/bin/env python3
"""
test_tv_account_coverage.py - Tests for detecting and retrying partial TradingView account reads.

Purpose:
    A sync that reads RRSP but not TFSA must be noticed and retried, and a partial
    position snapshot must not be saved as if it were complete (2026-10-08).

Layer:
    Testing / Plugins / TradingView

Usage Examples:
    pytest plugins/tradingview/tests/test_tv_account_coverage.py

Key Functions (Index):
    - test_a_partial_read_is_retried_until_every_account_is_covered()
    - test_the_most_complete_read_is_returned_with_what_is_still_missing()
    - test_a_partial_position_snapshot_is_refused()

Key Input Dependencies:
    - plugins/tradingview/scripts/tv_account_coverage.py
    - plugins/tradingview/scripts/fetch_broker_data.py
    - plugins/tradingview/scripts/tv_trades_import.py
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))

import fetch_broker_data  # noqa: E402
import tv_trades_import  # noqa: E402
from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from tv_account_coverage import accounts_with_holdings, missing_accounts, read_until_complete  # noqa: E402


def snap(*names: str) -> dict:
    return {"accounts": [{"accountType": name} for name in names]}


def names(snapshot: dict) -> list[str]:
    return [account["accountType"] for account in snapshot["accounts"]]


def reader(*results: dict):
    queue = list(results)
    calls = []

    def fetch() -> dict:
        calls.append(1)
        return queue.pop(0) if len(queue) > 1 else queue[0]
    fetch.calls = calls
    return fetch


def test_missing_accounts_ignores_case_and_extra_accounts():
    assert missing_accounts({"TFSA", "RRSP"}, ["rrsp", "CASH"]) == ["TFSA"]
    assert missing_accounts({"TFSA"}, ["TFSA", "RRSP"]) == []


def test_a_partial_read_is_retried_until_every_account_is_covered():
    fetch = reader(snap("RRSP"), snap("TFSA", "RRSP"))
    result, missing = read_until_complete(fetch, names, {"TFSA", "RRSP"})
    assert (names(result), missing, len(fetch.calls)) == (["TFSA", "RRSP"], [], 2)


def test_a_complete_first_read_is_not_repeated():
    fetch = reader(snap("TFSA", "RRSP"))
    assert read_until_complete(fetch, names, {"TFSA", "RRSP"})[1] == [] and len(fetch.calls) == 1


def test_the_most_complete_read_is_returned_with_what_is_still_missing():
    fetch = reader(snap(), snap("RRSP"), {"error": "panel closed"})
    result, missing = read_until_complete(fetch, names, {"TFSA", "RRSP"}, attempts=3)
    assert (names(result), missing, len(fetch.calls)) == (["RRSP"], ["TFSA"], 3)


def test_an_error_is_returned_only_when_every_read_failed():
    result, missing = read_until_complete(reader({"error": "no broker"}), names, {"TFSA"}, attempts=2)
    assert result == {"error": "no broker"} and missing == ["TFSA"]


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "domain_model.sqlite")
    conn = initialize_db(path)
    investment = resolve_investment(conn, "CORZ")
    for account, quantity in (("TFSA", 56), ("RRSP", 21), ("CASH", 0)):
        upsert_account(conn, account, account, account)
        upsert_account_investment(conn, account, investment, quantity=quantity, average_cost=1.0, book_value=quantity,
                                  currency="USD", last_synced_at="2026-10-08T00:00:00+00:00")
    conn.commit()
    yield conn, path
    conn.close()


def test_only_accounts_that_hold_something_are_expected(db):
    assert accounts_with_holdings(db[0]) == {"TFSA", "RRSP"}


def position_snapshot(**accounts: int) -> dict:
    snapshots = [{"accountType": name, "positions": [{"symbol": "CORZ", "quantity": qty}], "balances": {}}
                 for name, qty in accounts.items()]
    return {"accounts": [{"accountType": s["accountType"]} for s in snapshots], "snapshots": snapshots,
            "positions": [p for s in snapshots for p in s["positions"]]}


def test_a_partial_position_snapshot_is_refused(db, monkeypatch):
    """RRSP alone came back once and was saved, leaving TFSA stale with nothing said."""
    monkeypatch.setattr(fetch_broker_data, "fetch_tv_snapshot", lambda: position_snapshot(RRSP=21))
    snapshot, missing = fetch_broker_data.fetch_complete_tv_snapshot(db[1])
    assert missing == ["TFSA"] and [s["accountType"] for s in snapshot["snapshots"]] == ["RRSP"]


def test_an_account_that_failed_to_switch_counts_as_missing(db, monkeypatch):
    broken = position_snapshot(RRSP=21)
    broken["snapshots"].append({"accountType": "TFSA", "error": "switch failed", "positions": [], "balances": {}})
    monkeypatch.setattr(fetch_broker_data, "fetch_tv_snapshot", lambda: broken)
    assert fetch_broker_data.fetch_complete_tv_snapshot(db[1])[1] == ["TFSA"]


def test_a_complete_position_snapshot_passes(db, monkeypatch):
    reads = iter([position_snapshot(RRSP=21), position_snapshot(TFSA=56, RRSP=21)])
    monkeypatch.setattr(fetch_broker_data, "fetch_tv_snapshot", lambda: next(reads))
    snapshot, missing = fetch_broker_data.fetch_complete_tv_snapshot(db[1])
    assert missing == [] and len(snapshot["snapshots"]) == 2


def test_trade_import_reports_an_account_it_could_not_read(db, monkeypatch):
    monkeypatch.setattr(tv_trades_import, "fetch_tv_order_history",
                        lambda: {"accounts": [{"accountType": "TFSA", "orders": [], "expectedCount": 0}]})
    snapshot, missing = tv_trades_import.fetch_complete_order_history(db[1])
    assert missing == ["RRSP"] and len(snapshot["accounts"]) == 1
