import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model.db_backup import (  # noqa: E402
    BackupError,
    backup_database,
    list_backups,
    restore_database,
    verify_backup,
)


@pytest.fixture
def wal_db(tmp_path):
    """A WAL-mode database whose newest rows live ONLY in the -wal file (no checkpoint)."""
    path = tmp_path / "data.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA wal_autocheckpoint=0;")
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    conn.execute("INSERT INTO t (v) VALUES ('old')")
    conn.commit()
    conn.execute("INSERT INTO t (v) VALUES ('only-in-wal')")
    conn.commit()
    yield path, conn
    conn.close()


def test_backup_captures_rows_that_are_only_in_the_wal_file(wal_db):
    path, _conn = wal_db
    assert (path.parent / "data.sqlite-wal").stat().st_size > 0
    out = backup_database(path)
    copy = sqlite3.connect(out)
    assert [r[0] for r in copy.execute("SELECT v FROM t ORDER BY id")] == ["old", "only-in-wal"]
    copy.close()
    # A naive file copy of the main file alone would have lost the second row; ours is
    # one self-contained file with no sidecars.
    assert not list(path.parent.glob("backups/*-wal")) and not list(path.parent.glob("backups/*-shm"))


def test_backup_is_verified_and_labelled(wal_db):
    path, _ = wal_db
    out = backup_database(path, label="pre-migration-0002")
    assert out.name.endswith(".pre-migration-0002.sqlite")
    assert verify_backup(out) == 1


def test_invalid_label_is_rejected(wal_db):
    path, _ = wal_db
    with pytest.raises(BackupError, match="invalid label"):
        backup_database(path, label="../evil")


def test_corrupt_backup_fails_verification(tmp_path):
    bad = tmp_path / "bad.sqlite"
    bad.write_bytes(b"this is not a database" * 100)
    with pytest.raises(Exception):
        verify_backup(bad)


def test_prune_keeps_only_the_newest_n(wal_db):
    path, _ = wal_db
    for _ in range(5):
        backup_database(path, keep=3)
    assert len(list_backups(path.parent / "backups", "data")) == 3


def test_restore_requires_confirmation_and_saves_a_safety_copy(wal_db, tmp_path):
    path, conn = wal_db
    good = backup_database(path)
    conn.execute("DELETE FROM t")
    conn.commit()
    conn.close()

    with pytest.raises(BackupError, match="confirm=True"):
        restore_database(good, path, confirm=False)

    safety = restore_database(good, path, confirm=True)
    assert safety is not None and "pre-restore" in safety.name
    restored = sqlite3.connect(path)
    assert restored.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 2
    restored.close()
    # The destroyed state is recoverable from the safety copy.
    assert sqlite3.connect(safety).execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0


def test_missing_database_is_an_error(tmp_path):
    with pytest.raises(BackupError, match="not found"):
        backup_database(tmp_path / "nope.sqlite")
