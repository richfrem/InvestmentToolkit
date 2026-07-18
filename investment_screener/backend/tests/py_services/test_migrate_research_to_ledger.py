import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from migrate_research_to_ledger import scan_dated_files, migrate_to_ledger  # noqa: E402


def test_scan_dated_files_parses_ticker_and_date(tmp_path):
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    (research_dir / "PLTR_2026-07-02.md").write_text("# PLTR notes\nSome research.")
    (research_dir / "PLTR_2026-05-01.md").write_text("# PLTR notes\nOlder research.")
    (research_dir / "PLTR.md").write_text("# canonical, not dated - should be skipped")

    found = scan_dated_files(str(research_dir))
    assert len(found) == 2
    assert {f["ticker"] for f in found} == {"PLTR"}
    assert sorted(f["effective_at"] for f in found) == ["2026-05-01", "2026-07-02"]


def test_migrate_to_ledger_appends_one_event_per_file_and_archives_originals(tmp_path):
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    (research_dir / "PLTR_2026-07-02.md").write_text("# PLTR notes\nSome research.")
    jsonl_path = tmp_path / "observations.jsonl"
    archive_dir = tmp_path / "archive"

    manifest = migrate_to_ledger(str(research_dir), str(jsonl_path), str(archive_dir))

    events = [json.loads(l) for l in jsonl_path.read_text().splitlines()]
    assert len(events) == 1
    assert events[0]["event_type"] == "RESEARCH_IMPORT"
    assert events[0]["ticker"] == "PLTR"
    assert manifest["migrated_count"] == 1

    # Non-destructive: original still readable at its archived location, not deleted outright
    assert (archive_dir / "PLTR_2026-07-02.md").exists()
    assert not (research_dir / "PLTR_2026-07-02.md").exists()
