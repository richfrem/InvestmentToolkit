import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import get_investment  # noqa: E402
from domain_model.price_level_repository import get_price_levels  # noqa: E402
from domain_model.investment_note_repository import list_notes  # noqa: E402
from domain_model.alert_repository import list_alerts  # noqa: E402
from domain_model.migrate_target_portfolio_to_sqlite import (  # noqa: E402
    build_dry_run_report,
    execute_migration,
)


def _write_fixture(tmp_path):
    """Fixture matching the REAL confirmed shapes (read directly against the
    real files during Wave 2 Task 6): watchlist.json is {"watchlist": [...]},
    holdings use pillarId/subStrategyId, standingDecision uses "review" (not
    "lastReviewed"), alerts use "symbol" (exchange-qualified) + "alert_id".
    """
    target = {
        "updatedAt": "2026-07-01T00:00:00Z",
        "holdings": [
            {
                "ticker": "AAPL", "role": "active", "targetWeight": 0.05,
                "action": "ACCUMULATE", "pillarId": "AI_INFRA",
                "subStrategyId": "AI_COMPUTE",
                "standingDecision": {
                    "type": "HOLD", "reason": "DCF delta <15%",
                    "source": "daily_brief.py", "review": "2026-07-01",
                },
                "agentRationale": "DCF: INITIATE | FV $285 vs $421 price.",
                "priceLevels": {
                    "schemaVersion": "1.0", "lastUpdated": "2026-07-01",
                    "lastUpdatedBy": "update_price_levels.py", "note": None,
                    "buyTiers": [{"tier": 1, "price": 150.0, "action": "BUY"}],
                    "sellTiers": [], "stopLoss": None,
                },
                "targetEntryPrice": None,
            },
        ],
        "pillars": [{"id": "AI_INFRA", "name": "AI Infrastructure", "targetWeight": 0.35}],
    }
    watchlist_doc = {"watchlist": [{"ticker": "DRAM", "addedAt": "2026-06-01T00:00:00Z"}]}
    alerts = [
        {
            "alert_id": 12345, "symbol": "NASDAQ:AAPL", "type": "price",
            "message": "AAPL crossing 200", "active": True, "price": 200.0,
            "condition": {"type": "cross"}, "resolution": "1",
            "created": "2026-07-01T00:00:00Z", "last_fired": None, "expiration": None,
        },
    ]
    breaker_state = {"generatedAt": "2026-07-10T00:00:00Z", "holdings": {"AAPL": "TRIGGERED"}}

    target_path = tmp_path / "target-portfolio.json"
    watchlist_path = tmp_path / "watchlist.json"
    alerts_path = tmp_path / "tradingview_alerts_actual.json"
    breaker_path = tmp_path / "thesis_breaker_state.json"
    target_path.write_text(json.dumps(target))
    watchlist_path.write_text(json.dumps(watchlist_doc))
    alerts_path.write_text(json.dumps(alerts))
    breaker_path.write_text(json.dumps(breaker_state))
    return str(target_path), str(watchlist_path), str(alerts_path), str(breaker_path)


def test_build_dry_run_report_counts_holdings_and_pillars(tmp_path):
    paths = _write_fixture(tmp_path)
    report = build_dry_run_report(*paths)
    assert report["holdings_count"] == 1
    assert report["pillars_count"] == 1
    assert report["watchlist_count"] == 1
    assert report["alerts_count"] == 1
    assert report["holdings_with_price_levels"] == 1
    assert report["holdings_with_agent_rationale"] == 1
    assert report["holdings_with_standing_decision"] == 1
    assert report["thesis_breaker_holdings_count"] == 1
    assert report["warnings"] == []


def test_build_dry_run_report_flags_missing_ticker_as_warning(tmp_path):
    target_path = tmp_path / "target-portfolio.json"
    target_path.write_text(json.dumps({"holdings": [{"role": "active"}], "pillars": []}))
    watchlist_path = tmp_path / "watchlist.json"
    watchlist_path.write_text(json.dumps({"watchlist": []}))
    alerts_path = tmp_path / "tradingview_alerts_actual.json"
    alerts_path.write_text(json.dumps([]))
    breaker_path = tmp_path / "thesis_breaker_state.json"
    breaker_path.write_text(json.dumps({"holdings": {}}))
    report = build_dry_run_report(
        str(target_path), str(watchlist_path), str(alerts_path), str(breaker_path)
    )
    assert len(report["warnings"]) == 1
    assert "missing ticker" in report["warnings"][0].lower()


def test_build_dry_run_report_does_not_touch_any_sqlite_file(tmp_path):
    paths = _write_fixture(tmp_path)
    build_dry_run_report(*paths)
    assert not any(tmp_path.glob("*.sqlite"))


def test_execute_migration_writes_full_investment_row(tmp_path):
    paths = _write_fixture(tmp_path)
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    summary = execute_migration(conn, *paths)
    assert summary["investments_updated"] == 1

    row = get_investment(conn, "AAPL")
    assert row is not None
    assert row["target_weight"] == 0.05
    assert row["target_action"] == "ACCUMULATE"
    assert row["standing_decision_type"] == "HOLD"
    assert row["standing_decision_reason"] == "DCF delta <15%"
    assert row["pillar_id"] == "AI_INFRA"

    levels = get_price_levels(conn, "AAPL")
    assert levels is not None
    assert len(levels["buy_tiers"]) == 1

    notes = list_notes(conn, "AAPL")
    assert len(notes) == 1
    assert notes[0]["note_type"] == "MIGRATED_LEGACY_RATIONALE"


def test_execute_migration_sets_watchlist_flag_independent_of_role(tmp_path):
    """watchlist.json's population and role='watchlist' are two different questions
    (spec s2.1 -- DRAM disagrees on role vs. action in real data). This test locks
    in that watchlist membership is driven by watchlist.json membership, not
    inferred from role/action, and that a watchlist-only ticker (no holdings
    entry) still gets a resolvable investment row.
    """
    paths = _write_fixture(tmp_path)
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    execute_migration(conn, *paths)
    dram_row = get_investment(conn, "DRAM")
    assert dram_row is not None
    assert dram_row["is_watchlisted"] == 1


def test_execute_migration_migrates_alerts_stripping_exchange_prefix(tmp_path):
    paths = _write_fixture(tmp_path)
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    execute_migration(conn, *paths)
    alerts = list_alerts(conn, investment_id="AAPL")
    assert len(alerts) == 1
    assert alerts[0]["alert_id"] == "12345"
    assert alerts[0]["message"] == "AAPL crossing 200"


def test_execute_migration_migrates_thesis_breaker_status(tmp_path):
    paths = _write_fixture(tmp_path)
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    execute_migration(conn, *paths)
    row = get_investment(conn, "AAPL")
    assert row["thesis_breaker_status"] == "TRIGGERED"


def test_execute_migration_auto_creates_pillar_for_undefined_pillar_id(tmp_path):
    """Real data confirmed a holding referencing pillarId="other" -- not present
    in the pillars[] definition array (Norbert's Gambit conversion vehicles
    DLR.U.TO/DLR.TO in the real file). Must not FK-fail; must auto-create a
    minimal placeholder pillar row.
    """
    target_path, watchlist_path, alerts_path, breaker_path = _write_fixture(tmp_path)
    target = json.loads(Path(target_path).read_text())
    target["holdings"].append({
        "ticker": "DLR.TO", "role": "active", "targetWeight": 0.01,
        "pillarId": "other",
    })
    Path(target_path).write_text(json.dumps(target))

    conn = initialize_db(str(tmp_path / "test.sqlite"))
    execute_migration(conn, target_path, watchlist_path, alerts_path, breaker_path)
    row = get_investment(conn, "DLR.TO")
    assert row["pillar_id"] == "other"


def test_execute_migration_is_idempotent_on_rerun(tmp_path):
    paths = _write_fixture(tmp_path)
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    execute_migration(conn, *paths)
    execute_migration(conn, *paths)
    notes = list_notes(conn, "AAPL")
    assert len(notes) == 1
    levels = get_price_levels(conn, "AAPL")
    assert len(levels["buy_tiers"]) == 1
    alerts = list_alerts(conn, investment_id="AAPL")
    assert len(alerts) == 1
