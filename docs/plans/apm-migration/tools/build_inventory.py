#!/usr/bin/env python3
"""
build_inventory.py - APM migration Wave 0: record the pre-migration state of plugins/.

Purpose:
    Writes inventory-before.csv (every file and symlink under plugins/ at git HEAD) and
    external-links-before.csv (symlinks outside plugins/ that point into plugins/).
    HEAD is the source of truth for "old paths", so work already done in the working tree
    (the etf-analysis and questrade moves) does not distort the baseline. Where a HEAD file
    has since moved, `current_path` records where git rename detection finds it now.

Usage:
    python3 docs/plans/apm-migration/tools/build_inventory.py

Output:
    docs/plans/apm-migration/inventory-before.csv
    docs/plans/apm-migration/external-links-before.csv

Key Input Dependencies:
    - git (ls-tree, cat-file, diff -M)
"""
import csv
import hashlib
import os
import posixpath
import re
import subprocess
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
OUT = ROOT / "docs/plans/apm-migration"


def git(*args: str, raw: bool = False):
    out = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True)
    return out.stdout if raw else out.stdout.decode("utf-8", "replace")


def ls_tree(prefix: str) -> list[tuple[str, str, str]]:
    """Return (mode, blob_sha, path) for every entry under prefix at HEAD."""
    rows = []
    for line in git("ls-tree", "-r", "-z", "HEAD", "--", prefix, raw=True).decode().split("\0"):
        if not line:
            continue
        meta, path = line.split("\t", 1)
        mode, _type, sha = meta.split()
        rows.append((mode, sha, path))
    return rows


def blobs(shas: list[str]) -> dict[str, bytes]:
    """Read many blobs in one `git cat-file --batch` call."""
    proc = subprocess.run(["git", "cat-file", "--batch"], cwd=ROOT, check=True,
                          input=("\n".join(shas) + "\n").encode(), capture_output=True)
    data, pos, result = proc.stdout, 0, {}
    for sha in shas:
        eol = data.index(b"\n", pos)
        _sha, _type, size = data[pos:eol].decode().split()
        start = eol + 1
        result[sha] = data[start:start + int(size)]
        pos = start + int(size) + 1
    return result


def classify(path: str) -> tuple[str, str, str]:
    """Return (plugin, skill, kind) for a path under plugins/."""
    parts = path.split("/")
    plugin = parts[1]
    skill = "-"
    rest = parts[2:]
    if rest and rest[0] == "skills" and len(rest) > 2:
        skill, rest = rest[1], rest[2:]
    name = rest[-1]
    top = rest[0]
    if name == "SKILL.md":
        kind = "skill-md"
    elif top in ("scripts", "tests", "assets", "references", "agents", "evals", "audit"):
        kind = {"scripts": "script", "tests": "test", "assets": "asset", "references": "reference",
                "agents": "agent", "evals": "eval", "audit": "data"}[top]
        if top == "agents" and "evals" in rest:
            kind = "eval"
    elif name in ("plugin.json", "plugin.yaml", ".mcp.json", "apm.yml") or top == ".claude-plugin":
        kind = "manifest"
    elif name in ("README.md", "CONNECTORS.md"):
        kind = "doc"
    else:
        kind = "other"
    return plugin, skill, kind


def main() -> None:
    entries = ls_tree("plugins/")
    content = blobs([sha for _m, sha, _p in entries])

    # Where each HEAD file is now (rename detection over staged and unstaged changes).
    now: dict[str, str] = {}
    for line in git("diff", "HEAD", "-M", "--name-status", "--", "plugins/").splitlines():
        cols = line.split("\t")
        if cols[0].startswith("R"):
            now[cols[1]] = cols[2]
        elif cols[0] == "D":
            now.setdefault(cols[1], "(deleted)")

    # py_services symlinks that point into plugins/ (the backend's imports).
    ext_rows = []
    backend_link_for: dict[str, str] = {}
    all_links = [e for e in ls_tree("investment_screener/") + ls_tree("docs/") + ls_tree("references/")
                 + ls_tree(".agents/") if e[0] == "120000"]
    if all_links:
        link_blobs = blobs([sha for _m, sha, _p in all_links])
        for _m, sha, path in all_links:
            target = link_blobs[sha].decode()
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
            if resolved.startswith("plugins/"):
                plugin = resolved.split("/")[1]
                ext_rows.append({"link_path": path, "target": target, "resolved_target": resolved,
                                 "plugin": plugin, "link_area": path.split("/")[0]})
                if path.startswith("investment_screener/backend/py_services/"):
                    backend_link_for[resolved] = path

    inv = []
    for mode, sha, path in entries:
        plugin, skill, kind = classify(path)
        data = content[sha]
        is_link = mode == "120000"
        target = data.decode() if is_link else ""
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target)) if is_link else ""
        inv.append({
            "old_path": path, "old_plugin": plugin, "old_skill": skill, "kind": kind,
            "type": "symlink" if is_link else "file", "mode": mode,
            "symlink_target": target, "resolved_target": resolved,
            "target_inside_plugin": (resolved.startswith(f"plugins/{plugin}/") if is_link else ""),
            "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "backend_link": backend_link_for.get(path, ""),
            "current_path": now.get(path, path if (ROOT / path).exists() or (ROOT / path).is_symlink() else "(missing)"),
        })
    inv.sort(key=lambda r: r["old_path"])
    with open(OUT / "inventory-before.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(inv[0]))
        w.writeheader()
        w.writerows(inv)
    ext_rows.sort(key=lambda r: r["link_path"])
    with open(OUT / "external-links-before.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["link_path", "target", "resolved_target", "plugin", "link_area"])
        w.writeheader()
        w.writerows(ext_rows)

    by_plugin: dict[str, dict[str, int]] = {}
    for r in inv:
        d = by_plugin.setdefault(r["old_plugin"], {"files": 0, "symlinks": 0})
        d["symlink" + "s" if r["type"] == "symlink" else "files"] += 1
    print(f"inventory-before.csv: {len(inv)} entries")
    for p, d in sorted(by_plugin.items()):
        print(f"  {p:18} files={d['files']:4} symlinks={d['symlinks']:4}")
    print(f"external-links-before.csv: {len(ext_rows)} symlinks outside plugins/ into plugins/")
    moved = sum(1 for r in inv if r["current_path"] not in (r["old_path"],))
    print(f"already moved in the working tree: {moved}")


if __name__ == "__main__":
    main()
