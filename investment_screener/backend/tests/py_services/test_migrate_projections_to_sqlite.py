import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.migrate_projections_to_sqlite import (  # noqa: E402
    parse_projection_entry,
    migrate_ticker_file,
    run_dry_run,
)
from domain_model.db_client import initialize_db  # noqa: E402


LEGACY_ENTRY = {
    "id": "legacy-1", "ticker": "OLDCO", "version": 2, "source": "AI_AGENT",
    "savedAt": "2026-01-01T00:00:00Z", "fairValue": 100.0, "action": "HOLD",
    "snapshot": {"price": 95.0},
}

CURRENT_ENTRY = {
    "id": "current-1", "ticker": "AAPL", "version": 3, "source": "AI_AGENT",
    "savedAt": "2026-07-01T00:00:00Z",
    "aiThesis": {"fairValue": 190.0, "action": "MAINTAIN", "analyzedAt": "2026-07-01T00:00:00Z",
                 "model": "gemini-2.5-pro", "rationale": "test"},
    "snapshot": {"price": 180.0},
    "scenarios": {
        "bear": {"weight": 0.2, "scenarioPrice": 150.0},
        "base": {"weight": 0.5, "scenarioPrice": 190.0},
        "bull": {"weight": 0.3, "scenarioPrice": 230.0},
    },
}

NO_SCENARIOS_ENTRY = {
    "id": "no-scenarios-1", "ticker": "OLDCO", "version": 1, "source": "USER",
    "savedAt": "2025-06-01T00:00:00Z", "fairValue": 80.0, "action": "MAINTAIN",
    "snapshot": {"price": 82.0},
}

# Third shape variant, confirmed against real data: 2 of 132 real entries (across 82 files in
# investment_screener/backend/data/projections/, IONQ.json and QBTS.json, both version-1 /
# early-May-2026 entries) carry BOTH a top-level fairValue/action AND a nested
# aiThesis.fairValue/action. Each shape's write path (apply_catalyst.py main()) stamps its own
# real timestamp: writing the top-level fairValue/action sets entry["updatedAt"]; writing the
# nested aiThesis fields sets aiThesis["analyzedAt"]. Real IONQ.json has updatedAt
# "2026-05-13T15:02:10Z" (later) vs aiThesis.analyzedAt "2026-05-04T15:09:22Z" (earlier) — its
# own catalystUpdates[0].thesisImpact documents "FV $8.54->$10.24. Action: SELL->SELL.", proving
# the top-level 10.24 is the newer, catalyst-corrected value and aiThesis's 8.54 is stale.
# parse_projection_entry must therefore compare updatedAt vs analyzedAt and prefer whichever is
# genuinely more recent, falling back to "aiThesis wins" only when a timestamp is missing/
# unparseable.
BOTH_SHAPES_CONFLICTING_ENTRY = {
    "id": "both-1", "ticker": "IONQ", "version": 1, "source": "AI_AGENT",
    "savedAt": "2026-05-04T15:09:22Z",
    "fairValue": 10.24, "action": "SELL", "updatedAt": "2026-05-13T15:02:10Z",
    "aiThesis": {"fairValue": 8.54, "action": "SELL", "analyzedAt": "2026-05-04T15:09:22Z",
                 "model": "gemini-2.5-pro", "rationale": "test"},
    "snapshot": {"price": 9.0},
}

# Same both-shapes scenario, but aiThesis was written more recently than the top-level fields
# (the more common real-world direction, e.g. a fresh AI re-analysis after an older manual edit).
BOTH_SHAPES_AI_THESIS_NEWER_ENTRY = {
    "id": "both-2", "ticker": "QBTS", "version": 1, "source": "AI_AGENT",
    "savedAt": "2026-05-04T15:09:22Z",
    "fairValue": 1.0, "action": "HOLD", "updatedAt": "2026-05-01T00:00:00Z",
    "aiThesis": {"fairValue": 0.9, "action": "SELL", "analyzedAt": "2026-05-04T15:09:46Z",
                 "model": "gemini-2.5-pro", "rationale": "test"},
    "snapshot": {"price": 1.1},
}

# Both shapes present but timestamps missing on both sides -> must fall back to the documented
# "aiThesis wins" default rather than crashing or guessing.
BOTH_SHAPES_NO_TIMESTAMPS_ENTRY = {
    "id": "both-3", "ticker": "NOTS", "version": 1, "source": "AI_AGENT",
    "savedAt": "2026-05-04T15:09:22Z",
    "fairValue": 5.0, "action": "HOLD",
    "aiThesis": {"fairValue": 4.0, "action": "SELL",
                 "model": "gemini-2.5-pro", "rationale": "test"},
    "snapshot": {"price": 4.5},
}


def test_parse_projection_entry_handles_legacy_top_level_shape():
    parsed = parse_projection_entry(LEGACY_ENTRY)
    assert parsed["fair_value"] == 100.0
    assert parsed["action"] == "HOLD"


def test_parse_projection_entry_handles_current_nested_ai_thesis_shape():
    parsed = parse_projection_entry(CURRENT_ENTRY)
    assert parsed["fair_value"] == 190.0
    assert parsed["action"] == "MAINTAIN"
    assert parsed["model"] == "gemini-2.5-pro"


def test_parse_projection_entry_handles_missing_scenarios_block():
    parsed = parse_projection_entry(NO_SCENARIOS_ENTRY)
    assert parsed.get("scenarios") in (None, {})


def test_parse_projection_entry_prefers_top_level_when_updated_at_is_newer():
    """Real IONQ.json case: entry["updatedAt"] (2026-05-13) is later than
    aiThesis["analyzedAt"] (2026-05-04), and catalystUpdates[0].thesisImpact documents the
    top-level fairValue as the catalyst-corrected value (8.54 -> 10.24). The newer top-level
    write must win, not a blanket "aiThesis always wins" rule."""
    parsed = parse_projection_entry(BOTH_SHAPES_CONFLICTING_ENTRY)
    assert parsed["fair_value"] == 10.24
    assert parsed["action"] == "SELL"


def test_parse_projection_entry_prefers_ai_thesis_when_analyzed_at_is_newer():
    """When aiThesis.analyzedAt is more recent than the top-level updatedAt, aiThesis must
    win — the precedence rule is timestamp-driven in both directions, not hardcoded."""
    parsed = parse_projection_entry(BOTH_SHAPES_AI_THESIS_NEWER_ENTRY)
    assert parsed["fair_value"] == 0.9
    assert parsed["action"] == "SELL"


def test_parse_projection_entry_falls_back_to_ai_thesis_when_timestamps_missing():
    """When both shapes are present but neither timestamp is available to compare, fall back
    to the documented default of preferring aiThesis rather than crashing or guessing."""
    parsed = parse_projection_entry(BOTH_SHAPES_NO_TIMESTAMPS_ENTRY)
    assert parsed["fair_value"] == 4.0
    assert parsed["action"] == "SELL"


def test_migrate_ticker_file_against_in_memory_db():
    conn = initialize_db(":memory:")
    result = migrate_ticker_file(conn, "AAPL", [CURRENT_ENTRY])
    assert result["versions_migrated"] == 1
    assert result["scenarios_migrated"] == 3
    assert result["errors"] == []


def test_migrate_ticker_file_with_no_scenarios_reports_zero_not_error():
    conn = initialize_db(":memory:")
    result = migrate_ticker_file(conn, "OLDCO", [NO_SCENARIOS_ENTRY])
    assert result["versions_migrated"] == 1
    assert result["scenarios_migrated"] == 0
    assert result["errors"] == []


def test_run_dry_run_against_real_fixture_directory(tmp_path):
    ticker_file = tmp_path / "AAPL.json"
    ticker_file.write_text('[' + str(CURRENT_ENTRY).replace("'", '"') + ']')
    report = run_dry_run(tmp_path)
    assert report["total_files"] == 1
    assert report["total_versions"] >= 1


def test_run_dry_run_reports_per_file_error_for_non_dict_array_element(tmp_path):
    """A malformed file whose top-level array contains a non-dict element (e.g. a bare
    string) must not crash run_dry_run's shape-tally loop with an uncaught AttributeError.
    It must instead be reported as a per-file error, like any other bad-data case."""
    ticker_file = tmp_path / "BADCO.json"
    ticker_file.write_text('["not-a-dict-entry"]')

    report = run_dry_run(tmp_path)

    assert report["total_files"] == 1
    assert any("BADCO.json" in err for err in report["file_errors"])
