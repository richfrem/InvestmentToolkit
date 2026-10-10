#!/usr/bin/env python3
"""
archive_temp_json.py - Move old scratch JSON files in temp/ into temp/archive/ (never deletes).

Purpose:
    temp/ collects per-stock valuation intermediates (temp/evaluations/*_raw.json, *_scenarios.json,
    ...) and loose one-off JSON files. The web app never reads them, but plugin scripts do read
    some of temp/ (daily-run folders and their manifests, review and news-response folders), so
    only two places are touched: JSON/JSONL files directly in temp/ and in temp/evaluations/,
    and only those not modified in the last --older-than-days (default 7). Files move to
    temp/archive/<YYYY-MM-DD>/<original relative path>; nothing is deleted. Dry-run by default.

Layer:
    Maintenance (moves files; dry-run first)

Usage Examples:
    python3 plugins/toolkit-manager/scripts/archive_temp_json.py                       # list what would move
    python3 plugins/toolkit-manager/scripts/archive_temp_json.py --move                # move it
    python3 plugins/toolkit-manager/scripts/archive_temp_json.py --older-than-days 0 --move

Key Functions (Index):
    - find_candidates(): the files that would move
    - archive(): move them (or report in a dry run)
    - main(): CLI

Key Input Dependencies:
    - <repo>/temp/*.json[l], <repo>/temp/evaluations/*.json[l]

Key Output Dependencies:
    - <repo>/temp/archive/<date>/...
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import date
from pathlib import Path

SCAN_DIRS = (".", "evaluations")
SUFFIXES = {".json", ".jsonl"}


def find_candidates(temp_dir: Path, older_than_days: float, now: float | None = None) -> list[Path]:
    """JSON/JSONL files directly in temp/ and temp/evaluations/ not modified in ``older_than_days``."""
    cutoff = (now if now is not None else time.time()) - older_than_days * 86400
    found: list[Path] = []
    for sub in SCAN_DIRS:
        base = temp_dir / sub
        if not base.is_dir():
            continue
        for path in sorted(base.iterdir()):
            if path.is_file() and not path.is_symlink() and path.suffix in SUFFIXES and path.stat().st_mtime <= cutoff:
                found.append(path)
    return found


def archive(temp_dir: Path, older_than_days: float = 7, move: bool = False, today: str | None = None) -> dict:
    """Move (``move=True``) or list the candidates; returns {"candidates", "moved", "destination"}."""
    candidates = find_candidates(temp_dir, older_than_days)
    destination = temp_dir / "archive" / (today or date.today().isoformat())
    moved = 0
    if move:
        for path in candidates:
            target = destination / path.relative_to(temp_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                continue
            shutil.move(str(path), str(target))
            moved += 1
    return {"candidates": len(candidates), "moved": moved, "destination": str(destination)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temp-dir", default=str(Path(__file__).resolve().parents[3] / "temp"))
    parser.add_argument("--older-than-days", type=float, default=7)
    parser.add_argument("--move", action="store_true", help="Actually move the files (default: list only)")
    args = parser.parse_args()
    result = archive(Path(args.temp_dir), args.older_than_days, args.move)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
