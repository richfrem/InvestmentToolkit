#!/usr/bin/env python3
"""
rewrite_references.py - APM migration: find, rewrite and verify every stale reference.

Purpose:
    Reads name-map.csv and master_migration_inventory.csv (built by build_ledger.py) and
      scan      finds every occurrence of an old plugin path, skill name, script/asset/reference
                path, slash command or fragile Python path construction -> reference-index.csv
      plan      shows the unambiguous path rewrites for one wave as unified diffs (writes nothing)
      apply     performs those rewrites (needs --yes), backing up each original first
      rollback  restores the originals saved by `apply`
      dirfix    rewrites directory-level references (sys.path inserts of a plugin's scripts folder) to the folder(s)
                that now hold the modules the file actually imports; anything ambiguous is listed, not guessed
      verify    checks one wave is complete: files accounted for, no old paths left, no symlinks,
                links resolve, Python compiles, JSON/YAML parse
    Only exact old-path -> new-path rewrites are automatic. Skill names, plugin-name prose,
    basenames and Python path expressions are reported for a human or agent to decide.

Usage:
    python3 docs/plans/apm-migration/tools/rewrite_references.py scan   [--wave N]
    python3 docs/plans/apm-migration/tools/rewrite_references.py plan   --wave N
    python3 docs/plans/apm-migration/tools/rewrite_references.py apply  --wave N --yes
    python3 docs/plans/apm-migration/tools/rewrite_references.py rollback --wave N
    python3 docs/plans/apm-migration/tools/rewrite_references.py dirfix --wave N [--yes]
    python3 docs/plans/apm-migration/tools/rewrite_references.py verify --wave N

Output:
    docs/plans/apm-migration/reference-index.csv (scan)
    docs/plans/apm-migration/patches/wave-N/ (apply: originals + manifest.json)

Key Input Dependencies:
    - git (file list), PyYAML (verify)
"""
import argparse
import csv
import difflib
import json
import posixpath
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

EXTS = {".md", ".mmd", ".py", ".js", ".ts", ".tsx", ".json", ".yml", ".yaml", ".sh", ".ps1", ".toml",
        ".txt", ".template", ".sql", ".html", ".csv", ".cjs", ".mjs"}
EXTRA_NAMES = {".gitignore", ".gitattributes"}
# History, generated material and the data boundary are never rewritten
# (the history set is the one decouple_agent_paths.py excludes).
SKIP_DIRS = ("ARCHIVE/", "temp/", "build/", "venv/", "node_modules/", "docs/plans/apm-migration/",
             "docs/plans/apm-consolidation-plan.md", "research/", ".agents/", ".claude/", ".antigravitycli/",
             "investment_screener/venv/", "investment_screener/node_modules/",
             "investment_screener/frontend/node_modules/", "investment_screener/backend/node_modules/",
             "investment_screener/backend/dist/",
             "investment_screener/backend/data/", "context/", ".runtime/", "ecosystem_yaml_summary.md")
SKIP_NAMES = {"evolution-log.md", "map-debt.md", "CHANGELOG.md", "backlog.md"}
SKIP_FRAGMENTS = ("/ADRs/", "/handovers/", "/baseline/")
# Produced by audit_json_usage.py; regenerated once after the last wave rather than edited.
# (file-dependency-register.json is hand-curated, so its paths ARE rewritten.)
GENERATED = ("docs/architecture/json-discovery-audit", "docs/architecture/allowed-json-register")
PY_EXPRS = [
    (re.compile(r"\bparents\[\d+\]"), "pyexpr:parents"),
    (re.compile(r"""['"]plugins['"]"""), "pyexpr:plugins-segment"),
    (re.compile(r"""os\.path\.join\([^)]*plugins"""), "pyexpr:os.path.join"),
]
LINK_RE = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")


@dataclass
class Ctx:
    root: Path
    out: Path


def default_ctx() -> Ctx:
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    return Ctx(root, root / "docs/plans/apm-migration")


def in_scope(rel: str) -> str:
    """Return '' when a file is in scope, else the reason it is skipped."""
    p = Path(rel)
    if p.suffix not in EXTS and p.name not in EXTRA_NAMES:
        return "ext"
    if any(rel.startswith(d) for d in SKIP_DIRS):
        return "skip-dir"
    if p.name in SKIP_NAMES or any(f in rel for f in SKIP_FRAGMENTS):
        return "history"
    if any(rel.startswith(g) for g in GENERATED):
        return "generated"
    return ""


def tracked_files(ctx: Ctx) -> list[str]:
    raw = subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ctx.root, text=True)
    return [f for f in raw.split("\0") if f]


def load_csv(path: Path) -> list[dict]:
    return list(csv.DictReader(open(path)))


def path_rows(names: list[dict], wave: str | None, ready: set[str] | None = None) -> dict[str, dict]:
    """old path -> name-map row, for path-level entries (wave filter optional).

    When `ready` is given, only paths whose ledger action is settled are included, so a reference is
    never rewritten to a destination that is still pending a decision.
    """
    return {n["old_path"]: n for n in names
            if n["old_path"] and n["kind"] != "plugin" and n["new_path"] and n["new_path"] != n["old_path"]
            and (not wave or n["wave"] == wave)
            and (ready is None or n["old_path"] in ready)}


SETTLED = {"DELETED_APPROVED", "MOVED_TO_SKILL", "MOVED_TO_ENGINE", "MOVED_TO_ENGINE_TESTS", "MOVED_TO_AGENT",
           "CONSOLIDATED_INTO_SKILL", "CONSOLIDATED_INTO_DOC", "KEPT", "RETIRED_SYMLINK"}


def ready_paths(ctx: "Ctx") -> set[str]:
    return {r["old_path"] for r in load_csv(ctx.out / "master_migration_inventory.csv") if r["action"] in SETTLED}


def path_regex(rows: dict[str, dict]) -> re.Pattern | None:
    if not rows:
        return None
    alt = "|".join(re.escape(p) for p in sorted(rows, key=len, reverse=True))
    return re.compile(r"(?<![\w.\-])(?:" + alt + r")(?![\w\-])")


def rewrite_text(text: str, rows: dict[str, dict], rx: re.Pattern | None) -> tuple[str, int]:
    if rx is None:
        return text, 0
    count = 0

    def sub(m: re.Match) -> str:
        nonlocal count
        count += 1
        return rows[m.group(0)]["new_path"]

    return rx.sub(sub, text), count


# ------------------------------------------------------------------ scan
def scan(ctx: Ctx, wave: str | None) -> list[dict]:
    all_names = load_csv(ctx.out / "name-map.csv")
    names = [n for n in all_names if not wave or n["wave"] == wave]
    rows = path_rows(names, None)
    path_re = path_regex(rows)
    old_plugins = sorted({n["old_id"] for n in all_names if n["kind"] == "plugin"}, key=len, reverse=True)
    plugin_rows = {n["old_id"]: n for n in names if n["kind"] == "plugin" and n["old_id"] != n["new_id"]}
    plugin_re = re.compile(r"plugins/(" + "|".join(map(re.escape, old_plugins)) + r")\b")
    skill_rows = {n["old_id"]: n for n in names if n["kind"] == "skill"}
    skill_re = re.compile(r"(?<![\w/.\-])(" + "|".join(sorted(map(re.escape, skill_rows), key=len, reverse=True))
                          + r")(?![\w\-])") if skill_rows else None
    cmd_rows = {n["command"]: n for n in skill_rows.values() if n["command"]}
    cmd_re = re.compile(r"(?<![\w/.\-])(" + "|".join(sorted(map(re.escape, cmd_rows), key=len, reverse=True))
                        + r")(?![\w\-])") if cmd_rows else None
    base_rows = {}
    for n in names:
        if n["kind"] in ("script", "asset", "reference") and n["policy"] != "alias":
            b = n["old_id"]
            if len(b) >= 9 and ("_" in b or "-" in b) and b not in ("evolution-log.md", "fallback-tree.md"):
                base_rows.setdefault(b, n)
    base_re = re.compile(r"(?<![\w/.\-])(" + "|".join(sorted(map(re.escape, base_rows), key=len, reverse=True))
                         + r")(?![\w\-])") if base_rows else None

    index, skipped = [], Counter()
    for rel in tracked_files(ctx):
        why = in_scope(rel)
        if why:
            skipped[why] += 1
            continue
        try:
            text = (ctx.root / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError, IsADirectoryError):
            continue
        is_py = rel.endswith(".py")
        for ln, line in enumerate(text.splitlines(), 1):
            spans: list[tuple[int, int]] = []
            if path_re:
                for m in path_re.finditer(line):
                    index.append(_row(rel, ln, m, "path", rows[m.group(0)]["new_path"], "auto", line))
                    spans.append(m.span())
            for m in plugin_re.finditer(line):
                if any(s <= m.start() < e for s, e in spans):
                    continue
                n = plugin_rows.get(m.group(1))
                index.append(_row(rel, ln, m, "plugin-prefix", f"plugins/{n['new_id']}" if n else "", "review", line))
                spans.append(m.span())
            if skill_re:
                for m in skill_re.finditer(line):
                    if any(s <= m.start() < e for s, e in spans):
                        continue
                    n = skill_rows[m.group(1)]
                    index.append(_row(rel, ln, m, "skill-name", f"{n['hub']} ({n['mode']} mode)", "review", line))
            if cmd_re:
                for m in cmd_re.finditer(line):
                    index.append(_row(rel, ln, m, "command", m.group(1), "keep", line))
            if base_re:
                for m in base_re.finditer(line):
                    if any(s <= m.start() < e for s, e in spans):
                        continue
                    index.append(_row(rel, ln, m, "basename", base_rows[m.group(1)]["new_path"], "review", line))
            if is_py:
                for rx, tag in PY_EXPRS:
                    for m in rx.finditer(line):
                        index.append(_row(rel, ln, m, tag, "", "manual", line))
    print("files skipped by rule:", dict(skipped))
    return index


def _row(rel: str, ln: int, m: re.Match, rule: str, repl: str, status: str, line: str) -> dict:
    return {"file": rel, "line": ln, "col": m.start() + 1, "token": m.group(0), "rule": rule,
            "proposed_replacement": repl, "status": status, "context": line.strip()[:140]}


# ------------------------------------------------------------------ plan / apply
def wave_old_plugins(ctx: Ctx, wave: str) -> set[str]:
    return {r["old_plugin"] for r in load_csv(ctx.out / "master_migration_inventory.csv") if r["wave"] == wave}


def drop_symlinks_json(text: str, old_plugins: set[str]) -> tuple[str, int]:
    """Remove copy-manifest entries that involve a plugin of the wave (the symlinks are retired)."""
    data = json.loads(text)
    links = data["links"] if isinstance(data, dict) else data
    prefixes = tuple(f"plugins/{p}/" for p in old_plugins)
    kept = [e for e in links if not (str(e.get("src", "")).startswith(prefixes) or str(e.get("dst", "")).startswith(prefixes))]
    removed = len(links) - len(kept)
    if isinstance(data, dict):
        data["links"] = kept
    else:
        data = kept
    return json.dumps(data, indent=2) + "\n", removed


def compute_changes(ctx: Ctx, wave: str) -> list[dict]:
    names = load_csv(ctx.out / "name-map.csv")
    rows = path_rows(names, wave, ready_paths(ctx))
    rx = path_regex(rows)
    old_plugins = wave_old_plugins(ctx, wave)
    changes = []
    for rel in tracked_files(ctx):
        if in_scope(rel):
            continue
        p = ctx.root / rel
        if p.is_symlink() or not p.is_file():
            continue
        try:
            old = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if rel == "symlinks.json":
            new, n = drop_symlinks_json(old, old_plugins)
        else:
            new, n = rewrite_text(old, rows, rx)
        if new != old:
            changes.append({"file": rel, "old": old, "new": new, "count": n})
    return changes


def cmd_plan(ctx: Ctx, wave: str, show: int) -> int:
    changes = compute_changes(ctx, wave)
    total = sum(c["count"] for c in changes)
    print(f"wave {wave}: {total} rewrites (or removed manifest entries) in {len(changes)} files")
    for c in changes[:show]:
        diff = difflib.unified_diff(c["old"].splitlines(), c["new"].splitlines(), c["file"], c["file"], lineterm="", n=0)
        print("\n".join(list(diff)[:14]))
    if len(changes) > show:
        print(f"... {len(changes) - show} more files (use --show N)")
    return 0


def cmd_apply(ctx: Ctx, wave: str, yes: bool) -> int:
    if not yes:
        print("refusing to write without --yes (run `plan` first)")
        return 2
    changes = compute_changes(ctx, wave)
    dest = ctx.out / "patches" / f"wave-{wave}"
    if dest.exists() and any(dest.iterdir()):
        print(f"{dest} already has a backup; run `rollback --wave {wave}` or remove it first")
        return 2
    manifest = []
    for c in changes:
        bak = dest / "orig" / c["file"]
        bak.parent.mkdir(parents=True, exist_ok=True)
        bak.write_text(c["old"], encoding="utf-8")
        (ctx.root / c["file"]).write_text(c["new"], encoding="utf-8")
        manifest.append({"file": c["file"], "count": c["count"]})
    (dest / "manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"wave {wave}: rewrote {sum(m['count'] for m in manifest)} references in {len(manifest)} files; originals in {dest}")
    return 0


def cmd_rollback(ctx: Ctx, wave: str) -> int:
    dest = ctx.out / "patches" / f"wave-{wave}"
    mf = dest / "manifest.json"
    if not mf.exists():
        print("nothing to roll back")
        return 1
    for m in json.loads(mf.read_text()):
        shutil.copyfile(dest / "orig" / m["file"], ctx.root / m["file"])
    shutil.rmtree(dest)
    print(f"wave {wave}: restored originals")
    return 0



# ------------------------------------------------------------------ dirfix
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", re.M)


def compute_dirfix(ctx: Ctx, wave: str) -> tuple[list[dict], list[str]]:
    """Directory-level references to a moved plugin's scripts folder, rewritten per file.

    For each file that names `plugins/<old>/scripts` (or its segment form) the modules it imports are
    matched against the wave's old scripts; the new folders of those modules replace the old folder.
    """
    names = load_csv(ctx.out / "name-map.csv")
    ready = ready_paths(ctx)
    # stem -> new dir, per old plugin
    by_plugin: dict[str, dict[str, str]] = {}
    for n in names:
        if n["kind"] == "script" and n["wave"] == wave and n["new_path"] and n["old_path"] in ready:
            m = re.match(r"plugins/([\w-]+)/scripts/([\w]+)\.py$", n["old_path"])
            if m:
                by_plugin.setdefault(m.group(1), {})[m.group(2)] = posixpath.dirname(n["new_path"])
    changes, manual = [], []
    for rel in tracked_files(ctx):
        if in_scope(rel) or not rel.endswith(".py"):
            continue
        p = ctx.root / rel
        if p.is_symlink() or not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        stems = set(IMPORT_RE.findall(text))
        new_lines, touched = [], False
        for ln, line in enumerate(text.splitlines(keepends=True), 1):
            repl_line = None
            for plug, modules in by_plugin.items():
                lit = re.compile(r'plugins/' + re.escape(plug) + r'/scripts(?![/\w.])')
                seg = re.compile(r'"plugins"\s*(?:/|,)\s*"' + re.escape(plug) + r'"\s*(?:/|,)\s*"scripts"')
                if not (lit.search(line) or seg.search(line)):
                    continue
                dirs = sorted({modules[s_] for s_ in stems if s_ in modules})
                if not dirs:
                    manual.append(f"{rel}:{ln}: no imported module of {plug} found for: {line.strip()[:100]}")
                    break
                indent = re.match(r"\s*", line).group(0)
                out = []
                for d in dirs:
                    new = lit.sub(d, line)
                    new = seg.sub('"' + d + '"', new)
                    out.append(new)
                if len(out) > 1 and not line.lstrip().startswith("sys.path.insert"):
                    manual.append(f"{rel}:{ln}: {len(dirs)} target folders but not a plain sys.path insert: {line.strip()[:100]}")
                    break
                repl_line = "".join(out)
                break
            if repl_line is not None:
                new_lines.append(repl_line)
                touched = True
            else:
                new_lines.append(line)
        if touched:
            changes.append({"file": rel, "old": text, "new": "".join(new_lines),
                            "count": sum(1 for a, b in zip(text.splitlines(), "".join(new_lines).splitlines()) if a != b)
                            or 1})
    return changes, manual


def cmd_dirfix(ctx: Ctx, wave: str, yes: bool, show: int = 12) -> int:
    changes, manual = compute_dirfix(ctx, wave)
    print(f"wave {wave}: {len(changes)} files with directory-level references to fix; {len(manual)} need a human")
    for c in changes[:show]:
        diff = difflib.unified_diff(c["old"].splitlines(), c["new"].splitlines(), c["file"], c["file"], lineterm="", n=0)
        print("\n".join(list(diff)[:10]))
    for m in manual:
        print("  MANUAL:", m)
    if not yes:
        print("(plan only; pass --yes to write)")
        return 0
    dest = ctx.out / "patches" / f"wave-{wave}-dirfix"
    for c in changes:
        bak = dest / "orig" / c["file"]
        bak.parent.mkdir(parents=True, exist_ok=True)
        bak.write_text(c["old"], encoding="utf-8")
        (ctx.root / c["file"]).write_text(c["new"], encoding="utf-8")
    (dest).mkdir(parents=True, exist_ok=True)
    (dest / "manifest.json").write_text(json.dumps([{"file": c["file"]} for c in changes], indent=2))
    print(f"rewrote {len(changes)} files; originals in {dest}")
    return 0 if not manual else 1

# ------------------------------------------------------------------ verify
ACCOUNTED = {"MOVED_TO_SKILL", "MOVED_TO_ENGINE", "MOVED_TO_ENGINE_TESTS", "MOVED_TO_AGENT",
             "CONSOLIDATED_INTO_SKILL", "CONSOLIDATED_INTO_DOC", "KEPT", "RETIRED_MANIFEST"}


def cmd_verify(ctx: Ctx, wave: str) -> int:
    ledger = [r for r in load_csv(ctx.out / "master_migration_inventory.csv") if r["wave"] == wave]
    names = load_csv(ctx.out / "name-map.csv")
    fails: list[str] = []
    warns: list[str] = []

    # 1. accounting (pre-purge): every new path exists, every retired path is gone
    for r in ledger:
        old, new, act = r["old_path"], r["new_path"], r["action"]
        if act in ACCOUNTED:
            if not (ctx.root / new).exists():
                fails.append(f"missing target: {new}  (from {old})")
            if old != new and (ctx.root / old).exists() and (ctx.root / old).resolve() != (ctx.root / new).resolve():
                fails.append(f"old path still present: {old}")
        elif act == "RETIRED_SYMLINK":
            if (ctx.root / old).is_symlink() or (ctx.root / old).exists():
                fails.append(f"symlink still present: {old}")
        elif act == "DELETED_APPROVED":
            if (ctx.root / old).exists():
                fails.append(f"file approved for deletion still present: {old}")
        elif act == "COLLISION":
            fails.append(f"unresolved collision: {old} -> {new}")
        elif act in ("DECISION_PENDING", "RETIRE_PENDING", "UNMAPPED"):
            warns.append(f"{act}: {old}")

    # 2. no old paths left anywhere in scope
    rows = path_rows(names, wave, ready_paths(ctx))
    rx = path_regex(rows)
    left = 0
    if rx:
        for rel in tracked_files(ctx):
            if in_scope(rel):
                continue
            p = ctx.root / rel
            if p.is_symlink() or not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for ln, line in enumerate(text.splitlines(), 1):
                for m in rx.finditer(line):
                    left += 1
                    if left <= 25:
                        fails.append(f"stale path {rel}:{ln}: {m.group(0)}")
    if left > 25:
        fails.append(f"... {left - 25} more stale paths")

    # 3. no symlinks under the wave's new plugins; 4. links, compile, parse
    new_plugins = {r["new_plugin"] for r in ledger}
    for plug in sorted(new_plugins):
        base = ctx.root / "plugins" / plug
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if "__pycache__" in p.parts or "build" in p.parts:
                continue
            if p.is_symlink():
                fails.append(f"symlink in package: {p.relative_to(ctx.root)}")
            elif p.suffix == ".md":
                for m in LINK_RE.finditer(p.read_text(encoding="utf-8", errors="replace")):
                    target = m.group(1)
                    if re.match(r"^[a-z]+:", target) or target.startswith(("/", "#")) or "apm_modules" in target:
                        continue
                    if not (p.parent / target).exists():
                        fails.append(f"broken link {p.relative_to(ctx.root)}: {target}")
            elif p.suffix == ".py":
                try:
                    compile(p.read_text(encoding="utf-8"), str(p), "exec")
                except SyntaxError as e:
                    fails.append(f"syntax error {p.relative_to(ctx.root)}: {e}")
            elif p.suffix == ".json":
                try:
                    json.loads(p.read_text(encoding="utf-8"))
                except ValueError as e:
                    fails.append(f"bad json {p.relative_to(ctx.root)}: {e}")
            elif p.suffix in (".yml", ".yaml"):
                try:
                    import yaml
                    yaml.safe_load(p.read_text(encoding="utf-8"))
                except Exception as e:  # noqa: BLE001
                    fails.append(f"bad yaml {p.relative_to(ctx.root)}: {e}")
    for r in ledger:
        if r["action"] in ("MOVED_TO_ENGINE", "MOVED_TO_ENGINE_TESTS") and r["new_path"].endswith(".py"):
            p = ctx.root / r["new_path"]
            if p.is_file():
                try:
                    compile(p.read_text(encoding="utf-8"), str(p), "exec")
                except SyntaxError as e:
                    fails.append(f"syntax error {r['new_path']}: {e}")

    # 5. fragile Python path expressions in files this wave moved (for human sign-off)
    manual = 0
    for r in ledger:
        if r["new_path"].endswith(".py") and r["action"].startswith("MOVED"):
            p = ctx.root / r["new_path"]
            if p.is_file():
                for ln, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                    if any(rx2.search(line) for rx2, _t in PY_EXPRS):
                        manual += 1
                        warns.append(f"path expression to review: {r['new_path']}:{ln}: {line.strip()[:90]}")

    # 6. directory-level mentions of a retired plugin folder (the exact-path rule cannot rewrite these)
    old_plugs = sorted({x["old_plugin"] for x in ledger})
    dir_rx = re.compile(r"plugins/(" + "|".join(map(re.escape, old_plugs)) + r")/(scripts|assets|references|tests|skills|agents)(?![\w.\-])")
    dir_hits = 0
    for rel in tracked_files(ctx):
        if in_scope(rel):
            continue
        p = ctx.root / rel
        if p.is_symlink() or not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            if dir_rx.search(line):
                dir_hits += 1
                if dir_hits <= 25:
                    warns.append(f"directory-level mention {rel}:{ln}: {line.strip()[:100]}")
    if dir_hits > 25:
        warns.append(f"... {dir_hits - 25} more directory-level mentions")

    for w in warns[:80]:
        print("warn:", w)
    if len(warns) > 80:
        print(f"warn: ... {len(warns) - 80} more")
    for f in fails:
        print("FAIL:", f)
    print(f"\nwave {wave}: {len(ledger)} ledger rows | {len(fails)} failures | {len(warns)} warnings "
          f"({manual} path expressions to review)")
    return 1 if fails else 0


# ------------------------------------------------------------------ cli
def main(argv: list[str] | None = None, ctx: Ctx | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["scan", "plan", "apply", "rollback", "dirfix", "verify"])
    ap.add_argument("--wave")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--show", type=int, default=12)
    args = ap.parse_args(argv)
    ctx = ctx or default_ctx()
    if args.command != "scan" and not args.wave:
        ap.error("--wave is required")
    if args.command == "scan":
        idx = scan(ctx, args.wave)
        with open(ctx.out / "reference-index.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["file", "line", "col", "token", "rule", "proposed_replacement", "status", "context"])
            w.writeheader()
            w.writerows(idx)
        files = {r["file"] for r in idx}
        print(f"reference-index.csv: {len(idx)} occurrences in {len(files)} files")
        for rule, n in Counter(r["rule"] for r in idx).most_common():
            print(f"  {rule:26}{n}")
        return 0
    if args.command == "plan":
        return cmd_plan(ctx, args.wave, args.show)
    if args.command == "apply":
        return cmd_apply(ctx, args.wave, args.yes)
    if args.command == "rollback":
        return cmd_rollback(ctx, args.wave)
    if args.command == "dirfix":
        return cmd_dirfix(ctx, args.wave, args.yes, args.show)
    return cmd_verify(ctx, args.wave)


if __name__ == "__main__":
    sys.exit(main())
