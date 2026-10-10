#!/usr/bin/env python3
"""
brief_ledger_publisher.py - Python utility script.

Purpose:
    Publishes a finished daily brief to the intelligence ledger as a REVIEW_DAILY
    event so the Daily Brief page (GET /api/daily-brief/latest, which reads the
    ledger, not the JSON snapshot) always shows the NEWEST scan of the day.

    A second scan on the same day supersedes the first (the earlier event is flipped
    to SUPERSEDED), so "latest" is the newest brief and history keeps exactly one
    ACTIVE brief per day. A fixed idempotency key ``daily-brief-<date>`` would make
    ``append_event`` drop every scan after the first, so re-runs get a per-run key.

Layer:
    Backend / Python Services / Intelligence ledger

Usage Examples:
    from brief_ledger_publisher import publish_daily_brief
    publish_daily_brief(brief, conn, "2026-10-01")

Key Functions (Index):
    - publish_daily_brief(brief, conn, today_str, now) - append, superseding any ACTIVE
      brief already published for ``today_str``.

Key Input Dependencies:
    - intelligence.event_store.append_event (ledger writer)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from intelligence.event_store import append_event


def publish_daily_brief(
    brief: dict[str, Any],
    conn,
    today_str: str,
    now: datetime | None = None,
) -> str:
    """Append ``brief`` as a REVIEW_DAILY event.

    Args:
        brief: The finished daily brief payload.
        conn: Open sqlite3 connection to intelligence.sqlite.
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

    return append_event(
        conn,
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
