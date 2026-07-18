"""Tests for audit_json_usage.py — repo-wide JSON/JSONL discovery audit (Task 12A).

Key Input Dependencies: none (all tests operate on tmp_path fixture repos).
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from audit_json_usage import (  # noqa: E402
    scan_json_files,
    scan_references,
    classify_file,
    run_audit,
    write_reports,
)


def _make_repo(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.json").write_text("{}")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cache.json").write_text("{}")
    return tmp_path


def test_scan_json_files_finds_json_and_jsonl_and_excludes_vendor_dirs(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "data.json").write_text('{"a": 1}\n')
    (repo / "events.jsonl").write_text('{"a": 1}\n{"b": 2}\n')

    found = scan_json_files(str(repo))
    found_names = {f["path"] for f in found}

    assert "data.json" in found_names
    assert "events.jsonl" in found_names
    assert not any("node_modules" in p for p in found_names)
    assert not any("__pycache__" in p for p in found_names)


def test_scan_json_files_captures_metadata(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "events.jsonl").write_text('{"a": 1}\n{"b": 2}\n')

    found = scan_json_files(str(repo))
    entry = next(f for f in found if f["path"] == "events.jsonl")

    assert entry["extension"] == ".jsonl"
    assert entry["line_count"] == 2
    assert entry["size_bytes"] > 0
    assert "sha256" in entry and len(entry["sha256"]) == 64


def test_scan_references_detects_python_read_and_write(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "script.py").write_text(
        "import json\n"
        "def load():\n"
        "    with open('data/portfolio.json') as f:\n"
        "        return json.load(f)\n"
        "def save(x):\n"
        "    with open('data/portfolio.json', 'w') as f:\n"
        "        json.dump(x, f)\n"
    )

    refs = scan_references(str(repo), include_globs=["*.py"])

    ops = {r["operation"] for r in refs if r["referencing_file"] == "script.py"}
    assert "read" in ops
    assert "write" in ops
    assert all("line" in r for r in refs)


def test_scan_references_detects_node_read_and_write(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "route.ts").write_text(
        "import fs from 'fs';\n"
        "const data = fs.readFileSync('data/cache.json');\n"
        "fs.writeFileSync('data/cache.json', payload);\n"
    )

    refs = scan_references(str(repo), include_globs=["*.ts"])
    ops = {r["operation"] for r in refs if r["referencing_file"] == "route.ts"}
    assert "read" in ops
    assert "write" in ops


def test_scan_references_detects_markdown_mentions(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "SKILL.md").write_text("Write results to `data/ta-sweep-results.json`.\n")

    refs = scan_references(str(repo), include_globs=["*.md", "SKILL.md"])
    assert any(r["referencing_file"] == "SKILL.md" for r in refs)


def test_classify_file_defaults_to_unknown_requires_review():
    result = classify_file("some/totally/unrecognized/path/mystery.json", references=[])
    assert result == "UNKNOWN_REQUIRES_REVIEW"


def test_classify_file_recognizes_model_artifact_projections():
    result = classify_file(
        "investment_screener/backend/data/projections/PLTR.json", references=[]
    )
    assert result == "ALLOWED_MODEL_ARTIFACT_JSON"


def test_classify_file_recognizes_separate_domain_ledger():
    result = classify_file("investment_screener/backend/data/predictions.jsonl", references=[])
    assert result == "ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL"


def test_classify_file_recognizes_test_fixture():
    result = classify_file("investment_screener/backend/tests/fixtures/sample.json", references=[])
    assert result == "ALLOWED_TEST_FIXTURE_JSON"


def test_classify_file_recognizes_plugin_manifest():
    assert classify_file("plugins/tradingview/plugin.json", references=[]) == "ALLOWED_CONFIGURATION_JSON"
    assert classify_file("plugins/tradingview/.claude-plugin/plugin.json", references=[]) == "ALLOWED_CONFIGURATION_JSON"
    assert classify_file(".claude-plugin/marketplace.json", references=[]) == "ALLOWED_CONFIGURATION_JSON"


def test_classify_file_recognizes_eval_fixtures():
    assert classify_file("plugins/portfolio-advisor/skills/daily-brief/evals/evals.json", references=[]) == "ALLOWED_TEST_FIXTURE_JSON"
    assert classify_file("plugins/tradingview/agents/evals/ta-guide.json", references=[]) == "ALLOWED_TEST_FIXTURE_JSON"


def test_classify_file_recognizes_templates_and_examples():
    assert classify_file("plugins/portfolio-advisor/assets/templates/target_portfolio_template.json", references=[]) == "ALLOWED_CONFIGURATION_JSON"
    assert classify_file("plugins/stock-valuation/skills/stock_valuation/references/examples/example_NVDA_2026-05-02.json", references=[]) == "ALLOWED_TEST_FIXTURE_JSON"


def test_classify_file_flags_vite_cache_as_archive_candidate():
    result = classify_file("investment_screener/frontend/.vite/deps/_metadata.json", references=[])
    assert result == "ARCHIVE_LEGACY_READ_ONLY"


def test_classify_file_flags_ta_sweep_as_migrate_candidate():
    result = classify_file("investment_screener/backend/data/ta-sweep-results.json", references=[])
    assert result == "MIGRATE_TO_INTELLIGENCE_LEDGER"


def test_classify_file_flags_etf_and_13f_as_out_of_scope():
    assert classify_file("investment_screener/backend/data/etf_analysis/FOTO.json", references=[]) == "OUT_OF_SCOPE_FOR_THIS_PHASE"
    assert classify_file("investment_screener/backend/data/13f/0002045724_index.json", references=[]) == "OUT_OF_SCOPE_FOR_THIS_PHASE"


def test_migrate_candidate_reports_not_migrated_status(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "investment_screener").mkdir()
    (repo / "investment_screener" / "backend").mkdir()
    (repo / "investment_screener" / "backend" / "data").mkdir()
    (repo / "investment_screener" / "backend" / "data" / "ta-sweep-results.json").write_text("{}")

    result = run_audit(str(repo))
    entry = next(f for f in result["files"] if f["path"].endswith("ta-sweep-results.json"))

    assert entry["classification"] == "MIGRATE_TO_INTELLIGENCE_LEDGER"
    assert "NOT_MIGRATED" in entry["migration_status"]


def test_temp_folder_with_no_json_files_reported_as_empty(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "portfolio.json").write_text("{}")

    result = run_audit(str(repo))

    assert result["temp_folder_files"] == []


def test_temp_folder_json_files_are_captured_separately(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "temp").mkdir()
    (repo / "temp" / "scratch.json").write_text("{}")

    result = run_audit(str(repo))

    assert any(f["path"] == "temp/scratch.json" for f in result["temp_folder_files"])


def test_run_audit_does_not_modify_or_delete_any_file(tmp_path):
    repo = _make_repo(tmp_path)
    target = repo / "data.json"
    target.write_text('{"a": 1}\n')
    before_hash = target.read_bytes()

    run_audit(str(repo))

    assert target.exists()
    assert target.read_bytes() == before_hash


def test_write_reports_produces_all_four_required_files(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "portfolio.json").write_text('{"a": 1}\n')
    audits_dir = tmp_path / "audits"

    result = run_audit(str(repo))
    write_reports(result, str(audits_dir))

    assert (audits_dir / "json-discovery-audit.md").exists()
    assert (audits_dir / "json-discovery-audit.json").exists()
    assert (audits_dir / "allowed-json-register.md").exists()
    assert (audits_dir / "allowed-json-register.json").exists()


def test_write_reports_json_discovery_audit_is_valid_json_with_required_keys(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "mystery_unrecognized.json").write_text('{"a": 1}\n')
    audits_dir = tmp_path / "audits"

    result = run_audit(str(repo))
    write_reports(result, str(audits_dir))

    data = json.loads((audits_dir / "json-discovery-audit.json").read_text())
    assert "generated_at" in data
    assert "files" in data
    assert any(
        f["classification"] == "UNKNOWN_REQUIRES_REVIEW"
        for f in data["files"] if f["path"] == "mystery_unrecognized.json"
    )


def test_write_reports_allowed_register_only_contains_allowed_classifications(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "unclassified_mystery.json").write_text('{"a": 1}\n')
    (repo / "investment_screener").mkdir()
    (repo / "investment_screener" / "backend").mkdir()
    (repo / "investment_screener" / "backend" / "data").mkdir()
    (repo / "investment_screener" / "backend" / "data" / "projections").mkdir(parents=True, exist_ok=True)
    (repo / "investment_screener" / "backend" / "data" / "projections" / "PLTR.json").write_text('{}')
    audits_dir = tmp_path / "audits"

    result = run_audit(str(repo))
    write_reports(result, str(audits_dir))

    register = json.loads((audits_dir / "allowed-json-register.json").read_text())
    allowed_paths = {e["path_or_pattern"] for e in register["allowed_files"]}
    assert "unclassified_mystery.json" not in allowed_paths
    assert any("PLTR.json" in p for p in allowed_paths)
