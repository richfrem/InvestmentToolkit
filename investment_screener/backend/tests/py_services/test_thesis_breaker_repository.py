"""Tests for domain_model/thesis_breaker_repository.py and migration 0002 (thesis breaker tables).

Purpose:
    Pin the breaker definition and state round-trips, validation, derived investment status
    and the shared vocabulary.

Key Input Dependencies: none (each test builds a real temporary SQLite database).
"""
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model import thesis_breaker_repository as repo  # noqa: E402

AUTO = {"id": "rsi-low", "type": "auto", "metric": "rsi", "operator": "<", "threshold": 30,
        "horizon": 3, "note": "oversold for three runs"}
MANUAL = {"id": "ceo-exit", "type": "manual", "operator": "==", "threshold": True, "status": "OK",
          "statusSetAt": "2026-10-01", "reviewCadenceDays": 30, "note": "CEO departure"}


@pytest.fixture
def conn(tmp_path):
    """Fixture: conn."""
    c = initialize_db(str(tmp_path / "t.sqlite"))
    resolve_investment(c, "NVDA")
    resolve_investment(c, "AMD")
    return c


def test_migration_0002_creates_both_tables(conn):
    """Migration 0002 creates both tables."""
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"thesis_breaker", "thesis_breaker_state"} <= tables
    assert conn.execute("PRAGMA user_version").fetchone()[0] >= 2


def test_upsert_and_list_round_trip_the_definition_shape(conn):
    """Upsert and list round trip the definition shape."""
    repo.upsert_breaker(conn, "NVDA", AUTO)
    repo.upsert_breaker(conn, "NVDA", MANUAL)
    got = {b["id"]: b for b in repo.list_breakers(conn, "NVDA")}
    assert got["rsi-low"] == AUTO
    assert got["ceo-exit"] == MANUAL


def test_list_without_symbol_returns_every_holding_keyed_by_ticker(conn):
    """List without symbol returns every holding keyed by ticker."""
    repo.upsert_breaker(conn, "NVDA", AUTO)
    repo.upsert_breaker(conn, "AMD", {**AUTO, "id": "rsi-amd"})
    by_ticker = repo.list_breakers(conn)
    assert sorted(by_ticker) == ["AMD", "NVDA"]
    assert by_ticker["AMD"][0]["id"] == "rsi-amd"


def test_upsert_replaces_an_existing_breaker(conn):
    """Upsert replaces an existing breaker."""
    repo.upsert_breaker(conn, "NVDA", AUTO)
    repo.upsert_breaker(conn, "NVDA", {**AUTO, "threshold": 25})
    rows = repo.list_breakers(conn, "NVDA")
    assert len(rows) == 1 and rows[0]["threshold"] == 25


def test_in_operator_keeps_a_list_threshold(conn):
    """In operator keeps a list threshold."""
    b = {**AUTO, "id": "trend", "metric": "trendState", "operator": "in", "threshold": ["DOWNTREND", "WEAKENING"]}
    repo.upsert_breaker(conn, "NVDA", b)
    assert repo.list_breakers(conn, "NVDA")[0]["threshold"] == ["DOWNTREND", "WEAKENING"]


@pytest.mark.parametrize("bad, message", [
    ({**AUTO, "metric": "bogus"}, "metric"),
    ({**AUTO, "operator": "!="}, "operator"),
    ({**AUTO, "type": "other"}, "type"),
    ({**AUTO, "operator": "in", "threshold": 3}, "list"),
    ({k: v for k, v in AUTO.items() if k != "id"}, "id"),
    ({**MANUAL, "status": "BROKEN"}, "status"),
    ({k: v for k, v in MANUAL.items() if k != "reviewCadenceDays"}, "reviewCadenceDays"),
])
def test_upsert_rejects_invalid_breakers(conn, bad, message):
    """Upsert rejects invalid breakers."""
    with pytest.raises(ValueError, match=message):
        repo.upsert_breaker(conn, "NVDA", bad)


def test_upsert_rejects_unknown_ticker(conn):
    """Upsert rejects unknown ticker."""
    with pytest.raises(ValueError, match="ZZZZ"):
        repo.upsert_breaker(conn, "ZZZZ", AUTO)


def test_delete_breaker_removes_definition_and_state(conn):
    """Delete breaker removes definition and state."""
    repo.upsert_breaker(conn, "NVDA", AUTO)
    repo.replace_breaker_state(conn, {"NVDA": {"rsi-low": {"type": "auto", "status": "OK", "currentStreak": 0,
                                                           "streakStartDate": None, "lastEvaluatedAt": "2026-10-09T00:00:00Z"}}})
    repo.delete_breaker(conn, "NVDA", "rsi-low")
    assert repo.list_breakers(conn, "NVDA") == []
    assert repo.list_breaker_state(conn) == {}


def test_delete_unknown_breaker_raises(conn):
    """Delete unknown breaker raises."""
    with pytest.raises(ValueError, match="rsi-low"):
        repo.delete_breaker(conn, "NVDA", "rsi-low")


def test_set_manual_status_updates_status_date_and_appends_note(conn):
    """Set manual status updates status date and appends note."""
    repo.upsert_breaker(conn, "NVDA", MANUAL)
    repo.set_manual_status(conn, "NVDA", "ceo-exit", "WATCHING", "rumour", today="2026-10-09")
    b = repo.list_breakers(conn, "NVDA")[0]
    assert (b["status"], b["statusSetAt"]) == ("WATCHING", "2026-10-09")
    assert b["note"] == "CEO departure | status update 2026-10-09: rumour"


def test_set_manual_status_rejects_auto_breakers_and_bad_status(conn):
    """Set manual status rejects auto breakers and bad status."""
    repo.upsert_breaker(conn, "NVDA", AUTO)
    with pytest.raises(ValueError, match="manual"):
        repo.set_manual_status(conn, "NVDA", "rsi-low", "OK", None)
    repo.upsert_breaker(conn, "NVDA", MANUAL)
    with pytest.raises(ValueError, match="status"):
        repo.set_manual_status(conn, "NVDA", "ceo-exit", "BROKEN", None)


STATE = {
    "NVDA": {
        "rsi-low": {"type": "auto", "currentValue": 22.5, "conditionMet": True, "currentStreak": 2,
                    "streakStartDate": "2026-10-08", "lastEvaluatedAt": "2026-10-09T01:00:00Z", "status": "WATCHING"},
        "ceo-exit": {"type": "manual", "status": "OK", "statusSetAt": "2026-10-01", "reviewCadenceDays": 30,
                     "daysSinceReview": 8, "stale": False},
    }
}


def test_replace_state_round_trips_and_derives_investment_status(conn):
    """Replace state round trips and derives investment status."""
    repo.upsert_breaker(conn, "NVDA", AUTO)
    repo.upsert_breaker(conn, "NVDA", MANUAL)
    repo.replace_breaker_state(conn, STATE)
    got = repo.list_breaker_state(conn)["NVDA"]
    assert got["rsi-low"]["status"] == "WATCHING" and got["rsi-low"]["currentValue"] == 22.5
    assert got["rsi-low"]["currentStreak"] == 2 and got["rsi-low"]["conditionMet"] is True
    assert got["ceo-exit"]["stale"] is False and got["ceo-exit"]["type"] == "manual"
    status = conn.execute("SELECT thesis_breaker_status FROM investment WHERE symbol='NVDA'").fetchone()[0]
    assert status == "WATCHING"


def test_replace_state_replaces_everything_and_clears_status_of_dropped_holdings(conn):
    """Replace state replaces everything and clears status of dropped holdings."""
    repo.upsert_breaker(conn, "NVDA", AUTO)
    repo.upsert_breaker(conn, "NVDA", MANUAL)
    repo.replace_breaker_state(conn, STATE)
    repo.replace_breaker_state(conn, {})
    assert repo.list_breaker_state(conn) == {}
    assert conn.execute("SELECT thesis_breaker_status FROM investment WHERE symbol='NVDA'").fetchone()[0] is None


def test_worst_status_wins(conn):
    """Worst status wins."""
    repo.upsert_breaker(conn, "NVDA", AUTO)
    repo.upsert_breaker(conn, "NVDA", MANUAL)
    state = {"NVDA": {"rsi-low": {**STATE["NVDA"]["rsi-low"], "status": "TRIGGERED"}, "ceo-exit": STATE["NVDA"]["ceo-exit"]}}
    repo.replace_breaker_state(conn, state)
    assert conn.execute("SELECT thesis_breaker_status FROM investment WHERE symbol='NVDA'").fetchone()[0] == "TRIGGERED"


def test_state_for_an_undefined_breaker_is_rejected_and_nothing_is_written(conn):
    """State for an undefined breaker is rejected and nothing is written."""
    repo.upsert_breaker(conn, "NVDA", AUTO)
    with pytest.raises(ValueError, match="ceo-exit"):
        repo.replace_breaker_state(conn, STATE)
    assert repo.list_breaker_state(conn) == {}


def test_state_foreign_key_blocks_orphans(conn):
    """State foreign key blocks orphans."""
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO thesis_breaker_state (investment_id, breaker_id, status, last_evaluated_at) "
                     "VALUES ('NVDA','nope','OK','x')")


def test_shared_vocabulary_is_one_definition():
    """Shared vocabulary is one definition."""
    assert repo.AUTO_METRICS == {"rsi", "dcfFairValueGapPct", "trendState", "momentumPercentile", "pillarAvgScore"}
    assert repo.VALID_OPERATORS == {"<", "<=", ">", ">=", "==", "in"}
    assert repo.VALID_STATUSES == {"OK", "WATCHING", "TRIGGERED"}
    import thesis_breakers
    assert thesis_breakers.AUTO_METRICS is repo.AUTO_METRICS
    assert thesis_breakers.VALID_OPERATORS is repo.VALID_OPERATORS
