#!/usr/bin/env python3
"""
test_questrade_trades_import.py - Tests for importing executed Questrade trades into the trade log.

Purpose:
    Validates that executed trades are written to trade_log_entry as filled rows,
    keyed so re-imports never duplicate, with canonical account ids and no partial
    or invented rows.

Layer:
    Testing / Plugins / Questrade

Usage Examples:
    pytest plugins/questrade/tests/test_questrade_trades_import.py

Key Functions (Index):
    - test_import_writes_filled_rows_with_canonical_accounts()
    - test_reimport_is_idempotent_and_keeps_owner_edits()
    - test_invalid_trades_are_rejected_with_reasons_and_never_written()
    - test_cli_dry_run_writes_nothing_and_real_run_reports_counts()

Key Input Dependencies:
    - plugins/questrade/scripts/questrade_trades_import.py
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/questrade/scripts"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.trade_log_entry_repository import (  # noqa: E402
    list_filled_trades_since, list_trade_log_entries, upsert_trade_log_entry,
)
from questrade_trades_import import attach_order_details, import_trades, trades_from_activities  # noqa: E402

SCRIPT = REPO_ROOT / "plugins/questrade/scripts/questrade_trades_import.py"
TFSA_ID = "91484e92-b210-49d2-0afe-184f9d0a1f28"
RRSP_ID = "a35aef24-2e61-4202-079c-0d026087293a"
# Live list_accounts shape captured 2026-10-08: the number is masked, with no " - " separator.
ACCOUNTS = [
    {"id": TFSA_ID, "name": "TFSA ••••8189", "productType": "SD", "supportTrading": True},
    {"id": RRSP_ID, "name": "RRSP ••••8195", "productType": "SD", "supportTrading": True},
]
# Live get_account_activities "Trades" rows captured 2026-10-08 (see questrade-tool-schemas.md).
SELL_ACTIVITY = {"transactionId": "2861f1e0-b2b2-4c2e-9c9b-c84af5fdd544", "transactionType": "Trades",
                 "description": "ZSCALER INC COMMON STOCK WE ACTED AS AGENT", "amount": 414.79, "currency": "USD",
                 "symbol": "ZS", "quantity": -2, "price": 207.4, "commission": -0.01, "tradeDate": "2026-10-06",
                 "action": "Sell", "settlementDate": "2026-10-07", "gross": {"currencyCode": "USD", "amount": 414.8}}
BUY_ACTIVITY = {"transactionId": "7072c070-c534-4793-90e3-63ddfc97f6ec", "transactionType": "Trades",
                "description": "MICRON TECHNOLOGY INC WE ACTED AS AGENT", "amount": -208.45, "currency": "USD",
                "symbol": "MU", "quantity": 0.2, "price": 1042.228, "commission": 0, "tradeDate": "2026-09-28",
                "action": "Buy", "settlementDate": "2026-09-29", "gross": {"currencyCode": "USD", "amount": -208.45}}


def seeded_db(tmp_path):
    """A database that already knows the traded symbols, as the live portfolio does."""
    conn = initialize_db(str(tmp_path / "db.sqlite"))
    for symbol in ("ZS", "MU", "BE"):
        resolve_investment(conn, symbol)
    return conn


def trade(**overrides) -> dict:
    """One executed trade in the importer's normalised contract."""
    base = {"accountId": TFSA_ID, "symbol": "ZS", "side": "sell", "shares": 2, "price": 210.36,
            "date": "2026-10-06", "externalId": "act-1"}
    base.update(overrides)
    return base


def test_import_writes_filled_rows_with_canonical_accounts(tmp_path):
    """Fills land as filled, Questrade-sourced rows under TFSA/RRSP, never the account uuid."""
    conn = seeded_db(tmp_path)
    result = import_trades(conn, ACCOUNTS, [trade(), trade(accountId=RRSP_ID, shares=1, externalId="act-2")])
    assert (result["imported"], result["skipped"], result["rejected"]) == (2, 0, [])
    rows = {row["account_id"]: row for row in list_filled_trades_since(conn, "2026-10-01")}
    assert set(rows) == {"TFSA", "RRSP"}
    tfsa = rows["TFSA"]
    assert (tfsa["symbol"], tfsa["action"], tfsa["shares"], tfsa["price"]) == ("ZS", "sell", 2, 210.36)
    assert (tfsa["status"], tfsa["source"], tfsa["trade_date"]) == ("filled", "questrade", "2026-10-06")
    assert tfsa["total_cost"] == 420.72
    assert tfsa["entry_id"].startswith("qt-")


def test_reimport_is_idempotent_and_keeps_owner_edits(tmp_path):
    """Importing the same trade again adds nothing and does not overwrite a note the owner added."""
    conn = seeded_db(tmp_path)
    import_trades(conn, ACCOUNTS, [trade()])
    row = list_trade_log_entries(conn)[0]
    upsert_trade_log_entry(conn, {**row, "notes": "Trimmed after earnings"})
    again = import_trades(conn, ACCOUNTS, [trade(), trade(externalId="act-9", date="2026-10-07")])
    assert (again["imported"], again["skipped"]) == (1, 1)
    rows = list_trade_log_entries(conn)
    assert len(rows) == 2
    assert next(r for r in rows if r["entry_id"] == row["entry_id"])["notes"] == "Trimmed after earnings"


def test_same_trade_without_a_broker_id_still_dedupes_on_its_details(tmp_path):
    """A missing broker id falls back to account, symbol, date, side, shares and price."""
    conn = seeded_db(tmp_path)
    import_trades(conn, ACCOUNTS, [trade(externalId=None)])
    again = import_trades(conn, ACCOUNTS, [trade(externalId=None), trade(externalId=None, price=211.0)])
    assert (again["imported"], again["skipped"]) == (1, 1)


def test_invalid_trades_are_rejected_with_reasons_and_never_written(tmp_path):
    """Unknown accounts, bad sides, non-positive shares and bad dates are reported, not guessed."""
    conn = seeded_db(tmp_path)
    bad = [trade(accountId="unknown"), trade(side="short"), trade(shares=0), trade(date="06/10/2026"),
           trade(price=None), trade(symbol="")]
    result = import_trades(conn, ACCOUNTS, bad + [trade(externalId="ok")])
    assert result["imported"] == 1
    assert len(result["rejected"]) == 6
    assert all(item["reason"] for item in result["rejected"])
    assert len(list_trade_log_entries(conn)) == 1


def test_raw_trade_activities_map_to_the_trade_contract() -> None:
    """Signed quantities become positive shares, the action gives the side, and the broker id is kept."""
    trades = trades_from_activities({TFSA_ID: [SELL_ACTIVITY, BUY_ACTIVITY]})
    assert trades[0] == {"accountId": TFSA_ID, "symbol": "ZS", "side": "sell", "shares": 2, "price": 207.4,
                         "date": "2026-10-06", "externalId": "2861f1e0-b2b2-4c2e-9c9b-c84af5fdd544", "grossAmount": 414.8}
    assert (trades[1]["side"], trades[1]["shares"], trades[1]["grossAmount"]) == ("buy", 0.2, 208.45)


def test_non_trade_activities_are_ignored_not_imported() -> None:
    """Dividends and other ledger rows never become trades."""
    dividend = {**SELL_ACTIVITY, "transactionType": "Dividends", "action": "Dividend"}
    assert trades_from_activities({TFSA_ID: [dividend]}) == []


def test_imported_activity_uses_the_broker_gross_amount_and_is_idempotent(tmp_path):
    """The saved total is Questrade's own gross amount; importing the same activities twice adds nothing."""
    conn = seeded_db(tmp_path)
    trades = trades_from_activities({TFSA_ID: [SELL_ACTIVITY, BUY_ACTIVITY], RRSP_ID: [SELL_ACTIVITY | {"transactionId": "other"}]})
    first = import_trades(conn, ACCOUNTS, trades)
    assert (first["imported"], first["rejected"]) == (3, [])
    rows = list_trade_log_entries(conn)
    assert sorted(row["account_id"] for row in rows) == ["RRSP", "TFSA", "TFSA"]
    mu = next(row for row in rows if row["investment_id"] == "MU")
    assert (mu["action"], mu["shares"], mu["price"], mu["total_cost"], mu["trade_date"]) == ("buy", 0.2, 1042.228, 208.45, "2026-09-28")
    assert import_trades(conn, ACCOUNTS, trades)["imported"] == 0


def test_cli_accepts_raw_activities_keyed_by_account(tmp_path):
    """The agent can stage raw tool responses without reshaping them."""
    db = tmp_path / "db.sqlite"
    seeded_db(tmp_path).close()
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({"accounts": ACCOUNTS, "activities": {TFSA_ID: [SELL_ACTIVITY], RRSP_ID: []}}))
    result = subprocess.run([sys.executable, str(SCRIPT), "--payload", str(payload), "--db-path", str(db), "--json"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["imported"] == 1


# Live get_order_history rows captured 2026-10-08. lastModified (epoch seconds) is when the order was last
# changed, not when it filled: this KOID limit order was placed Sunday 23:00 ET and filled Monday.
ZS_ORDER = {"id": "178a491e-3d06-4842-014e-290c0531245c", "instrument": "ZS", "qty": 2, "side": "sell", "type": "market",
            "status": "filled", "filledQty": 2, "avgPrice": 207.4, "duration": {"type": "Day"}, "lastModified": 1791301745}
KOID_ORDER = {"id": "07c9363a-3848-4c82-0d81-2d540f3d6803", "instrument": "KOID", "qty": 3, "side": "buy", "type": "limit",
              "status": "filled", "filledQty": 3, "avgPrice": 36.99, "limitPrice": 37, "lastModified": 1791169238}


def test_order_history_adds_order_type_limit_price_and_market_order_time() -> None:
    """A matching filled order supplies type and limit; only a market order's time (US Eastern) is trusted."""
    trades = trades_from_activities({TFSA_ID: [SELL_ACTIVITY]})
    koid = trade(symbol="KOID", side="buy", shares=3, price=36.99, date="2026-10-05", externalId="k")
    enriched = attach_order_details(trades + [koid], {TFSA_ID: {"open": [ZS_ORDER], "history": [ZS_ORDER, KOID_ORDER]}})
    assert enriched[0]["orderType"] == "market" and enriched[0]["executedAt"] == "2026-10-06T11:49:05-04:00"
    assert (enriched[1]["orderType"], enriched[1]["limitPrice"]) == ("limit", 37)
    assert "executedAt" not in enriched[1]


def test_unmatched_cancelled_or_ambiguous_orders_add_nothing() -> None:
    """No time is attached unless exactly the same filled order is found."""
    trades = trades_from_activities({TFSA_ID: [SELL_ACTIVITY]})
    other = {**ZS_ORDER, "avgPrice": 208.0}
    cancelled = {**ZS_ORDER, "status": "cancelled"}
    for orders in ({}, {TFSA_ID: [other]}, {TFSA_ID: [cancelled]}, {RRSP_ID: [ZS_ORDER]}):
        assert "executedAt" not in attach_order_details(trades, orders)[0]


def test_fill_time_is_saved_with_the_trade_date_and_dropped_when_it_disagrees(tmp_path):
    """The saved date keeps its YYYY-MM-DD prefix; a time on a different day is not trusted."""
    conn = seeded_db(tmp_path)
    good = trade(externalId="g", orderType="market", executedAt="2026-10-06T11:49:05-04:00")
    wrong_day = trade(externalId="w", symbol="BE", executedAt="2026-10-07T09:31:00-04:00", orderType="swap")
    import_trades(conn, ACCOUNTS, [good, wrong_day])
    rows = {row["investment_id"]: row for row in list_trade_log_entries(conn)}
    assert rows["ZS"]["trade_date"] == "2026-10-06T11:49:05-04:00" and rows["ZS"]["order_type"] == "market"
    assert rows["BE"]["trade_date"] == "2026-10-06" and rows["BE"]["order_type"] is None
    assert [row["symbol"] for row in list_filled_trades_since(conn, "2026-10-06")] == ["BE", "ZS"]


def test_reimport_fills_in_missing_details_without_touching_owner_edits(tmp_path):
    """Trades imported before order details existed gain time and type; notes and status stay as edited."""
    conn = seeded_db(tmp_path)
    import_trades(conn, ACCOUNTS, [trade()])
    row = list_trade_log_entries(conn)[0]
    upsert_trade_log_entry(conn, {**row, "notes": "Trimmed after earnings"})
    detailed = trade(orderType="limit", limitPrice=211.0, executedAt="2026-10-06T11:49:05-04:00")
    report = import_trades(conn, ACCOUNTS, [detailed])
    assert (report["imported"], report["skipped"], report["enriched"]) == (0, 0, 1)
    after = list_trade_log_entries(conn)[0]
    assert (after["trade_date"], after["order_type"], after["limit_price"]) == ("2026-10-06T11:49:05-04:00", "limit", 211.0)
    assert (after["notes"], after["entry_id"], after["logged_at"]) == ("Trimmed after earnings", row["entry_id"], row["logged_at"])
    assert import_trades(conn, ACCOUNTS, [detailed])["enriched"] == 0


def test_unknown_symbols_are_rejected_unless_explicitly_allowed(tmp_path):
    """Broker-only symbols (cash funds, conversion legs) must not create junk investments."""
    conn = seeded_db(tmp_path)
    odd = [trade(symbol="G036247", externalId="g"), trade(symbol="PSUCF", externalId="p")]
    report = import_trades(conn, ACCOUNTS, odd + [trade()])
    assert report["imported"] == 1
    assert [item["reason"] for item in report["rejected"]] == [
        "unknown symbol G036247: not an investment in the portfolio database",
        "unknown symbol PSUCF: not an investment in the portfolio database"]
    assert {row["investment_id"] for row in list_trade_log_entries(conn)} == {"ZS"}
    allowed = import_trades(conn, ACCOUNTS, odd, allow_new_symbols=True)
    assert (allowed["imported"], allowed["rejected"]) == (2, [])


def test_cli_dry_run_writes_nothing_and_real_run_reports_counts(tmp_path):
    """The CLI previews first, writes on a real run, and exits non-zero when trades are rejected."""
    db = tmp_path / "db.sqlite"
    seeded_db(tmp_path).close()
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({"accounts": ACCOUNTS, "trades": [trade(), trade(side="short", externalId="bad")]}))
    run = lambda *extra: subprocess.run(  # noqa: E731
        [sys.executable, str(SCRIPT), "--payload", str(payload), "--db-path", str(db), "--json", *extra],
        capture_output=True, text=True)
    preview = run("--dry-run")
    assert preview.returncode == 2, preview.stderr
    assert json.loads(preview.stdout)["would_import"] == 1
    assert list_trade_log_entries(initialize_db(str(db))) == []
    real = run()
    assert real.returncode == 2
    report = json.loads(real.stdout)
    assert (report["imported"], len(report["rejected"])) == (1, 1)
    assert len(list_trade_log_entries(initialize_db(str(db)))) == 1
