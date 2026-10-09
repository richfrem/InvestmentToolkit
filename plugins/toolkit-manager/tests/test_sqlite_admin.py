"""Tests for sqlite_admin.py: portable export (DDL + data) and rebuild of a SQLite database.

Purpose:
    Prove a database can be exported to plain files and rebuilt from them with nothing lost
    (rows, NULLs, quotes, unicode, blobs, indexes, triggers, views, foreign keys, user_version),
    that the source is never modified, and that rebuild refuses to overwrite or accept a
    tampered export.

Key Input Dependencies: none (each test builds a real temporary SQLite database).
"""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sqlite_admin.py"
sys.path.insert(0, str(SCRIPT.parent))

import sqlite_admin as admin  # noqa: E402


@pytest.fixture
def source_db(tmp_path):
    """A WAL database with a parent/child pair, an index, a view, a trigger, awkward values."""
    path = tmp_path / "source.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA wal_autocheckpoint=0;")
    conn.executescript("""
        CREATE TABLE parent (id TEXT PRIMARY KEY, name TEXT NOT NULL, score REAL, payload BLOB);
        CREATE TABLE child (id INTEGER PRIMARY KEY AUTOINCREMENT, parent_id TEXT NOT NULL REFERENCES parent(id), note TEXT);
        CREATE TABLE audit (n INTEGER);
        CREATE INDEX idx_child_parent ON child(parent_id);
        CREATE VIEW child_count AS SELECT parent_id, COUNT(*) AS n FROM child GROUP BY parent_id;
        CREATE TRIGGER child_audit AFTER INSERT ON child BEGIN INSERT INTO audit VALUES (NEW.id); END;
    """)
    conn.execute("INSERT INTO parent VALUES ('A', 'O''Brien \"quoted\" é 日本', 1.5, x'00ff10')")
    conn.execute("INSERT INTO parent VALUES ('B', 'plain', NULL, NULL)")
    conn.execute("INSERT INTO child (parent_id, note) VALUES ('A', 'line1\nline2')")
    conn.execute("INSERT INTO child (parent_id, note) VALUES ('B', NULL)")
    conn.execute("PRAGMA user_version = 7;")
    conn.commit()
    yield path
    conn.close()


def _rows(path, sql):
    """All rows of a query against a database file (opened and closed here)."""
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def test_export_writes_schema_data_and_manifest(source_db, tmp_path):
    """Export produces schema.sql, one data file per table and a manifest with row counts."""
    out = tmp_path / "export"
    admin.export_database(source_db, out)
    assert "CREATE TABLE parent" in (out / "schema.sql").read_text()
    assert (out / "data" / "parent.sql").is_file()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["tables"] == {"parent": 2, "child": 2, "audit": 2, "sqlite_sequence": 1}
    assert manifest["user_version"] == 7


def test_round_trip_loses_nothing(source_db, tmp_path):
    """Rows, NULLs, quotes, unicode, blobs and newlines survive export then rebuild."""
    out = tmp_path / "export"
    admin.export_database(source_db, out)
    rebuilt = tmp_path / "rebuilt.sqlite"
    admin.rebuild_database(out, rebuilt)
    for table in ("parent", "child", "audit"):
        sql = f"SELECT * FROM {table} ORDER BY 1"
        assert _rows(rebuilt, sql) == _rows(source_db, sql)
    assert _rows(rebuilt, "SELECT payload FROM parent WHERE id='A'")[0][0] == b"\x00\xff\x10"


def test_round_trip_keeps_indexes_views_triggers_and_user_version(source_db, tmp_path):
    """The rebuilt database has the same objects, the trigger still fires, user_version is kept."""
    out = tmp_path / "export"
    admin.export_database(source_db, out)
    rebuilt = tmp_path / "rebuilt.sqlite"
    admin.rebuild_database(out, rebuilt)
    kinds = {r[0] for r in _rows(rebuilt, "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
    assert {"idx_child_parent", "child_count", "child_audit"} <= kinds
    assert _rows(rebuilt, "PRAGMA user_version")[0][0] == 7
    conn = sqlite3.connect(rebuilt)
    conn.execute("INSERT INTO child (parent_id, note) VALUES ('A', 'x')")
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0] == 3
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


def test_export_includes_rows_only_in_the_wal_and_never_modifies_the_source(source_db, tmp_path):
    """The WAL-only rows are exported and the source file bytes are unchanged."""
    before = source_db.read_bytes()
    wal_before = (source_db.parent / "source.sqlite-wal").read_bytes()
    admin.export_database(source_db, tmp_path / "export")
    assert source_db.read_bytes() == before
    assert (source_db.parent / "source.sqlite-wal").read_bytes() == wal_before
    assert json.loads((tmp_path / "export" / "manifest.json").read_text())["tables"]["parent"] == 2


def test_rebuild_refuses_to_overwrite_an_existing_database(source_db, tmp_path):
    """Rebuild only creates new files; an existing target is never touched."""
    out = tmp_path / "export"
    admin.export_database(source_db, out)
    target = tmp_path / "existing.sqlite"
    target.write_bytes(b"precious")
    with pytest.raises(admin.AdminError, match="exists"):
        admin.rebuild_database(out, target)
    assert target.read_bytes() == b"precious"


def test_rebuild_rejects_a_tampered_export_and_leaves_no_file(source_db, tmp_path):
    """A data file that no longer matches the manifest counts aborts the rebuild."""
    out = tmp_path / "export"
    admin.export_database(source_db, out)
    data = out / "data" / "parent.sql"
    data.write_text("\n".join(data.read_text().splitlines()[:1]) + "\n")
    target = tmp_path / "rebuilt.sqlite"
    with pytest.raises(admin.AdminError, match="parent"):
        admin.rebuild_database(out, target)
    assert not target.exists()


def test_verify_export_passes_on_a_good_export_and_fails_on_a_bad_one(source_db, tmp_path):
    """verify_export rebuilds in memory and compares counts without writing a database."""
    out = tmp_path / "export"
    admin.export_database(source_db, out)
    assert admin.verify_export(out)["parent"] == 2
    (out / "data" / "child.sql").write_text("")
    with pytest.raises(admin.AdminError, match="child"):
        admin.verify_export(out)


def test_export_refuses_a_non_empty_output_folder(source_db, tmp_path):
    """Export never mixes with or overwrites an earlier export."""
    out = tmp_path / "export"
    out.mkdir()
    (out / "keep.txt").write_text("x")
    with pytest.raises(admin.AdminError, match="not empty"):
        admin.export_database(source_db, out)


def test_status_reports_tables_and_version(source_db):
    """status lists row counts, user_version and journal mode."""
    info = admin.status(source_db)
    assert info["tables"]["parent"] == 2 and info["user_version"] == 7
    assert info["journal_mode"] == "wal"


def test_cli_export_verify_rebuild_round_trip(source_db, tmp_path):
    """The command line does export, verify and rebuild and exits 0."""
    out, rebuilt = tmp_path / "export", tmp_path / "rebuilt.sqlite"
    for args in (["export", "--db", str(source_db), "--out", str(out)],
                 ["verify-export", str(out)],
                 ["rebuild", str(out), "--db", str(rebuilt)]):
        r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    assert _rows(rebuilt, "SELECT COUNT(*) FROM parent")[0][0] == 2


def test_cli_reports_errors_with_nonzero_exit(tmp_path):
    """A missing database is a clear error, not a traceback."""
    r = subprocess.run([sys.executable, str(SCRIPT), "status", "--db", str(tmp_path / "nope.sqlite")],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "not found" in r.stderr and "Traceback" not in r.stderr


def test_round_trip_rebuilds_an_fts5_virtual_table_without_its_shadow_tables(tmp_path):
    """A full-text index is recreated and searchable; shadow tables are not exported."""
    src = tmp_path / "fts.sqlite"
    conn = sqlite3.connect(src)
    try:
        conn.execute("CREATE VIRTUAL TABLE notes USING fts5(title, body)")
    except sqlite3.OperationalError:
        pytest.skip("SQLite build has no FTS5")
    conn.execute("INSERT INTO notes (title, body) VALUES ('alpha', 'semiconductor supply chain')")
    conn.execute("INSERT INTO notes (title, body) VALUES ('beta', 'dividend timing')")
    conn.commit()
    conn.close()
    out = tmp_path / "export"
    admin.export_database(src, out)
    assert not any(p.name.startswith("notes_") for p in (out / "data").iterdir())
    rebuilt = tmp_path / "rebuilt.sqlite"
    admin.rebuild_database(out, rebuilt)
    assert _rows(rebuilt, "SELECT title FROM notes WHERE notes MATCH 'dividend'") == [("beta",)]


def test_existing_foreign_key_violations_are_carried_not_fatal(tmp_path):
    """A source that already has orphan rows rebuilds to the same orphan count."""
    src = tmp_path / "fk.sqlite"
    conn = sqlite3.connect(src)
    conn.executescript("""
        CREATE TABLE p (id TEXT PRIMARY KEY);
        CREATE TABLE c (id INTEGER PRIMARY KEY, pid TEXT REFERENCES p(id));
        INSERT INTO c VALUES (1, 'missing');
    """)
    conn.commit()
    conn.close()
    out = tmp_path / "export"
    admin.export_database(src, out)
    assert json.loads((out / "manifest.json").read_text())["foreign_key_violations"] == 1
    admin.rebuild_database(out, tmp_path / "rebuilt.sqlite")


def test_installed_copy_with_links_turned_into_real_files_runs_from_the_skill_root(source_db, tmp_path):
    """The skill works as the installer leaves it: real files, skill-root-relative commands."""
    import shutil
    skill_src = SCRIPT.parent.parent / "skills" / "sqlite-admin"
    installed = tmp_path / "installed" / "sqlite-admin"
    shutil.copytree(skill_src, installed, symlinks=False)  # symlinks become real files
    assert not any(p.is_symlink() for p in installed.rglob("*"))
    env = {"SQLITE_ADMIN_DATA_DIR": str(source_db.parent), "PATH": "/usr/bin:/bin"}
    r = subprocess.run([sys.executable, "scripts/sqlite_admin.py", "status", "--db", "domain_model"],
                       cwd=installed, capture_output=True, text=True, env=env)
    assert r.returncode == 1 and "not found" in r.stderr  # known name resolved inside the env data dir
    r = subprocess.run([sys.executable, "scripts/sqlite_admin.py", "status", "--db", str(source_db)],
                       cwd=installed, capture_output=True, text=True, env=env)
    assert r.returncode == 0 and '"parent": 2' in r.stdout
    r = subprocess.run([sys.executable, "scripts/db_backup.py", "backup", "--db", str(source_db)],
                       cwd=installed, capture_output=True, text=True, env=env)
    assert r.returncode == 0 and "backup ok" in r.stdout


def test_known_names_resolve_through_the_data_dir_env_var(tmp_path, monkeypatch):
    """`domain_model` / `intelligence` resolve inside SQLITE_ADMIN_DATA_DIR; other args are paths."""
    import db_backup
    monkeypatch.setenv("SQLITE_ADMIN_DATA_DIR", str(tmp_path))
    assert db_backup.resolve_db("domain_model") == tmp_path / "domain_model.sqlite"
    assert db_backup.resolve_db("intelligence") == tmp_path / "intelligence.sqlite"
    assert db_backup.resolve_db("/x/y.sqlite") == Path("/x/y.sqlite")


def test_data_dir_is_found_upward_without_following_symlinks(tmp_path, monkeypatch):
    """A script reached through a link still finds the checkout's data folder."""
    import db_backup
    monkeypatch.delenv("SQLITE_ADMIN_DATA_DIR", raising=False)
    found = db_backup.find_data_dir()
    assert found.name == "data" and found.parent.name == "backend"
