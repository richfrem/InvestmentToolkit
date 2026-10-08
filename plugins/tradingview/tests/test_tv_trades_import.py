#!/usr/bin/env python3
"""
test_tv_trades_import.py - Tests for importing executed trades from TradingView's order history.

Purpose:
    Validates that filled orders read from TradingView's broker panel map to the
    shared trade contract, import as filled rows, and never duplicate trades that
    another source already recorded.

Layer:
    Testing / Plugins / TradingView

Usage Examples:
    pytest plugins/tradingview/tests/test_tv_trades_import.py

Key Functions (Index):
    - test_filled_orders_map_to_the_trade_contract()
    - test_unfilled_orders_and_failed_accounts_are_reported_not_imported()
    - test_cli_imports_a_saved_snapshot_and_is_idempotent()

Key Input Dependencies:
    - plugins/tradingview/scripts/tv_trades_import.py
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.trade_log_entry_repository import list_trade_log_entries  # noqa: E402
from tv_trades_import import trades_from_tv_history  # noqa: E402

SCRIPT = REPO_ROOT / "plugins/tradingview/scripts/tv_trades_import.py"
# Shapes returned by getOrderHistoryAllAccounts(), from the live panel captured 2026-10-08.
BE = {"symbol": "BE", "side": "sell", "type": "market", "qty": 1, "filledQty": 1, "limitPrice": None, "avgFillPrice": 293.6581,
      "status": "filled", "updateTime": "2026-10-06 07:57:58", "updateTimeIso": "2026-10-06T14:57:58.000Z",
      "orderId": "320209bf-3157-4072-0172-29c808010710", "brokerStatus": "Executed"}
KOID = {"symbol": "KOID", "side": "buy", "type": "limit", "qty": 6, "filledQty": 6, "limitPrice": 37, "avgFillPrice": 36.99,
        "status": "filled", "updateTime": "2026-10-04 20:00:10", "updateTimeIso": "2026-10-05T03:00:10.000Z",
        "orderId": "34382b4a-3a46-4362-0b63-05c70d3b6601", "brokerStatus": "Executed"}


def snapshot(*accounts) -> dict:
    return {"dataSource": "tradingview-cdp", "accounts": list(accounts)}


def test_filled_orders_map_to_the_trade_contract():
    """Times are converted to US Eastern; only a market order's time is kept as the trade time."""
    trades, warnings = trades_from_tv_history(snapshot({"accountType": "TFSA", "orders": [BE, KOID], "expectedCount": 2}))
    assert warnings == []
    assert trades[0] == {"account": "TFSA", "symbol": "BE", "side": "sell", "shares": 1, "price": 293.6581, "date": "2026-10-06",
                         "orderId": "320209bf-3157-4072-0172-29c808010710", "orderType": "market", "limitPrice": None,
                         "executedAt": "2026-10-06T10:57:58-04:00"}
    assert (trades[1]["date"], trades[1]["orderType"], trades[1]["limitPrice"]) == ("2026-10-04", "limit", 37)
    assert "executedAt" not in trades[1]


def test_unfilled_orders_and_failed_accounts_are_reported_not_imported():
    """Cancelled or zero-fill rows are skipped; unreadable accounts and short reads become warnings."""
    cancelled = {**BE, "status": "cancelled", "filledQty": 0, "orderId": "c"}
    untimed = {**BE, "updateTimeIso": None, "updateTime": "", "orderId": "u"}
    trades, warnings = trades_from_tv_history(snapshot(
        {"accountType": "TFSA", "orders": [BE, cancelled, untimed], "expectedCount": 5},
        {"accountType": "RRSP", "orders": [], "error": "Account not found in dropdown: RRSP"},
        {"accountType": "CASH", "orders": [], "missingColumns": ["Avg Fill Price"]}))
    assert [trade["orderId"] for trade in trades] == [BE["orderId"]]
    assert len(warnings) == 4
    assert any("RRSP" in w and "Account not found" in w for w in warnings)
    assert any("TFSA" in w and "expected 5" in w for w in warnings)
    assert any("no usable time" in w for w in warnings)
    assert any("Avg Fill Price" in w for w in warnings)


def test_cli_imports_a_saved_snapshot_and_is_idempotent(tmp_path):
    """The CLI previews, imports through the shared core, and a second run adds nothing."""
    db = tmp_path / "db.sqlite"
    conn = initialize_db(str(db))
    for symbol in ("BE", "KOID"):
        resolve_investment(conn, symbol)
    conn.close()
    payload = tmp_path / "history.json"
    payload.write_text(json.dumps(snapshot({"accountType": "TFSA", "orders": [BE, KOID], "expectedCount": 2})))
    run = lambda *extra: subprocess.run(  # noqa: E731
        [sys.executable, str(SCRIPT), "--payload", str(payload), "--db-path", str(db), "--json", *extra],
        capture_output=True, text=True)
    preview = run("--dry-run")
    assert preview.returncode == 0, preview.stderr
    assert json.loads(preview.stdout)["would_import"] == 2
    assert list_trade_log_entries(initialize_db(str(db))) == []
    first = json.loads(run().stdout)
    assert (first["imported"], first["source"], first["warnings"]) == (2, "tradingview", [])
    rows = {row["investment_id"]: row for row in list_trade_log_entries(initialize_db(str(db)))}
    assert (rows["BE"]["source"], rows["BE"]["trade_date"], rows["BE"]["tv_order_id"]) == (
        "tradingview", "2026-10-06T10:57:58-04:00", BE["orderId"])
    assert (rows["KOID"]["order_type"], rows["KOID"]["limit_price"], rows["KOID"]["trade_date"]) == ("limit", 37.0, "2026-10-04")
    assert json.loads(run().stdout)["imported"] == 0
