"""build_consumer_inventory.py — Task 18 consumer inventory generator.

Purpose:
    Inverts audit_json_usage.py's per-JSON-FILE producer/consumer/doc-reference
    data (docs/architecture/json-discovery-audit.json) into a per-
    CONSUMER-FILE view: for every script/SKILL.md/route/component that
    references at least one discovered JSON/JSONL file, report every file it
    touches and a Task-18-taxonomy classification of what should happen to it.

    Read-only — consumes the already-generated discovery audit, never
    re-scans the repository itself and never modifies any source file.

Layer: Codify / Audit

Key Input Dependencies:
    - docs/architecture/json-discovery-audit.json (produced by audit_json_usage.py)

Key Output Dependencies:
    - docs/superpowers/audits/task18-consumer-inventory.md / .json

Usage:
    python3 build_consumer_inventory.py \
        --audit docs/architecture/json-discovery-audit.json \
        --out docs/superpowers/audits

Index:
    - CLASSIFICATION_PRIORITY
    - build_consumer_inventory(discovery_result) -> list[dict]
    - classify_consumer(referenced_classifications, consumer_file) -> str
    - render_inventory_md(inventory) -> str
    - write_inventory(inventory, out_dir) -> None
    - main() -> CLI entry point
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

# Priority order when a consumer touches JSON files with mixed classifications —
# highest-signal / most-actionable finding wins.
CLASSIFICATION_PRIORITY = [
    "MIGRATION_REQUIRED",
    "USES_LEDGER_REPOSITORY",
    "OUT_OF_SCOPE",
    "REMAINS_JSON_BY_DESIGN",
    "UNKNOWN_REQUIRES_REVIEW",
]

_MIGRATE_SOURCE_CLASSIFICATIONS = {"MIGRATE_TO_INTELLIGENCE_LEDGER", "GENERATE_FROM_LEDGER_OR_SQLITE"}
_ALLOWED_CLASSIFICATIONS_PREFIX = "ALLOWED_"


def classify_consumer(referenced_classifications: list, consumer_file: str) -> str:
    """Classify a consumer file per the Task 18 taxonomy.

    Args:
        referenced_classifications: List of classification strings for every
            JSON/JSONL file this consumer references.
        consumer_file: Repo-relative path of the referencing file.

    Returns:
        One of CLASSIFICATION_PRIORITY's values.
    """
    if "/py_services/intelligence/" in consumer_file.replace("\\", "/"):
        # The ledger repository layer itself — its own internal JSON access
        # (schema/config) is by definition using the ledger repository, not
        # a legacy consumer of it.
        return "USES_LEDGER_REPOSITORY"

    if any(c in _MIGRATE_SOURCE_CLASSIFICATIONS for c in referenced_classifications):
        return "MIGRATION_REQUIRED"

    if referenced_classifications and all(c == "OUT_OF_SCOPE_FOR_THIS_PHASE" for c in referenced_classifications):
        return "OUT_OF_SCOPE"

    if referenced_classifications and all(
        c.startswith(_ALLOWED_CLASSIFICATIONS_PREFIX) or c == "OUT_OF_SCOPE_FOR_THIS_PHASE"
        for c in referenced_classifications
    ):
        return "REMAINS_JSON_BY_DESIGN"

    return "UNKNOWN_REQUIRES_REVIEW"


def build_consumer_inventory(discovery_result: dict) -> list:
    """Invert the discovery audit's per-file reference data into a per-consumer view.

    Only `producer`/`consumer` roles (actual json.load/json.dump/open/
    readFileSync/writeFileSync-style code operations) count as a "reader/
    writer" for Task 18's purposes. A file that only MENTIONS a JSON filename
    in prose (README.md, architecture.md, a docstring) is not a code
    consumer — including it here with the same migration urgency as a real
    reader/writer would be misleading. Doc-only mentions are omitted from
    this inventory entirely (they remain visible in the discovery audit's
    own `doc_references` field per JSON file, which is where documentation
    reference tracking belongs).

    Args:
        discovery_result: The parsed json-discovery-audit.json structure
            (output of audit_json_usage.run_audit()).

    Returns:
        List of dicts: consumer_file, referenced_json_files (list of
        {json_path, json_classification, role, line, confidence}),
        classification.
    """
    consumers = {}

    for f in discovery_result["files"]:
        json_path = f["path"]
        json_classification = f["classification"]
        for role, refs in (
            ("producer", f.get("known_producers", [])),
            ("consumer", f.get("known_consumers", [])),
        ):
            for ref in refs:
                consumer_file = ref["referencing_file"]
                bucket = consumers.setdefault(consumer_file, [])
                bucket.append({
                    "json_path": json_path,
                    "json_classification": json_classification,
                    "role": role,
                    "line": ref["line"],
                    "confidence": ref["confidence"],
                })

    inventory = []
    for consumer_file, referenced in sorted(consumers.items()):
        classifications = [r["json_classification"] for r in referenced]
        inventory.append({
            "consumer_file": consumer_file,
            "referenced_json_files": referenced,
            "classification": classify_consumer(classifications, consumer_file),
        })
    return inventory


_ACTION_BY_CLASSIFICATION = {
    "MIGRATION_REQUIRED": "Rewire to intelligence.event_store/event_repository once Phase 3 migration tooling runs",
    "USES_LEDGER_REPOSITORY": "None — already using the shared data layer",
    "OUT_OF_SCOPE": "None — domain explicitly out of scope for this phase",
    "REMAINS_JSON_BY_DESIGN": "None — legitimate flat-file JSON per ADR-028 scope boundary",
    "UNKNOWN_REQUIRES_REVIEW": "Manual review required to determine correct classification",
}


def render_inventory_md(inventory: list) -> str:
    """Render the human-readable Task 18 consumer inventory table."""
    lines = [
        "# Task 18 Consumer Inventory — Legacy JSON Readers/Writers",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}. "
        "Machine-generated by inverting docs/architecture/json-discovery-audit.json's "
        "per-file reference data. Every consumer discovered by the (bug-fixed) audit script "
        "is listed — none were guessed at. Doc-only mentions (README.md, architecture.md, "
        "prose) are excluded from this list entirely — this covers code readers/writers only.",
        "",
        "**Known false-positive class:** the underlying audit script does line-level string "
        "matching, not real static analysis. Two known false-positive patterns show up as "
        "`MIGRATION_REQUIRED` entries below even though they never call `open()`/`json.load`/"
        "`json.dump` on the file: (1) `audit_json_usage.py` and its test reference filenames "
        "as classification-pattern strings, not I/O targets; (2) files whose docstring lists "
        "a filename under a \"Key Input Dependencies\" documentation header (per this repo's "
        "coding-conventions rule) get picked up the same as a real code reference. Neither is "
        "corrected automatically — treat any `MIGRATION_REQUIRED` entry with only one weak "
        "reference as worth a quick manual check before assuming it needs code changes.",
        "",
        "| Consumer | Current data source | Legacy reference? | Target source | Action | Test required | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in inventory:
        sources = ", ".join(sorted({r["json_path"] for r in c["referenced_json_files"]}))
        is_legacy = "Yes" if c["classification"] == "MIGRATION_REQUIRED" else "No"
        target = "intelligence_event (ledger)" if c["classification"] == "MIGRATION_REQUIRED" else "n/a"
        action = _ACTION_BY_CLASSIFICATION[c["classification"]]
        test_required = "Yes" if c["classification"] in ("MIGRATION_REQUIRED", "UNKNOWN_REQUIRES_REVIEW") else "No"
        lines.append(
            f"| `{c['consumer_file']}` | {sources} | {is_legacy} | {target} | {action} | "
            f"{test_required} | {c['classification']} |"
        )

    counts = {}
    for c in inventory:
        counts[c["classification"]] = counts.get(c["classification"], 0) + 1
    lines += ["", "## Summary", "", "| Classification | Count |", "|---|---:|"]
    for cls in CLASSIFICATION_PRIORITY:
        lines.append(f"| {cls} | {counts.get(cls, 0)} |")

    return "\n".join(lines) + "\n"


def write_inventory(inventory: list, out_dir: str) -> None:
    """Write both Markdown and JSON forms of the consumer inventory.

    Args:
        inventory: Output of build_consumer_inventory().
        out_dir: Directory to write task18-consumer-inventory.md/.json into.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "task18-consumer-inventory.md").write_text(render_inventory_md(inventory))
    (out_path / "task18-consumer-inventory.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "consumers": inventory,
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Task 18 consumer inventory generator.")
    parser.add_argument("--audit", default="docs/architecture/json-discovery-audit.json")
    parser.add_argument("--out", default="docs/superpowers/audits")
    args = parser.parse_args()

    discovery_result = json.loads(Path(args.audit).read_text())
    inventory = build_consumer_inventory(discovery_result)
    write_inventory(inventory, args.out)
    print(f"Consumer inventory complete: {len(inventory)} consumer files found. Reports written to {args.out}")


if __name__ == "__main__":
    main()
