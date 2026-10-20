"""Pin review_cycle.py: every followed name starts and resets to NEEDS_ANALYSIS, triage only
clears names with nothing new, hard triggers need a valuation saved today, and verify fails
while anything is left."""
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.investment_repository import get_investment, resolve_investment, update_investment_fields  # noqa: E402
import review_cycle as rc  # noqa: E402

TODAY = date(2026, 10, 20)


def _db(tmp_path):
    conn = initialize_db(str(tmp_path / "t.sqlite"))
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    return conn


def _name(conn, sym, held=True, price=100.0, valued_on=None, watch=False):
    inv = resolve_investment(conn, sym)
    if held:
        upsert_account_investment(conn, "TFSA", inv, quantity=1, average_cost=price, book_value=None, currency="USD", last_synced_at="x")
    if watch:
        update_investment_fields(conn, inv, is_watchlisted=1)
    upsert_investment_price(conn, inv, price, "USD", f"{TODAY}T14:00:00+00:00")
    if valued_on:
        conn.execute("INSERT INTO projection_version (projection_id, investment_id, version, saved_at, analyzed_at, fair_value, action, source) "
                     "VALUES (?, ?, 1, ?, ?, 120, 'BUY', 'AI_AGENT')", (f"{sym}:1", inv, f"{valued_on}T12:00:00+00:00", f"{valued_on}T12:00:00+00:00"))
        conn.commit()
    return inv


def test_new_ticker_defaults_to_needs_analysis(tmp_path):
    conn = _db(tmp_path)
    inv = _name(conn, "CLS", held=False, watch=True)
    assert get_investment(conn, inv)["review_state"] == rc.NEEDS_ANALYSIS
    assert [x["symbol"] for x in rc.verify(conn)] == ["CLS"]


def test_start_resets_every_holding_and_watchlist_name_and_skips_cash(tmp_path):
    conn = _db(tmp_path)
    for s in ("AAA", "BBB"):
        update_investment_fields(conn, _name(conn, s, valued_on="2026-10-15"), review_state=rc.REVIEWED)
    _name(conn, "CASH_USD")
    assert rc.start(conn) == 2
    assert {x["symbol"] for x in rc.verify(conn)} == {"AAA", "BBB"}


def test_triage_clears_only_names_with_nothing_new(tmp_path):
    conn = _db(tmp_path)
    _name(conn, "FRESH", valued_on="2026-10-15")
    _name(conn, "OLD", valued_on="2026-09-01")
    _name(conn, "NOVAL")
    _name(conn, "EARN", valued_on="2026-10-01")
    rc.start(conn)
    queue = rc.triage(conn, TODAY, last_earnings=lambda s: "2026-10-10" if s == "EARN" else None)
    assert {q["symbol"] for q in queue} == {"OLD", "NOVAL", "EARN"}
    hard = {q["symbol"]: q["hard"] for q in queue}
    assert hard == {"OLD": False, "NOVAL": True, "EARN": True}
    assert [x["symbol"] for x in rc.verify(conn)].count("FRESH") == 0


def test_age_only_name_can_be_marked_with_a_reason(tmp_path):
    conn = _db(tmp_path)
    _name(conn, "OLD", valued_on="2026-09-01")
    rc.start(conn); rc.triage(conn, TODAY)
    assert rc.mark(conn, "OLD", "short", TODAY)["ok"] is False
    assert rc.mark(conn, "OLD", "No earnings since; price within 5% of last review", TODAY)["ok"] is True
    assert rc.verify(conn) == []


def test_hard_trigger_needs_a_valuation_saved_today(tmp_path):
    conn = _db(tmp_path)
    _name(conn, "EARN", valued_on="2026-10-01")
    rc.start(conn); rc.triage(conn, TODAY, last_earnings=lambda s: "2026-10-10")
    refused = rc.mark(conn, "EARN", "Looked at it, thesis unchanged overall", TODAY)
    assert refused["ok"] is False and "earnings reported 2026-10-10" in refused["error"]
    conn.execute("INSERT INTO projection_version (projection_id, investment_id, version, saved_at, analyzed_at, fair_value, action, source) "
                 "VALUES ('EARN:2', 'EARN', 2, ?, ?, 130, 'BUY', 'AI_AGENT')", (f"{TODAY}T15:00:00+00:00", f"{TODAY}T15:00:00+00:00"))
    conn.commit()
    assert rc.mark(conn, "EARN", "Re-valued today after the Oct 10 report", TODAY)["ok"] is True


def test_price_move_since_last_review_is_a_hard_trigger(tmp_path):
    conn = _db(tmp_path)
    inv = _name(conn, "MOVE", price=130.0, valued_on="2026-10-15")
    update_investment_fields(conn, inv, review_state=rc.REVIEWED, review_price=100.0)
    rc.start(conn)
    queue = rc.triage(conn, TODAY)
    assert queue[0]["symbol"] == "MOVE" and queue[0]["hard"] and "price moved +30%" in queue[0]["reasons"][0]


def test_first_review_measures_price_move_from_the_saved_valuation(tmp_path):
    """Before any review_price exists, a large move since the valuation is still a hard trigger."""
    conn = _db(tmp_path)
    inv = _name(conn, "DROP", price=70.0, valued_on="2026-10-08")
    _name(conn, "FLAT", price=101.0, valued_on="2026-10-08")
    conn.execute("UPDATE projection_version SET snapshot_json = '{\"currentPrice\": 100}'"); conn.commit()
    rc.start(conn)
    queue = {q["symbol"]: q for q in rc.triage(conn, TODAY)}
    assert queue["DROP"]["hard"] is True
    assert "since the saved valuation" in queue["DROP"]["reasons"][0]
    assert "FLAT" not in queue
    assert rc.mark(conn, "DROP", "Looked at it; nothing new beyond the price drop", TODAY)["ok"] is False
    assert get_investment(conn, inv)["review_state"] == rc.NEEDS_ANALYSIS


def test_breaker_is_a_hard_trigger_and_queue_puts_holdings_first(tmp_path):
    conn = _db(tmp_path)
    _name(conn, "WATCH", held=False, watch=True)
    _name(conn, "BRK", valued_on="2026-10-15")
    rc.start(conn)
    queue = rc.triage(conn, TODAY, breakers={"BRK"})
    assert [q["symbol"] for q in queue] == ["BRK", "WATCH"]
    assert "thesis breaker" in queue[0]["reasons"][0]


def test_failed_earnings_lookup_never_auto_clears(tmp_path):
    conn = _db(tmp_path)
    _name(conn, "FRESH", valued_on="2026-10-15")
    rc.start(conn)
    def boom(_):
        raise LookupError("parser missing")
    queue = rc.triage(conn, TODAY, last_earnings=boom)
    assert queue[0]["symbol"] == "FRESH" and "earnings date unavailable" in queue[0]["reasons"][0]
    assert rc.mark(conn, "FRESH", "Checked the IR page: no report since Oct 15", TODAY)["ok"] is True


def test_cash_parking_fund_is_out_of_scope(tmp_path):
    conn = _db(tmp_path)
    _name(conn, "PSU-U.TO")
    assert rc.start(conn) == 0
