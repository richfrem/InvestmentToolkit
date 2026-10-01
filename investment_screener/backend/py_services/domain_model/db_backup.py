"""Consistent, verified backups of the gitignored SQLite databases.

Why this exists: `domain_model.sqlite` and `intelligence.sqlite` are gitignored, run in WAL
mode, and hold data that cannot be rebuilt from git. Copying only the `.sqlite` file silently
drops anything still in the `-wal` file, so every backup here goes through SQLite's online
backup API, which produces one self-contained file, then proves it with `integrity_check`.

Library use (called by `schema_migrator` before it changes a populated database):

    backup_database(db_path, label="pre-migration-0002")

CLI:

    python3 db_backup.py backup  [--db domain_model|intelligence|PATH] [--keep N]
    python3 db_backup.py list    [--db ...]
    python3 db_backup.py verify  BACKUP_FILE
    python3 db_backup.py restore BACKUP_FILE --db ... --yes

Standalone on purpose (no sibling imports) so `intelligence` code can reuse it unchanged.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_KEEP = 14
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_KNOWN_DBS = {
    "domain_model": _DATA_DIR / "domain_model.sqlite",
    "intelligence": _DATA_DIR / "intelligence.sqlite",
}
_LABEL_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


class BackupError(RuntimeError):
    pass


def default_backup_dir(db_path: str | Path) -> Path:
    return Path(db_path).resolve().parent / "backups"


def verify_backup(path: str | Path) -> int:
    """Raise `BackupError` unless `path` is an intact, non-empty SQLite file.

    Returns the number of user tables so callers can log it.
    """
    p = Path(path)
    if not p.is_file():
        raise BackupError(f"backup file not found: {p}")
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        result = conn.execute("PRAGMA integrity_check;").fetchone()[0]
        if result != "ok":
            raise BackupError(f"integrity_check failed for {p}: {result}")
        tables = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
    finally:
        conn.close()
    if tables == 0:
        raise BackupError(f"backup {p} contains no tables")
    return tables


def backup_database(
    db_path: str | Path,
    backup_dir: str | Path | None = None,
    *,
    label: str | None = None,
    keep: int = DEFAULT_KEEP,
) -> Path:
    """Write a verified backup of `db_path` and prune old ones. Returns the backup path."""
    src_path = Path(db_path).resolve()
    if not src_path.is_file():
        raise BackupError(f"database not found: {src_path}")
    if label is not None and not _LABEL_RE.match(label):
        raise BackupError(f"invalid label {label!r}: use letters, digits, '-' and '_' only")
    if keep < 1:
        raise BackupError("keep must be >= 1")

    out_dir = Path(backup_dir) if backup_dir else default_backup_dir(src_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = f".{label}" if label else ""
    final = out_dir / f"{src_path.stem}.{stamp}{suffix}.sqlite"
    counter = 1
    while final.exists():
        final = out_dir / f"{src_path.stem}.{stamp}{suffix}-{counter}.sqlite"
        counter += 1
    tmp = final.with_name(final.name + ".partial")

    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    dst = sqlite3.connect(tmp)
    try:
        src.backup(dst)
        # A single self-contained file: no -wal/-shm sidecars to lose or leave behind.
        dst.execute("PRAGMA journal_mode=DELETE;")
        dst.commit()
    except Exception:
        dst.close()
        src.close()
        tmp.unlink(missing_ok=True)
        raise
    dst.close()
    src.close()

    try:
        verify_backup(tmp)
    except BackupError:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(final)
    prune_backups(out_dir, src_path.stem, keep)
    return final


def list_backups(backup_dir: str | Path, stem: str) -> list[Path]:
    """Backups for `stem`, newest first."""
    pattern = re.compile(rf"^{re.escape(stem)}\.\d{{8}}-\d{{6}}.*\.sqlite$")
    found = [p for p in Path(backup_dir).glob(f"{stem}.*.sqlite") if pattern.match(p.name)]
    return sorted(found, key=lambda p: p.name, reverse=True)


def prune_backups(backup_dir: str | Path, stem: str, keep: int) -> list[Path]:
    """Delete all but the newest `keep` backups for `stem`. Returns what was deleted."""
    removed = []
    for old in list_backups(backup_dir, stem)[keep:]:
        old.unlink()
        removed.append(old)
    return removed


def restore_database(backup_path: str | Path, db_path: str | Path, *, confirm: bool) -> Path | None:
    """Overwrite `db_path` with the contents of `backup_path`.

    Refuses unless `confirm=True`. First takes a labelled safety backup of the current
    database (returned) so a restore can itself be undone. Stop the backend first: open
    connections to the target will see a lock error rather than silently diverging.
    """
    if not confirm:
        raise BackupError("restore overwrites the live database; pass confirm=True")
    verify_backup(backup_path)
    target = Path(db_path).resolve()
    safety = None
    if target.is_file():
        safety = backup_database(target, label="pre-restore")
    src = sqlite3.connect(f"file:{Path(backup_path).resolve()}?mode=ro", uri=True)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
        dst.execute("PRAGMA journal_mode=WAL;")
        dst.commit()
    finally:
        dst.close()
        src.close()
    return safety


def _resolve_db(arg: str) -> Path:
    return _KNOWN_DBS.get(arg) or Path(arg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("backup", "list", "restore"):
        p = sub.add_parser(name)
        p.add_argument("--db", default="domain_model", help="domain_model | intelligence | path")
        if name == "backup":
            p.add_argument("--keep", type=int, default=DEFAULT_KEEP)
            p.add_argument("--label")
        if name == "restore":
            p.add_argument("backup_file")
            p.add_argument("--yes", action="store_true", help="confirm overwriting the live database")
    v = sub.add_parser("verify")
    v.add_argument("backup_file")
    args = parser.parse_args(argv)

    try:
        if args.cmd == "backup":
            out = backup_database(_resolve_db(args.db), label=args.label, keep=args.keep)
            print(f"backup ok: {out} ({verify_backup(out)} tables, integrity ok)")
        elif args.cmd == "list":
            db = _resolve_db(args.db)
            for p in list_backups(default_backup_dir(db), db.stem):
                print(p)
        elif args.cmd == "verify":
            print(f"ok: {verify_backup(args.backup_file)} tables, integrity ok")
        elif args.cmd == "restore":
            safety = restore_database(args.backup_file, _resolve_db(args.db), confirm=args.yes)
            print(f"restored. previous state saved at: {safety}")
    except BackupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
