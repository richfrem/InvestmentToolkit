#!/usr/bin/env python3
"""
sqlite_admin.py - Portable export and rebuild of a SQLite database (DDL + data as plain files).

Purpose:
    A database that can be rebuilt from plain text is never lost to a corrupt file, a bad
    migration or a tool upgrade. `export` writes the schema and every table's rows to a folder
    of SQL files plus a manifest of row counts; `rebuild` creates a NEW database from that
    folder and proves it matches the manifest before putting it in place; `verify-export`
    does the same check in memory. Binary snapshots (backup / restore) stay in db_backup.py.
    Stdlib only. Never modifies a source database and never overwrites an existing file.

Layer:
    Backend / Database administration

Usage Examples:
    python3 sqlite_admin.py status --db domain_model
    python3 sqlite_admin.py export --db domain_model --out temp/exports/domain_model-2026-10-09
    python3 sqlite_admin.py verify-export temp/exports/domain_model-2026-10-09
    python3 sqlite_admin.py rebuild temp/exports/domain_model-2026-10-09 --db temp/rebuilt.sqlite

Key Functions (Index):
    - export_database(): write schema.sql, data/<table>.sql and manifest.json
    - rebuild_database(): create a new database from an export and verify it
    - verify_export(): rebuild in memory and compare with the manifest
    - status(): tables, row counts, user_version, journal mode
    - main(): command line

Key Input Dependencies:
    - db_backup.py in the same folder (database name resolution: find_data_dir / resolve_db)
    - Optional env var SQLITE_ADMIN_DATA_DIR
    - The source database file (read through SQLite's online backup API, so WAL rows are included)
    - An export folder produced by `export` (for rebuild / verify-export)

Key Output Dependencies:
    - <out>/schema.sql, <out>/data/<table>.sql, <out>/manifest.json
    - A new database file from `rebuild`
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_backup import BackupError, resolve_db  # noqa: E402  (same folder; linked beside this file in the skill)



class AdminError(RuntimeError):
    """A clear, user-facing failure (missing file, existing target, mismatched export)."""


def _ident(name: str) -> str:
    """Quote an SQL identifier."""
    return '"' + name.replace('"', '""') + '"'


def _snapshot(db_path: Path) -> sqlite3.Connection:
    """Copy the database (WAL included) into memory through the online backup API, read-only."""
    if not db_path.is_file():
        raise AdminError(f"database not found: {db_path}")
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    mem = sqlite3.connect(":memory:")
    try:
        src.backup(mem)
    finally:
        src.close()
    return mem


def _schema_objects(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """(type, name, sql) for every user object that has SQL, tables first in creation order."""
    rows = conn.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY rowid"
    ).fetchall()
    return [tuple(r) for r in rows]


def _virtual_tables(objects: list[tuple[str, str, str]]) -> set[str]:
    """Names of virtual tables (for example FTS5 indexes)."""
    return {n for t, n, sql in objects if t == "table" and sql.upper().startswith("CREATE VIRTUAL")}


def _is_shadow(name: str, virtual: set[str]) -> bool:
    """True for a table SQLite maintains itself for a virtual table (`notes_data`, `notes_idx`, ...)."""
    return any(name.startswith(v + "_") for v in virtual)


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """Insertable column names of a table or virtual table, in declaration order."""
    return [r[1] for r in conn.execute(f"PRAGMA table_info({_ident(table)})")]


def _table_data_sql(conn: sqlite3.Connection, table: str, virtual: bool) -> tuple[str, int]:
    """INSERT statements (one per row, SQLite `quote()` literals) and the row count for one table."""
    cols = _columns(conn, table)
    names = (["rowid"] if virtual else []) + cols
    select = ", ".join(f"quote({_ident(c)})" if c != "rowid" else "quote(rowid)" for c in names)
    head = f"INSERT INTO {_ident(table)} ({', '.join(_ident(c) for c in names)}) VALUES ("
    lines = [head + ", ".join(row) + ");" for row in conn.execute(f"SELECT {select} FROM {_ident(table)}")]
    return "\n".join(lines) + ("\n" if lines else ""), len(lines)


def _foreign_key_violations(conn: sqlite3.Connection) -> int:
    """Number of rows that violate a foreign key (existing databases may already have some)."""
    return len(conn.execute("PRAGMA foreign_key_check").fetchall())


def export_database(db_path: str | Path, out_dir: str | Path) -> dict:
    """Write `schema.sql`, `data/<table>.sql` and `manifest.json` for a database.

    Args:
        db_path: Source database. Never modified.
        out_dir: Output folder; must be absent or empty.

    Returns:
        The manifest dict.

    Raises:
        AdminError: Source missing or output folder not empty.
    """
    out = Path(out_dir)
    if out.exists() and any(out.iterdir()):
        raise AdminError(f"output folder is not empty: {out}")
    conn = _snapshot(Path(db_path))
    try:
        objects = _schema_objects(conn)
        virtual = _virtual_tables(objects)
        (out / "data").mkdir(parents=True, exist_ok=True)
        counts: dict[str, int] = {}
        for kind, name, _sql in objects:
            if kind != "table" or _is_shadow(name, virtual):
                continue
            text, counts[name] = _table_data_sql(conn, name, name in virtual)
            (out / "data" / f"{name}.sql").write_text(text, encoding="utf-8")
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name='sqlite_sequence'").fetchone():
            text, counts["sqlite_sequence"] = _table_data_sql(conn, "sqlite_sequence", False)
            (out / "data" / "sqlite_sequence.sql").write_text(text, encoding="utf-8")
        ddl = [sql.rstrip().rstrip(";") + ";" for _k, name, sql in objects if not _is_shadow(name, virtual)]
        (out / "schema.sql").write_text("\n\n".join(ddl) + "\n", encoding="utf-8")
        manifest = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "source": str(db_path),
            "user_version": conn.execute("PRAGMA user_version").fetchone()[0],
            "foreign_key_violations": _foreign_key_violations(conn),
            "tables": counts,
        }
    finally:
        conn.close()
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _load_manifest(export_dir: Path) -> dict:
    """Read manifest.json, failing clearly when the folder is not an export."""
    path = export_dir / "manifest.json"
    if not path.is_file() or not (export_dir / "schema.sql").is_file():
        raise AdminError(f"not an export folder (manifest.json / schema.sql missing): {export_dir}")
    return json.loads(path.read_text(encoding="utf-8"))


def _split_schema(export_dir: Path) -> tuple[list[str], list[str]]:
    """(tables, later objects) from schema.sql; indexes, views and triggers are created after the data."""
    conn = sqlite3.connect(":memory:")
    first: list[str] = []
    later: list[str] = []
    buf = ""
    for line in (export_dir / "schema.sql").read_text(encoding="utf-8").splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            stmt = buf.strip()
            buf = ""
            word = stmt.split(None, 3)
            is_table = word[0].upper() == "CREATE" and (word[1].upper() == "TABLE" or word[1].upper() == "VIRTUAL")
            (first if is_table else later).append(stmt)
    conn.close()
    return first, later


def _build(conn: sqlite3.Connection, export_dir: Path, manifest: dict) -> dict[str, int]:
    """Create the schema and load every data file into `conn`; return the loaded row counts."""
    tables, later = _split_schema(export_dir)
    conn.execute("PRAGMA foreign_keys=OFF;")
    for stmt in tables:
        conn.execute(stmt)
    names = [n for n in manifest["tables"] if n != "sqlite_sequence"]
    for name in names:
        conn.executescript((export_dir / "data" / f"{name}.sql").read_text(encoding="utf-8"))
    if "sqlite_sequence" in manifest["tables"]:
        conn.execute("DELETE FROM sqlite_sequence;")
        conn.executescript((export_dir / "data" / "sqlite_sequence.sql").read_text(encoding="utf-8"))
    for stmt in later:
        conn.execute(stmt)
    conn.execute(f"PRAGMA user_version = {int(manifest['user_version'])};")
    conn.commit()
    return {n: conn.execute(f"SELECT COUNT(*) FROM {_ident(n)}").fetchone()[0] for n in manifest["tables"]}


def _check(conn: sqlite3.Connection, manifest: dict) -> dict[str, int]:
    """Compare a rebuilt database with the manifest; raise AdminError naming the first mismatch."""
    counts = {n: conn.execute(f"SELECT COUNT(*) FROM {_ident(n)}").fetchone()[0] for n in manifest["tables"]}
    for name, expected in manifest["tables"].items():
        if name == "audit" or counts[name] != expected:
            if counts[name] != expected:
                raise AdminError(f"table {name}: rebuilt {counts[name]} rows, manifest says {expected}")
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise AdminError("integrity_check failed on the rebuilt database")
    if _foreign_key_violations(conn) != manifest["foreign_key_violations"]:
        raise AdminError("foreign key violations differ from the source database")
    return counts


def verify_export(export_dir: str | Path) -> dict[str, int]:
    """Rebuild the export in memory and check it against the manifest; returns the row counts."""
    folder = Path(export_dir)
    manifest = _load_manifest(folder)
    conn = sqlite3.connect(":memory:")
    try:
        try:
            _build(conn, folder, manifest)
        except (sqlite3.Error, OSError) as exc:
            raise AdminError(f"export cannot be loaded: {exc}") from exc
        return _check(conn, manifest)
    finally:
        conn.close()


def rebuild_database(export_dir: str | Path, db_path: str | Path) -> Path:
    """Create a NEW database from an export, verify it, then move it to `db_path`.

    Raises:
        AdminError: `db_path` already exists, the export is incomplete, or verification fails.
            In every failure case no file is left at `db_path`.
    """
    folder, target = Path(export_dir), Path(db_path)
    if target.exists():
        raise AdminError(f"target exists, refusing to overwrite: {target}")
    manifest = _load_manifest(folder)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    partial.unlink(missing_ok=True)
    conn = sqlite3.connect(partial)
    try:
        try:
            _build(conn, folder, manifest)
            _check(conn, manifest)
        except (sqlite3.Error, OSError) as exc:
            raise AdminError(f"export cannot be loaded: {exc}") from exc
    except AdminError:
        conn.close()
        partial.unlink(missing_ok=True)
        raise
    conn.close()
    partial.replace(target)
    return target


def status(db_path: str | Path) -> dict:
    """Tables with row counts, user_version, journal mode and size of a database (read-only)."""
    path = Path(db_path)
    if not path.is_file():
        raise AdminError(f"database not found: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        objects = _schema_objects(conn)
        virtual = _virtual_tables(objects)
        tables = {n: conn.execute(f"SELECT COUNT(*) FROM {_ident(n)}").fetchone()[0]
                  for k, n, _s in objects if k == "table" and not _is_shadow(n, virtual)}
        return {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "user_version": conn.execute("PRAGMA user_version").fetchone()[0],
            "journal_mode": conn.execute("PRAGMA journal_mode").fetchone()[0],
            "tables": tables,
        }
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    """Command line entry point; returns the process exit status (1 on AdminError)."""
    parser = argparse.ArgumentParser(description="Portable export and rebuild of a SQLite database.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status", help="tables, row counts, user_version")
    s.add_argument("--db", default="domain_model", help="domain_model | intelligence | path")
    e = sub.add_parser("export", help="write schema.sql, data/*.sql and manifest.json")
    e.add_argument("--db", default="domain_model", help="domain_model | intelligence | path")
    e.add_argument("--out", required=True, help="output folder (absent or empty)")
    v = sub.add_parser("verify-export", help="rebuild in memory and compare with the manifest")
    v.add_argument("export_dir")
    r = sub.add_parser("rebuild", help="create a NEW database from an export (never overwrites)")
    r.add_argument("export_dir")
    r.add_argument("--db", required=True, help="path of the new database file")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "status":
            print(json.dumps(status(resolve_db(args.db)), indent=2))
        elif args.cmd == "export":
            m = export_database(resolve_db(args.db), args.out)
            print(f"exported {len(m['tables'])} tables to {args.out} (user_version {m['user_version']})")
        elif args.cmd == "verify-export":
            counts = verify_export(args.export_dir)
            print(f"export ok: {len(counts)} tables, {sum(counts.values())} rows, matches manifest")
        else:
            print(f"rebuilt and verified: {rebuild_database(args.export_dir, resolve_db(args.db))}")
    except (AdminError, BackupError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
