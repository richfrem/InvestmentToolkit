#!/usr/bin/env python3
"""
research_parity_report.py — Read-only report of which on-disk research files are already in the ledger.

Purpose:
    For every research source that still exists as a file (research markdown,
    observations.jsonl, intelligence_events.jsonl, daily-briefs, projections,
    etf_analysis), list the items already present in the ledger
    (intelligence.sqlite or domain_model.sqlite), the items missing from it, and
    the items with no ledger target. Nothing is written: both databases are
    opened read-only. The owner approves this report before any migrator runs
    with --write.

Layer: Plugins / Portfolio Advisor / Reporting

Usage:
    python3 plugins/portfolio-advisor/scripts/research_parity_report.py
    python3 plugins/portfolio-advisor/scripts/research_parity_report.py --json
    python3 plugins/portfolio-advisor/scripts/research_parity_report.py --data-dir <dir>

Key Functions (Index):
    - load_ledger_index(): idempotency keys, event ids and content hashes in intelligence_event
    - check_research_files(): research markdown by `research-import-<name>` key
    - check_event_jsonl(): observations.jsonl / intelligence_events.jsonl lines by event id, key, hash
    - check_daily_briefs(): daily-briefs/*.json by `daily-brief-<date>` key
    - check_projections(): projections/*.json tickers against projection_version
    - check_etf_analysis(): etf_analysis/*.json (no ledger target)
    - build_report(): run every check and return the report dict
    - render_markdown(): human-readable summary of a report
    - main(): CLI entry point

Key Input Dependencies:
    - <data-dir>/intelligence.sqlite (read-only)
    - <data-dir>/domain_model.sqlite (read-only; projection_version)
    - <data-dir>/research/, observations.jsonl, intelligence_events.jsonl, daily-briefs/,
      projections/, etf_analysis/

Key Output Dependencies:
    - stdout only (markdown, or JSON with --json)
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
DATED_RESEARCH_RE = re.compile(r"^([A-Z0-9.\-]+)_(\d{4}-\d{2}-\d{2})\.md$")
DERIVED_RESEARCH_RE = re.compile(r"^[A-Z0-9.\-]+(\.summary|\.timeline)?\.md$")


def _open_readonly(path: Path) -> sqlite3.Connection | None:
    """Open a SQLite file read-only; None when the file does not exist."""
    if not path.exists():
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_ledger_index(conn: sqlite3.Connection | None) -> dict:
    """Return the sets of idempotency keys, event ids and content hashes in the ledger."""
    index = {"keys": set(), "ids": set(), "hashes": set(), "bodies_by_key": {}, "count": 0}
    if conn is None:
        return index
    for row in conn.execute(
        "SELECT event_id, idempotency_key, content_hash, body_markdown FROM intelligence_event"
    ):
        index["count"] += 1
        index["ids"].add(row["event_id"])
        index["hashes"].add(row["content_hash"])
        if row["idempotency_key"]:
            index["keys"].add(row["idempotency_key"])
            index["bodies_by_key"][row["idempotency_key"]] = row["body_markdown"] or ""
    return index


def check_research_files(research_dir: Path, ledger: dict) -> dict:
    """Classify research markdown files as present, missing, content-different, derived or other.

    A dated file `<TICKER>_<YYYY-MM-DD>.md`, in the folder or any subfolder, maps to the key
    `research-import-<name>`. `<TICKER>.md`, `<TICKER>.summary.md` and `<TICKER>.timeline.md`
    are consolidated views built from the dated files and are listed under `derived`. Anything
    else is listed under `other`.
    """
    result = {"present": [], "missing": [], "content_differs": [], "derived": [], "other": []}
    if not research_dir.exists():
        return result
    for path in sorted(research_dir.rglob("*.md")):
        rel = str(path.relative_to(research_dir))
        if DATED_RESEARCH_RE.match(path.name):
            key = f"research-import-{path.name}"
            if key not in ledger["keys"]:
                result["missing"].append(rel)
            elif ledger["bodies_by_key"][key].strip() != path.read_text(errors="replace").strip():
                result["content_differs"].append(rel)
            else:
                result["present"].append(rel)
        elif DERIVED_RESEARCH_RE.match(path.name):
            result["derived"].append(rel)
        else:
            result["other"].append(rel)
    return result


def check_event_jsonl(jsonl_path: Path, ledger: dict) -> dict:
    """Check each ledger-JSONL line by idempotency key, event id or content hash."""
    result = {"lines": 0, "present": 0, "missing": [], "unreadable": 0}
    if not jsonl_path.exists():
        return result
    for line in jsonl_path.read_text().splitlines():
        if not line.strip():
            continue
        result["lines"] += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            result["unreadable"] += 1
            continue
        key = record.get("idempotency_key")
        found = (
            (key and key in ledger["keys"])
            or record.get("event_id") in ledger["ids"]
            or record.get("content_hash") in ledger["hashes"]
        )
        if found:
            result["present"] += 1
        else:
            result["missing"].append(
                {"event_id": record.get("event_id"), "event_type": record.get("event_type"),
                 "ticker": record.get("ticker"), "effective_at": record.get("effective_at"),
                 "idempotency_key": key}
            )
    return result


def check_daily_briefs(briefs_dir: Path, ledger: dict) -> dict:
    """Check daily-briefs/<date>.json against the key `daily-brief-<date>`."""
    result = {"present": [], "missing": []}
    if not briefs_dir.exists():
        return result
    for path in sorted(briefs_dir.glob("*.json")):
        (result["present"] if f"daily-brief-{path.stem}" in ledger["keys"] else result["missing"]).append(path.name)
    return result


def check_projections(projections_dir: Path, domain_conn: sqlite3.Connection | None) -> dict:
    """Check each projections/<TICKER>.json ticker has a projection_version row."""
    result = {"present": [], "missing": []}
    if not projections_dir.exists():
        return result
    stored: set[str] = set()
    if domain_conn is not None:
        for row in domain_conn.execute(
            "SELECT DISTINCT i.symbol FROM projection_version p JOIN investment i "
            "ON i.investment_id = p.investment_id"
        ):
            stored.add(row["symbol"])
    for path in sorted(projections_dir.glob("*.json")):
        (result["present"] if path.stem in stored else result["missing"]).append(path.name)
    return result


def check_etf_analysis(etf_dir: Path) -> dict:
    """List etf_analysis/*.json; the ledger has no event type for them."""
    files = sorted(p.name for p in etf_dir.glob("*.json")) if etf_dir.exists() else []
    return {"files": files, "ledger_target": "none: needs an owner decision"}


def build_report(data_dir: Path) -> dict:
    """Run every parity check against the databases and files under ``data_dir``."""
    ledger_conn = _open_readonly(data_dir / "intelligence.sqlite")
    domain_conn = _open_readonly(data_dir / "domain_model.sqlite")
    ledger = load_ledger_index(ledger_conn)
    report = {
        "ledger_events": ledger["count"],
        "research": check_research_files(data_dir / "research", ledger),
        "observations_jsonl": check_event_jsonl(data_dir / "observations.jsonl", ledger),
        "intelligence_events_jsonl": check_event_jsonl(data_dir / "intelligence_events.jsonl", ledger),
        "daily_briefs": check_daily_briefs(data_dir / "daily-briefs", ledger),
        "projections": check_projections(data_dir / "projections", domain_conn),
        "etf_analysis": check_etf_analysis(data_dir / "etf_analysis"),
    }
    for conn in (ledger_conn, domain_conn):
        if conn is not None:
            conn.close()
    return report


def render_markdown(report: dict) -> str:
    """Render the report as a short markdown summary."""
    r = report["research"]
    out = [f"# Research parity report\n", f"Ledger events: {report['ledger_events']}\n"]
    out.append(
        f"- research markdown: {len(r['present'])} present, {len(r['missing'])} missing, "
        f"{len(r['content_differs'])} content differs, {len(r['derived'])} derived views, {len(r['other'])} other"
    )
    for name in ("observations_jsonl", "intelligence_events_jsonl"):
        j = report[name]
        out.append(f"- {name}: {j['lines']} lines, {j['present']} in ledger, {len(j['missing'])} missing, {j['unreadable']} unreadable")
    b = report["daily_briefs"]
    out.append(f"- daily briefs: {len(b['present'])} present, {len(b['missing'])} missing")
    p = report["projections"]
    out.append(f"- projections: {len(p['present'])} tickers in projection_version, {len(p['missing'])} missing")
    out.append(f"- etf_analysis: {len(report['etf_analysis']['files'])} files, {report['etf_analysis']['ledger_target']}")
    return "\n".join(out) + "\n"


def main() -> int:
    """CLI: print the parity report (markdown, or JSON with --json). Writes nothing."""
    parser = argparse.ArgumentParser(description="Read-only research parity report.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON")
    args = parser.parse_args()
    report = build_report(Path(args.data_dir))
    print(json.dumps(report, indent=2) if args.json else render_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
