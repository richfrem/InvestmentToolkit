#!/usr/bin/env python3
"""
record_intelligence_event.py (Intelligence Event Ledger Tool)
============================================================

Purpose:
    Canonical CLI tool and python service to record structured research, news sweeps,
    and thesis updates into intelligence.sqlite without inline SQL execution.

Layer:
    Backend / Python Services / Intelligence Ledger

Usage Examples:
    # Record a thesis update event:
    python3 investment_screener/backend/py_services/record_intelligence_event.py \
        --ticker STM \
        --type THESIS_UPDATE \
        --title "STM Initiated into Power Pillar" \
        --summary "Onboarding thesis with $85.47 DCF Fair Value" \
        --payload '{"pillar": "power", "fair_value": 85.47}'

Key Functions:
    - record_event() - Computes sequence, content hash, registers instrument, and inserts event row.

Key Input Dependencies:
    - investment_screener/backend/data/intelligence.sqlite
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sqlite3
import sys
import uuid
from typing import Any, Dict, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
DB_PATH = os.path.join(PROJECT_ROOT, "investment_screener/backend/data/intelligence.sqlite")

VALID_EVENT_TYPES = {
    "RESEARCH_IMPORT",
    "NEWS_SWEEP",
    "EARNINGS",
    "VALUATION_UPDATE",
    "TECHNICAL_SWEEP",
    "PORTFOLIO_DECISION",
    "THESIS_UPDATE",
    "MACRO_EVENT",
    "REVIEW_DAILY",
    "REVIEW_WEEKLY",
    "PREDICTION_CLAIM",
    "PREDICTION_GRADED",
}


def record_event(
    ticker: str,
    event_type: str,
    title: str,
    summary: str = "",
    body_markdown: str = "",
    payload: Optional[Dict[str, Any]] = None,
    source_id: str = "ai-research-agent",
    confidence_score: float = 0.95,
) -> Dict[str, Any]:
    """
    Record a validated intelligence event into intelligence.sqlite.
    """
    ticker = ticker.strip().upper()
    event_type = event_type.strip().upper()

    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event_type: '{event_type}'. Must be one of: {sorted(VALID_EVENT_TYPES)}")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Ensure instrument exists
    cursor.execute("""
        INSERT OR REPLACE INTO instrument (instrument_id, ticker, exchange, name, active_from, active_to)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ticker, ticker, "UNKNOWN", ticker, timestamp, None))

    # Calculate next event sequence
    cursor.execute("SELECT COALESCE(MAX(event_sequence), 0) + 1 FROM intelligence_event;")
    seq = cursor.fetchone()[0]

    event_id = f"event-{uuid.uuid4().hex[:12]}"
    payload_str = json.dumps(payload or {})
    content_hash = hashlib.sha256((event_id + payload_str).encode("utf-8")).hexdigest()

    cursor.execute("""
        INSERT INTO intelligence_event (
            event_id, event_sequence, instrument_id, event_type, effective_at, observed_at, ingested_at,
            source_id, confidence_score, status, title, body_markdown, payload_json, content_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_id, seq, ticker, event_type, timestamp, timestamp, timestamp,
        source_id, confidence_score, "ACTIVE", title, body_markdown or summary, payload_str, content_hash
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "event_id": event_id,
        "event_sequence": seq,
        "ticker": ticker,
        "event_type": event_type,
        "title": title,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Record an event into intelligence.sqlite")
    parser.add_argument("--ticker", "-t", required=True, help="Stock ticker symbol")
    parser.add_argument("--type", required=True, help="Event type (e.g. THESIS_UPDATE, NEWS_SWEEP)")
    parser.add_argument("--title", required=True, help="Event headline/title")
    parser.add_argument("--summary", default="", help="Short event summary")
    parser.add_argument("--body", default="", help="Detailed markdown body")
    parser.add_argument("--payload", default="{}", help="JSON payload string")
    parser.add_argument("--source", default="ai-research-agent", help="Source ID identifier")

    args = parser.parse_args()

    try:
        payload_dict = json.loads(args.payload)
    except Exception as e:
        print(f"Error parsing JSON payload: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        res = record_event(
            ticker=args.ticker,
            event_type=args.type,
            title=args.title,
            summary=args.summary,
            body_markdown=args.body,
            payload=payload_dict,
            source_id=args.source,
        )
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
