import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import list_accounts  # noqa: E402
from domain_model.account_investment_repository import list_account_investments  # noqa: E402
from domain_model.migrate_portfolio_to_sqlite import (  # noqa: E402
    run_dry_run_migration,
    run_real_migration,
)

FIXTURE_PORTFOLIO = {
    "holdings": [
        {"symbol": "AAPL", "shares": 13, "price": 150.0},
    ],
    "totals": {"totalUSD": 1950.0, "totalCAD": 2691.0, "exchangeRate": 1.38, "totalSource": "tv_authoritative"},
    "tvSnapshot": {
        "accounts": [
            {"accountType": "TFSA", "accountId": "acct-tfsa-1", "displayText": "TFSA - acct-tfsa-1"},
            {"accountType": "RRSP", "accountId": "acct-rrsp-1", "displayText": "RRSP - acct-rrsp-1"},
        ],
        "snapshots": [
            {
                "accountType": "TFSA", "accountId": "acct-tfsa-1",
                "balances": {"cashUSD": 100.0, "cashCAD": 0.0},
                "positions": [
                    {"symbol": "AAPL", "direction": "Long", "quantity": 10, "avgFillPrice": 140.0, "positionId": "p1"},
                ],
            },
            {
                "accountType": "RRSP", "accountId": "acct-rrsp-1",
                "balances": {"cashUSD": 50.0, "cashCAD": 0.0},
                "positions": [
                    {"symbol": "AAPL", "direction": "Long", "quantity": 3, "avgFillPrice": 140.0, "positionId": "p2"},
                ],
            },
        ],
    },
}


def test_dry_run_does_not_touch_any_db(tmp_path):
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(FIXTURE_PORTFOLIO))
    report = run_dry_run_migration(str(portfolio_path))
    assert report["positions_count"] == 2  # one position row per (account, symbol), not per aggregated holding
    assert report["accounts_found"] == {"TFSA", "RRSP"}
    # No db_path was ever passed -- dry run cannot have written anything.


def test_real_migration_writes_account_investments_per_real_account(tmp_path):
    """Per ADR-030 / Task 0's finding: real per-account attribution comes from
    tvSnapshot.snapshots[].positions[], never from an invented "account" field
    on the flat holdings[] array (which has no such field in real data)."""
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(FIXTURE_PORTFOLIO))
    db_path = str(tmp_path / "test.sqlite")
    report = run_real_migration(str(portfolio_path), db_path)
    assert report["account_investments_written"] == 2  # TFSA:AAPL, RRSP:AAPL

    conn = initialize_db(db_path)
    accounts = {a["account_id"] for a in list_accounts(conn)}
    assert accounts == {"TFSA", "RRSP"}
    rows = {r["account_id"]: r for r in list_account_investments(conn)}
    assert rows["TFSA"]["quantity"] == 10
    assert rows["TFSA"]["average_cost"] == 140.0
    assert rows["RRSP"]["quantity"] == 3


def test_real_migration_writes_cash_as_investment_rows(tmp_path):
    """Wave 0 resolved decision 5: cash is a real INVESTMENT row (asset_class='CASH'),
    held via account_investment like any other position -- not a separate table."""
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(FIXTURE_PORTFOLIO))
    db_path = str(tmp_path / "test.sqlite")
    run_real_migration(str(portfolio_path), db_path)

    conn = initialize_db(db_path)
    rows = list_account_investments(conn, account_id="TFSA")
    cash_investment_ids = [r["investment_id"] for r in rows if r["investment_id"] == "CASH_USD"]
    assert cash_investment_ids  # TFSA's $100 cash balance became a CASH_USD account_investment row


def test_real_migration_excludes_zero_quantity_positions(tmp_path):
    """A closed/flattened position (quantity: 0) still present in a stale snapshot
    must not produce a noise row in account_investment, but real positions in the
    same account/snapshot must still be written."""
    fixture = json.loads(json.dumps(FIXTURE_PORTFOLIO))
    fixture["tvSnapshot"]["snapshots"][1]["positions"].append(
        {"symbol": "MSFT", "direction": "Long", "quantity": 0, "avgFillPrice": 300.0, "positionId": "p3"}
    )
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(fixture))
    db_path = str(tmp_path / "test.sqlite")
    report = run_real_migration(str(portfolio_path), db_path)
    assert report["account_investments_written"] == 2  # MSFT excluded, RRSP:AAPL still written

    conn = initialize_db(db_path)
    rows = list_account_investments(conn, account_id="RRSP")
    investment_ids = {r["investment_id"] for r in rows}
    assert "MSFT" not in investment_ids
    assert "AAPL" in investment_ids


def test_real_migration_is_idempotent(tmp_path):
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(FIXTURE_PORTFOLIO))
    db_path = str(tmp_path / "test.sqlite")
    run_real_migration(str(portfolio_path), db_path)
    run_real_migration(str(portfolio_path), db_path)
    conn = initialize_db(db_path)
    rows = list_account_investments(conn)
    assert len(rows) == 4  # TFSA:AAPL, TFSA:CASH_USD, RRSP:AAPL, RRSP:CASH_USD -- re-run does not duplicate
