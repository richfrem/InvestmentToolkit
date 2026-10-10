#!/usr/bin/env python3
"""
import_valuation_workpapers.py - One-time load of the per-stock JSON files in temp/ into valuation_workpaper.

Purpose:
    temp/ and temp/evaluations/ hold the working files of past valuation runs, named
    <ticker>_<stage>.json (for example mu_raw.json, MU_scenarios.json, amat_dcf_out.json). This
    reads those files and stores each in the valuation_workpaper table (symbol = the ticker,
    stage = the rest of the name, as_of = the file's modification date). A ticker the database
    does not know, a file that is not JSON and a name without <ticker>_<stage> are reported and
    skipped. Identical content is stored once, so re-running adds nothing. Files are never moved
    or deleted here (archive_temp_json.py does that afterwards). Dry-run by default.

Layer:
    Backend / Python Services / Migration (one-time)

Usage Examples:
    python3 import_valuation_workpapers.py --dry-run
    python3 import_valuation_workpapers.py --write

Key Functions (Index):
    - scan(): classify every candidate file
    - import_workpapers(): scan, and (unless dry-run) store the importable ones
    - main(): CLI entry point

Key Input Dependencies:
    - <repo>/temp/*.json, <repo>/temp/evaluations/*.json
    - domain_model.sqlite (investment symbols, valuation_workpaper)

Key Output Dependencies:
    - valuation_workpaper rows
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.valuation_workpaper_repository import put_workpaper  # noqa: E402

DEFAULT_DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"
SCAN_DIRS = (".", "evaluations")
NAME_RX = re.compile(r"^([A-Za-z][A-Za-z0-9.\-]*?)_(.+)\.json$")


def scan(temp_dir: Path, known_symbols: set[str]) -> dict:
    """Classify the JSON files: {"importable": [(path, symbol, stage, as_of, payload)], "skipped": [(path, reason)]}."""
    importable, skipped = [], []
    for sub in SCAN_DIRS:
        base = temp_dir / sub
        if not base.is_dir():
            continue
        for path in sorted(base.iterdir()):
            if not path.is_file() or path.is_symlink() or path.suffix != ".json":
                continue
            match = NAME_RX.match(path.name)
            if not match:
                skipped.append((path, "name is not <ticker>_<stage>.json"))
                continue
            symbol, stage = match.group(1).upper(), match.group(2).lower()
            if symbol not in known_symbols:
                skipped.append((path, f"unknown ticker {symbol}"))
                continue
            try:
                payload = json.loads(path.read_text())
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                skipped.append((path, f"not JSON: {exc}"))
                continue
            as_of = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            importable.append((path, symbol, stage, as_of, payload))
    return {"importable": importable, "skipped": skipped}


def import_workpapers(
    temp_dir: Path, db_path: Path, dry_run: bool = True, extra_symbols: set[str] | None = None
) -> dict:
    """Scan ``temp_dir`` and store the importable files; returns counts and the skipped list.

    ``extra_symbols`` names tickers that were analysed but are not in the database (for example a
    stock researched and never added); files for any other unknown prefix are skipped.
    """
    conn = initialize_db(str(db_path)) if (Path(db_path).exists() or not dry_run) else None
    try:
        known = {r[0].upper() for r in conn.execute("SELECT symbol FROM investment;")} if conn else set()
        known |= {s.upper() for s in (extra_symbols or set())}
        found = scan(temp_dir, known)
        report = {
            "importable": len(found["importable"]), "created": 0, "already_present": 0,
            "skipped": [(str(p.relative_to(temp_dir)), why) for p, why in found["skipped"]],
        }
        if dry_run:
            return report
        for path, symbol, stage, as_of, payload in found["importable"]:
            _id, created = put_workpaper(conn, symbol, stage, payload, as_of, source=str(path.relative_to(temp_dir)))
            report["created" if created else "already_present"] += 1
        return report
    finally:
        if conn is not None:
            conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temp-dir", default=str(REPO_ROOT / "temp"))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--extra-symbols", default="", help="Comma-separated tickers analysed but not in the database")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()
    print(json.dumps(import_workpapers(
        Path(args.temp_dir), Path(args.db_path), dry_run=args.dry_run,
        extra_symbols={s for s in args.extra_symbols.upper().split(",") if s},
    ), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
