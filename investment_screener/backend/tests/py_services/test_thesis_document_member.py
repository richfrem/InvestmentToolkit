"""Tests: thesis document membership table, repository and the one-time import from the document tables."""
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))

import pytest  # noqa: E402

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.thesis_document_member_repository import list_members, replace_members  # noqa: E402
from import_thesis_members import import_members, parse_members  # noqa: E402

DOC = """# Thesis

**Active Positions**

| Ticker | Shares | Actual% | Target% | Gap | Action | Entry Price |
|--------|--------|---------|---------|-----|--------|-------------|
| **PLTR** | 0 | 0.0% | 2.4% | -2.4pp | INITIATE | $109.50 |
| **NVDA** | 4 | 6.0% | 5.0% | +1.0pp | MAINTAIN | — |

**Pending Initiation**

| Ticker | Target% |
|---|---|
| **AMD** | 1.0% |
| ZZZ | not bold, not a ticker row |
"""


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "domain_model.sqlite"
    conn = initialize_db(str(path))
    conn.close()
    return path


def test_parse_members_reads_the_bold_ticker_rows_of_every_table():
    assert parse_members(DOC) == ["AMD", "NVDA", "PLTR"]


def test_replace_members_overwrites_one_document_and_leaves_others(db):
    conn = sqlite3.connect(db)
    replace_members(conn, "ai", ["NVDA", "AMD"])
    replace_members(conn, "robotics", ["TSLA"])
    replace_members(conn, "ai", ["NVDA"])
    assert list_members(conn) == {"NVDA": ["ai"], "TSLA": ["robotics"]}


def test_a_stock_can_belong_to_two_documents(db):
    conn = sqlite3.connect(db)
    replace_members(conn, "ai", ["NVDA"])
    replace_members(conn, "power", ["NVDA"])
    assert list_members(conn) == {"NVDA": ["ai", "power"]}


def test_import_is_dry_run_by_default_and_reports(tmp_path, db):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "ontological_os.md").write_text(DOC)
    (docs / "empty.md").write_text("# Nothing here\n")
    report = import_members(docs, db)
    assert report["documents"] == {"ontological_os": ["AMD", "NVDA", "PLTR"]}
    assert report["no_tickers"] == ["empty"]
    assert report["written"] == 0
    assert list_members(sqlite3.connect(db)) == {}


def test_import_write_stores_members_and_a_rerun_changes_nothing(tmp_path, db):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "ontological_os.md").write_text(DOC)
    first = import_members(docs, db, dry_run=False)
    second = import_members(docs, db, dry_run=False)
    assert first["written"] == 3
    assert second["written"] == 3  # replaced with identical content
    assert list_members(sqlite3.connect(db)) == {"AMD": ["ontological_os"], "NVDA": ["ontological_os"], "PLTR": ["ontological_os"]}
