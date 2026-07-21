import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.account_repository import list_accounts  # noqa: E402
from domain_model.account_investment_repository import list_account_investments  # noqa: E402
from domain_model.investment_price_repository import get_investment_price  # noqa: E402
from domain_model.investment_repository import list_investments  # noqa: E402
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
    # CASH is always seeded by seed_real_accounts() even when the fixture has no
    # CASH snapshot -- it just has no positions/cash rows in that case.
    assert accounts == {"TFSA", "RRSP", "CASH"}
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


def test_real_migration_includes_cash_account():
    """Per explicit user decision (Wave 3 scope extension): the CASH broker
    sub-account, previously excluded, must now be migrated like TFSA/RRSP --
    its own cash balance and positions become account_investment rows, not
    silently skipped."""
    import tempfile

    fixture = json.loads(json.dumps(FIXTURE_PORTFOLIO))
    fixture["tvSnapshot"]["accounts"].append(
        {"accountType": "CASH", "accountId": "acct-cash-1", "displayText": "Cash - acct-cash-1"}
    )
    fixture["tvSnapshot"]["snapshots"].append(
        {
            "accountType": "CASH", "accountId": "acct-cash-1",
            "balances": {"cashUSD": 500.0, "cashCAD": 0.0},
            "positions": [
                {"symbol": "AAPL", "direction": "Long", "quantity": 2, "avgFillPrice": 145.0, "positionId": "p4"},
            ],
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        portfolio_path = Path(tmp) / "portfolio.json"
        portfolio_path.write_text(json.dumps(fixture))
        db_path = str(Path(tmp) / "test.sqlite")

        dry_run_report = run_dry_run_migration(str(portfolio_path))
        assert dry_run_report["accounts_found"] == {"TFSA", "RRSP", "CASH"}

        report = run_real_migration(str(portfolio_path), db_path)
        assert report["account_investments_written"] == 3  # TFSA:AAPL, RRSP:AAPL, CASH:AAPL (cash rows aren't counted in this metric)

        conn = initialize_db(db_path)
        accounts = {a["account_id"] for a in list_accounts(conn)}
        assert accounts == {"TFSA", "RRSP", "CASH"}

        cash_rows = {r["investment_id"]: r for r in list_account_investments(conn, account_id="CASH")}
        assert cash_rows["AAPL"]["quantity"] == 2
        assert cash_rows["AAPL"]["average_cost"] == 145.0
        assert "CASH_USD" in cash_rows  # CASH account's own $500 cash balance migrated too
        assert cash_rows["CASH_USD"]["quantity"] == 500.0


def test_real_migration_writes_price_row_for_cash(tmp_path):
    """Bug 1: a CASH_USD account_investment row is written for each account's cash
    balance, but no investment_price row was ever written for CASH_USD -- so
    portfolio_repository.py's SUM(quantity * price) silently counts cash as worth
    $0. A cash dollar is always worth exactly $1.00; this must be persisted."""
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(FIXTURE_PORTFOLIO))
    db_path = str(tmp_path / "test.sqlite")
    run_real_migration(str(portfolio_path), db_path)

    conn = initialize_db(db_path)
    price_row = get_investment_price(conn, "CASH_USD")
    assert price_row is not None, "CASH_USD must have an investment_price row"
    assert price_row["price"] == 1.0


def test_real_migration_resolves_psu_ticker_alias(tmp_path):
    """Bug 2: real portfolio.json's flat holdings[] array uses the canonical
    ticker PSU-U.TO (hyphen), but tvSnapshot.snapshots[].positions[] uses the
    broker's raw format PSU.U.TO (period) for the same real position.
    _load_prices_by_symbol() keys its dict off holdings[]'s canonical symbol,
    but the main loop looked up prices_by_symbol.get(pos["symbol"]) using the
    tvSnapshot's raw, un-normalized symbol -- a guaranteed miss that left the
    real 23-share PSU position priced at 0."""
    fixture = json.loads(json.dumps(FIXTURE_PORTFOLIO))
    fixture["holdings"].append({"symbol": "PSU-U.TO", "shares": 23, "price": 100.0})
    fixture["tvSnapshot"]["snapshots"][0]["positions"].append(
        {"symbol": "PSU.U.TO", "direction": "Long", "quantity": 23, "avgFillPrice": 95.0, "positionId": "p5"}
    )
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(fixture))
    db_path = str(tmp_path / "test.sqlite")
    run_real_migration(str(portfolio_path), db_path)

    conn = initialize_db(db_path)
    price_row = get_investment_price(conn, "PSU-U.TO")
    assert price_row is not None, "PSU-U.TO must have a resolved investment_price row"
    assert price_row["price"] == 100.0


def test_real_migration_merges_broker_raw_symbol_into_single_investment_identity(tmp_path):
    """Regression for the duplicate-identity variant of Bug 2: if the main
    migration loop's resolve_investment() call is ever fed the raw, un-normalized
    tvSnapshot symbol (PSU.U.TO) while _load_prices_by_symbol()'s dict key is
    normalized (PSU-U.TO), the SAME real position held in TWO accounts (TFSA and
    RRSP) creates TWO separate `investment` rows for one real holding -- a
    duplicate-identity data integrity bug, not just a missed price. There must be
    exactly ONE investment row for this position, with the correct aggregated
    per-account quantities and a real non-zero price."""
    fixture = json.loads(json.dumps(FIXTURE_PORTFOLIO))
    # Flat holdings[] carries the canonical, hyphenated symbol with a real price.
    fixture["holdings"].append({"symbol": "PSU-U.TO", "shares": 23, "price": 100.0223})
    # tvSnapshot positions carry the broker-raw, period-delimited symbol, in TWO
    # different real accounts (TFSA and RRSP) for the same real holding.
    fixture["tvSnapshot"]["snapshots"][0]["positions"].append(
        {"symbol": "PSU.U.TO", "direction": "Long", "quantity": 20, "avgFillPrice": 95.0, "positionId": "p6"}
    )
    fixture["tvSnapshot"]["snapshots"][1]["positions"].append(
        {"symbol": "PSU.U.TO", "direction": "Long", "quantity": 3, "avgFillPrice": 95.0, "positionId": "p7"}
    )
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps(fixture))
    db_path = str(tmp_path / "test.sqlite")
    run_real_migration(str(portfolio_path), db_path)

    conn = initialize_db(db_path)
    psu_investments = [
        i for i in list_investments(conn)
        if i["investment_id"] in ("PSU-U.TO", "PSU.U.TO")
    ]
    assert len(psu_investments) == 1, (
        f"Expected exactly one merged investment identity for PSU-U.TO, got {psu_investments}"
    )
    assert psu_investments[0]["investment_id"] == "PSU-U.TO"

    tfsa_rows = {r["investment_id"]: r for r in list_account_investments(conn, account_id="TFSA")}
    rrsp_rows = {r["investment_id"]: r for r in list_account_investments(conn, account_id="RRSP")}
    assert "PSU.U.TO" not in tfsa_rows and "PSU.U.TO" not in rrsp_rows
    assert tfsa_rows["PSU-U.TO"]["quantity"] == 20
    assert rrsp_rows["PSU-U.TO"]["quantity"] == 3

    price_row = get_investment_price(conn, "PSU-U.TO")
    assert price_row is not None and price_row["price"] == 100.0223
