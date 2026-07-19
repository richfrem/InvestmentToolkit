"""audit_json_usage.py — Repository-wide JSON/JSONL discovery, reference, and
legitimacy audit (Plan Task 12A).

Purpose:
    Deterministically scan every .json/.jsonl file in the repository plus every
    code/doc reference to those files, classify each file's legitimacy, and
    write both human-readable and machine-readable reports. Read-only —
    NEVER deletes, moves, or rewrites a discovered file.

Layer: Codify / Audit

Key Input Dependencies:
    - The full repository tree (scanned in place, no external data files required)

Key Output Dependencies:
    - docs/architecture/json-discovery-audit.md / .json
    - docs/architecture/allowed-json-register.md / .json

Usage:
    python3 audit_json_usage.py --root <repo_root> --out docs/architecture

Index:
    - EXCLUDED_DIRS, JSON_EXTENSIONS, CODE_GLOBS, DOC_GLOBS
    - scan_json_files(root) -> list[dict]
    - scan_references(root, include_globs) -> list[dict]
    - classify_file(path, references) -> str
    - build_register_entry(path, classification, references) -> dict
    - run_audit(root) -> dict
    - render_discovery_md(result) -> str
    - render_register_md(result) -> str
    - write_reports(result, out_dir) -> None
    - main() -> CLI entry point
"""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EXCLUDED_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    ".pytest_cache", "dist", "build", "coverage", ".cache",
    ".worktrees", "worktrees",
}

JSON_EXTENSIONS = {".json", ".jsonl"}

REFERENCE_PATTERNS = [
    (re.compile(r"\bjson\.load\("), "read"),
    (re.compile(r"\bjson\.loads\("), "read"),
    (re.compile(r"\bjson\.dump\("), "write"),
    (re.compile(r"\bjson\.dumps\("), "write"),
    (re.compile(r"\bJSON\.parse\("), "read"),
    (re.compile(r"\bJSON\.stringify\("), "write"),
    (re.compile(r"\bfs\.readFile(Sync)?\("), "read"),
    (re.compile(r"\bfs\.writeFile(Sync)?\("), "write"),
    (re.compile(r"\breadFileSync\("), "read"),
    (re.compile(r"\bwriteFileSync\("), "write"),
    (re.compile(r"\bopen\("), "open"),  # mode-dependent — resolved by _classify_open_mode
    (re.compile(r"\.jsonl?\b"), "mention"),
]

WRITE_MODE_RE = re.compile(r"""["\']w[b]?["\']|["\']a[b]?["\']""")
STRING_LITERAL_RE = re.compile(r"""["\']([^"\']+)["\']""")
IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
CONST_ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*[\w\[\], .\"']+)?\s*=\s*(.+?)\s*$")

DOC_EXTENSIONS = {".md"}
DOC_FILENAMES = {"AGENTS.md", "CLAUDE.md", "GEMINI.md", "README.md", "SKILL.md", "architecture.md"}


def _classify_open_line_operation(op: str, line: str) -> str:
    """Resolve a raw matched operation into read/write, given the full line text."""
    if op == "open":
        return "write" if WRITE_MODE_RE.search(line) else "read"
    if op == "mention":
        return "mention"
    return op

CLASSIFICATIONS = [
    "ALLOWED_AUTHORITATIVE_JSON",
    "ALLOWED_CONFIGURATION_JSON",
    "ALLOWED_MODEL_ARTIFACT_JSON",
    "ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL",
    "ALLOWED_TEST_FIXTURE_JSON",
    "ALLOWED_GENERATED_CACHE_JSON",
    "MIGRATE_TO_INTELLIGENCE_LEDGER",
    "GENERATE_FROM_LEDGER_OR_SQLITE",
    "ARCHIVE_LEGACY_READ_ONLY",
    "DELETE_AFTER_VERIFIED_ARCHIVE",
    "OUT_OF_SCOPE_FOR_THIS_PHASE",
    "UNKNOWN_REQUIRES_REVIEW",
]

ALLOWED_PREFIX = "ALLOWED_"

# One-line purpose text per ALLOWED_* classification, shown in the register's
# Purpose column. Mirrors the rationale coded into classify_file()'s matching
# rules rather than restating the classification name.
CLASSIFICATION_PURPOSE = {
    "ALLOWED_AUTHORITATIVE_JSON": (
        "Live application/execution state (portfolio holdings, targets, watchlist, "
        "trade log, cash flows, alerts) — outside the qualitative intelligence "
        "ledger's scope; mutated in place, not event-sourced."
    ),
    "ALLOWED_CONFIGURATION_JSON": (
        "Static configuration: plugin manifests, lockfiles, tsconfig, schemas, or "
        "template assets — not runtime data."
    ),
    "ALLOWED_MODEL_ARTIFACT_JSON": (
        "Generated valuation/projection artifact (e.g., data/projections/*.json) — "
        "model output, not source data."
    ),
    "ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL": (
        "An independent JSONL ledger for a different domain than the intelligence "
        "ledger (predictions, evolution/self-improvement events, context events)."
    ),
    "ALLOWED_TEST_FIXTURE_JSON": (
        "Test fixture, eval, or example data — not production data."
    ),
    "ALLOWED_GENERATED_CACHE_JSON": (
        "Regenerable cache or report output — safe to exist as long as its "
        "generating source is known."
    ),
}


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def _sha256_of(path: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _git(root: str, args: list) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", root] + args, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return ""


def scan_json_files(root: str) -> list:
    """Discover every .json/.jsonl file under root, excluding vendor/cache dirs.

    Args:
        root: Repository root directory to scan.

    Returns:
        List of dicts with path, extension, size_bytes, line_count, sha256,
        git_tracked, git_ignored, last_commit.
    """
    root_path = Path(root)
    found = []
    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root_path)
        if _is_excluded(rel):
            continue
        if path.suffix not in JSON_EXTENSIONS:
            continue
        rel_str = str(rel)
        try:
            content = path.read_text(errors="replace")
            line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        except Exception:
            line_count = 0
        tracked = _git(root, ["ls-files", "--error-unmatch", rel_str]) != ""
        ignored = _git(root, ["check-ignore", rel_str]) != ""
        last_commit = _git(root, ["log", "-1", "--format=%h %ai", "--", rel_str])
        found.append({
            "path": rel_str,
            "extension": path.suffix,
            "size_bytes": path.stat().st_size,
            "line_count": line_count,
            "sha256": _sha256_of(path),
            "git_tracked": tracked,
            "git_ignored": ignored,
            "last_commit": last_commit or None,
        })
    return found


def scan_references(root: str, include_globs: list) -> list:
    """Scan code/doc files for references to JSON/JSONL paths and operations.

    Captures the full line text (not just the matched operation token) so
    the linking pass can resolve the actual file being read/written, via
    either a literal path substring or a same-file constant assignment.

    Args:
        root: Repository root directory to scan.
        include_globs: Filename glob patterns to scan (e.g. ["*.py", "*.ts"]).

    Returns:
        List of dicts: referencing_file, line, matched_text, operation,
        line_text.
    """
    root_path = Path(root)
    refs = []
    seen_files = set()
    for pattern in include_globs:
        for path in root_path.rglob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(root_path)
            if _is_excluded(rel):
                continue
            if str(rel) in seen_files:
                continue
            seen_files.add(str(rel))
            try:
                lines = path.read_text(errors="replace").splitlines()
            except Exception:
                continue
            for lineno, line in enumerate(lines, start=1):
                matched_op = None
                matched_text = None
                for regex, op in REFERENCE_PATTERNS:
                    m = regex.search(line)
                    if m:
                        matched_op = _classify_open_line_operation(op, line)
                        matched_text = m.group(0)
                        break
                if matched_op:
                    refs.append({
                        "referencing_file": str(rel),
                        "line": lineno,
                        "matched_text": matched_text,
                        "operation": matched_op,
                        "line_text": line.strip(),
                    })
    return refs


def _build_constants_map(root: str, referencing_files: set) -> dict:
    """Build a per-file map of {CONST_NAME: json_filename} from assignment lines.

    Scans every line of every referencing file (not just operation-matched
    lines) for a `NAME = <expr>` assignment whose right-hand side contains a
    string literal ending in a known-looking `.json`/`.jsonl` filename.

    Args:
        root: Repository root directory.
        referencing_files: Set of repo-relative file path strings to scan.

    Returns:
        Dict of {file_path: {const_name: json_filename}}.
    """
    root_path = Path(root)
    result = {}
    for rel in referencing_files:
        path = root_path / rel
        try:
            lines = path.read_text(errors="replace").splitlines()
        except Exception:
            continue
        file_consts = {}
        for line in lines:
            m = CONST_ASSIGN_RE.match(line)
            if not m:
                continue
            name, expr = m.group(1), m.group(2)
            for literal in STRING_LITERAL_RE.findall(expr):
                if literal.endswith(".json") or literal.endswith(".jsonl"):
                    file_consts[name] = Path(literal).name
        if file_consts:
            result[rel] = file_consts
    return result


def _resolve_reference(ref: dict, known_names: set, constants_by_file: dict):
    """Resolve a raw reference line to a target JSON filename + confidence.

    Args:
        ref: A raw reference dict from scan_references().
        known_names: Set of every discovered JSON/JSONL filename (basenames).
        constants_by_file: Output of _build_constants_map().

    Returns:
        (resolved_filename, confidence) tuple, or (None, None) if unresolved.
        confidence is one of "exact", "probable".
    """
    line_text = ref["line_text"]

    # Exact: a string literal on this line ends with a known filename.
    for literal in STRING_LITERAL_RE.findall(line_text):
        name = Path(literal).name
        if name in known_names:
            return name, "exact"

    # Probable: an identifier token on this line resolves via a same-file constant.
    file_consts = constants_by_file.get(ref["referencing_file"], {})
    if file_consts:
        for token in IDENTIFIER_RE.findall(line_text):
            if token in file_consts:
                return file_consts[token], "probable"

    # Fallback: a known filename appears as bare, unquoted text on the line
    # (typical of prose/Markdown documentation mentions, e.g.
    # "Read ta-sweep-results.json before generating the report.").
    for name in known_names:
        if name in line_text:
            return name, "exact"

    return None, None


def link_references_to_files(root: str, files: list, raw_refs: list) -> None:
    """Link raw reference lines to their target JSON file entries, in place.

    Populates each file entry's known_producers, known_consumers, and
    doc_references lists with {referencing_file, line, confidence} dicts.

    Args:
        root: Repository root directory.
        files: List of file entries from scan_json_files() (mutated in place).
        raw_refs: Output of scan_references().
    """
    known_names = {Path(f["path"]).name for f in files}
    files_by_name = {}
    for f in files:
        files_by_name.setdefault(Path(f["path"]).name, []).append(f)
        f["known_producers"] = []
        f["known_consumers"] = []
        f["doc_references"] = []

    referencing_files = {r["referencing_file"] for r in raw_refs}
    constants_by_file = _build_constants_map(root, referencing_files)

    for ref in raw_refs:
        resolved_name, confidence = _resolve_reference(ref, known_names, constants_by_file)
        if not resolved_name:
            continue
        referencing_path = Path(ref["referencing_file"])
        is_doc = referencing_path.suffix in DOC_EXTENSIONS or referencing_path.name in DOC_FILENAMES

        entry = {
            "referencing_file": ref["referencing_file"],
            "line": ref["line"],
            "confidence": confidence,
        }
        for target in files_by_name.get(resolved_name, []):
            if is_doc:
                target["doc_references"].append({**entry, "confidence": "mention_only"})
            elif ref["operation"] == "write":
                target["known_producers"].append(entry)
            elif ref["operation"] == "read":
                target["known_consumers"].append(entry)
            else:
                # Path constructed/referenced but no explicit read/write call
                # on this line (e.g. `Path(...) / "file.json"`) — still a real
                # reference, default-bucketed as a consumer.
                target["known_consumers"].append(entry)


def classify_file(path: str, references: list) -> str:
    """Assign a classification to a discovered JSON/JSONL file path.

    Heuristic, illustrative-not-binding classification per the plan's Task
    12A starting categories. Defaults to UNKNOWN_REQUIRES_REVIEW for any
    path that doesn't match a known pattern — never silently out-of-scope.

    Args:
        path: Repo-relative file path.
        references: Reference entries already discovered for this path (unused
            by the heuristic today, reserved for future refinement).

    Returns:
        One of the CLASSIFICATIONS constants.
    """
    p = path.replace("\\", "/")
    name = Path(p).name

    if p in (
        "docs/architecture/json-discovery-audit.json",
        "docs/architecture/allowed-json-register.json",
    ):
        return "ALLOWED_GENERATED_CACHE_JSON"

    if "/.vite/" in p or "/dist/" in p or "/node_modules/" in p:
        return "ARCHIVE_LEGACY_READ_ONLY"

    if "/tests/fixtures/" in p or "/__fixtures__/" in p or name.startswith("sample"):
        return "ALLOWED_TEST_FIXTURE_JSON"

    if "/evals/" in p or "/references/examples/" in p:
        return "ALLOWED_TEST_FIXTURE_JSON"

    if p.endswith("predictions.jsonl") or p.endswith("evolution_events.jsonl") or p.endswith("context/events.jsonl"):
        return "ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL"

    if "/data/projections/" in p:
        return "ALLOWED_MODEL_ARTIFACT_JSON"

    if "/etf_analysis/" in p or "/13f/" in p:
        return "OUT_OF_SCOPE_FOR_THIS_PHASE"

    if "/data/cache/" in p or "/scripts/cache/" in p or p.endswith(".metrics.json") or name.startswith("latest-"):
        return "ALLOWED_GENERATED_CACHE_JSON"

    if p.endswith("ta-sweep-results.json"):
        return "MIGRATE_TO_INTELLIGENCE_LEDGER"

    if "/daily-briefs/" in p or "/reviews/daily/" in p or "/reviews/weekly/" in p:
        return "MIGRATE_TO_INTELLIGENCE_LEDGER"

    portfolio_domain_names = {
        "portfolio.json", "watchlist.json", "watchlists.json",
        "target-portfolio.json", "trade-log.json", "cash_flows.json",
        "account_policy.json", "thesis_breaker_state.json",
        "tradingview_alerts_actual.json",
    }
    if name in portfolio_domain_names:
        return "ALLOWED_AUTHORITATIVE_JSON"

    if name == "plugin.json" or p.endswith(".claude-plugin/plugin.json") or p.endswith(".claude-plugin/marketplace.json"):
        return "ALLOWED_CONFIGURATION_JSON"

    if "/assets/templates/" in p:
        return "ALLOWED_CONFIGURATION_JSON"

    if p.startswith("schemas/") or "/schemas/" in p:
        return "ALLOWED_CONFIGURATION_JSON"

    config_names = {
        "package.json", "package-lock.json", "tsconfig.json", "tsconfig.node.json",
        "tsconfig.app.json", "symlinks.json", "skills-lock.json", "plugin-sources.json",
    }
    if name in config_names:
        return "ALLOWED_CONFIGURATION_JSON"

    return "UNKNOWN_REQUIRES_REVIEW"


def run_audit(root: str) -> dict:
    """Run the full four-pass audit and return the structured result.

    Args:
        root: Repository root directory to audit.

    Returns:
        Dict with generated_at, files (each with classification + refs),
        and references (flat list).
    """
    files = scan_json_files(root)
    references = scan_references(
        root, include_globs=["*.py", "*.js", "*.ts", "*.tsx", "*.md", "*.yml", "*.yaml", "*.sh"]
    )

    link_references_to_files(root, files, references)

    for f in files:
        combined_refs = f["known_producers"] + f["known_consumers"]
        f["classification"] = classify_file(f["path"], combined_refs)
        f["migration_status"] = _migration_status(f)

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": files,
        "references": references,
        "temp_folder_files": [f for f in files if f["path"].startswith("temp/")],
    }


def _migration_status(f: dict) -> str:
    """Assign a plain-language migration status for MIGRATE_TO_INTELLIGENCE_LEDGER files.

    Args:
        f: A file entry dict (already classified).

    Returns:
        Human-readable migration status string, or "n/a" if not applicable.
    """
    if f["classification"] != "MIGRATE_TO_INTELLIGENCE_LEDGER":
        return "n/a"
    # As of this audit, Phase 3 (Tasks 12A/14-19, which would perform the actual
    # JSON-to-ledger migration) has not started. Phase 1/2 only migrated dated
    # research Markdown, never JSON. So every MIGRATE_TO_INTELLIGENCE_LEDGER file
    # is, by construction, not yet migrated — still the sole copy of its data.
    return "NOT_MIGRATED — still the only copy of this data; do not remove"


def render_discovery_md(result: dict) -> str:
    """Render the human-readable JSON discovery audit report."""
    files = result["files"]
    counts = {c: 0 for c in CLASSIFICATIONS}
    for f in files:
        counts[f["classification"]] = counts.get(f["classification"], 0) + 1

    lines = ["# JSON Discovery Audit", "", "## Summary", "", "| Category | Count |", "|---|---:|"]
    lines.append(f"| JSON files discovered | {sum(1 for f in files if f['extension'] == '.json')} |")
    lines.append(f"| JSONL files discovered | {sum(1 for f in files if f['extension'] == '.jsonl')} |")
    for c in CLASSIFICATIONS:
        lines.append(f"| Files classified {c} | {counts.get(c, 0)} |")

    lines += [
        "",
        "## High-Risk Findings",
        "",
        "- **Nothing has been migrated to SQLite/the intelligence ledger yet.** Phase 3 "
        "(the tasks that would actually move JSON data into `intelligence.sqlite` and "
        "retire the JSON source) has not started. Every file classified "
        "`MIGRATE_TO_INTELLIGENCE_LEDGER` below is still the sole, authoritative copy of "
        "its data — none are safe to remove.",
    ]
    vite_hits = [f for f in files if "/.vite/" in f["path"]]
    if vite_hits:
        lines.append(
            f"- **{len(vite_hits)} Vite dev-server cache file(s) are git-tracked and not "
            "gitignored** (e.g. `investment_screener/frontend/.vite/deps/_metadata.json`). "
            "This is a build tool artifact that should never be committed — worth adding to "
            "`.gitignore` and removing from git tracking (a separate, low-risk cleanup task, "
            "not part of this discovery pass)."
        )
    temp_files = result.get("temp_folder_files", [])
    if temp_files:
        lines.append(
            f"- **{len(temp_files)} JSON/JSONL file(s) found under `temp/`** — see the "
            "Temp Folder Analysis section below."
        )
    else:
        lines.append(
            "- **No JSON/JSONL files currently exist under `temp/`** at audit time — the "
            "concern (durable data accidentally living in scratch space) does not apply "
            "right now, though `temp/` is gitignored so this can change between runs."
        )
    unknown_count = counts.get("UNKNOWN_REQUIRES_REVIEW", 0)
    lines.append(
        f"- **{unknown_count} file(s) remain `UNKNOWN_REQUIRES_REVIEW`** after heuristic "
        "classification — see 'Files Requiring Human Review' below."
    )

    legit = [f for f in files if f["classification"].startswith(ALLOWED_PREFIX)]
    lines += [
        "",
        "## Files That Should Legitimately Exist",
        "",
        "| File | Classification | Why it stays JSON |",
        "|---|---|---|",
    ]
    _WHY = {
        "ALLOWED_AUTHORITATIVE_JSON": "Live portfolio/execution-domain state, outside the qualitative intelligence ledger's scope.",
        "ALLOWED_CONFIGURATION_JSON": "Static configuration/manifest/schema/template — not durable observation data.",
        "ALLOWED_MODEL_ARTIFACT_JSON": "Versioned DCF/model output artifact, consumed directly by valuation workflows.",
        "ALLOWED_SEPARATE_DOMAIN_LEDGER_JSONL": "Its own append-only ledger for a different domain (predictions, agent telemetry) — not merged into observations.jsonl without a separate ADR.",
        "ALLOWED_TEST_FIXTURE_JSON": "Test/eval fixture or prompt reference example, not application state.",
        "ALLOWED_GENERATED_CACHE_JSON": "Regenerable cache — safe to exist as long as its generating source is known.",
    }
    for f in legit:
        lines.append(f"| `{f['path']}` | {f['classification']} | {_WHY.get(f['classification'], '')} |")

    not_long_term = [
        f for f in files
        if f["classification"] in ("MIGRATE_TO_INTELLIGENCE_LEDGER", "ARCHIVE_LEGACY_READ_ONLY", "DELETE_AFTER_VERIFIED_ARCHIVE")
    ]
    lines += [
        "",
        "## Files That Likely Should Not Exist Long-Term",
        "",
        "| File | Reason | Required next action |",
        "|---|---|---|",
    ]
    for f in not_long_term:
        if f["classification"] == "MIGRATE_TO_INTELLIGENCE_LEDGER":
            reason = "Durable observation data that belongs in the intelligence ledger once Phase 3 migration tooling runs."
            action = f["migration_status"]
        elif f["classification"] == "ARCHIVE_LEGACY_READ_ONLY":
            reason = "Build-tool cache artifact, checked into git by mistake." if "/.vite/" in f["path"] else "Legacy artifact."
            action = "Add to .gitignore, git rm --cached (separate low-risk task)"
        else:
            reason = "Verified-archived, deletion candidate."
            action = "Confirm archive exists, then delete per the Task 19 cleanup gate."
        lines.append(f"| `{f['path']}` | {reason} | {action} |")
    if not not_long_term:
        lines.append("| (none) | | |")

    lines += ["", "## Files Requiring Human Review", "", "| File | Reason | Suggested next action |", "|---|---|---|"]
    for f in files:
        if f["classification"] == "UNKNOWN_REQUIRES_REVIEW":
            lines.append(f"| `{f['path']}` | No known heuristic match | INVESTIGATE |")

    lines += ["", "## Temp Folder Analysis", ""]
    if temp_files:
        lines.append("| File | Assessment |")
        lines.append("|---|---|")
        for f in temp_files:
            lines.append(f"| `{f['path']}` | {f['classification']} |")
    else:
        lines.append(
            "No `.json`/`.jsonl` files currently exist under `temp/` (which is gitignored "
            "scratch space per `.gitignore`). Re-run this audit periodically if `temp/` is "
            "suspected of accumulating durable data over time — nothing to report as of "
            f"{result['generated_at']}."
        )

    lines += ["", "## Per-File Inventory", ""]
    for f in files:
        lines.append(f"### {f['path']}")
        lines.append("")
        lines.append(f"**Classification:** {f['classification']}")
        lines.append("")
        lines.append("**Known producers:**")
        for r in f["known_producers"]:
            lines.append(f"- {r['referencing_file']}:{r['line']}")
        if not f["known_producers"]:
            lines.append("- (none detected)")
        lines.append("")
        lines.append("**Known consumers:**")
        for r in f["known_consumers"]:
            lines.append(f"- {r['referencing_file']}:{r['line']}")
        if not f["known_consumers"]:
            lines.append("- (none detected)")
        lines.append("")

    return "\n".join(lines) + "\n"


def render_register_md(result: dict) -> str:
    """Render the human-readable allowed JSON register (ALLOWED_* entries only)."""
    allowed = [f for f in result["files"] if f["classification"].startswith(ALLOWED_PREFIX)]
    lines = [
        "# Allowed JSON / JSONL Register",
        "",
        "## Purpose",
        "",
        "This register identifies JSON and JSONL files that are allowed to remain after "
        "the SQLite intelligence ledger migration. A file appearing here is not automatically "
        "exempt forever; it is exempt because its current purpose and ownership are documented.",
        "",
        "## Register",
        "",
        "| File / pattern | Status | Purpose | Producers | Consumers | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for f in allowed:
        purpose = CLASSIFICATION_PURPOSE.get(f["classification"], "")
        producers = "<br>".join(f"{r['referencing_file']}:{r['line']}" for r in f["known_producers"]) or "(none detected)"
        consumers = "<br>".join(f"{r['referencing_file']}:{r['line']}" for r in f["known_consumers"]) or "(none detected)"
        lines.append(f"| `{f['path']}` | {f['classification']} | {purpose} | {producers} | {consumers} | |")
    return "\n".join(lines) + "\n"


def write_reports(result: dict, out_dir: str) -> None:
    """Write all four required Task 12A output files.

    Args:
        result: Output of run_audit().
        out_dir: Directory to write docs/superpowers/audits/-style output into.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    (out_path / "json-discovery-audit.md").write_text(render_discovery_md(result))
    (out_path / "json-discovery-audit.json").write_text(json.dumps(result, indent=2))

    allowed = [f for f in result["files"] if f["classification"].startswith(ALLOWED_PREFIX)]
    register = {
        "generated_at": result["generated_at"],
        "allowed_files": [
            {
                "path_or_pattern": f["path"],
                "classification": f["classification"],
                "git_tracked": f["git_tracked"],
                "producers": [f"{r['referencing_file']}:{r['line']}" for r in f["known_producers"]],
                "consumers": [f"{r['referencing_file']}:{r['line']}" for r in f["known_consumers"]],
            }
            for f in allowed
        ],
    }
    (out_path / "allowed-json-register.md").write_text(render_register_md(result))
    (out_path / "allowed-json-register.json").write_text(json.dumps(register, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Repository-wide JSON/JSONL discovery audit.")
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    parser.add_argument("--out", default="docs/architecture", help="Output directory for reports.")
    args = parser.parse_args()

    result = run_audit(args.root)
    write_reports(result, args.out)
    print(f"Audit complete: {len(result['files'])} JSON/JSONL files found. Reports written to {args.out}")


if __name__ == "__main__":
    main()
