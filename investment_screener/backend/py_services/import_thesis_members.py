#!/usr/bin/env python3
"""
import_thesis_members.py - One-time load of each thesis document's stock list into thesis_document_member.

Purpose:
    Each thesis document under data/theses/sub_strategies/ carries its stocks as markdown tables
    (rows that start with a bold ticker, such as ``| **PLTR** | ...``). This reads those rows and
    stores the tickers per document in thesis_document_member, so the web app can show the live
    positions table for one thesis. Only the ticker names are taken; shares, weights and actions
    in those tables are stale and are ignored. Dry-run by default; --write replaces each
    document's members. Documents with no ticker rows are reported and left alone.

Layer:
    Backend / Python Services / Migration (one-time)

Usage Examples:
    python3 import_thesis_members.py --dry-run
    python3 import_thesis_members.py --write

Key Functions (Index):
    - parse_members(): the tickers in one document's tables
    - import_members(): scan a folder of documents and (unless dry-run) store the members
    - main(): CLI entry point

Key Input Dependencies:
    - <repo>/investment_screener/backend/data/theses/sub_strategies/*.md
    - domain_model.sqlite (thesis_document_member)

Key Output Dependencies:
    - thesis_document_member rows
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.thesis_document_member_repository import replace_members  # noqa: E402

DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"
DEFAULT_DOCS_DIR = REPO_ROOT / "investment_screener/backend/data/theses/sub_strategies"
TICKER_ROW = re.compile(r"^\|\s*\*\*([A-Za-z0-9.\-_]+)\*\*\s*\|", re.MULTILINE)


def parse_members(markdown: str) -> list[str]:
    """The distinct tickers (sorted) in the document's table rows that start with a bold ticker."""
    return sorted({m.group(1).upper() for m in TICKER_ROW.finditer(markdown)})


def import_members(docs_dir: Path, db_path: Path, dry_run: bool = True) -> dict:
    """Scan ``docs_dir`` and store each document's members; report what was found."""
    documents: dict[str, list[str]] = {}
    no_tickers: list[str] = []
    for path in sorted(Path(docs_dir).glob("*.md")):
        members = parse_members(path.read_text(errors="replace"))
        if members:
            documents[path.stem] = members
        else:
            no_tickers.append(path.stem)
    written = 0
    if not dry_run:
        conn = initialize_db(str(db_path))
        try:
            for document_id, members in documents.items():
                written += replace_members(conn, document_id, members)
        finally:
            conn.close()
    return {"documents": documents, "no_tickers": no_tickers, "written": written}


def main() -> int:
    """CLI: print the report as JSON; store members only with --write."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-dir", default=str(DEFAULT_DOCS_DIR))
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="report only (default)")
    mode.add_argument("--write", action="store_true", help="store the members")
    args = parser.parse_args()
    print(json.dumps(import_members(Path(args.docs_dir), Path(args.db), dry_run=not args.write), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
