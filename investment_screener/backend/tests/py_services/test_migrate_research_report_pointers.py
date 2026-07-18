import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from migrate_research_report_pointers import migrate_pointers  # noqa: E402

def test_migrate_pointers_rewrites_all_versions_to_canonical(tmp_path):
    projections_dir = tmp_path / "projections"
    projections_dir.mkdir()
    (projections_dir / "PLTR.json").write_text(json.dumps([
        {"version": 1, "researchReport": "PLTR_2026-05-01.md"},
        {"version": 2, "researchReport": "PLTR_2026-07-02.md"},
        {"version": 3},  # no researchReport field — must be left untouched
    ]))

    result = migrate_pointers(str(projections_dir))

    updated = json.loads((projections_dir / "PLTR.json").read_text())
    assert updated[0]["researchReport"] == "PLTR.summary.md"
    assert updated[1]["researchReport"] == "PLTR.summary.md"
    assert "researchReport" not in updated[2]
    assert result["rewritten_count"] == 2
