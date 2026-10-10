"""Tests for audit_file_dependencies.py: every code dependency on a data file is registered, and new ones fail."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "plugins/toolkit-manager/scripts/audit_file_dependencies.py"
sys.path.insert(0, str(SCRIPT.parent))

import audit_file_dependencies as guard  # noqa: E402


def _tree(tmp_path, py=None, ts=None, register=None):
    scripts = tmp_path / "plugins/demo/scripts"
    scripts.mkdir(parents=True)
    for name, text in (py or {}).items():
        (scripts / name).write_text(text)
    if ts:
        src = tmp_path / "investment_screener/backend/src/routes"
        src.mkdir(parents=True)
        for name, text in ts.items():
            (src / name).write_text(text)
    (tmp_path / "docs/architecture").mkdir(parents=True)
    (tmp_path / guard.REGISTER_PATH).write_text(json.dumps({"dependencies": register or []}))
    return tmp_path


def _run(root, *flags):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *flags], capture_output=True, text=True)


def test_the_repository_register_matches_the_code():
    result = _run(REPO_ROOT, "--check")
    assert result.returncode == 0, result.stdout


def test_a_new_python_read_of_a_json_file_fails_the_check(tmp_path):
    root = _tree(tmp_path, py={"load.py": "import json\ndef f():\n    return json.load(open('data/thing.json'))\n"})
    result = _run(root, "--check")
    assert result.returncode == 1 and "NEW" in result.stdout and "load.py" in result.stdout


def test_a_new_python_write_of_a_jsonl_file_fails_the_check(tmp_path):
    root = _tree(tmp_path, py={"save.py": "from pathlib import Path\ndef f(t):\n    Path('x/events.jsonl').write_text(t)\n"})
    assert _run(root, "--check").returncode == 1


def test_a_new_typescript_fs_read_fails_the_check(tmp_path):
    root = _tree(tmp_path, ts={"thing.ts": "import fs from 'fs';\nexport const a = fs.readFileSync('x.json', 'utf-8');\n"})
    result = _run(root, "--check")
    assert result.returncode == 1 and "fs-read" in result.stdout


def test_code_without_file_dependencies_passes(tmp_path):
    root = _tree(tmp_path, py={"pure.py": "def f(conn):\n    return conn.execute('select 1').fetchone()\n"})
    assert _run(root, "--check").returncode == 0


def test_a_registered_dependency_passes_and_a_stale_entry_fails(tmp_path):
    code = {"load.py": "import json\ndef f():\n    return json.load(open('data/thing.json'))\n"}
    entry = {"file": "plugins/demo/scripts/load.py", "kind": "read", "label": "data/thing.json",
             "disposition": "table", "step": "step 6", "note": ""}
    root = _tree(tmp_path / "a", py=code, register=[entry])
    assert _run(root, "--check").returncode == 0
    stale = _tree(tmp_path / "b", py={"pure.py": "x = 1\n"}, register=[entry])
    result = _run(stale, "--check")
    assert result.returncode == 1 and "STALE" in result.stdout


def test_strict_fails_while_a_non_tooling_entry_remains(tmp_path):
    code = {"load.py": "import json\ndef f():\n    return json.load(open('data/thing.json'))\n"}
    entry = {"file": "plugins/demo/scripts/load.py", "kind": "read", "label": "data/thing.json",
             "disposition": "table", "step": "step 6", "note": ""}
    assert _run(_tree(tmp_path / "a", py=code, register=[entry]), "--strict").returncode == 1
    entry["disposition"] = "tooling"
    assert _run(_tree(tmp_path / "b", py=code, register=[entry]), "--strict").returncode == 0
