#!/usr/bin/env python3
"""
build_mode_files.py - APM migration: turn each old SKILL.md of a wave into a mode file of its hub,
and merge the old per-skill evals into one evals.json per hub.

Purpose:
    For every skill of the wave in name-map.csv, reads the old SKILL.md from the pinned baseline
    commit and writes `<hub>/references/modes/<mode>.md`:
      - frontmatter and the "Contents" list are dropped; the body (constraints, workflow, guards)
        is kept verbatim;
      - script/asset/reference paths become hub-relative text (`scripts/x.py`) when the file now
        lives in the same hub, or its repository path when it lives in the engine or elsewhere;
      - markdown links are recomputed so they resolve from the mode file;
      - mentions of other skills become links to their mode files (same hub) or "the `<mode>` mode
        of the `<hub>` skill"; slash commands are left alone.
    Two old skills that share one mode (tv-setup + tv-onboarding, adversarial-review +
    external-review) are written as sections of one file.
    `check` compares every substantive old line with the new text, ignoring paths and skill names.
    `evals` merges the old evals into the hub's evals.json (each tagged with its `mode`).

Usage:
    python3 docs/plans/apm-migration/tools/build_mode_files.py build <wave>
    python3 docs/plans/apm-migration/tools/build_mode_files.py check <wave>
    python3 docs/plans/apm-migration/tools/build_mode_files.py evals <wave>

Key Input Dependencies:
    - name-map.csv, master_migration_inventory.csv, baseline-commit.txt, git
"""
import csv
import difflib
import json
import os
import posixpath
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
OUT = ROOT / "docs/plans/apm-migration"
BASE = (OUT / "baseline-commit.txt").read_text().strip()


def show(path: str) -> str:
    r = subprocess.run(["git", "show", f"{BASE}:{path}"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout


def split_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    fm: dict = {}
    key = None
    for line in m.group(1).splitlines():
        km = re.match(r"^([\w-]+):\s*(.*)$", line)
        if km:
            key, val = km.group(1), km.group(2).strip()
            fm[key] = val.lstrip(">-").strip() if val in (">-", ">", "|", "") else val
        elif key:
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return fm, m.group(2)


def load() -> tuple[list[dict], dict, dict, dict]:
    names = list(csv.DictReader(open(OUT / "name-map.csv")))
    skills = {n["old_id"]: n for n in names if n["kind"] == "skill"}
    paths = {n["old_path"]: n for n in names if n["old_path"] and n["kind"] != "skill" and n["new_path"]}
    skill_by_path = {n["old_path"]: n for n in skills.values()}
    return names, skills, paths, skill_by_path


def hub_dir_of(mode_path: str) -> str:
    return mode_path.split("/references/modes/")[0]


def convert(body: str, skill: dict, skills: dict, paths: dict, skill_by_path: dict) -> str:
    mode_path = skill["new_path"]
    hubdir = hub_dir_of(mode_path)
    mode_dir = posixpath.dirname(mode_path)
    old_skill_dir = posixpath.dirname(skill["old_path"])

    # 1. drop the Contents list
    body = re.sub(r"^## Contents\n(?:\s*- \[[^\n]*\n?)+", "", body, flags=re.M)
    body = re.sub(r"^# [^\n]*\n", "", body, count=1, flags=re.M)

    def new_text_path(newp: str) -> str:
        return newp[len(hubdir) + 1:] if newp.startswith(hubdir + "/") else newp

    # 2. markdown links
    def link(m: re.Match) -> str:
        text, target = m.group(1), m.group(2)
        if re.match(r"^[a-z]+:", target) or target.startswith("#"):
            return m.group(0)
        frag = ""
        if "#" in target:
            target, frag = target.split("#", 1)
            frag = "#" + frag
        old_abs = posixpath.normpath(posixpath.join(old_skill_dir, target))
        if old_abs in skill_by_path:
            sk = skill_by_path[old_abs]
            if hub_dir_of(sk["new_path"]) == hubdir:
                return f"[{text}]({posixpath.relpath(sk['new_path'], mode_dir)}{frag})"
            return f"{text} (the `{sk['mode']}` mode of the `{sk['hub']}` skill)"
        row = paths.get(old_abs)
        if row:
            newp = row["new_path"]
            if newp.startswith(hubdir + "/"):
                return f"[{text}]({posixpath.relpath(newp, mode_dir)}{frag})"
            plug = "/".join(hubdir.split("/")[:2])
            if newp.startswith(plug + "/"):
                return f"[{text}]({posixpath.relpath(newp, mode_dir)}{frag})"
            return f"{text} (`{newp}`)"
        return m.group(0)

    body = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, body)

    # 3. code-text paths (longest first)
    if paths:
        alt = "|".join(re.escape(p) for p in sorted(paths, key=len, reverse=True))
        rx = re.compile(r"(?<![\w.\-])(?:" + alt + r")(?![\w\-])")
        body = rx.sub(lambda m: new_text_path(paths[m.group(0)]["new_path"]), body)

    # 4. other skills mentioned by name (not slash commands, not path pieces)
    names_alt = "|".join(re.escape(n) for n in sorted(skills, key=len, reverse=True))
    srx = re.compile(r"(?<![\w/.\-])(`?)(" + names_alt + r")(`?)(?![\w\-/.])")

    def repl(m: re.Match) -> str:
        sk = skills[m.group(2)]
        if sk["old_id"] == skill["old_id"]:
            return "this mode"
        if hub_dir_of(sk["new_path"]) == hubdir:
            return f"[{sk['mode']} mode]({posixpath.relpath(sk['new_path'], mode_dir)})"
        return f"the `{sk['mode']}` mode of the `{sk['hub']}` skill"

    body = srx.sub(repl, body)
    body = re.sub(r"\bthis skill\b", "this mode", body)
    body = re.sub(r"\bThis skill\b", "This mode", body)
    return body.strip("\n") + "\n"


def build(wave: str) -> int:
    names, skills, paths, skill_by_path = load()
    todo = [s for s in skills.values() if s["wave"] == wave]
    groups: dict[str, list[dict]] = {}
    for s in todo:
        groups.setdefault(s["new_path"], []).append(s)
    for newp, group in groups.items():
        parts = []
        for s in group:
            fm, body = split_frontmatter(show(s["old_path"]))
            cmd = f" (`{s['command']}`)" if s["command"] else ""
            head = f"# Mode: {s['mode']}{cmd}" if len(group) == 1 else f"## Part: {s['old_id']}{cmd}"
            desc = fm.get("description", "").strip().strip('"')
            tools = fm.get("allowed-tools", "")
            intro = [head, ""]
            if desc:
                intro += [desc]
            if tools:
                intro += [f"Allowed tools: {tools}."]
            parts.append("\n".join(intro) + "\n\n" + convert(body, s, skills, paths, skill_by_path))
        text = parts[0] if len(group) == 1 else f"# Mode: {group[0]['mode']}\n\nThis mode combines " + \
            " and ".join(f"`{s['old_id']}`" for s in group) + ".\n\n" + "\n".join(parts)
        dest = Path(os.environ.get("MODE_OUT_ROOT", ROOT)) / newp   # MODE_OUT_ROOT redirects output (testing)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    print(f"wave {wave}: wrote {len(groups)} mode files from {len(todo)} skills")
    return 0


# ----------------------------------------------------------------------------- check
def denoise(s: str, skill_names: set[str]) -> str:
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = s.replace("`", "")
    s = re.sub(r"\S*/\S*", " ", s)                      # path-like tokens
    s = re.sub(r"\S+\.(py|md|json|js|pine|sql|ps1|template)\b", " ", s)
    for n in sorted(skill_names, key=len, reverse=True):
        s = re.sub(rf"(?<![\w/]){re.escape(n)}(?![\w-])", " ", s)
    s = re.sub(r"\b(this|the|mode|skill|of|a|an)\b", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip().lower()


def check(wave: str) -> int:
    names, skills, paths, skill_by_path = load()
    skill_names = set(skills)
    total = bad_n = 0
    by_file: dict[str, str] = {}
    for s in skills.values():
        if s["wave"] != wave:
            continue
        mode_text = (ROOT / s["new_path"]).read_text(encoding="utf-8")
        new_dn = denoise(mode_text, skill_names)
        new_lines = [denoise(x, skill_names) for x in mode_text.splitlines() if len(x.strip()) > 10]
        _fm, body = split_frontmatter(show(s["old_path"]))
        bad = []
        for line in body.splitlines():
            if not line.strip() or line.startswith("#") or "](#" in line or line.strip().startswith("- ["):
                continue
            n = denoise(line, skill_names)
            if len(n) < 12:
                continue
            total += 1
            if n in new_dn or any(difflib.SequenceMatcher(None, n, c).ratio() > 0.86 for c in new_lines):
                continue
            bad.append(line.strip()[:160])
        bad_n += len(bad)
        print(f"{s['old_id']:34} -> {s['mode']:22} missing={len(bad)}")
        for b in bad:
            print("      MISSING:", b)
    print(f"\nchecked {total} substantive lines; {bad_n} not found")
    return 0


# ----------------------------------------------------------------------------- evals
def evals(wave: str) -> int:
    names, skills, paths, skill_by_path = load()
    hubs: dict[str, list] = {}
    for s in skills.values():
        if s["wave"] != wave:
            continue
        old_dir = posixpath.dirname(s["old_path"])
        raw = show(f"{old_dir}/evals/evals.json")
        if not raw.strip():
            continue
        for e in json.loads(raw):
            e = dict(e)
            e["mode"] = s["mode"]
            hubs.setdefault(hub_dir_of(s["new_path"]), []).append(e)
    n_in = 0
    for hub, arr in hubs.items():
        dest = ROOT / hub / "evals/evals.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(arr, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        n_in += len(arr)
        print(f"{hub.split('/')[-1]}: {len(arr)} evals")
    print(f"wave {wave}: {n_in} evals merged into {len(hubs)} hubs")
    return 0


if __name__ == "__main__":
    cmd, wave = sys.argv[1], sys.argv[2]
    sys.exit({"build": build, "check": check, "evals": evals}[cmd](wave))
