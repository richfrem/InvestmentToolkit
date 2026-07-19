#!/usr/bin/env python3
"""Query research reports from the SQLite Intelligence Ledger.

Usage:
    python3 query_ledger_research.py --list [--db-path PATH]
    python3 query_ledger_research.py --get FILENAME [--db-path PATH]
"""
import sys
from pathlib import Path
import json
import sqlite3
import argparse
import re

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

DATED_FILE_RE = re.compile(r"^([A-Z0-9.\-]+)_(\d{4}-\d{2}-\d{2})\.md$")

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true")
    group.add_argument("--get", type=str)
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
        if args.list:
            # Query all ACTIVE RESEARCH_IMPORT events
            cursor = conn.execute("""
                SELECT i.ticker, ie.effective_at
                FROM intelligence_event ie
                JOIN instrument i ON i.instrument_id = ie.instrument_id
                WHERE ie.event_type = 'RESEARCH_IMPORT' AND ie.status = 'ACTIVE'
                ORDER BY ie.effective_at DESC, ie.ingested_at DESC;
            """)
            rows = cursor.fetchall()
            reports = []
            for ticker, effective_at in rows:
                filename = f"{ticker}_{effective_at}.md"
                reports.append({
                    "filename": filename,
                    "ticker": ticker,
                    "date": effective_at
                })
            print(json.dumps(reports))

        elif args.get:
            filename = args.get
            match = DATED_FILE_RE.match(filename)
            if not match:
                print(json.dumps(None))
                return

            ticker = match.group(1)
            effective_at = match.group(2)

            cursor = conn.execute("""
                SELECT ie.body_markdown
                FROM intelligence_event ie
                JOIN instrument i ON i.instrument_id = ie.instrument_id
                WHERE ie.event_type = 'RESEARCH_IMPORT' 
                  AND i.ticker = ? 
                  AND ie.effective_at = ? 
                  AND ie.status = 'ACTIVE'
                ORDER BY ie.ingested_at DESC LIMIT 1;
            """, (ticker, effective_at))
            row = cursor.fetchone()
            if row:
                print(json.dumps({
                    "filename": filename,
                    "content": row[0],
                    "ticker": ticker,
                    "date": effective_at
                }))
            else:
                print(json.dumps(None))

    finally:
        conn.close()

if __name__ == "__main__":
    main()
