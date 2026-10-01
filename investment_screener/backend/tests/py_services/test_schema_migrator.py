import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

from domain_model import schema_migrator  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.schema_migrator import SchemaError, discover, migrate  # noqa: E402
from legacy_db import make_legacy_db  # noqa: E402


def _write(dir_: Path, name: str, sql: str) -> None:
    (dir_ / name).write_text(sql)


@pytest.fixture
def mig_dir(tmp_path):
    d = tmp_path / "migs"
    d.mkdir()
    _write(d, "0001_base.sql", "CREATE TABLE widget (id INTEGER PRIMARY KEY, label TEXT);\n")
    return d


def test_fresh_database_gets_baseline_ledger_and_user_version(tmp_path):
    conn = initialize_db(str(tmp_path / "fresh.sqlite"))
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
    assert versions == [m.version for m in discover()]
    assert conn.execute("PRAGMA user_version").fetchone()[0] == versions[-1]


def test_initialize_db_is_idempotent(tmp_path):
    path = str(tmp_path / "again.sqlite")
    initialize_db(path).close()
    conn = initialize_db(path)
    assert migrate(conn, db_path=path) == []


def test_pending_migration_applies_once_and_bumps_user_version(tmp_path, mig_dir):
    conn = sqlite3.connect(str(tmp_path / "m.sqlite"))
    assert migrate(conn, directory=mig_dir) == [1]
    _write(mig_dir, "0002_add_col.sql", "ALTER TABLE widget ADD COLUMN size INTEGER;\n")
    assert migrate(conn, directory=mig_dir) == [2]
    assert migrate(conn, directory=mig_dir) == []
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
    assert "size" in {r[1] for r in conn.execute("PRAGMA table_info(widget)")}


def test_failed_migration_rolls_back_completely(tmp_path, mig_dir):
    conn = sqlite3.connect(str(tmp_path / "m.sqlite"))
    migrate(conn, directory=mig_dir)
    _write(
        mig_dir,
        "0002_bad.sql",
        "ALTER TABLE widget ADD COLUMN ok_col INTEGER;\nCREATE TABLE widget (dup INTEGER);\n",
    )
    with pytest.raises(SchemaError, match="rolled back"):
        migrate(conn, directory=mig_dir)
    assert "ok_col" not in {r[1] for r in conn.execute("PRAGMA table_info(widget)")}
    assert conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 1


def test_editing_an_applied_migration_is_refused(tmp_path, mig_dir):
    conn = sqlite3.connect(str(tmp_path / "m.sqlite"))
    migrate(conn, directory=mig_dir)
    _write(mig_dir, "0001_base.sql", "CREATE TABLE widget (id INTEGER PRIMARY KEY, label TEXT, extra TEXT);\n")
    with pytest.raises(SchemaError, match="edited after it was applied"):
        migrate(conn, directory=mig_dir)


def test_database_newer_than_checkout_is_refused(tmp_path, mig_dir):
    conn = sqlite3.connect(str(tmp_path / "m.sqlite"))
    _write(mig_dir, "0002_more.sql", "CREATE TABLE gadget (id INTEGER PRIMARY KEY);\n")
    migrate(conn, directory=mig_dir)
    (mig_dir / "0002_more.sql").unlink()
    with pytest.raises(SchemaError, match="older than the database"):
        migrate(conn, directory=mig_dir)


def test_gap_in_migration_numbers_is_refused(mig_dir):
    _write(mig_dir, "0003_skip.sql", "SELECT 1;\n")
    with pytest.raises(SchemaError, match="contiguous"):
        discover(mig_dir)


def test_bad_filename_is_refused(mig_dir):
    _write(mig_dir, "add-thing.sql", "SELECT 1;\n")
    with pytest.raises(SchemaError, match="must be named"):
        discover(mig_dir)


def test_legacy_file_is_adopted_with_data_intact_and_stamped(tmp_path):
    path = str(tmp_path / "legacy.sqlite")
    make_legacy_db(path)
    raw = sqlite3.connect(path)
    raw.execute(
        "INSERT INTO investment (investment_id, symbol, asset_class, currency, updated_at) "
        "VALUES ('x-1', 'XYZ', 'EQUITY', 'USD', '2026-01-01T00:00:00Z')"
    )
    raw.commit()
    raw.close()

    conn = initialize_db(path)
    assert conn.execute("SELECT symbol FROM investment WHERE investment_id='x-1'").fetchone()[0] == "XYZ"
    assert {"sector", "industry"} <= {r[1] for r in conn.execute("PRAGMA table_info(investment)")}
    assert conn.execute("SELECT MIN(version) FROM schema_migrations").fetchone()[0] == 1


def test_legacy_file_missing_a_whole_table_gets_it_created(tmp_path):
    path = str(tmp_path / "legacy.sqlite")
    make_legacy_db(path)
    raw = sqlite3.connect(path)
    raw.execute("DROP TABLE broker_reported_total")
    raw.commit()
    raw.close()
    conn = initialize_db(path)
    assert conn.execute("SELECT 1 FROM sqlite_master WHERE name='broker_reported_total'").fetchone()


def test_drifted_legacy_file_is_refused_and_left_untouched(tmp_path):
    path = str(tmp_path / "drifted.sqlite")
    make_legacy_db(path)
    raw = sqlite3.connect(path)
    raw.execute("ALTER TABLE account DROP COLUMN base_currency")
    raw.commit()
    before = sorted(r[0] for r in raw.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"))
    raw.close()

    with pytest.raises(SchemaError, match="refusing to adopt"):
        initialize_db(path)

    after_conn = sqlite3.connect(path)
    after = sorted(r[0] for r in after_conn.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"))
    assert after == before, "a refused adoption must not alter the file"
    assert not after_conn.execute("SELECT 1 FROM sqlite_master WHERE name='schema_migrations'").fetchone()


def test_populated_database_is_backed_up_before_a_pending_migration(tmp_path):
    path = tmp_path / "pop.sqlite"
    make_legacy_db(str(path))  # populated, un-stamped
    initialize_db(str(path)).close()
    backups = list((tmp_path / "backups").glob("pop.*.pre-migration-*.sqlite"))
    # Adoption (stamping) is not a schema change, so no backup is needed for it...
    assert backups == []
    # ...but a real pending migration on a populated file must be preceded by one.
    d = tmp_path / "migs"
    d.mkdir()
    base = (Path(schema_migrator.MIGRATIONS_DIR) / "0001_baseline.sql").read_text()
    _write(d, "0001_baseline.sql", base)
    _write(d, "0002_marker.sql", "CREATE TABLE marker (id INTEGER PRIMARY KEY);\n")
    conn = sqlite3.connect(str(path))
    # Ledger holds the real baseline checksum, identical text, so this applies only 0002.
    migrate(conn, db_path=str(path), directory=d)
    found = list((tmp_path / "backups").glob("pop.*.pre-migration-0002.sqlite"))
    assert len(found) == 1
