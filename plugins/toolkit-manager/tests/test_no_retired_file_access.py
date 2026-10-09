"""Guard: no code reads, writes or stats a retired portfolio data file.

Purpose:
    Fail the build when Python, TypeScript or JavaScript touches a retired portfolio file.

Portfolio data lives only in domain_model.sqlite. This test runs audit_sqlite_usage over the
repository and fails on any live reader/writer, vestigial parameter or unused path constant for
the retired files, except the frozen migration tools. TypeScript/JavaScript sources are checked
for the same file names and the path constants that pointed at them.

Key Input Dependencies:
    - The repository tree (plugins/, investment_screener/, tradingview-cdp/)
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/toolkit-manager/scripts"))

import audit_sqlite_usage as audit  # noqa: E402


def _format(f):
    """Format."""
    kinds = sorted({k for k, *_ in f["uses"] if k in audit.VIOLATION_VERDICTS})
    return f"{f['file']}:{f['line']} {f['legacy']} {kinds}"


def test_no_python_access_to_retired_files():
    """No python access to retired files."""
    found = audit.run(REPO_ROOT, False)
    violations = audit.python_violations(found)
    assert not violations, "Python access to retired files:\n" + "\n".join(sorted({_format(f) for f in violations}))


def test_no_typescript_access_to_retired_files():
    """No typescript access to retired files."""
    hits = audit.ts_violations(REPO_ROOT)
    assert not hits, "TypeScript/JavaScript references to retired files:\n" + "\n".join(f"{f}:{n} {t}" for f, n, t in hits)


def test_no_document_describes_a_retired_file_as_current():
    """Docs, skills, evals and templates may name a retired file only as history (see audit_sqlite_usage.DOC_HISTORY_*)."""
    hits = audit.doc_violations(REPO_ROOT)
    assert not hits, "Documents that name a retired file without saying it is retired:\n" + "\n".join(f"{f}:{n} {t}" for f, n, t in hits)


def test_doc_check_allows_history_words_and_history_files(tmp_path):
    """A line saying the file is retired passes; a present-tense instruction fails; history folders are skipped."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "good.md").write_text("`portfolio.json` is retired; use SQLite.\nformerly read target-portfolio.json\n")
    (tmp_path / "docs" / "bad.md").write_text("Run the tool, it reads portfolio.json and writes trade-log.json.\n")
    (tmp_path / "docs" / "plans").mkdir()
    (tmp_path / "docs" / "plans" / "plan.md").write_text("portfolio.json is read by x\n")
    hits = audit.doc_violations(tmp_path)
    assert sorted({f for f, _n, _t in hits}) == ["docs/bad.md"]


def test_doc_check_window_covers_wrapped_sentence(tmp_path):
    """A history word on the adjacent line covers a sentence wrapped across two lines."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "wrapped.md").write_text("The file `portfolio.json`\nis retired and unused.\n")
    (tmp_path / "docs" / "far.md").write_text("The file `portfolio.json` holds the data.\n\n\nThis is retired.\n")
    hits = audit.doc_violations(tmp_path)
    assert sorted({f for f, _n, _t in hits}) == ["docs/far.md"]
