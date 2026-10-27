#!/usr/bin/env python3
"""
execute_wave.py - APM migration: perform the file moves of one approved wave from the ledger.

Purpose:
    Reads master_migration_inventory.csv and, for every row of the wave, does the git operation
    the ledger names:
      MOVED_TO_SKILL | MOVED_TO_ENGINE | MOVED_TO_ENGINE_TESTS | MOVED_TO_AGENT  -> git mv old new
      RETIRED_SYMLINK | DELETED_APPROVED | RETIRED_MANIFEST                      -> git rm
    Rows that are authored by hand (CONSOLIDATED_*), kept, pending or colliding are reported, not
    touched. A destination that is a tracked symlink (the backend's links to a plugin script) is
    removed first so the real file takes its place. Idempotent: rows already done are skipped.
    Refuses to run for a wave that is not listed in mapping.yaml `approved_waves`.

Usage:
    python3 docs/plans/apm-migration/tools/execute_wave.py <wave> [--dry-run]
    python3 docs/plans/apm-migration/tools/execute_wave.py <wave> --retire-skills   # git rm the old skills/ folders (after hubs are authored)

Key Input Dependencies:
    - master_migration_inventory.csv, inventory-before.csv (current_path), mapping.yaml, git
"""
import csv
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
OUT = ROOT / "docs/plans/apm-migration"
MOVE = {"MOVED_TO_SKILL", "MOVED_TO_ENGINE", "MOVED_TO_ENGINE_TESTS", "MOVED_TO_AGENT"}
REMOVE = {"RETIRED_SYMLINK", "DELETED_APPROVED", "RETIRED_MANIFEST"}


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, check=check, capture_output=True, text=True)


def tracked(path: str) -> bool:
    return bool(git("ls-files", "--", path).stdout.strip())


def is_tracked_symlink(path: str) -> bool:
    return git("ls-files", "-s", "--", path).stdout.startswith("120000")


def main() -> int:
    wave, flags = sys.argv[1], set(sys.argv[2:])
    dry = "--dry-run" in flags
    cfg = yaml.safe_load((OUT / "mapping.yaml").read_text())
    if int(wave) not in [int(w) for w in cfg.get("approved_waves", [])]:
        print(f"wave {wave} is not in approved_waves; refusing")
        return 2
    ledger = [r for r in csv.DictReader(open(OUT / "master_migration_inventory.csv")) if r["wave"] == wave]
    cur = {r["old_path"]: r["current_path"] for r in csv.DictReader(open(OUT / "inventory-before.csv"))}

    if "--retire-skills" in flags:
        old_skill_dirs = sorted({f"plugins/{r['old_plugin']}/skills/{r['old_skill']}" for r in ledger
                                 if r["old_skill"] != "-" and r["old_path"].startswith(f"plugins/{r['old_plugin']}/skills/")})
        for d in old_skill_dirs:
            if (ROOT / d).exists() or tracked(d):
                print(f"git rm -r {d}")
                if not dry:
                    git("rm", "-r", "-q", "-f", d, check=False)
        return 0

    done = skipped = 0
    problems = []
    for r in ledger:
        old, new, act = r["old_path"], r["new_path"], r["action"]
        src = cur.get(old, old)
        if act in MOVE:
            if not (ROOT / src).exists() and not (ROOT / src).is_symlink():
                if (ROOT / new).exists():
                    skipped += 1
                    continue
                problems.append(f"missing source {src} (-> {new})")
                continue
            if (ROOT / new).exists() or (ROOT / new).is_symlink():
                if is_tracked_symlink(new):
                    print(f"git rm (backend link) {new}")
                    if not dry:
                        git("rm", "-q", "-f", new)
                else:
                    problems.append(f"destination exists: {new}")
                    continue
            print(f"git mv {src} -> {new}")
            if not dry:
                (ROOT / new).parent.mkdir(parents=True, exist_ok=True)
                git("mv", src, new)
            done += 1
        elif act in REMOVE:
            p = src if (ROOT / src).exists() or (ROOT / src).is_symlink() else old
            if (ROOT / p).exists() or (ROOT / p).is_symlink() or tracked(p):
                print(f"git rm {p}")
                if not dry:
                    git("rm", "-q", "-f", p, check=False)
                done += 1
            else:
                skipped += 1
        else:
            skipped += 1
    print(f"\nwave {wave}: {done} operations, {skipped} skipped/not mine; {len(problems)} problems")
    for p in problems:
        print("  PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
