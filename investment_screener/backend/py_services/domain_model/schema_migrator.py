"""The ONLY code that creates or changes domain_model.sqlite tables.

Schema lives in numbered SQL files under `investment_screener/backend/schema/domain_model/`
(`0001_baseline.sql`, `0002_<name>.sql`, ...). Each file is applied once, inside one
transaction, and recorded in the `schema_migrations` table with a checksum. The newest
applied version is also stored in `PRAGMA user_version` so other processes (the Node
backend) can verify they are talking to a compatible schema without parsing anything.

Rules
-----
* Applied migration files are immutable: an edited file fails the checksum check.
* Add a column/table/index by adding the next numbered file. Never edit an old one.
* Node code does not create or alter tables. It checks `user_version` and fails loudly.
* A populated database is backed up (`db_backup`, label `pre-migration-NNNN`) before any
  pending migration runs.
* A database created before this system existed (tables present, no ledger) is first
  self-healed with the retired additive column list, then compared against the baseline,
  and stamped as version 1 only if they match. A mismatch raises `SchemaError` and the
  file is left untouched.

CLI:  python3 schema_migrator.py [--db PATH] [--status]
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:  # imported as part of the `domain_model` package
    from .db_backup import backup_database
except ImportError:  # run as a script
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from db_backup import backup_database  # type: ignore[no-redef]

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "schema" / "domain_model"
_FILE_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")
_LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    checksum    TEXT NOT NULL,
    applied_at  TEXT NOT NULL
);
"""

# Retired: the additive column list that used to be patched in on every open. Kept only so
# a database file created before the migrator existed can be healed to the baseline shape
# before it is verified and stamped. New columns go in numbered migrations instead.
_LEGACY_ADDITIVE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "projection_version": [
        ("source", "TEXT"),
        ("last_grok_sweep", "TEXT"),
        ("catalyst_updates_json", "TEXT"),
    ],
    "investment": [
        ("sector", "TEXT"),
        ("industry", "TEXT"),
        ("last_deep_analysis_at", "TEXT"),
    ],
    "trade_log_entry": [
        ("tv_order_id", "TEXT"),
    ],
}


class SchemaError(RuntimeError):
    """The database and the migration files disagree in a way that needs a human."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str
    checksum: str


def discover(directory: Path | None = None) -> list[Migration]:
    """Load migration files, validating names, contiguity (1..N) and uniqueness."""
    directory = directory or MIGRATIONS_DIR
    found: list[Migration] = []
    for path in sorted(directory.glob("*.sql")):
        match = _FILE_RE.match(path.name)
        if not match:
            raise SchemaError(f"migration file {path.name!r} must be named NNNN_snake_case.sql")
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        found.append(
            Migration(
                version=int(match.group(1)),
                name=match.group(2),
                sql=text,
                checksum=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            )
        )
    versions = [m.version for m in found]
    if versions != list(range(1, len(versions) + 1)):
        raise SchemaError(f"migration versions must be contiguous from 0001; found {versions}")
    return found


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return (
        conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
        is not None
    )


def _user_tables(conn: sqlite3.Connection) -> list[str]:
    return [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' AND name <> 'schema_migrations'"
        )
    ]


def _fingerprint(conn: sqlite3.Connection) -> dict:
    """Structure that must match between two databases: columns, FKs and indexes."""
    shape: dict = {}
    for table in _user_tables(conn):
        cols = {
            r[1]: (r[2].upper(), r[3], r[4], r[5])
            for r in conn.execute(f'PRAGMA table_info("{table}")')
        }
        fks = sorted((r[2], r[3], r[4]) for r in conn.execute(f'PRAGMA foreign_key_list("{table}")'))
        shape[table] = {"columns": cols, "foreign_keys": fks}
    shape["__indexes__"] = sorted(
        (r[0], r[1])
        for r in conn.execute(
            "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        )
    )
    return shape


def _diff(expected: dict, actual: dict) -> list[str]:
    problems: list[str] = []
    for table in sorted(set(expected) | set(actual)):
        if table not in actual:
            problems.append(f"missing table or index set: {table}")
        elif table not in expected:
            problems.append(f"unexpected table or index set: {table}")
        elif expected[table] != actual[table]:
            if table == "__indexes__":
                problems.append(f"indexes differ: expected {expected[table]}, found {actual[table]}")
                continue
            e, a = expected[table], actual[table]
            for col in sorted(set(e["columns"]) | set(a["columns"])):
                if e["columns"].get(col) != a["columns"].get(col):
                    problems.append(
                        f"{table}.{col}: expected {e['columns'].get(col)}, found {a['columns'].get(col)}"
                    )
            if e["foreign_keys"] != a["foreign_keys"]:
                problems.append(f"{table}: foreign keys differ")
    return problems


def _expected_fingerprint(migrations: list[Migration], up_to: int) -> dict:
    scratch = sqlite3.connect(":memory:")
    try:
        for m in migrations:
            if m.version <= up_to:
                scratch.executescript(m.sql)
        return _fingerprint(scratch)
    finally:
        scratch.close()


_CREATE_RE = re.compile(r"^\s*CREATE\s+(?:UNIQUE\s+)?(TABLE|INDEX)\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", re.I)


def _statements(sql: str) -> list[str]:
    """Split a SQL script into complete statements (comments and blanks dropped)."""
    out, buf = [], ""
    for line in sql.split("\n"):
        if not buf and (not line.strip() or line.lstrip().startswith("--")):
            continue
        buf += line + "\n"
        if sqlite3.complete_statement(buf):
            out.append(buf.strip())
            buf = ""
    return out


def _create_missing_from_baseline(conn: sqlite3.Connection, baseline_sql: str) -> None:
    """Old files lack tables added in later waves; create exactly those, as the retired
    `CREATE TABLE IF NOT EXISTS` code did. Existing objects are never touched."""
    existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    for stmt in _statements(baseline_sql):
        match = _CREATE_RE.match(stmt)
        if match and match.group(2) not in existing:
            conn.execute(stmt)
            existing.add(match.group(2))


def _legacy_self_heal(conn: sqlite3.Connection) -> None:
    for table, columns in _LEGACY_ADDITIVE_COLUMNS.items():
        if not _has_table(conn, table):
            continue
        existing = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
        for column, col_type in columns:
            if column not in existing:
                conn.execute(f'ALTER TABLE "{table}" ADD COLUMN {column} {col_type};')


def _record(conn: sqlite3.Connection, m: Migration) -> None:
    conn.execute(
        "INSERT INTO schema_migrations (version, name, checksum, applied_at) VALUES (?, ?, ?, ?)",
        (m.version, m.name, m.checksum, datetime.now(timezone.utc).isoformat()),
    )


def current_version(conn: sqlite3.Connection) -> int:
    if not _has_table(conn, "schema_migrations"):
        return 0
    row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    return row[0] or 0


def migrate(
    conn: sqlite3.Connection,
    *,
    db_path: str | Path | None = None,
    directory: Path | None = None,
    backup: bool = True,
) -> list[int]:
    """Bring `conn`'s database to the newest schema. Returns the versions applied/stamped.

    `db_path` is needed (and used) only to take the pre-migration backup of a populated,
    file-backed database; in-memory databases are never backed up.
    """
    migrations = discover(directory)
    # The ledger is created only once there is something to record, so refusing to adopt a
    # drifted file really does leave it byte-for-byte as found.
    ledger = (
        {
            r[0]: (r[1], r[2])
            for r in conn.execute("SELECT version, name, checksum FROM schema_migrations")
        }
        if _has_table(conn, "schema_migrations")
        else {}
    )
    by_version = {m.version: m for m in migrations}
    for version, (_name, checksum) in sorted(ledger.items()):
        known = by_version.get(version)
        if known is None:
            raise SchemaError(
                f"database is at migration {version} but no such file exists here: "
                "this checkout is older than the database"
            )
        if known.checksum != checksum:
            raise SchemaError(
                f"migration {version:04d}_{known.name}.sql was edited after it was applied "
                "(checksum mismatch). Restore the file and add a new migration instead."
            )

    done: list[int] = []
    populated = bool(_user_tables(conn))

    if not ledger and populated:
        # Created before the migrator existed. Heal, verify, then adopt as the baseline,
        # all in one transaction: a refusal leaves the file exactly as it was found.
        conn.execute("BEGIN IMMEDIATE")
        try:
            _create_missing_from_baseline(conn, migrations[0].sql)
            _legacy_self_heal(conn)
            problems = _diff(_expected_fingerprint(migrations, 1), _fingerprint(conn))
            if problems:
                raise SchemaError(
                    "existing database does not match 0001_baseline.sql; refusing to adopt it "
                    "(nothing was changed):\n  " + "\n  ".join(problems)
                )
            conn.execute(_LEDGER_DDL)
            _record(conn, migrations[0])
            conn.execute(f"PRAGMA user_version = {migrations[0].version}")
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        ledger[1] = (migrations[0].name, migrations[0].checksum)
        done.append(1)

    pending = [m for m in migrations if m.version not in ledger]
    if pending and populated and backup and db_path and str(db_path) != ":memory:":
        backup_database(db_path, label=f"pre-migration-{pending[0].version:04d}")

    if pending:
        conn.execute(_LEDGER_DDL)
        conn.commit()

    for m in pending:
        # Version and name come from a validated filename; the checksum is hex. Safe to inline.
        script = (
            "BEGIN IMMEDIATE;\n"
            + m.sql
            + f"\nINSERT INTO schema_migrations (version, name, checksum, applied_at) VALUES "
            f"({m.version}, '{m.name}', '{m.checksum}', '{datetime.now(timezone.utc).isoformat()}');\n"
            "COMMIT;\n"
        )
        try:
            conn.executescript(script)
        except Exception as exc:
            if conn.in_transaction:
                conn.rollback()
            raise SchemaError(f"migration {m.version:04d}_{m.name}.sql failed and was rolled back: {exc}") from exc
        conn.execute(f"PRAGMA user_version = {m.version}")
        conn.commit()
        done.append(m.version)

    return done


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply pending domain_model schema migrations.")
    parser.add_argument(
        "--db",
        default=str(Path(__file__).resolve().parents[2] / "data" / "domain_model.sqlite"),
    )
    parser.add_argument("--status", action="store_true", help="show version and pending, change nothing")
    args = parser.parse_args(argv)

    migrations = discover()
    if args.status:
        conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
        at = current_version(conn)
        conn.close()
        pending = [f"{m.version:04d}_{m.name}" for m in migrations if m.version > at]
        print(f"database at version {at}; newest available {migrations[-1].version}; pending: {pending or 'none'}")
        return 0

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        applied = migrate(conn, db_path=args.db)
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    print(f"applied: {applied}" if applied else "schema already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
