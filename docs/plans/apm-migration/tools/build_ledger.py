#!/usr/bin/env python3
"""
build_ledger.py - APM migration Wave 0: turn inventory-before.csv + mapping.yaml into the ledger.

Purpose:
    Produces master_migration_inventory.csv (one row per file or symlink at git HEAD, with its
    proposed new path and action) and name-map.csv (old plugin, skill, command and path
    aliases -> new ids and paths, consumed by the reference-rewrite tool). Anything the mapping
    does not place is reported as UNMAPPED; a destination that already exists is reported as
    COLLISION. Re-run after editing mapping.yaml.

Usage:
    python3 docs/plans/apm-migration/tools/build_ledger.py

Output:
    docs/plans/apm-migration/master_migration_inventory.csv
    docs/plans/apm-migration/name-map.csv

Key Input Dependencies:
    - docs/plans/apm-migration/inventory-before.csv (run build_inventory.py first)
    - docs/plans/apm-migration/mapping.yaml
    - PyYAML, git
"""
import csv
import posixpath
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
OUT = ROOT / "docs/plans/apm-migration"
BASE = (OUT / "baseline-commit.txt").read_text().strip()   # pre-migration commit
M = yaml.safe_load((OUT / "mapping.yaml").read_text())
INV = list(csv.DictReader(open(OUT / "inventory-before.csv")))
# collisions are judged against the baseline commit (the pre-migration tree), not the working tree
TRACKED = set(subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE], cwd=ROOT, text=True).splitlines())
ENGINE, ENGINE_TESTS = M["engine_dir"], M["engine_tests_dir"]


def hub_dir(plugin: str, hub: str) -> str:
    return f"plugins/{M['plugins'][plugin]}/.apm/skills/{hub}"


def parse_value(v: str) -> tuple[str, str]:
    """Split 'DECIDE:proposal' style values into (verb, rest); plain values return ('', v)."""
    for verb in ("DECIDE", "RETIRE", "DELETE", "MERGE", "KEEP", "TESTS"):
        if v.startswith(verb + ":"):
            return verb, v[len(verb) + 1:]
    return "", v


def place(plugin: str, rel: str, row: dict) -> tuple[str, str, str, str]:
    """Return (new_path, action, scope, notes) for a real file."""
    key = f"{plugin}/{rel}"
    kind = row["kind"]
    np_ = M["plugins"][plugin]

    if rel in M["manifests"]:
        return f"plugins/{np_}/apm.yml", "RETIRED_MANIFEST", "manifest", "replaced by the new apm.yml (Decision 4A)"
    if key in M["docs"]:
        verb, rest = parse_value(M["docs"][key])
        return f"plugins/{rest}", ("KEPT" if verb == "KEEP" else "CONSOLIDATED_INTO_DOC"), "doc", ""
    for pref, v in M["data_prefixes"].items():
        if key.startswith(pref):
            return "", "DECISION_PENDING", "data", v
    if kind == "skill-md":
        spec = M["skills"].get(row["old_skill"])
        if not spec:
            return "", "UNMAPPED", "", f"skill {row['old_skill']} not in mapping"
        return (f"{hub_dir(plugin, spec['hub'])}/references/modes/{spec['mode']}.md",
                "CONSOLIDATED_INTO_SKILL", spec["hub"], "hub SKILL.md is new; this skill becomes a mode file")
    if kind == "eval":
        if row["old_skill"] != "-":
            spec = M["skills"].get(row["old_skill"])
            if not spec:
                return "", "UNMAPPED", "", f"skill {row['old_skill']} not in mapping"
            return (f"{hub_dir(plugin, spec['hub'])}/evals/evals.json", "CONSOLIDATED_INTO_SKILL", spec["hub"],
                    "merged into one evals.json array per hub")
        return f"plugins/{np_}/.apm/agents/evals/{posixpath.basename(rel)}", "MOVED_TO_AGENT", "agent", "agent eval"
    if kind == "agent":
        if key not in M["agents"]:
            return "", "UNMAPPED", "", "agent not in mapping"
        name = posixpath.basename(rel)[:-3]
        return f"plugins/{M['agents'][key]}/.apm/agents/{name}.agent.md", "MOVED_TO_AGENT", "agent", \
            "rewrite as its own short definition; use skills by name (SF-12)"
    if kind == "script":
        v = M["scripts"].get(key)
        if v is None:
            return "", "UNMAPPED", "", "script not in mapping"
        verb, rest = parse_value(v)
        name = posixpath.basename(rel)
        if verb == "DECIDE":
            hub, _, why = rest.partition(" ")
            return f"{hub_dir(plugin, hub)}/scripts/{name}", "DECISION_PENDING", hub, why.strip("()")
        if verb == "RETIRE":
            return "", "RETIRE_PENDING", "", rest
        if verb == "DELETE":
            return "", "DELETED_APPROVED", "", rest
        if verb == "TESTS":
            return f"{ENGINE_TESTS}/{name}", "MOVED_TO_ENGINE_TESTS", "engine", "test living in scripts/"
        if v == "engine":
            # land exactly where the backend already links to this script, else in the engine dir
            return (row.get("backend_link") or f"{ENGINE}/{name}"), "MOVED_TO_ENGINE", "engine", ""
        return f"{hub_dir(plugin, v)}/scripts/{name}", "MOVED_TO_SKILL", v, ""
    if kind == "asset":
        v = M["assets"].get(key)
        sub = rel[len("assets/"):]
        if v is None:
            for pref, hub in M["asset_prefixes"].items():
                if key.startswith(pref):
                    return f"{hub_dir(plugin, hub)}/assets/{sub}", "MOVED_TO_SKILL", hub, ""
            return "", "UNMAPPED", "", "asset not in mapping"
        verb, rest = parse_value(v)
        if verb == "RETIRE":
            return "", "RETIRE_PENDING", "", rest
        if verb == "DELETE":
            return "", "DELETED_APPROVED", "", rest
        return f"{hub_dir(plugin, v)}/assets/{sub}", "MOVED_TO_SKILL", v, ""
    if kind == "reference":
        v = M["references"].get(key)
        sub = rel[len("references/"):]
        if v is None:
            for pref, hub in M["reference_prefixes"].items():
                if key.startswith(pref):
                    return f"{hub_dir(plugin, hub)}/references/{sub}", "MOVED_TO_SKILL", hub, ""
            return "", "UNMAPPED", "", "reference not in mapping"
        verb, rest = parse_value(v)
        if verb == "MERGE":
            return f"plugins/{M['plugins'][plugin]}/.apm/skills/{rest}", "CONSOLIDATED_INTO_SKILL", rest.split("/")[0], \
                "merged with its near-duplicate"
        if verb == "DECIDE":
            hub, _, why = rest.partition(" ")
            return f"{hub_dir(plugin, hub)}/references/{sub}", "DECISION_PENDING", hub, why.strip("()")
        # evolution logs of merged plugins keep their own file name so history is not mixed
        if posixpath.basename(rel) == "evolution-log.md" and plugin in ("etf-analysis",):
            return f"{hub_dir(plugin, v)}/references/evolution-log-{plugin}.md", "MOVED_TO_SKILL", v, "history kept separate"
        return f"{hub_dir(plugin, v)}/references/{sub}", "MOVED_TO_SKILL", v, ""
    if kind == "test":
        v = M["test_overrides"].get(key)
        name = posixpath.basename(rel)
        sub = rel[len("tests/"):]
        if v is None:
            stem = re.sub(r"^test_", "", name[:-3]) if name.endswith(".py") else ""
            cands = []
            for k, sv in M["scripts"].items():
                if posixpath.basename(k)[:-3] == stem or stem.startswith(posixpath.basename(k)[:-3] + "_"):
                    cands.append((k, sv))
            cands = [c for c in cands if c[0].split("/")[0] == plugin] or cands
            cands.sort(key=lambda c: -len(posixpath.basename(c[0])))
            if not cands:
                return "", "UNMAPPED", "", "no script/override matches this test"
            v = parse_value(cands[0][1])[1].split(" ")[0] if parse_value(cands[0][1])[0] == "DECIDE" else cands[0][1]
        if v == "engine":
            return f"{ENGINE_TESTS}/{sub}", "MOVED_TO_ENGINE_TESTS", "engine", ""
        return f"{hub_dir(plugin, v)}/tests/{sub}", "MOVED_TO_SKILL", v, ""
    return "", "UNMAPPED", "", f"kind {kind} not handled"


def resolve_new(old_path: str, rows_by_path: dict[str, dict]) -> str:
    """New location of a path (follows a symlink to its target's new location)."""
    r = rows_by_path.get(old_path)
    if not r:
        return old_path
    if r["type"] == "symlink":
        t = r["resolved_target"]
        return resolve_new(t, rows_by_path) if t in rows_by_path else t
    return r["new_path"] or old_path


def skill_command(old_path: str) -> str:
    text = subprocess.run(["git", "show", f"{BASE}:{old_path}"], cwd=ROOT, capture_output=True, text=True).stdout
    # only an explicit "Trigger on /command" counts; a stray slash (DLR.TO/DLR.U) is not a command
    m = re.search(r"^description:.*?(?:Trigger on|Trigger:)\s*(/[\w-]+)", text, re.M | re.S)
    return m.group(1) if m else ""


def main() -> None:
    ledger = []
    by_path = {r["old_path"]: r for r in INV}
    for r in INV:
        plugin = r["old_plugin"]
        rel = r["old_path"][len(f"plugins/{plugin}/"):]
        base = {"old_path": r["old_path"], "old_plugin": plugin, "old_skill": r["old_skill"], "kind": r["kind"],
                "type": r["type"], "new_plugin": M["plugins"][plugin], "wave": M["waves"][plugin],
                "status": "approved" if str(M["waves"][plugin]) in [str(w) for w in M.get("approved_waves", [])] else "proposed"}
        if r["type"] == "symlink":
            r["new_path"] = ""
            ledger.append({**base, "new_path": "", "action": "RETIRED_SYMLINK", "scope": "",
                           "new_hub": "", "new_mode": "", "notes": f"was -> {r['resolved_target']}"})
            continue
        new_path, action, scope, notes = place(plugin, rel, r)
        r["new_path"] = new_path
        spec = M["skills"].get(r["old_skill"], {}) if r["kind"] in ("skill-md", "eval") else {}
        hub = spec.get("hub", scope if scope not in ("engine", "manifest", "doc", "data", "agent", "") else "")
        # destination collisions (real file already there; a backend symlink at the path is expected)
        if new_path and action.startswith("MOVED") and new_path in TRACKED and new_path != r["old_path"]:
            link = next((x for x in INV if False), None)
            is_link = subprocess.run(["git", "ls-files", "-s", new_path], cwd=ROOT, capture_output=True,
                                     text=True).stdout.startswith("120000")
            if not is_link:
                action, notes = "COLLISION", f"destination already exists; {notes}".strip("; ")
            else:
                notes = (notes + "; replaces the backend symlink at this path").strip("; ")
        ledger.append({**base, "new_path": new_path, "action": action, "scope": scope, "new_hub": hub,
                       "new_mode": spec.get("mode", ""), "notes": notes})

    # symlink rows: record where their target ends up
    for row in ledger:
        if row["action"] == "RETIRED_SYMLINK":
            t = by_path[row["old_path"]]["resolved_target"]
            row["notes"] += f"; target now at {resolve_new(t, by_path)}"

    cols = ["old_path", "new_path", "action", "notes", "wave", "old_plugin", "old_skill", "new_plugin",
            "new_hub", "new_mode", "scope", "kind", "type", "status"]
    with open(OUT / "master_migration_inventory.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(ledger)

    # name map
    names = []
    for old, new in M["plugins"].items():
        names.append({"kind": "plugin", "old_id": old, "old_path": f"plugins/{old}", "new_id": new,
                      "new_path": f"plugins/{new}", "hub": "", "mode": "", "command": "",
                      "wave": M["waves"][old], "policy": "rewrite" if old != new else "keep"})
    skill_md = {r["old_skill"]: r for r in INV if r["kind"] == "skill-md"}
    for skill, spec in M["skills"].items():
        r = skill_md.get(skill)
        if not r:
            continue
        plugin = r["old_plugin"]
        names.append({"kind": "skill", "old_id": skill, "old_path": r["old_path"], "new_id": spec["hub"],
                      "new_path": f"{hub_dir(plugin, spec['hub'])}/references/modes/{spec['mode']}.md",
                      "hub": spec["hub"], "mode": spec["mode"], "command": skill_command(r["old_path"]),
                      "wave": M["waves"][plugin], "policy": "rewrite"})
    for row in ledger:
        if row["kind"] in ("skill-md", "eval"):
            continue
        if row["action"] == "RETIRED_SYMLINK":
            t = by_path[row["old_path"]]["resolved_target"]
            new = resolve_new(t, by_path)
            names.append({"kind": row["kind"], "old_id": posixpath.basename(row["old_path"]), "old_path": row["old_path"],
                          "new_id": posixpath.basename(new), "new_path": new, "hub": "", "mode": "", "command": "",
                          "wave": row["wave"], "policy": "alias"})
        elif row["new_path"]:
            names.append({"kind": row["kind"], "old_id": posixpath.basename(row["old_path"]), "old_path": row["old_path"],
                          "new_id": posixpath.basename(row["new_path"]), "new_path": row["new_path"],
                          "hub": row["new_hub"], "mode": "", "command": "", "wave": row["wave"],
                          "policy": "rewrite" if row["status"] == "proposed" else "keep"})
    with open(OUT / "name-map.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["kind", "old_id", "old_path", "new_id", "new_path", "hub", "mode",
                                          "command", "wave", "policy"])
        w.writeheader()
        w.writerows(names)

    # report
    from collections import Counter
    print(f"master_migration_inventory.csv: {len(ledger)} rows | name-map.csv: {len(names)} rows")
    for a, n in sorted(Counter(r["action"] for r in ledger).items(), key=lambda x: -x[1]):
        print(f"  {a:26}{n}")
    for flag in ("UNMAPPED", "COLLISION"):
        bad = [r for r in ledger if r["action"] == flag]
        if bad:
            print(f"\n{flag} ({len(bad)}):")
            for r in bad:
                print(f"  {r['old_path']}  -> {r['new_path'] or '-'}  [{r['notes']}]")
    pend = [r for r in ledger if r["action"] in ("DECISION_PENDING", "RETIRE_PENDING")]
    if pend:
        print(f"\nPENDING YOUR DECISION ({len(pend)}):")
        for r in pend:
            print(f"  {r['old_path']}  [{r['notes']}]")


if __name__ == "__main__":
    main()
