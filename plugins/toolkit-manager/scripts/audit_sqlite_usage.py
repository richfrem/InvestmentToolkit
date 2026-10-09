#!/usr/bin/env python3
"""
audit_sqlite_usage.py - Flag Python code that still reads or writes portfolio data outside SQLite.

Purpose:
    For every non-symlink .py file under plugins/ and investment_screener/, find string
    literals (and imported path constants) naming a legacy portfolio data file, follow the
    path through constants, function defaults, wrappers and call arguments, and classify
    each use site:
      READ_CONTENT   the file's content is opened or parsed
      STAT_ONLY      only existence / modification time / size is checked
      WRITE          the file is written, renamed or deleted
      VESTIGIAL      the path is only handed to a function known to ignore it
      UNUSED         a path constant that nothing in the repository uses (dead)
      CLI_DEFAULT    only the default of a command-line option
      NAME_LIST      listed in a collection of names (classification tables)
      MESSAGE        appears only in printed or logged text
      UNRESOLVED     could not be followed (reported, never silently dropped)
    Each live use site is reported with its function, the callers of that function inside
    the file, and whether the script is referenced elsewhere (skills, docs, other code).
    Read-only: never modifies any file. Tests and symlinks are skipped.
    Portfolio data lives only in domain_model.sqlite; any READ_CONTENT, STAT_ONLY, WRITE,
    VESTIGIAL or UNUSED finding outside ALLOWED_MIGRATION_TOOLS breaks that rule.

Layer:
    Audit (read-only guard)

Usage Examples:
    python3 plugins/toolkit-manager/scripts/audit_sqlite_usage.py --root .
    python3 plugins/toolkit-manager/scripts/audit_sqlite_usage.py --root . --check
    python3 plugins/toolkit-manager/scripts/audit_sqlite_usage.py --root . --json out.json --artifacts
    python3 plugins/toolkit-manager/scripts/audit_sqlite_usage.py --self-test

Key Functions (Index):
    - legacy_bindings(): string literals and imported constants that name a legacy file
    - classify_expr_use(): follow one path expression to its use sites
    - resolve_name_uses(): follow a path-holding name (constant, parameter) to its use sites
    - audit_file(): findings for one file
    - external_name_uses(): cross-module users of an exported path constant
    - run(): findings for every Python file under plugins/ and investment_screener/
    - python_violations(): findings that break the SQLite-only rule (outside ALLOWED_MIGRATION_TOOLS)
    - ts_violations(): TypeScript/JavaScript lines that name a retired file or path constant
    - report(): human-readable report
    - self_test(): fixture cases covering each known blind spot
    - main(): CLI; --check exits 1 when any violation exists

Key Input Dependencies:
    - The repository tree (plugins/, investment_screener/, tradingview-cdp/)

Key Output Dependencies:
    - Report on stdout; optional JSON; exit status for --check
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

LEGACY = {
    "portfolio.json": r"(?<![\w-])portfolio\.json",
    "target-portfolio.json": r"target-portfolio\.json",
    "trade-log.json": r"trade-log\.json",
    "orders_executed.jsonl": r"orders_executed\.jsonl",
    "cash_flows.json": r"cash_flows\.json",
    "account_policy.json": r"account_policy\.json",
    "watchlist.json": r"watchlists?\.json",
    "tradingview_alerts_actual.json": r"tradingview_alerts_actual\.json",
    "ta-sweep-results.json": r"ta-sweep-results\.json",
}
# Model/report artifacts rather than portfolio information; reported only with --artifacts.
ARTIFACTS = {
    "thesis_breaker_state.json": r"thesis_breaker_state\.json",
    "risk_snapshot.json": r"risk_snapshot\.json",
    "rebalance_plan.json": r"rebalance_plan\.json",
    "ytd_performance_report.json": r"ytd_performance_report\.json",
    "projections/": r"[\"'/]projections[\"'/]",
}
# Imported or defined constants that name a legacy file even when the literal lives elsewhere.
CONST_NAME_RX = re.compile(r"^(PORTFOLIO|TARGET_PORTFOLIO|THESIS|TARGET|TRADE_LOG|CASH_FLOWS?|ORDERS_EXECUTED|ACCOUNT_POLICY)_(PATH|FILE|JSON)$")
IGNORES_PATH = {"load_portfolio_state"}          # accepts a path for compatibility, never opens it
STAT_ATTRS = {"exists", "is_file", "stat", "getmtime", "getsize", "isfile"}
READ_ATTRS = {"read_text", "read_bytes", "open"}
WRITE_ATTRS = {"write_text", "write_bytes", "unlink", "rename", "replace", "touch"}
WRAPPERS = {"Path", "str", "fspath", "join", "abspath", "realpath", "expanduser", "normpath"}
MESSAGE_CALLS = {"print", "log_fail", "log_ok", "log_warn", "warning", "error", "info", "write", "echo", "exit", "debug"}
SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", "ARCHIVE", "worktrees", ".git", "dist"}


def link_parents(tree):
    """Link parents."""
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            c._p = n


def doc_ids(tree):
    """Doc ids."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body \
           and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant):
            out.add(id(n.body[0].value))
    return out


def callee_name(call):
    """Callee name."""
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return "?"


def open_is_write(call):
    """Open is write."""
    for a in list(call.args[1:2]) + [k.value for k in call.keywords if k.arg == "mode"]:
        if isinstance(a, ast.Constant) and isinstance(a.value, str) and any(c in a.value for c in "wax"):
            return True
    return False


def enclosing_func(node):
    """Enclosing func."""
    cur = node
    while cur is not None:
        cur = getattr(cur, "_p", None)
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur.name
    return "<module>"


def is_env_get(call):
    """Is env get."""
    return callee_name(call) in {"get", "getenv"} and isinstance(call.func, ast.Attribute)


_TRANSPARENT_ATTRS = {"resolve", "absolute", "parent", "expanduser", "with_suffix", "with_name"}


def _passes_through(cur, p):
    """True when parent ``p`` keeps the path value held by ``cur`` (so the climb continues)."""
    if isinstance(p, (ast.JoinedStr, ast.FormattedValue, ast.BoolOp)):
        return True
    if isinstance(p, ast.BinOp):
        return isinstance(p.op, (ast.Div, ast.Add))      # d / "x.json"; path + ".tmp"
    if isinstance(p, ast.IfExp):
        return cur is not p.test
    if isinstance(p, ast.Call):
        if cur in p.args and callee_name(p) in WRAPPERS:
            return True
        return is_env_get(p) and len(p.args) >= 2 and cur is p.args[1]   # os.environ.get("X", <this>)
    return False


def climb(node):
    """Climb through value-preserving wrappers to the node that finally consumes the path.

    Returns:
        (node, parent): the outermost wrapper still holding the path and the node consuming it;
        parent is None when the climb reaches the module root.
    """
    cur = node
    while True:
        p = getattr(cur, "_p", None)
        if p is None:
            return cur, None
        if _passes_through(cur, p):
            cur = p
        elif isinstance(p, ast.Attribute) and p.attr in _TRANSPARENT_ATTRS and isinstance(getattr(p, "_p", None), ast.Call):
            cur = p._p
        else:
            return cur, p


def T(kind, node):
    """T."""
    return (kind, getattr(node, "lineno", 0), enclosing_func(node))


def _classify_attribute_parent(parent):
    """Use of a path held in ``Path(...).<attr>``: read, write, stat or unresolved."""
    call = getattr(parent, "_p", None)
    if parent.attr in WRITE_ATTRS:
        return {T("WRITE", parent)}
    if parent.attr == "open" and isinstance(call, ast.Call):
        return {T("WRITE" if open_is_write(call) else "READ_CONTENT", parent)}
    if parent.attr in READ_ATTRS:
        return {T("READ_CONTENT", parent)}
    if parent.attr in STAT_ATTRS:
        return {T("STAT_ONLY", parent)}
    return {T("UNRESOLVED", parent)}


def _classify_known_call(call, kw, cn):
    """Use sites for calls whose behaviour is known from the callee name; None when not known."""
    if cn == "open":
        return {T("WRITE" if open_is_write(call) else "READ_CONTENT", call)}
    if cn in STAT_ATTRS:
        return {T("STAT_ONLY", call)}
    if cn in {"copyfile", "copy", "copy2", "move", "remove", "unlink", "rmtree", "replace", "rename"}:
        return {T("WRITE", call)}
    if cn in {"load", "loads"} and call.args and not isinstance(call.args[0], ast.Constant):
        return {T("READ_CONTENT", call)}
    if cn == "add_argument":
        return {T("CLI_DEFAULT" if kw == "default" else "MESSAGE", call)}
    if cn in IGNORES_PATH:
        return {T("VESTIGIAL", call)}
    if cn in MESSAGE_CALLS:
        return {T("MESSAGE", call)}
    return None


def _classify_call_parent(node, parent, tree, depth, funcs, seen):
    """Use of a path passed to a call: a known callee, or follow it into a function in this file."""
    call = parent if isinstance(parent, ast.Call) else parent._p
    kw = parent.arg if isinstance(parent, ast.keyword) else None
    cn = callee_name(call)
    known = _classify_known_call(call, kw, cn)
    if known is not None:
        return known
    if cn in funcs and depth < 5:
        fn = funcs[cn]
        names = [a.arg for a in fn.args.posonlyargs + fn.args.args]
        target = kw
        if target is None and node in call.args:
            i = call.args.index(node)
            target = names[i] if i < len(names) else None
        if target:
            got = resolve_param_uses(fn, target, tree, depth + 1, funcs, seen)
            return got or {T("UNRESOLVED", call)}
    return {T(f"PASSED({cn})", call)}


def classify_expr_use(expr, tree, depth, funcs, seen):
    """Use sites of the path value held by ``expr``: a set of (kind, line, function)."""
    node, parent = climb(expr)
    if parent is None:
        return {T("UNRESOLVED", expr)}
    if isinstance(parent, ast.Assign):
        out = set()
        for t in parent.targets:
            if isinstance(t, ast.Name):
                out |= resolve_name_uses(t.id, tree, depth + 1, funcs, seen)
        return out or {T("UNRESOLVED", parent)}
    if isinstance(parent, ast.AnnAssign) and isinstance(parent.target, ast.Name):
        return resolve_name_uses(parent.target.id, tree, depth + 1, funcs, seen)
    if isinstance(parent, ast.Attribute):
        return _classify_attribute_parent(parent)
    if isinstance(parent, (ast.Call, ast.keyword)):
        return _classify_call_parent(node, parent, tree, depth, funcs, seen)
    if isinstance(parent, (ast.Set, ast.List, ast.Tuple, ast.Dict)):
        return {T("NAME_LIST", parent)}
    if isinstance(parent, ast.Compare):
        return {T("MESSAGE", parent)}
    return {T("UNRESOLVED", parent)}


def resolve_param_uses(fn, param, tree, depth, funcs, seen):
    """Resolve param uses."""
    key = (fn.name, param)
    if key in seen:
        return set()
    seen = seen | {key}
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and n.id == param and isinstance(n.ctx, ast.Load):
            out |= classify_expr_use(n, tree, depth, funcs, seen)
    return out


def resolve_name_uses(name, tree, depth, funcs, seen):
    """Resolve name uses."""
    if depth > 6:
        return {("UNRESOLVED", 0, "<depth>")}
    key = ("name", name)
    if key in seen:
        return set()
    seen = seen | {key}
    out = set()
    # the name used as a parameter default (positional, keyword-only)
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = fn.args
            pos = a.posonlyargs + a.args
            pairs = list(zip(pos[len(pos) - len(a.defaults):], a.defaults)) if a.defaults else []
            pairs += [(arg, d) for arg, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None]
            for arg, d in pairs:
                if isinstance(d, ast.Name) and d.id == name:
                    out |= resolve_param_uses(fn, arg.arg, tree, depth + 1, funcs, seen)
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load):
            if isinstance(getattr(n, "_p", None), ast.arguments):
                continue
            out |= classify_expr_use(n, tree, depth, funcs, seen)
    return out


def legacy_bindings(tree, names_rx):
    """Yield (node, legacy_name, kind): string literals naming a legacy file, plus imported
    path constants (PORTFOLIO_FILE, ...) whose literal lives in another module."""
    docs = doc_ids(tree)
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
            for name, rx in names_rx.items():
                if re.search(rx, n.value):
                    yield n, name, "literal"
        elif isinstance(n, ast.ImportFrom):
            for al in n.names:
                if CONST_NAME_RX.match(al.asname or al.name):
                    yield n, f"<imported {al.name}>", "import"


def external_name_uses(root, name, rel, all_files):
    """Files that import ``name`` from this module (or use ``module.name``). A bare name match is
    not enough: generic names such as TARGET_PATH are defined independently in many files."""
    mod = Path(rel).stem
    imp = re.compile(r"from\s+(?:[\w.]*\.)?" + re.escape(mod) + r"\s+import\s+(?:\([^)]*|[^\n]*)\b" + re.escape(name) + r"\b", re.S)
    attr = re.compile(r"\b" + re.escape(mod) + r"\." + re.escape(name) + r"\b")
    out = []
    for f in all_files:
        if f == rel:
            continue
        text = (root / f).read_text(errors="ignore")
        if imp.search(text) or attr.search(text):
            out.append(f)
    return out


PARAM_RX = re.compile(r"^(portfolio|target_portfolio|thesis|target|trade_log|cash_flows?|orders_executed|account_policy)_(path|file)$")


def function_refs(tree, fn):
    """Where ``fn`` is called or referenced as a value (e.g. stored in a dispatch table)."""
    refs = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id == fn and isinstance(n.ctx, ast.Load):
            refs.add(enclosing_func(n))
    return sorted(refs)


def cli_dest(call):
    """The attribute name argparse stores an add_argument() option under."""
    for k in call.keywords:
        if k.arg == "dest" and isinstance(k.value, ast.Constant):
            return k.value.value
    for a in call.args:
        if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("--"):
            return a.value.lstrip("-").replace("-", "_")
    return None


def cli_flows(tree, funcs, names_rx):
    """add_argument() options whose help or default names a legacy file: follow ``args.<dest>``."""
    found = []
    for call in ast.walk(tree):
        if isinstance(call, ast.Call) and callee_name(call) == "add_argument":
            text = " ".join(k.value.value for k in call.keywords
                            if k.arg in ("help", "default", "metavar") and isinstance(k.value, ast.Constant) and isinstance(k.value.value, str))
            hit = next((n for n, rx in names_rx.items() if re.search(rx, text)), None)
            dest = cli_dest(call)
            if hit and dest:
                uses = set()
                for a in ast.walk(tree):
                    if isinstance(a, ast.Attribute) and a.attr == dest and isinstance(a.ctx, ast.Load) and isinstance(a.value, ast.Name):
                        uses |= classify_expr_use(a, tree, 0, funcs, frozenset())
                found.append((call, hit, dest, uses))
    return found


def _unresolved(uses):
    """Unresolved."""
    return not uses or all(k == "UNRESOLVED" for k, *_ in uses)


def _literal_uses(node, tree, func, funcs, root, rel, all_files):
    """Use sites of one legacy string literal, falling back to UNUSED / EXPORTED for module constants."""
    uses = classify_expr_use(node, tree, 0, funcs, frozenset())
    if _unresolved(uses):
        p = climb(node)[1]
        if isinstance(p, ast.Assign) and isinstance(p.targets[0], ast.Name) and func == "<module>":
            nm = p.targets[0].id
            if _unresolved(resolve_name_uses(nm, tree, 0, funcs, frozenset())):
                ext = external_name_uses(root, nm, rel, all_files)
                uses = {("UNUSED" if not ext else "EXPORTED", node.lineno, f"{nm} <- {ext[:3]}")}
    return uses


def _param_findings(funcs, funcs_by_line_done, funcs_tree):
    """(function, parameter, uses) for parameters named like a legacy path that reach file I/O."""
    tree = funcs_tree
    for fn in funcs.values():
        for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs:
            if PARAM_RX.match(a.arg):
                uses = {u for u in resolve_param_uses(fn, a.arg, tree, 0, funcs, frozenset())
                        if u[0] in ("READ_CONTENT", "STAT_ONLY", "WRITE")}
                if uses:
                    yield fn, a.arg, uses


def audit_file(path: Path, root: Path, names_rx, all_files):
    """Findings for one Python file: literal and imported-constant bindings, CLI options, path parameters."""
    src = path.read_text()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    link_parents(tree)
    funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    rel = str(path.relative_to(root))
    out = []

    def add(line, legacy, func, uses, via=""):
        """Add."""
        io = {k for k, *_ in uses} & {"READ_CONTENT", "STAT_ONLY", "WRITE"}
        refs = {fn: function_refs(tree, fn) for k, ln, fn in uses if k in io and fn in funcs}
        out.append({"file": rel, "line": line, "legacy": legacy + via, "func": func,
                    "uses": sorted(uses), "internal_refs": refs})

    for node, legacy, kind in legacy_bindings(tree, names_rx):
        if kind == "import":
            names = [al.asname or al.name for al in node.names if CONST_NAME_RX.match(al.asname or al.name)]
            uses = set()
            for nm in names:
                uses |= resolve_name_uses(nm, tree, 0, funcs, frozenset())
            add(node.lineno, legacy, "<module>", uses)
        else:
            func = enclosing_func(node)
            add(node.lineno, legacy, func, _literal_uses(node, tree, func, funcs, root, rel, all_files))

    for call, hit, dest, uses in cli_flows(tree, funcs, names_rx):
        add(call.lineno, hit, "<cli>", uses or {("CLI_DEFAULT", call.lineno, dest)}, via=f" (via --{dest.replace('_','-')})")

    # parameters named like a legacy path that reach file I/O, with no literal in sight
    for fn, param, uses in _param_findings(funcs, None, tree):
        if not any(o["line"] == fn.lineno and o["func"] == "<param>" for o in out):
            add(fn.lineno, f"<param {param}>", "<param>", uses)
    return out


def verdict(uses):
    """Verdict."""
    kinds = {k for k, *_ in uses}
    for k in ("WRITE", "READ_CONTENT", "STAT_ONLY", "VESTIGIAL", "EXPORTED", "UNUSED"):
        if k in kinds:
            return k
    rest = kinds - {"UNRESOLVED"}
    if rest and rest <= {"CLI_DEFAULT", "MESSAGE", "NAME_LIST"}:
        return "/".join(sorted(rest))
    if rest:
        return "PASSED:" + ",".join(sorted(rest))
    return "UNRESOLVED"


def referenced_by(root, rel):
    """Referenced by."""
    base = Path(rel).name
    r = subprocess.run(["grep", "-rIl", "--include=*.py", "--include=*.md", "--include=*.json", "--include=*.sh", "--include=*.ts",
                        "-e", base, "plugins", "investment_screener", "AGENTS.md", "run_tests.py"],
                       cwd=root, capture_output=True, text=True)
    return [f for f in r.stdout.split("\n") if f and f != rel and "node_modules" not in f
            and "/tests/" not in f and "ARCHIVE" not in f and "worktrees" not in f]


def collect(root: Path):
    """Collect."""
    files = []
    for top in ("plugins", "investment_screener"):
        for p in sorted((root / top).rglob("*.py")):
            rel = p.relative_to(root)
            if p.is_symlink() or any(s in rel.parts for s in SKIP_DIRS) or "tests" in rel.parts or p.name.startswith("test_"):
                continue
            files.append(str(rel))
    return files


def run(root: Path, artifacts: bool):
    """Run."""
    names_rx = dict(LEGACY)
    if artifacts:
        names_rx.update(ARTIFACTS)
    files = collect(root)
    found = []
    for rel in files:
        found += audit_file(root / rel, root, names_rx, files)
    for f in found:
        f["verdict"] = verdict(f["uses"])
    return found


# One-time migration tools that read the retired files to load them into SQLite. Frozen: adding
# an entry needs an ADR.
ALLOWED_MIGRATION_TOOLS = {
    "migrate_portfolio_to_sqlite.py",
    "migrate_target_portfolio_to_sqlite.py",
    "migrate_wave4_to_sqlite.py",
    "migrate_account_policy_to_sqlite.py",
    "remove_drift_threshold_fields.py",
}
VIOLATION_VERDICTS = ("READ_CONTENT", "STAT_ONLY", "WRITE", "VESTIGIAL", "UNUSED")
TS_ROOTS = ("investment_screener/backend/src", "investment_screener/frontend/src", "tradingview-cdp")
TS_SUFFIXES = {".ts", ".tsx", ".js", ".mjs", ".cjs"}
TS_SKIP_PARTS = {"node_modules", "dist", "tests", "__tests__", "test", "coverage", ".vite"}
TS_RX = re.compile("|".join(list(LEGACY.values()) + [
    r"\bPORTFOLIO_FILE\b", r"\bTHESIS_FILE\b", r"\bTARGET_PORTFOLIO_FILE\b", r"\breadPortfolio\(",
]))


def python_violations(found):
    """Findings that break the SQLite-only rule: live I/O, vestigial or unused retired-path
    references in any file other than the frozen migration tools."""
    return [f for f in found
            if f["verdict"] in VIOLATION_VERDICTS and Path(f["file"]).name not in ALLOWED_MIGRATION_TOOLS]


def ts_violations(root: Path):
    """(file, line, text) for TypeScript/JavaScript lines naming a retired file or path constant."""
    out = []
    for top in TS_ROOTS:
        base = root / top
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            rel = p.relative_to(root)
            if p.suffix not in TS_SUFFIXES or not p.is_file() or p.is_symlink() \
               or any(s in rel.parts for s in TS_SKIP_PARTS) or ".test." in p.name or ".spec." in p.name:
                continue
            for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                if TS_RX.search(line):
                    out.append((str(rel), i, line.strip()[:160]))
    return out


def exists_on_disk(root, legacy):
    """Exists on disk."""
    d = root / "investment_screener/backend/data"
    return any((d / x).exists() for x in (legacy, "theses/" + legacy))


def report(root, found):
    """Report."""
    live = [f for f in found if f["verdict"] in ("READ_CONTENT", "STAT_ONLY", "WRITE")]
    print(f"{len(found)} legacy references in {len({f['file'] for f in found})} files; "
          f"{len(live)} are live I/O in {len({f['file'] for f in live})} files\n")
    groups = {}
    for f in found:
        groups.setdefault(f["verdict"], []).append(f)
    order = ["WRITE", "READ_CONTENT", "STAT_ONLY", "VESTIGIAL", "UNUSED", "EXPORTED", "UNRESOLVED"]
    for v in sorted(groups, key=lambda x: (order.index(x) if x in order else 9, x)):
        g = groups[v]
        print(f"=== {v}: {len(g)} in {len({f['file'] for f in g})} file(s)")
        if v in ("CLI_DEFAULT", "MESSAGE", "NAME_LIST", "CLI_DEFAULT/MESSAGE"):
            continue
        printed = set()
        for f in g:
            key = (f["file"], f["line"], f["legacy"], tuple(f["uses"]))
            if key in printed:
                continue
            printed.add(key)
            disk = "on-disk" if exists_on_disk(root, re.sub(r"^<[a-z]+ [^>]*>|\s\(via.*$", "", f["legacy"]) or f["legacy"]) else "MISSING"
            if v in ("READ_CONTENT", "STAT_ONLY", "WRITE"):
                for k, ln, fn in f["uses"]:
                    if k == v:
                        refs = f["internal_refs"].get(fn)
                        cs = f" referenced-in-file-by={refs}" if refs is not None else ""
                        print(f"  {f['file']}:{ln} in {fn}() -> {f['legacy']} [{disk}]{cs} | script referenced by {len(referenced_by(root, f['file']))} file(s)")
            else:
                extra = ""
                if v == "EXPORTED":
                    extra = f" used elsewhere: {[u for u in f['uses'] if u[0]=='EXPORTED']}"
                print(f"  {f['file']}:{f['line']} {f['legacy']} [{disk}]{extra}")


# ── self test ────────────────────────────────────────────────────────────────────────────
FIXTURES = {
    "direct_open": ("def f():\n    with open('x/portfolio.json') as fh:\n        return fh.read()\n", "READ_CONTENT"),
    "const_read_text": ("from pathlib import Path\nP = Path('d') / 'target-portfolio.json'\ndef f():\n    return P.read_text()\n", "READ_CONTENT"),
    "write_mode": ("P = 'd/trade-log.json'\ndef f(d):\n    open(P, 'w').write(d)\n", "WRITE"),
    "write_attr": ("from pathlib import Path\nP = Path('cash_flows.json')\ndef f(d):\n    P.write_text(d)\n", "WRITE"),
    "stat_only": ("import os\nP = 'portfolio.json'\ndef age():\n    return os.path.getmtime(P)\n", "STAT_ONLY"),
    "exists_only": ("import os\nP = 'portfolio.json'\ndef has():\n    return os.path.exists(P)\n", "STAT_ONLY"),
    "env_get_default": ("import os\nP = os.environ.get('X', os.path.join('d', 'portfolio.json'))\ndef f():\n    return open(P).read()\n", "READ_CONTENT"),
    "boolop_vestigial": ("P = 'portfolio.json'\ndef load_portfolio_state(p): pass\ndef f(path=None):\n    return load_portfolio_state(path or P)\n", "VESTIGIAL"),
    "kwonly_default": ("P = 'target-portfolio.json'\ndef f(*, path=P):\n    return open(path).read()\n", "READ_CONTENT"),
    "fstring_path": ("def f(d):\n    return open(f'{d}/portfolio.json').read()\n", "READ_CONTENT"),
    "param_default_flow": ("P = 'portfolio.json'\ndef inner(p):\n    return open(p).read()\ndef outer(p=P):\n    return inner(p)\n", "READ_CONTENT"),
    "ignored_param": ("P = 'portfolio.json'\ndef load_portfolio_state(p): pass\ndef f(p=P):\n    return load_portfolio_state(p)\n", "VESTIGIAL"),
    "unused_const": ("P = 'portfolio.json'\ndef f():\n    return 1\n", "UNUSED"),
    "cli_default": ("import argparse\nap = argparse.ArgumentParser()\nap.add_argument('--p', default='portfolio.json')\n", "CLI_DEFAULT"),
    "derived_tmp_write": ("import os\nP = 'target-portfolio.json'\ndef save(d):\n    tmp = P + '.tmp'\n    open(tmp, 'w').write(d)\n    os.replace(tmp, P)\n", "WRITE"),
    "with_suffix_write": ("from pathlib import Path\nP = Path('portfolio.json')\ndef save(d):\n    P.with_suffix('.tmp').write_text(d)\n", "WRITE"),
    "name_list": ("NAMES = {'portfolio.json', 'x'}\n", "NAME_LIST"),
    "message_only": ("def f():\n    print('portfolio.json not found')\n", "MESSAGE"),
    "shutil_copy": ("import shutil\ndef f():\n    shutil.copyfile('a', 'portfolio.json')\n", "WRITE"),
    "imported_const": ("from paths import PORTFOLIO_FILE\ndef f():\n    return open(PORTFOLIO_FILE).read()\n", "READ_CONTENT"),
    "cli_help_then_open": ("import argparse\nap = argparse.ArgumentParser()\nap.add_argument('--target-file', required=True, help='Path to target-portfolio.json')\nargs = ap.parse_args()\nopen(args.target_file).read()\n", "READ_CONTENT"),
    "path_named_param": ("def load(portfolio_path):\n    return open(portfolio_path).read()\n", "READ_CONTENT"),
    "dispatch_table_ref": ("def chk():\n    return open('portfolio.json').read()\nCHECKS = [('x', chk)]\n", "READ_CONTENT"),
    "exported_via_import": ({"a.py": "PORTFOLIO_PATH = 'portfolio.json'\n", "b.py": "from a import PORTFOLIO_PATH\ndef f():\n    return open(PORTFOLIO_PATH).read()\n"}, "EXPORTED"),
    "generic_name_not_exported": ({"a.py": "TARGET_PATH = 'target-portfolio.json'\n", "b.py": "TARGET_PATH = 3\n"}, "UNUSED"),
}


def self_test():
    """Self test."""
    ok = True
    for name, (src, want) in FIXTURES.items():
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "plugins").mkdir()
            for fname, text in (src if isinstance(src, dict) else {"m.py": src}).items():
                (root / "plugins" / fname).write_text(text)
            got = run(root, False)
            vs = {f["verdict"] for f in got}
            good = want in vs
            ok &= good
            print(f"{'ok  ' if good else 'FAIL'} {name:<20} want {want:<13} got {sorted(vs)}")
    return ok


def main():
    """Main."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json")
    ap.add_argument("--artifacts", action="store_true", help="also report model/report JSON artifacts")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--check", action="store_true", help="exit 1 when Python or TS/JS violations exist")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test() else 1)
    root = Path(a.root).resolve()
    found = run(root, a.artifacts)
    report(root, found)
    if a.json:
        Path(a.json).write_text(json.dumps(found, indent=1, default=list))
    if a.check:
        py, ts = python_violations(found), ts_violations(root)
        print(f"\nGUARD: {len(py)} Python and {len(ts)} TypeScript/JavaScript violation(s)")
        sys.exit(1 if py or ts else 0)


if __name__ == "__main__":
    main()
