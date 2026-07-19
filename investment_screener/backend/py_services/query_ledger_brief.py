#!/usr/bin/env python3
"""Query daily brief data from the SQLite Intelligence Ledger.

Usage:
    python3 query_ledger_brief.py --latest [--db-path PATH]
    python3 query_ledger_brief.py --history [--db-path PATH]
    python3 query_ledger_brief.py --conviction TICKER [--db-path PATH]
"""
import sys
from pathlib import Path
import json
import sqlite3
import argparse

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from intelligence.event_repository import get_latest_event_by_type


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--latest", action="store_true")
    group.add_argument("--history", action="store_true")
    group.add_argument("--conviction", type=str)
    parser.add_argument("--db-path", type=str)
    args = parser.parse_args()

    db_path = args.db_path or str(REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite")

    if not Path(db_path).exists():
        print(json.dumps({"error": f"Database file not found: {db_path}"}))
        sys.exit(1)

    try:
        conn = sqlite3.connect(db_path)
    except Exception as exc:
        print(json.dumps({"error": f"Failed to connect to database: {exc}"}))
        sys.exit(1)

    try:
        if args.latest:
            event = get_latest_event_by_type(conn, "REVIEW_DAILY")
            if not event or not event.get("payload_json"):
                print(json.dumps(None))
            else:
                # Output the exact payload JSON
                print(event["payload_json"])

        elif args.history:
            # Query all REVIEW_DAILY events
            cursor = conn.execute("""
                SELECT payload_json, effective_at, ingested_at
                FROM intelligence_event
                WHERE event_type = 'REVIEW_DAILY' AND status = 'ACTIVE'
                ORDER BY effective_at DESC, ingested_at DESC;
            """)
            rows = cursor.fetchall()
            history = []
            for payload_json, effective_at, ingested_at in rows:
                if payload_json:
                    try:
                        d = json.loads(payload_json)
                        # Build history entry mapping the legacy fields
                        history.append({
                            "date": d.get("date"),
                            "regime": d.get("macro_regime", {}).get("regime"),
                            "reduce_count": len([s for s in d.get("conviction_scores", []) if s.get("band") in ("REDUCE", "EXIT")]),
                            "accum_count": len([s for s in d.get("conviction_scores", []) if s.get("band") == "ACCUMULATE"]),
                            "ta_refreshed": d.get("ta_refreshed"),
                        })
                    except Exception:
                        pass
            print(json.dumps(history))

        elif args.conviction:
            ticker = args.conviction.upper()
            cursor = conn.execute("""
                SELECT payload_json
                FROM intelligence_event
                WHERE event_type = 'REVIEW_DAILY' AND status = 'ACTIVE'
                ORDER BY effective_at ASC, ingested_at ASC;
            """)
            rows = cursor.fetchall()
            history = []
            for (payload_json,) in rows:
                if payload_json:
                    try:
                        d = json.loads(payload_json)
                        scores = d.get("conviction_scores", [])
                        score = next((s for s in scores if s.get("ticker") == ticker), None)
                        if score:
                            # Prepend/include date
                            history.append({
                                "date": d.get("date"),
                                **score
                            })
                    except Exception:
                        pass
            print(json.dumps(history))

    finally:
        conn.close()


if __name__ == "__main__":
    main()
