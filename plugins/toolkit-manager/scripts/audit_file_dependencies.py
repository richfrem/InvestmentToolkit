#!/usr/bin/env python3
"""
audit_file_dependencies.py - Inventory and guard every place code reads or writes a data file.

Purpose:
    The data rule is SQLite only: no .py, .ts, .tsx or .js file reads or writes a JSON,
    JSONL, CSV or spreadsheet file, or a data directory such as research/, daily-briefs/,
    etf_analysis/, 13f/ or projections/. This tool finds every place that still does, and
    compares the result with a register (docs/architecture/file-dependency-register.json)
    in which each remaining dependency is listed with the step that removes it.
      - Python: reuses the path-following engine of audit_sqlite_usage.py (constants,
        parameters, wrappers, call arguments) with extension and directory patterns.
      - TypeScript/JavaScript: lines that call fs read/write/exists/readdir functions,
        name a .json/.jsonl file, or import a .json file.
    --check fails when a dependency is found that the register does not list (a new
    dependency), or when the register lists one that no longer exists (remove the entry).
    --strict fails while the register still lists anything other than the tooling
    dispositions in FINAL_DISPOSITIONS; it is the end state of the migration.

Layer:
    Audit (read-only guard)

Usage Examples:
    python3 plugins/toolkit-manager/scripts/audit_file_dependencies.py --root .
    python3 plugins/toolkit-manager/scripts/audit_file_dependencies.py --root . --check
    python3 plugins/toolkit-manager/scripts/audit_file_dependencies.py --root . --strict
    python3 plugins/toolkit-manager/scripts/audit_file_dependencies.py --root . --write-register

Key Functions (Index):
    - python_dependencies(): (file, kind, label) for Python files that read or write a data file
    - ts_dependencies(): (file, kind, label) for TypeScript/JavaScript files that do
    - find_dependencies(): both lists as register keys
    - load_register(): the register entries
    - compare(): new dependencies and stale register entries
    - strict_remaining(): register entries that are not allowed in the end state
    - main(): CLI

Key Input Dependencies:
    - The repository tree (plugins/, investment_screener/, tradingview-cdp/, root *.py)
    - docs/architecture/file-dependency-register.json
    - audit_sqlite_usage.py (path-following engine)

Key Output Dependencies:
    - Report on stdout; exit status for --check and --strict; the register with --write-register
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_sqlite_usage as engine  # noqa: E402

REGISTER_PATH = "docs/architecture/file-dependency-register.json"
# Dispositions allowed to remain in the end state (--strict).
FINAL_DISPOSITIONS = {"tooling"}
NAME_PATTERNS = {
    "json-file": r"\.jsonl?(?![\w])",
    "table-file": r"\.(csv|xlsx|parquet|pkl)(?![\w])",
    "data-dir": r"[\"'/](research|daily-briefs|etf_analysis|13f|projections)[\"'/]",
}
COUNTED_VERDICTS = {"READ_CONTENT": "read", "WRITE": "write", "STAT_ONLY": "exists"}
TS_ROOTS = ("investment_screener/backend/src", "investment_screener/frontend/src", "tradingview-cdp")
TS_SUFFIXES = {".ts", ".tsx", ".js", ".mjs", ".cjs"}
TS_SKIP_PARTS = {"node_modules", "dist", "tests", "__tests__", "test", "coverage", ".vite"}
TS_KINDS = {
    "fs-read": re.compile(r"\bfs\.(?:promises\.)?(?:readFile|readFileSync|createReadStream|readdir|readdirSync)\b"),
    "fs-write": re.compile(r"\bfs\.(?:promises\.)?(?:writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream|mkdir|mkdirSync)\b"),
    "fs-exists": re.compile(r"\bfs\.(?:existsSync|statSync|promises\.stat|promises\.access)\b"),
    "json-literal": re.compile(r"\.jsonl?['\"`]"),
}


def _literal_label(line: str) -> str:
    """The first quoted path-like string on ``line`` that carries a data extension, else ''."""
    m = re.search(r"['\"]([^'\"\n]*\.(?:jsonl?|csv|xlsx)[^'\"\n]*)['\"]", line)
    return m.group(1) if m else ""


def python_dependencies(root: Path) -> set[tuple[str, str, str]]:
    """(file, kind, label) for each Python file that reads, writes or checks a data file."""
    files = engine.collect(root)
    files += [p.name for p in sorted(root.glob("*.py")) if not p.is_symlink()]
    found: set[tuple[str, str, str]] = set()
    for rel in files:
        path = root / rel
        lines = path.read_text(errors="ignore").splitlines()
        for item in engine.audit_file(path, root, NAME_PATTERNS, files):
            verdict = engine.verdict(item["uses"])
            kind = COUNTED_VERDICTS.get(verdict)
            if kind is None and verdict.startswith("PASSED"):
                kind = "passed"
            if kind is None and verdict == "UNRESOLVED":
                kind = "unresolved"
            if kind is None:
                continue
            text = lines[item["line"] - 1] if 0 < item["line"] <= len(lines) else ""
            label = _literal_label(text) or item["legacy"]
            if " " in label or label.startswith("http") or "://" in text and not _literal_label(text):
                continue  # prose (help text, messages) or a URL, not a file path
            found.add((rel, kind, label))
    return found


def ts_dependencies(root: Path) -> set[tuple[str, str, str]]:
    """(file, kind, label) for each TypeScript/JavaScript file that touches a data file."""
    found: set[tuple[str, str, str]] = set()
    for top in TS_ROOTS:
        base = root / top
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            rel = p.relative_to(root)
            if p.suffix not in TS_SUFFIXES or not p.is_file() or p.is_symlink() \
               or any(s in rel.parts for s in TS_SKIP_PARTS) or ".test." in p.name or ".spec." in p.name:
                continue
            for line in p.read_text(errors="ignore").splitlines():
                for kind, rx in TS_KINDS.items():
                    if rx.search(line):
                        found.add((str(rel), kind, ""))
    return found


def find_dependencies(root: Path) -> set[tuple[str, str, str]]:
    """Every Python and TypeScript/JavaScript data-file dependency as (file, kind, label)."""
    return python_dependencies(root) | ts_dependencies(root)


def load_register(root: Path) -> list[dict]:
    """The register entries, or [] when the register does not exist."""
    path = root / REGISTER_PATH
    return json.loads(path.read_text())["dependencies"] if path.exists() else []


def _entry_key(entry: dict) -> tuple[str, str, str]:
    return (entry["file"], entry["kind"], entry.get("label", ""))


def compare(found: set, register: list[dict]):
    """(new, stale): found-but-unregistered and registered-but-gone dependencies."""
    registered = {_entry_key(e) for e in register}
    return sorted(found - registered), sorted(registered - found)


def strict_remaining(register: list[dict]) -> list[dict]:
    """Register entries whose disposition may not remain in the end state."""
    return [e for e in register if e.get("disposition") not in FINAL_DISPOSITIONS]


def main() -> int:
    """CLI: report; --check and --strict set the exit status; --write-register rewrites the register."""
    parser = argparse.ArgumentParser(description="Inventory and guard data-file dependencies in code.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--check", action="store_true", help="Fail on new or stale dependencies")
    parser.add_argument("--strict", action="store_true", help="Fail while the register lists non-tooling entries")
    parser.add_argument("--write-register", action="store_true",
                        help="Add unlisted dependencies to the register as 'unreviewed' and drop stale ones")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    found = find_dependencies(root)
    register = load_register(root)
    new, stale = compare(found, register)
    if args.write_register:
        kept = [e for e in register if _entry_key(e) in found]
        kept += [{"file": f, "kind": k, "label": lbl, "disposition": "unreviewed", "step": "", "note": ""}
                 for f, k, lbl in new]
        kept.sort(key=lambda e: (e["file"], e["kind"], e.get("label", "")))
        out = root / REGISTER_PATH
        out.write_text(json.dumps({"dependencies": kept}, indent=1) + "\n")
        print(f"register written: {len(kept)} entries ({len(new)} added, {len(stale)} removed)")
        return 0
    print(f"{len(found)} data-file dependencies found; {len(register)} registered")
    for f, k, lbl in new:
        print(f"NEW   {f} [{k}] {lbl}")
    for f, k, lbl in stale:
        print(f"STALE {f} [{k}] {lbl}  (no longer found: remove from the register)")
    remaining = strict_remaining(register)
    if args.strict:
        print(f"{len(remaining)} registered dependencies are not allowed in the end state")
    failed = bool(new or stale) if args.check else False
    failed = failed or (args.strict and (bool(remaining) or bool(new)))
    print("FILE-DEPENDENCY GUARD:", "FAIL" if failed else "ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
