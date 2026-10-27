#!/usr/bin/env python3
"""
record_news_sweep.py - Record a news sweep's findings in the intelligence ledger (intelligence.sqlite).

Purpose:
    A daily or weekly news sweep produces findings per ticker. They used to live only in a
    markdown file under temp/, so nothing downstream could use them. This reads the triangulated
    findings as markdown on stdin, one `## TICKER` section per stock (and an optional
    `## MACRO` section), and writes one NEWS_SWEEP event per section. Re-running the same sweep
    changes nothing; a changed finding supersedes the earlier one. The thesis pages read these
    events (thesis_currency.py) to stay current.

Layer:
    Plugins / Portfolio Advisor / Scripts (writes the ledger)

Usage Examples:
    python3 plugins/portfolio-advisor/scripts/record_news_sweep.py --source grok --as-of 2026-10-10 < findings.md
    pbpaste | python3 plugins/portfolio-advisor/scripts/record_news_sweep.py --source claude --write

Key Functions (Index):
    - parse_findings(): (ticker or None, text) per `## TICKER` / `## MACRO` section
    - record_findings(): write the events; returns {written, unchanged, corrected, tickers}
    - main(): CLI (dry run unless --write)

Key Input Dependencies:
    - findings markdown on stdin
    - intelligence.event_store (append_or_supersede_event), intelligence.sqlite

Key Output Dependencies:
    - NEWS_SWEEP events in intelligence_event
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "investment_screener/backend/py_services"))

from intelligence.db_client import initialize_db  # noqa: E402
from intelligence.event_store import append_or_supersede_event  # noqa: E402

DEFAULT_DB = ROOT / "investment_screener/backend/data/intelligence.sqlite"
HEADING = re.compile(r"^##\s+(.*?)\s*$")
TICKER = re.compile(r"^[A-Za-z][A-Za-z0-9.\-]{0,9}$")


def parse_findings(markdown: str) -> list[tuple[str | None, str]]:
    """Sections as (TICKER, text); MACRO gives ticker None. Headings that are not a ticker are dropped."""
    sections: list[tuple[str | None, str]] = []
    label: str | None = None
    keep = False
    lines: list[str] = []

    def close() -> None:
        text = "\n".join(lines).strip()
        if keep and text:
            sections.append((None if label == "MACRO" else label, text))

    for line in markdown.splitlines():
        heading = HEADING.match(line)
        if heading:
            close()
            lines = []
            name = heading.group(1)
            keep = bool(TICKER.match(name))
            label = name.upper() if keep else None
        else:
            lines.append(line)
    close()
    return sections


def _chain_head(conn, key: str) -> str | None:
    row = conn.execute(
        "SELECT event_id FROM intelligence_event WHERE idempotency_key = ? OR idempotency_key LIKE ? "
        "ORDER BY event_sequence DESC LIMIT 1;", (key, key + "#r%"),
    ).fetchone()
    return row[0] if row else None


def record_findings(markdown: str, db_path: Path, as_of: str, source: str) -> dict:
    """Write one NEWS_SWEEP event per section of ``markdown``; nothing is written when the input is invalid."""
    source = (source or "").strip().lower()
    if not source:
        raise ValueError("source must not be empty")
    if not markdown.strip():
        raise ValueError("no findings given")
    date.fromisoformat(as_of)
    sections = parse_findings(markdown)
    if not sections:
        raise ValueError("no `## TICKER` sections found")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = initialize_db(str(db_path))
    receipt = {"written": 0, "unchanged": 0, "corrected": 0, "tickers": []}
    try:
        for ticker, text in sections:
            label = ticker or "MACRO"
            key = f"news-sweep-{as_of}-{source}-{label}"
            before = _chain_head(conn, key)
            first = next((ln.lstrip("-* ").strip() for ln in text.splitlines() if ln.strip()), "")
            event_id = append_or_supersede_event(
                conn, idempotency_key=key,
                payload={"source": source, "asOf": as_of, "ticker": ticker, "bodySha256": hashlib.sha256(text.encode()).hexdigest()},
                event_type="NEWS_SWEEP", effective_at=as_of, status="ACTIVE",
                title=f"{source} sweep {as_of}: {label} - {first[:90]}",
                body_markdown=text, ticker=ticker, source_id=f"news-sweep:{source}",
            )
            receipt["written" if before is None else "unchanged" if event_id == before else "corrected"] += 1
            receipt["tickers"].append(label)
    finally:
        conn.close()
    return receipt


def main() -> int:
    """CLI: read findings from stdin; print what would be (or was) recorded."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Model or desk the findings came from, e.g. grok, claude, chatgpt")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="Date of the sweep (YYYY-MM-DD)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--write", action="store_true", help="Record the events (default: show what was parsed)")
    args = parser.parse_args()
    markdown = sys.stdin.read()
    try:
        if not args.write:
            sections = parse_findings(markdown)
            date.fromisoformat(args.as_of)
            print(json.dumps({"dry_run": True, "sections": [t or "MACRO" for t, _ in sections]}))
            return 0 if sections else 1
        print(json.dumps(record_findings(markdown, args.db, args.as_of, args.source)))
        return 0
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
