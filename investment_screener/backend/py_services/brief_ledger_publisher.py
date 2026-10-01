#!/usr/bin/env python3
"""
brief_ledger_publisher.py - Python utility script.

Purpose:
    Publishes a finished daily brief to the intelligence ledger as a REVIEW_DAILY
    event so the Daily Brief page (GET /api/daily-brief/latest, which reads the
    ledger, not the JSON snapshot) always shows the NEWEST scan of the day.

    A second scan on the same day supersedes the first (the earlier event is flipped
    to SUPERSEDED), so "latest" is the newest brief and history keeps exactly one
    ACTIVE brief per day. Before this module, daily_brief.py wrote every brief with the
    fixed idempotency key ``daily-brief-<date>``; ``append_event`` dedupes on that key,
    so only the first scan of a day ever reached the page.

Layer:
    Backend / Python Services / Intelligence ledger

Usage Examples:
    from brief_ledger_publisher import publish_daily_brief
    publish_daily_brief(brief, jsonl_path, conn, "2026-10-01")

Key Functions (Index):
    - publish_daily_brief(brief, jsonl_path, conn, today_str, now) - append + replay,
      superseding any ACTIVE brief already published for ``today_str``.

Key Input Dependencies:
    - intelligence.event_store.append_event (JSONL ledger writer)
    - intelligence.replay_ledger.replay_events_to_db (JSONL -> SQLite read model)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from intelligence.event_store import append_event
from intelligence.replay_ledger import replay_events_to_db


def publish_daily_brief(
    brief: dict[str, Any],
    jsonl_path: str,
    conn,
    today_str: str,
    now: datetime | None = None,
) -> str:
    """Append ``brief`` as a REVIEW_DAILY event and replay it into the read model.

    Args:
        brief: The finished daily brief payload.
        jsonl_path: Path to the observations.jsonl ledger.
        conn: Open sqlite3 connection to intelligence.sqlite (read-model schema applied).
        today_str: The brief's date, ``YYYY-MM-DD``; used as ``effective_at``.
        now: Clock override for tests; defaults to the current UTC time.

    Returns:
        The ``event_id`` of the newly written event.
    """
    prior = conn.execute(
        "SELECT event_id FROM intelligence_event "
        "WHERE event_type = 'REVIEW_DAILY' AND effective_at = ? AND status = 'ACTIVE' "
        "ORDER BY event_sequence DESC LIMIT 1;",
        (today_str,),
    ).fetchone()
    prior_id = prior[0] if prior else None

    # First scan of the day keeps the stable key; re-runs get a per-run key so the
    # ledger's idempotency dedup does not swallow them.
    stamp = (now or datetime.now(timezone.utc)).strftime("%H%M%S%f")
    key = f"daily-brief-{today_str}" if prior_id is None else f"daily-brief-{today_str}-{stamp}"

    event_id = append_event(
        jsonl_path,
        event_type="REVIEW_DAILY",
        effective_at=today_str,
        status="ACTIVE",
        title=f"Daily Brief for {today_str}",
        body_markdown="Generated daily brief summary metrics.",
        ticker=None,
        source_id="daily_brief",
        payload=brief,
        supersedes_event_id=prior_id,
        idempotency_key=key,
    )
    replay_events_to_db(jsonl_path, conn)
    return event_id
