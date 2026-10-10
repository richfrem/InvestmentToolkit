"""Tests for brief_ledger_publisher.publish_daily_brief.

2026-10-01: the Daily Brief page read the brief from the REVIEW_DAILY ledger, but
daily_brief.py wrote it with the fixed idempotency key ``daily-brief-<date>``.
``append_event`` returns the existing event and writes nothing when that key is already
present, so only the FIRST scan of each day ever reached the page; later runs rewrote
the JSON file and were silently dropped from the ledger (a corrected MU/RIOT brief never
showed up). A new scan on the same day must supersede the earlier one.

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_brief_ledger_publisher.py -v
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.event_repository import (  # noqa: E402
    get_latest_event_by_type,
    list_active_events_by_type,
)
from brief_ledger_publisher import publish_daily_brief  # noqa: E402


def _ledger(tmp_path):
    return initialize_db(str(tmp_path / "intelligence.sqlite"))


def _publish(conn, day, marker, second):
    brief = {"date": day, "marker": marker, "recommendations": []}
    return publish_daily_brief(
        brief, conn, day,
        now=datetime(2026, 10, 1, 15, 0, second, tzinfo=timezone.utc),
    )


def test_first_scan_of_the_day_is_published(tmp_path):
    conn = _ledger(tmp_path)
    _publish(conn, "2026-10-01", "first", 1)

    latest = get_latest_event_by_type(conn, "REVIEW_DAILY")
    assert json.loads(latest["payload_json"])["marker"] == "first"
    assert latest["idempotency_key"] == "daily-brief-2026-10-01"


def test_second_scan_same_day_replaces_the_first_in_latest(tmp_path):
    conn = _ledger(tmp_path)
    first_id = _publish(conn, "2026-10-01", "first", 1)
    second_id = _publish(conn, "2026-10-01", "second", 2)

    assert second_id != first_id
    latest = get_latest_event_by_type(conn, "REVIEW_DAILY")
    assert json.loads(latest["payload_json"])["marker"] == "second"
    status = dict(conn.execute(
        "SELECT event_id, status FROM intelligence_event WHERE event_type='REVIEW_DAILY'"
    ).fetchall())
    assert status[first_id] == "SUPERSEDED"
    assert status[second_id] == "ACTIVE"


def test_history_keeps_exactly_one_active_brief_per_day(tmp_path):
    conn = _ledger(tmp_path)
    _publish(conn, "2026-09-30", "yesterday", 1)
    _publish(conn, "2026-10-01", "first", 2)
    _publish(conn, "2026-10-01", "second", 3)
    _publish(conn, "2026-10-01", "third", 4)

    active = list_active_events_by_type(conn, "REVIEW_DAILY")
    markers = sorted(json.loads(e["payload_json"])["marker"] for e in active)
    assert markers == ["third", "yesterday"]


def test_a_new_day_does_not_supersede_the_previous_day(tmp_path):
    conn = _ledger(tmp_path)
    _publish(conn, "2026-09-30", "yesterday", 1)
    _publish(conn, "2026-10-01", "today", 2)

    active = list_active_events_by_type(conn, "REVIEW_DAILY")
    assert len(active) == 2


def test_two_scans_in_the_same_second_both_publish(tmp_path):
    conn = _ledger(tmp_path)
    _publish(conn, "2026-10-01", "first", 5)
    _publish(conn, "2026-10-01", "second", 5)

    latest = get_latest_event_by_type(conn, "REVIEW_DAILY")
    assert json.loads(latest["payload_json"])["marker"] == "second"
