import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment  # noqa: E402
from domain_model.investment_note_repository import (  # noqa: E402
    add_note,
    list_notes,
    get_latest_note,
)


def _seed_investment(conn):
    return resolve_investment(conn, "IREN", asset_class="EQUITY", currency="USD")


def test_add_note_appends_does_not_replace(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    add_note(conn, investment_id, "2026-01-01T00:00:00Z", "First rationale entry.")
    add_note(conn, investment_id, "2026-03-01T00:00:00Z", "Second rationale entry.")
    notes = list_notes(conn, investment_id)
    assert len(notes) == 2


def test_list_notes_ordered_by_date_ascending(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    add_note(conn, investment_id, "2026-03-01T00:00:00Z", "Later entry.")
    add_note(conn, investment_id, "2026-01-01T00:00:00Z", "Earlier entry.")
    notes = list_notes(conn, investment_id)
    assert notes[0]["body"] == "Earlier entry."
    assert notes[1]["body"] == "Later entry."


def test_get_latest_note_returns_most_recent(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    add_note(conn, investment_id, "2026-01-01T00:00:00Z", "Earlier entry.")
    add_note(conn, investment_id, "2026-03-01T00:00:00Z", "Later entry.")
    latest = get_latest_note(conn, investment_id)
    assert latest["body"] == "Later entry."


def test_get_latest_note_returns_none_when_no_notes(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    assert get_latest_note(conn, investment_id) is None


def test_migrated_legacy_rationale_note_type(tmp_path):
    conn = initialize_db(str(tmp_path / "test.sqlite"))
    investment_id = _seed_investment(conn)
    add_note(
        conn, investment_id, "2026-07-19T00:00:00Z",
        "DCF: INITIATE | FV $285 vs $421 price | -32.4% upside.",
        note_type="MIGRATED_LEGACY_RATIONALE", source="target-portfolio.json migration",
    )
    notes = list_notes(conn, investment_id)
    assert notes[0]["note_type"] == "MIGRATED_LEGACY_RATIONALE"
