"""Pin target_rebaseline.py: a fill re-baselines that target, the rest rescale to 100%,
untraded targets are never overwritten, and stale targets are flagged."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.account_investment_repository import upsert_account_investment  # noqa: E402
from domain_model.account_repository import upsert_account  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_price_repository import upsert_investment_price  # noqa: E402
from domain_model.investment_repository import (  # noqa: E402
    get_investment, resolve_investment, update_investment_fields,
)
from domain_model.portfolio_change_log_repository import list_change_log  # noqa: E402
from domain_model.trade_log_entry_repository import upsert_trade_log_entry  # noqa: E402
from target_rebaseline import apply_rebaseline, plan_rebaseline, target_staleness  # noqa: E402

NOW = datetime(2026, 10, 16, 15, 0, tzinfo=timezone.utc)
FRESH = (NOW - timedelta(hours=1)).isoformat()


def _portfolio(tmp_path, holdings, targets, price_at=None):
    """holdings: {symbol: (qty, price)}; targets: {symbol: (weight, set_at)}."""
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    upsert_account(conn, "TFSA", "TFSA", "TFSA")
    for sym, (qty, price) in holdings.items():
        inv = resolve_investment(conn, sym)
        upsert_account_investment(conn, "TFSA", inv, quantity=qty, average_cost=price,
                                  book_value=None, currency="USD", last_synced_at=FRESH)
        upsert_investment_price(conn, inv, price, "USD", (price_at or {}).get(sym, FRESH))
    for sym, (weight, set_at) in targets.items():
        update_investment_fields(conn, resolve_investment(conn, sym), target_weight=weight, target_set_at=set_at)
    return conn


def _fill(conn, sym, when, action="buy", status="filled"):
    upsert_trade_log_entry(conn, {
        "entry_id": f"{sym}-{when}", "investment_id": resolve_investment(conn, sym), "account_id": "TFSA",
        "action": action, "shares": 1, "price": 1, "trade_date": when, "status": status, "source": "test",
    })


def _changes(plan):
    return {c["symbol"]: c for c in plan["changes"]}


def test_fill_resets_traded_target_and_scales_the_rest_down_only_when_needed(tmp_path):
    # MU 60%, AAA 40% held; targets MU 20 / AAA 50 / BBB 30, all set Oct 1.
    set_at = "2026-10-01T00:00:00+00:00"
    conn = _portfolio(tmp_path, {"MU": (60, 1.0), "AAA": (40, 1.0)},
                      {"MU": (20, set_at), "AAA": (50, set_at), "BBB": (30, set_at)})
    _fill(conn, "MU", "2026-10-15T11:08:09-04:00")

    plan = plan_rebaseline(conn, now=NOW)
    ch = _changes(plan)
    assert ch["MU"]["new"] == 60.0 and ch["MU"]["reason"] == "traded since target was set"
    # 50 + 30 no longer fit beside MU's 60%: they are scaled down to the remaining 40%.
    assert ch["AAA"]["new"] == 25.0 and ch["BBB"]["new"] == 15.0
    assert ch["AAA"]["reason"] == "scaled down to fit 100%"
    assert plan["total_after"] == 100.0


def test_sold_position_target_goes_to_zero_and_cash_target_absorbs_it(tmp_path):
    set_at = "2026-10-01T00:00:00+00:00"
    conn = _portfolio(tmp_path, {"AAA": (100, 1.0)},
                      {"KOID": (3.14, set_at), "AAA": (84.06, set_at), "CASH_USD": (12.8, set_at)})
    _fill(conn, "KOID", "2026-10-15T11:02:08-04:00", action="sell")

    plan = plan_rebaseline(conn, now=NOW)
    ch = _changes(plan)
    assert ch["KOID"]["new"] == 0.0 and ch["KOID"]["reason"] == "sold to zero"
    # The untraded target is left exactly as set; cash takes the freed 3.14%.
    assert "AAA" not in ch
    assert ch["CASH_USD"]["new"] == 15.94
    assert plan["total_after"] == 100.0


def test_untraded_targets_are_never_scaled_up(tmp_path):
    set_at = "2026-10-01T00:00:00+00:00"
    conn = _portfolio(tmp_path, {"MU": (20, 1.0), "AAA": (80, 1.0)},
                      {"MU": (40, set_at), "AAA": (50, set_at), "CASH_USD": (10, set_at)})
    _fill(conn, "MU", "2026-10-15T11:08:09-04:00")

    ch = _changes(plan_rebaseline(conn, now=NOW))
    assert ch["MU"]["new"] == 20.0
    assert "AAA" not in ch                      # no invented buy signal on AAA
    assert ch["CASH_USD"]["new"] == 30.0


def test_fill_older_than_target_and_unfilled_orders_change_nothing(tmp_path):
    conn = _portfolio(tmp_path, {"MU": (60, 1.0), "AAA": (40, 1.0)},
                      {"MU": (50, "2026-10-15T16:00:00+00:00"), "AAA": (50, "2026-10-01T00:00:00+00:00")})
    _fill(conn, "MU", "2026-10-15T11:08:09-04:00")             # 15:08 UTC, before the target
    _fill(conn, "AAA", "2026-10-15T12:00:00-04:00", status="cancelled")

    assert plan_rebaseline(conn, now=NOW)["changes"] == []


def test_unstamped_target_counts_only_fills_inside_the_window(tmp_path):
    conn = _portfolio(tmp_path, {"MU": (60, 1.0), "AAA": (40, 1.0)}, {"MU": (50, None), "AAA": (50, None)})
    _fill(conn, "AAA", "2026-08-01")                            # older than 30 days
    assert plan_rebaseline(conn, now=NOW)["changes"] == []
    _fill(conn, "MU", "2026-10-12")
    assert "MU" in _changes(plan_rebaseline(conn, now=NOW))


def test_position_missed_by_price_refresh_is_skipped_not_reset(tmp_path):
    set_at = "2026-10-01T00:00:00+00:00"
    conn = _portfolio(tmp_path, {"MU": (60, 1.0), "AAA": (40, 1.0)}, {"MU": (20, set_at), "AAA": (80, set_at)},
                      price_at={"MU": "2026-10-13T00:00:00+00:00"})
    _fill(conn, "MU", "2026-10-15T11:08:09-04:00")

    plan = plan_rebaseline(conn, now=NOW)
    assert plan["changes"] == []
    assert plan["skipped"] == [{"symbol": "MU", "reason": "price missed by the latest refresh"}]


def test_apply_stamps_reset_targets_keeps_rescaled_dates_and_logs_once(tmp_path):
    set_at = "2026-10-01T00:00:00+00:00"
    conn = _portfolio(tmp_path, {"MU": (60, 1.0), "AAA": (40, 1.0)}, {"MU": (20, set_at), "AAA": (80, set_at)})
    _fill(conn, "MU", "2026-10-15T11:08:09-04:00")

    assert apply_rebaseline(conn, plan_rebaseline(conn, now=NOW)) == 2
    mu, aaa = get_investment(conn, "MU"), get_investment(conn, "AAA")
    assert mu["target_weight"] == 60.0 and mu["target_set_at"] > set_at
    assert aaa["target_weight"] == 40.0 and aaa["target_set_at"] == set_at
    log = list_change_log(conn)
    assert len(log) == 1 and "MU 20.00%→60.00%" in log[0]["note"]
    # Applied once, the same fill no longer moves anything.
    assert plan_rebaseline(conn)["changes"] == []


def test_update_investment_fields_stamps_target_set_at_only_on_a_changed_target(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    inv = resolve_investment(conn, "MU")
    update_investment_fields(conn, inv, target_weight=5.0)
    first = get_investment(conn, inv)["target_set_at"]
    assert first
    update_investment_fields(conn, inv, target_weight=5.0, agent_rationale="unchanged target")
    assert get_investment(conn, inv)["target_set_at"] == first


def test_target_staleness_reasons():
    set_at = "2026-10-10T00:00:00+00:00"
    assert target_staleness(None, None, NOW) == "no record of when this target was set"
    assert target_staleness("2026-08-01T00:00:00+00:00", None, NOW) == "target set 76 days ago"
    assert target_staleness(set_at, "2026-10-12T09:00:00+00:00", NOW) == (
        "valuation updated 2026-10-12 after the target was set 2026-10-10")
    assert target_staleness(set_at, "2026-10-09T00:00:00+00:00", NOW) is None
