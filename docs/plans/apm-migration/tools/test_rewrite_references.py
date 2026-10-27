"""Tests for rewrite_references.py using a throwaway git repository.

Layer: docs/plans/apm-migration/tools (retired with the migration).
Key Input Dependencies: git, pytest, PyYAML.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import rewrite_references as rr  # noqa: E402

NAME_COLS = ["kind", "old_id", "old_path", "new_id", "new_path", "hub", "mode", "command", "wave", "policy"]
LEDGER_COLS = ["old_path", "new_path", "action", "notes", "wave", "old_plugin", "old_skill", "new_plugin",
               "new_hub", "new_mode", "scope", "kind", "type", "status"]


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def write(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def make_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


OLD_SCRIPT = "plugins/old-plug/scripts/wacc.py"
NEW_ENGINE = "investment_screener/backend/py_services/wacc.py"
OLD_REF = "plugins/old-plug/references/guide.md"
NEW_REF = "plugins/new-plug/.apm/skills/hub/references/guide.md"
OLD_PENDING = "plugins/old-plug/scripts/maybe.py"


@pytest.fixture()
def repo(tmp_path: Path):
    git(tmp_path, "init", "-q", ".")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    # files at their NEW locations (the move has happened)
    write(tmp_path, NEW_ENGINE, "print('wacc')\n")
    write(tmp_path, NEW_REF, "# guide\nsee [x](other.md)\n")
    write(tmp_path, "plugins/new-plug/.apm/skills/hub/references/other.md", "# other\n")
    write(tmp_path, "plugins/new-plug/apm.yml", "name: new-plug\nversion: 1.0.0\n")
    # consumers
    write(tmp_path, "docs/a.md", f"run `python3 {OLD_SCRIPT}` and read {OLD_REF}.\nAlso {OLD_PENDING} stays.\n")
    write(tmp_path, "tests/t.py", f'P = "{OLD_SCRIPT}"\n')
    write(tmp_path, "docs/handovers/h.md", f"history mentions {OLD_SCRIPT}\n")  # history: untouched
    write(tmp_path, "evolution-log.md", f"- moved {OLD_SCRIPT}\n")               # history: untouched
    write(tmp_path, "investment_screener/backend/data/d.json", json.dumps({"p": OLD_SCRIPT}))  # data boundary
    write(tmp_path, "plugins/new-plug/.apm/skills/hub/SKILL.md", f"hand-authored {OLD_SCRIPT}\n")  # hand-authored
    write(tmp_path, "symlinks.json", json.dumps({"version": 1, "links": [
        {"src": OLD_SCRIPT, "dst": "investment_screener/backend/py_services/wacc.py", "strategy": "symlink"},
        {"src": "plugins/keep/x.py", "dst": "plugins/keep/y.py", "strategy": "symlink"}]}, indent=2) + "\n")
    git(tmp_path, "add", "-A")
    out = tmp_path / "docs/plans/apm-migration"
    out.mkdir(parents=True, exist_ok=True)
    make_csv(out / "name-map.csv", NAME_COLS, [
        {"kind": "plugin", "old_id": "old-plug", "old_path": "plugins/old-plug", "new_id": "new-plug",
         "new_path": "plugins/new-plug", "wave": "1", "policy": "rewrite"},
        {"kind": "script", "old_id": "wacc.py", "old_path": OLD_SCRIPT, "new_id": "wacc.py", "new_path": NEW_ENGINE,
         "wave": "1", "policy": "rewrite"},
        {"kind": "reference", "old_id": "guide.md", "old_path": OLD_REF, "new_id": "guide.md", "new_path": NEW_REF,
         "wave": "1", "policy": "rewrite"},
        {"kind": "script", "old_id": "maybe.py", "old_path": OLD_PENDING, "new_id": "maybe.py",
         "new_path": "plugins/new-plug/.apm/skills/hub/scripts/maybe.py", "wave": "1", "policy": "rewrite"},
    ])
    make_csv(out / "master_migration_inventory.csv", LEDGER_COLS, [
        {"old_path": OLD_SCRIPT, "new_path": NEW_ENGINE, "action": "MOVED_TO_ENGINE", "wave": "1",
         "old_plugin": "old-plug", "new_plugin": "new-plug"},
        {"old_path": OLD_REF, "new_path": NEW_REF, "action": "MOVED_TO_SKILL", "wave": "1",
         "old_plugin": "old-plug", "new_plugin": "new-plug"},
        {"old_path": OLD_PENDING, "new_path": "plugins/new-plug/.apm/skills/hub/scripts/maybe.py",
         "action": "DECISION_PENDING", "wave": "1", "old_plugin": "old-plug", "new_plugin": "new-plug"},
    ])
    return rr.Ctx(tmp_path, out)


def read(ctx: rr.Ctx, rel: str) -> str:
    return (ctx.root / rel).read_text(encoding="utf-8")


def test_scope_rules():
    assert rr.in_scope("docs/a.md") == ""
    assert rr.in_scope("docs/handovers/h.md") == "history"
    assert rr.in_scope("plugins/x/references/evolution-log.md") == "history"
    assert rr.in_scope("investment_screener/backend/data/d.json") == "skip-dir"
    assert rr.in_scope("docs/architecture/json-discovery-audit.json") == "generated"
    assert rr.in_scope("image.png") == "ext"


def test_rewrite_text_respects_boundaries():
    rows = {"plugins/a/x.py": {"new_path": "NEW/x.py"}}
    rx = rr.path_regex(rows)
    new, n = rr.rewrite_text("plugins/a/x.py plugins/a/x.pyc myplugins/a/x.py /abs/plugins/a/x.py.", rows, rx)
    assert n == 2
    assert new == "NEW/x.py plugins/a/x.pyc myplugins/a/x.py /abs/NEW/x.py."


def test_plan_writes_nothing(repo, capsys):
    before = read(repo, "docs/a.md")
    assert rr.cmd_plan(repo, "1", 5) == 0
    assert read(repo, "docs/a.md") == before
    assert "rewrites" in capsys.readouterr().out


def test_apply_requires_yes(repo):
    assert rr.cmd_apply(repo, "1", False) == 2
    assert OLD_SCRIPT in read(repo, "docs/a.md")


def test_apply_rewrites_settled_paths_only_and_skips_protected_files(repo):
    assert rr.cmd_apply(repo, "1", True) == 0
    a = read(repo, "docs/a.md")
    assert NEW_ENGINE in a and NEW_REF in a and OLD_SCRIPT not in a
    assert OLD_PENDING in a                       # DECISION_PENDING is never rewritten
    assert NEW_ENGINE in read(repo, "tests/t.py")
    assert OLD_SCRIPT in read(repo, "docs/handovers/h.md")                           # history untouched
    assert OLD_SCRIPT in read(repo, "evolution-log.md")
    assert OLD_SCRIPT in read(repo, "investment_screener/backend/data/d.json")       # data boundary untouched
    assert OLD_SCRIPT in read(repo, "plugins/new-plug/.apm/skills/hub/SKILL.md")     # hand-authored untouched


def test_symlinks_json_entries_of_the_wave_are_removed(repo):
    rr.cmd_apply(repo, "1", True)
    links = json.loads(read(repo, "symlinks.json"))["links"]
    assert [e["src"] for e in links] == ["plugins/keep/x.py"]
    assert read(repo, "symlinks.json").endswith("}\n")


def test_apply_is_idempotent(repo, capsys):
    rr.cmd_apply(repo, "1", True)
    snapshot = {f: read(repo, f) for f in ("docs/a.md", "tests/t.py", "symlinks.json")}
    rr.cmd_rollback(repo, "1")
    rr.cmd_apply(repo, "1", True)
    rr.cmd_rollback(repo, "1")
    rr.cmd_apply(repo, "1", True)
    assert {f: read(repo, f) for f in snapshot} == snapshot
    # a second plan after apply finds nothing left to do
    capsys.readouterr()
    rr.cmd_plan(repo, "1", 5)
    assert "wave 1: 0 rewrites" in capsys.readouterr().out


def test_rollback_restores_originals(repo):
    originals = {f: read(repo, f) for f in ("docs/a.md", "tests/t.py", "symlinks.json")}
    rr.cmd_apply(repo, "1", True)
    assert rr.cmd_rollback(repo, "1") == 0
    assert {f: read(repo, f) for f in originals} == originals
    assert rr.cmd_rollback(repo, "1") == 1       # nothing left to roll back


def test_apply_refuses_when_a_backup_exists(repo):
    rr.cmd_apply(repo, "1", True)
    assert rr.cmd_apply(repo, "1", True) == 2


def test_verify_fails_before_and_passes_after(repo, capsys):
    assert rr.cmd_verify(repo, "1") == 1
    out = capsys.readouterr().out
    assert "stale path" in out and "docs/a.md" in out
    rr.cmd_apply(repo, "1", True)
    # the hand-authored hub file still names an old path: verify must flag it for a human
    assert rr.cmd_verify(repo, "1") == 1
    assert "SKILL.md" in capsys.readouterr().out
    write(repo.root, "plugins/new-plug/.apm/skills/hub/SKILL.md", "fixed by hand\n")
    git(repo.root, "add", "-A")
    assert rr.cmd_verify(repo, "1") == 0


def test_verify_flags_symlinks_and_broken_links_and_syntax(repo, capsys):
    rr.cmd_apply(repo, "1", True)
    write(repo.root, "plugins/new-plug/.apm/skills/hub/SKILL.md", "ok\n")
    write(repo.root, "plugins/new-plug/.apm/skills/hub/references/broken.md", "[gone](missing.md)\n")
    write(repo.root, "plugins/new-plug/.apm/skills/hub/scripts/bad.py", "def (:\n")
    (repo.root / "plugins/new-plug/.apm/skills/hub/scripts/link.py").symlink_to("bad.py")
    git(repo.root, "add", "-A")
    assert rr.cmd_verify(repo, "1") == 1
    out = capsys.readouterr().out
    assert "broken link" in out and "syntax error" in out and "symlink in package" in out


def test_verify_requires_old_paths_gone(repo, capsys):
    rr.cmd_apply(repo, "1", True)
    write(repo.root, "plugins/new-plug/.apm/skills/hub/SKILL.md", "ok\n")
    write(repo.root, OLD_SCRIPT, "old copy\n")
    git(repo.root, "add", "-A")
    assert rr.cmd_verify(repo, "1") == 1
    assert "old path still present" in capsys.readouterr().out


def test_scan_classifies_rules(repo):
    idx = rr.scan(repo, None)
    rules = {(r["file"], r["rule"]) for r in idx}
    assert ("docs/a.md", "path") in rules
    assert not any(r["file"].startswith("docs/handovers") for r in idx)
    assert not any(r["file"].startswith("investment_screener/backend/data") for r in idx)
