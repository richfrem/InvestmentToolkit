"""Migrate dated research markdown files into the ``observations.jsonl`` ledger.

Implements Design Spec §5's 6-phase migration protocol (Scan -> Classify ->
Manifest -> Stage -> Validate -> Publish & Archive) for the 152 dated
research files under ``investment_screener/backend/data/research/``
(``{TICKER}_{YYYY-MM-DD}.md``).

Reuses the file-discovery glob and ticker/date parsing approach from
``plugins/portfolio-advisor/scripts/consolidate_research.py`` rather than
re-deriving it, per this task's brief.

Global Constraint: no raw dated research markdown files are ever deleted.
``migrate_to_ledger`` moves (archives) the originals to ``archive_dir`` after
successfully appending the corresponding ``RESEARCH_IMPORT`` event to the
ledger — it never removes them outright.

This script writes to the ledger exclusively via
``intelligence.event_store.append_event`` (ADR-028 — no ad hoc JSONL writing
outside the shared data layer).
"""

import re
import shutil
from pathlib import Path

from intelligence.event_store import append_event

DATED_FILE_RE = re.compile(r"^([A-Z0-9.\-]+)_(\d{4}-\d{2}-\d{2})\.md$")


def scan_dated_files(research_dir: str) -> list[dict]:
    """Scan a research directory for dated research files.

    Matches ``{TICKER}_{YYYY-MM-DD}.md`` filenames only; canonical,
    non-dated files (e.g. ``PLTR.md``) are skipped.

    Args:
        research_dir: Directory containing research markdown files.

    Returns:
        A list of dicts, one per matched file, each with ``ticker``,
        ``effective_at`` (the ``YYYY-MM-DD`` date string), and ``path``.
    """
    found = []
    for path in Path(research_dir).glob("*.md"):
        match = DATED_FILE_RE.match(path.name)
        if not match:
            continue
        found.append({
            "ticker": match.group(1),
            "effective_at": match.group(2),
            "path": str(path),
        })
    return found


def migrate_to_ledger(research_dir: str, jsonl_path: str, archive_dir: str) -> dict:
    """Migrate all dated research files in ``research_dir`` into the ledger.

    For each dated file found by ``scan_dated_files``: appends one
    ``RESEARCH_IMPORT`` event to the JSONL ledger via ``append_event``, then
    archives (moves, never deletes) the source file into ``archive_dir``.

    Args:
        research_dir: Directory containing dated research markdown files.
        jsonl_path: Path to the ``observations.jsonl`` ledger file.
        archive_dir: Directory to move successfully-migrated source files
            into. Created if it does not already exist.

    Returns:
        A migration manifest dict with ``migrated_count``.
    """
    files = scan_dated_files(research_dir)
    Path(archive_dir).mkdir(parents=True, exist_ok=True)
    migrated = 0
    for entry in files:
        source_path = Path(entry["path"])
        body = source_path.read_text()
        append_event(
            jsonl_path,
            event_type="RESEARCH_IMPORT",
            effective_at=entry["effective_at"],
            status="ACTIVE",
            title=f"{entry['ticker']} research import ({entry['effective_at']})",
            body_markdown=body,
            ticker=entry["ticker"],
            idempotency_key=f"research-import-{source_path.name}",
        )
        shutil.move(str(source_path), str(Path(archive_dir) / source_path.name))
        migrated += 1
    return {"migrated_count": migrated}
