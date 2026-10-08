"""Purpose: contract tests for the broker-neutral executed-trade import core.

Layer: Tests. Uses real SQLite repositories; no network.
Key Functions: write, idempotency, cross-source de-duplication and enrichment cases.
Key Input Dependencies: trade_log_import.py; domain_model repositories.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.trade_log_entry_repository import list_trade_log_entries, upsert_trade_log_entry  # noqa: E402
from trade_log_import import import_filled_trades  # noqa: E402

ORDER_ID = "178a491e-3d06-4842-014e-290c0531245c"


def db(tmp_path):
    """A database that already knows the traded symbols."""
    conn = initialize_db(str(tmp_path / "db.sqlite"))
    for symbol in ("ZS", "HUMN", "KOID"):
        resolve_investment(conn, symbol)
    return conn


def fill(**overrides) -> dict:
    """One executed trade in the import contract."""
    base = {"account": "TFSA", "symbol": "ZS", "side": "sell", "shares": 2, "price": 207.4, "date": "2026-10-06"}
    base.update(overrides)
    return base


def test_writes_filled_rows_tagged_with_their_source(tmp_path):
    conn = db(tmp_path)
    report = import_filled_trades(conn, [fill(orderId=ORDER_ID, orderType="market")], source="tradingview")
    assert (report["imported"], report["skipped"], report["enriched"], report["rejected"]) == (1, 0, 0, [])
    row = list_trade_log_entries(conn)[0]
    assert (row["status"], row["source"], row["account_id"], row["tv_order_id"]) == ("filled", "tradingview", "TFSA", ORDER_ID)
    assert row["entry_id"].startswith("tv-") and row["total_cost"] == 414.8
    assert import_filled_trades(conn, [fill(orderId=ORDER_ID, orderType="market")], source="tradingview")["imported"] == 0


def test_same_fill_from_a_second_source_is_recognised_not_duplicated(tmp_path):
    """A trade imported from Questrade (keyed by transaction id) is the same fill TradingView reports by order id."""
    conn = db(tmp_path)
    import_filled_trades(conn, [fill(externalId="questrade-transaction-1")], source="questrade")
    tv = fill(orderId=ORDER_ID, orderType="market", executedAt="2026-10-06T11:48:48-04:00")
    report = import_filled_trades(conn, [tv], source="tradingview")
    assert (report["imported"], report["enriched"]) == (0, 1)
    rows = list_trade_log_entries(conn)
    assert len(rows) == 1
    assert (rows[0]["source"], rows[0]["tv_order_id"], rows[0]["order_type"]) == ("questrade", ORDER_ID, "market")
    assert rows[0]["trade_date"] == "2026-10-06T11:48:48-04:00"
    again = import_filled_trades(conn, [tv], source="tradingview")
    assert (again["imported"], again["enriched"], again["skipped"]) == (0, 0, 1)


def test_order_id_match_survives_a_different_date(tmp_path):
    """A limit order's update time can precede its fill; the order id still identifies the trade."""
    conn = db(tmp_path)
    import_filled_trades(conn, [fill(symbol="KOID", side="buy", shares=3, price=36.99, date="2026-10-05",
                                     externalId="t", orderId="koid-order")], source="questrade")
    report = import_filled_trades(conn, [fill(symbol="KOID", side="buy", shares=3, price=36.99, date="2026-10-04",
                                              orderId="koid-order", orderType="limit", limitPrice=37)], source="tradingview")
    assert report["imported"] == 0
    row = list_trade_log_entries(conn)[0]
    assert (row["trade_date"], row["order_type"], row["limit_price"]) == ("2026-10-05", "limit", 37.0)


def test_one_recorded_trade_filled_as_several_orders_is_not_double_counted(tmp_path):
    """Questrade posts one 22-share sale; TradingView lists the two orders (4 and 18) that made it up."""
    conn = db(tmp_path)
    import_filled_trades(conn, [fill(symbol="HUMN", shares=22, price=29.906, date="2026-10-02", externalId="h")], source="questrade")
    parts = [fill(symbol="HUMN", shares=4, price=29.906, date="2026-10-02", orderId="o4"),
             fill(symbol="HUMN", shares=18, price=29.906, date="2026-10-02", orderId="o18")]
    report = import_filled_trades(conn, parts, source="tradingview")
    assert (report["imported"], report["skipped"]) == (0, 2)
    assert len(list_trade_log_entries(conn)) == 1


def test_genuinely_different_trades_on_the_same_day_are_both_kept(tmp_path):
    """Same ticker and day but a different price or account is a different trade."""
    conn = db(tmp_path)
    import_filled_trades(conn, [fill(externalId="a")], source="questrade")
    report = import_filled_trades(conn, [fill(price=208.1, orderId="x"), fill(account="RRSP", shares=1, orderId="y")], source="tradingview")
    assert report["imported"] == 2
    assert len(list_trade_log_entries(conn)) == 3


def test_owner_edits_survive_enrichment_and_bad_rows_are_rejected(tmp_path):
    conn = db(tmp_path)
    import_filled_trades(conn, [fill(externalId="a")], source="questrade")
    row = list_trade_log_entries(conn)[0]
    upsert_trade_log_entry(conn, {**row, "notes": "Trimmed after earnings"})
    report = import_filled_trades(conn, [fill(orderId=ORDER_ID, orderType="market"), fill(account=None), fill(symbol="NOPE", orderId="n"),
                                         fill(side="short"), fill(shares=0), fill(date="06/10/2026")], source="tradingview")
    assert report["enriched"] == 1 and len(report["rejected"]) == 5
    assert list_trade_log_entries(conn)[0]["notes"] == "Trimmed after earnings"
    assert "unknown symbol NOPE" in " ".join(item["reason"] for item in report["rejected"])


def test_dry_run_reports_without_writing(tmp_path):
    conn = db(tmp_path)
    report = import_filled_trades(conn, [fill(orderId=ORDER_ID)], source="tradingview", dry_run=True)
    assert report["imported"] == 1 and list_trade_log_entries(conn) == []
