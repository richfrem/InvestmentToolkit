"""Tests for build_consumer_inventory.py — inverts the JSON discovery audit's
per-file producer/consumer/doc-reference data into a per-CONSUMER-FILE view
(Task 18 consumer inventory).

Key Input Dependencies: none (all tests build a synthetic discovery-audit-shaped dict).
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from build_consumer_inventory import (  # noqa: E402
    build_consumer_inventory,
    classify_consumer,
    render_inventory_md,
)


def _discovery_result(files):
    return {"generated_at": "2026-07-18T00:00:00Z", "files": files, "references": []}


def _file_entry(path, classification, producers=None, consumers=None, doc_refs=None):
    return {
        "path": path,
        "classification": classification,
        "known_producers": producers or [],
        "known_consumers": consumers or [],
        "doc_references": doc_refs or [],
    }


def test_build_consumer_inventory_inverts_producer_and_consumer_refs():
    files = [
        _file_entry(
            "investment_screener/backend/data/ta-sweep-results.json",
            "MIGRATE_TO_INTELLIGENCE_LEDGER",
            producers=[{"referencing_file": "plugins/tradingview/scripts/ta_sweep_batch.py", "line": 40, "confidence": "exact"}],
            consumers=[{"referencing_file": "plugins/portfolio-advisor/scripts/daily_brief.py", "line": 48, "confidence": "probable"}],
        ),
    ]
    result = build_consumer_inventory(_discovery_result(files))
    consumer_names = {c["consumer_file"] for c in result}

    assert "plugins/tradingview/scripts/ta_sweep_batch.py" in consumer_names
    assert "plugins/portfolio-advisor/scripts/daily_brief.py" in consumer_names


def test_build_consumer_inventory_groups_multiple_json_refs_under_one_consumer():
    files = [
        _file_entry(
            "investment_screener/backend/data/ta-sweep-results.json",
            "MIGRATE_TO_INTELLIGENCE_LEDGER",
            consumers=[{"referencing_file": "shared_script.py", "line": 10, "confidence": "exact"}],
        ),
        _file_entry(
            "investment_screener/backend/data/portfolio.json",
            "ALLOWED_AUTHORITATIVE_JSON",
            consumers=[{"referencing_file": "shared_script.py", "line": 20, "confidence": "exact"}],
        ),
    ]
    result = build_consumer_inventory(_discovery_result(files))
    entry = next(c for c in result if c["consumer_file"] == "shared_script.py")

    assert len(entry["referenced_json_files"]) == 2
    referenced_paths = {r["json_path"] for r in entry["referenced_json_files"]}
    assert "investment_screener/backend/data/ta-sweep-results.json" in referenced_paths
    assert "investment_screener/backend/data/portfolio.json" in referenced_paths


def test_classify_consumer_migration_required_when_any_ref_is_migrate_candidate():
    result = classify_consumer(["MIGRATE_TO_INTELLIGENCE_LEDGER", "ALLOWED_AUTHORITATIVE_JSON"], "some_script.py")
    assert result == "MIGRATION_REQUIRED"


def test_classify_consumer_remains_json_by_design_when_all_refs_allowed():
    result = classify_consumer(["ALLOWED_AUTHORITATIVE_JSON", "ALLOWED_CONFIGURATION_JSON"], "some_script.py")
    assert result == "REMAINS_JSON_BY_DESIGN"


def test_classify_consumer_out_of_scope_when_all_refs_out_of_scope():
    result = classify_consumer(["OUT_OF_SCOPE_FOR_THIS_PHASE"], "some_script.py")
    assert result == "OUT_OF_SCOPE"


def test_classify_consumer_uses_ledger_repository_when_consumer_is_in_intelligence_package():
    result = classify_consumer(["ALLOWED_AUTHORITATIVE_JSON"], "investment_screener/backend/py_services/intelligence/event_repository.py")
    assert result == "USES_LEDGER_REPOSITORY"


def test_classify_consumer_migration_required_wins_over_other_classifications():
    # Priority order: MIGRATION_REQUIRED beats everything else, since it's the
    # most actionable / highest-signal finding for a consumer touching mixed sources.
    result = classify_consumer(
        ["ALLOWED_AUTHORITATIVE_JSON", "OUT_OF_SCOPE_FOR_THIS_PHASE", "MIGRATE_TO_INTELLIGENCE_LEDGER"],
        "mixed_consumer.py",
    )
    assert result == "MIGRATION_REQUIRED"


def test_classify_consumer_unknown_when_no_recognized_classification():
    result = classify_consumer(["UNKNOWN_REQUIRES_REVIEW"], "some_script.py")
    assert result == "UNKNOWN_REQUIRES_REVIEW"


def test_build_consumer_inventory_real_repo_finds_ta_sweep_consumers():
    """Regression test: run against the ACTUAL committed discovery audit output.

    This is the direct successor to the reference-linking bug fix — proves the
    inversion correctly surfaces the same 3 real consumers of ta-sweep-results.json
    that the fixed audit now detects, and correctly classifies them MIGRATION_REQUIRED.
    """
    audit_path = REPO_ROOT / "docs/architecture/json-discovery-audit.json"
    discovery_result = json.loads(audit_path.read_text())

    inventory = build_consumer_inventory(discovery_result)
    by_name = {c["consumer_file"]: c for c in inventory}

    ta_sweep_consumers = [
        c for path, c in by_name.items()
        if "ta_sweep_batch.py" in path or "daily_brief.py" in path or "compute_conviction_scores.py" in path
    ]
    assert len(ta_sweep_consumers) >= 3
    assert all(c["classification"] == "MIGRATION_REQUIRED" for c in ta_sweep_consumers)


def test_doc_only_mentions_are_excluded_from_the_code_consumer_inventory():
    """A file that only MENTIONS a JSON filename in prose (README.md, architecture.md,
    a docstring, etc.) is not a "reader/writer" in Task 18's sense — it never
    calls open()/json.load/json.dump. Including it in the main inventory with
    the same MIGRATION_REQUIRED urgency as a real code consumer is misleading.
    Doc-only mentions must be reported separately, not classified into the
    Task 18 code-consumer taxonomy.
    """
    files = [
        _file_entry(
            "investment_screener/backend/data/ta-sweep-results.json",
            "MIGRATE_TO_INTELLIGENCE_LEDGER",
            consumers=[{"referencing_file": "real_reader.py", "line": 10, "confidence": "exact"}],
            doc_refs=[{"referencing_file": "README.md", "line": 3, "confidence": "mention_only"}],
        ),
    ]
    result = build_consumer_inventory(_discovery_result(files))
    consumer_names = {c["consumer_file"] for c in result}

    assert "real_reader.py" in consumer_names
    assert "README.md" not in consumer_names


def test_render_inventory_md_produces_required_table_columns():
    files = [
        _file_entry(
            "investment_screener/backend/data/ta-sweep-results.json",
            "MIGRATE_TO_INTELLIGENCE_LEDGER",
            consumers=[{"referencing_file": "some_script.py", "line": 5, "confidence": "exact"}],
        ),
    ]
    inventory = build_consumer_inventory(_discovery_result(files))
    md = render_inventory_md(inventory)

    assert "| Consumer | Current data source | Legacy reference? | Target source | Action | Test required | Status |" in md
    assert "some_script.py" in md
