"""Tests for audit_sqlite_usage.py.

Purpose:
    Each fixture case classifies as expected, and the guard helpers separate allowed
    migration tools from violations.

Key Input Dependencies: none (all fixtures are written to tmp_path).
"""
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import audit_sqlite_usage as audit  # noqa: E402


def _run_fixture(tmp_path, src):
    """Run fixture."""
    (tmp_path / "plugins").mkdir()
    for name, text in (src if isinstance(src, dict) else {"m.py": src}).items():
        (tmp_path / "plugins" / name).write_text(text)
    return audit.run(tmp_path, False)


@pytest.mark.parametrize("name", sorted(audit.FIXTURES))
def test_fixture_classification(tmp_path, name, monkeypatch):
    """Fixture classification."""
    monkeypatch.setattr(audit, "IGNORES_PATH", {"load_portfolio_state"})
    src, want = audit.FIXTURES[name]
    verdicts = {f["verdict"] for f in _run_fixture(tmp_path, src)}
    assert want in verdicts, f"{name}: want {want}, got {sorted(verdicts)}"


def test_self_test_passes():
    """Self test passes."""
    assert audit.self_test() is True


def test_migration_tool_is_not_a_violation(tmp_path):
    """Migration tool is not a violation."""
    found = _run_fixture(tmp_path, {"migrate_portfolio_to_sqlite.py": "def f():\n    return open('portfolio.json').read()\n"})
    assert {f["verdict"] for f in found} == {"READ_CONTENT"}
    assert audit.python_violations(found) == []


def test_other_reader_is_a_violation(tmp_path):
    """Other reader is a violation."""
    found = _run_fixture(tmp_path, {"report.py": "def f():\n    return open('portfolio.json').read()\n"})
    assert [f["file"] for f in audit.python_violations(found)] == ["plugins/report.py"]


@pytest.mark.parametrize("verdict_src", [
    "P = 'portfolio.json'\ndef f():\n    return 1\n",
    "P = 'portfolio.json'\ndef load_portfolio_state(p): pass\ndef f(path=None):\n    return load_portfolio_state(path or P)\n",
    "import os\nP = 'portfolio.json'\ndef age():\n    return os.path.getmtime(P)\n",
])
def test_unused_vestigial_and_stat_are_violations(tmp_path, verdict_src, monkeypatch):
    """Unused vestigial and stat are violations."""
    monkeypatch.setattr(audit, "IGNORES_PATH", {"load_portfolio_state"})
    assert audit.python_violations(_run_fixture(tmp_path, verdict_src))


def test_messages_and_name_lists_are_not_violations(tmp_path):
    """Messages and name lists are not violations."""
    found = _run_fixture(tmp_path, "NAMES = {'portfolio.json'}\ndef f():\n    print('portfolio.json not found')\n")
    assert audit.python_violations(found) == []


def test_ts_violations_flags_retired_names_and_skips_tests(tmp_path):
    """Ts violations flags retired names and skips tests."""
    src = tmp_path / "investment_screener/backend/src"
    src.mkdir(parents=True)
    (src / "a.ts").write_text("const x = readPortfolio();\nconst ok = 1;\n")
    (src / "b.ts").write_text("import { PORTFOLIO_FILE } from './paths';\n")
    (src / "a.test.ts").write_text("readPortfolio();\n")
    hits = audit.ts_violations(tmp_path)
    assert sorted((f, n) for f, n, _ in hits) == [
        ("investment_screener/backend/src/a.ts", 1),
        ("investment_screener/backend/src/b.ts", 1),
    ]


def test_no_function_is_assumed_to_ignore_its_path_by_default():
    """The path-ignoring list is empty: load_portfolio_state now opens the database path it is given."""
    assert audit.IGNORES_PATH == set()
