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
