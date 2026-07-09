#!/usr/bin/env python3
"""
update_thesis.py (Python Service)
=====================================

Purpose:
    CLI tool for modifying target weights, roles, and rationale in the portfolio thesis JSON.
    Enforces strict validation rules (e.g., weights must sum to 100%) and maintains a versioned changeLog.
    Aligns changes with the primary investment thesis Markdown document.

Layer: Backend / Python Services / Strategy Configuration

Usage Examples:
    # Update a pillar's target weight
    python3 update_thesis.py --pillar ai-compute --target 45.0

    # Update a holding's target weight
    python3 update_thesis.py --holding INTC --target 8.0

    # Move a holding to a different pillar
    python3 update_thesis.py --holding INTC --pillar sovereign-infra

    # Update holding role
    python3 update_thesis.py --holding OKLO --role speculative

    # Update holding thesis-for-inclusion text
    python3 update_thesis.py --holding CRWV --thesis "CoreWeave: pure-play GPU cloud for hyperscaler overflow"

    # Batch update from a JSON patch file
    python3 update_thesis.py --patch /tmp/formula_changes.json

    # Preview without writing
    python3 update_thesis.py --holding INTC --target 8.0 --dry-run

    # Bump version and write a change note
    python3 update_thesis.py --holding AVGO --target 8.0 --note "Strategic review: increase weight per conviction"

Key Functions:
    - apply_patch() - Supports batch updates from a JSON patch file
    - validate_weights() - Hard-gate validation ensuring all target allocations sum exactly to 100%
    - save_thesis() - Atomic write operation that bumps version numbers and persists changes to data storage
"""

import argparse
import copy
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
THESIS_PATH = REPO_ROOT / "investment_screener" / "backend" / "data" / "theses" / "target-portfolio.json"
THESIS_DOC  = REPO_ROOT / "plugins" / "portfolio-advisor" / "references" / "investment_thesis.md"

VALID_ROLES = {"core", "hedge", "speculative", "reserve"}

AUTO_METRICS = frozenset({
    "rsi", "dcfFairValueGapPct", "trendState", "momentumPercentile", "pillarAvgScore",
})
VALID_OPERATORS = frozenset({"<", "<=", ">", ">=", "==", "in"})
VALID_STATUSES = frozenset({"OK", "WATCHING", "TRIGGERED"})


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_thesis() -> dict:
    if not THESIS_PATH.exists():
        sys.exit(f"ERROR: thesis file not found at {THESIS_PATH}")
    with open(THESIS_PATH) as f:
        return json.load(f)


def save_thesis(data: dict, dry_run: bool, note: str | None) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    data["updatedAt"] = now
    version = data.get("version", 1)
    if isinstance(version, str):
        try:
            if "." in version:
                version = str(round(float(version) + 0.1, 4))
            else:
                version = str(int(version) + 1)
        except ValueError:
            version = version + "_updated"
    else:
        version = version + 1
    data["version"] = version
    if note:
        data.setdefault("changeLog", []).append({
            "version": data["version"],
            "date": now[:10],
            "note": note,
        })

    if dry_run:
        print("\n── DRY RUN — no file written ──")
        print(json.dumps(data, indent=2)[:3000], "…")
        return

    tmp = THESIS_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, THESIS_PATH)
    print(f"✅  Saved thesis.json  (version {data['version']})")

    # Refresh all thesis pages and role fields after any thesis write.
    import subprocess
    refresh = Path(__file__).parent / "refresh_all.py"
    if refresh.exists():
        subprocess.run([sys.executable, str(refresh)], check=False)


def validate_weights(data: dict) -> list[str]:
    errors = []
    pillar_sum = sum(p["targetWeight"] for p in data["pillars"])
    if abs(pillar_sum - 100) > 0.5:
        errors.append(f"Pillar weights sum to {pillar_sum:.2f}% (must be 100%)")
    holding_sum = sum(h["targetWeight"] for h in data["holdings"])
    if abs(holding_sum - 100) > 0.5:
        errors.append(f"Holding weights sum to {holding_sum:.2f}% (must be 100%)")
    return errors


def print_diff(before: dict, after: dict) -> None:
    """Print a human-readable diff of pillar and holding weights."""
    print("\n── Changes ──────────────────────────────────────────────────────")

    before_pillars = {p["id"]: p for p in before["pillars"]}
    for p in after["pillars"]:
        bp = before_pillars.get(p["id"], {})
        if bp.get("targetWeight") != p["targetWeight"]:
            print(f"  PILLAR  {p['id']:30s}  {bp.get('targetWeight', '—'):>6} → {p['targetWeight']:>6} %")

    before_holdings = {h["ticker"]: h for h in before["holdings"]}
    for h in after["holdings"]:
        bh = before_holdings.get(h["ticker"], {})
        changes = []
        if bh.get("targetWeight") != h["targetWeight"]:
            changes.append(f"weight {bh.get('targetWeight', '—')} → {h['targetWeight']} %")
        if bh.get("pillarId") != h.get("pillarId"):
            changes.append(f"pillar {bh.get('pillarId', '—')} → {h.get('pillarId', '—')}")
        if bh.get("role") != h.get("role"):
            changes.append(f"role {bh.get('role', '—')} → {h.get('role', '—')}")
        if bh.get("thesisForInclusion") != h.get("thesisForInclusion"):
            changes.append("thesis updated")
        if changes:
            print(f"  HOLDING {h['ticker']:10s}  {', '.join(changes)}")

    print()
    psum = sum(p["targetWeight"] for p in after["pillars"])
    hsum = sum(h["targetWeight"] for h in after["holdings"])
    print(f"  Pillar weight total:  {psum:.2f} %")
    print(f"  Holding weight total: {hsum:.2f} %")
    print("──────────────────────────────────────────────────────────────────\n")


# ── Patch file support ─────────────────────────────────────────────────────────
# Patch file format (JSON):
# {
#   "pillars": [{"id": "ai-compute", "targetWeight": 45.0}],
#   "holdings": [{"ticker": "INTC", "targetWeight": 8.0, "role": "core"}]
# }

def apply_patch(data: dict, patch: dict) -> dict:
    for pp in patch.get("pillars", []):
        pillar = next((p for p in data["pillars"] if p["id"] == pp["id"]), None)
        if not pillar:
            sys.exit(f"ERROR: pillar id '{pp['id']}' not found in thesis")
        if "targetWeight" in pp:
            pillar["targetWeight"] = float(pp["targetWeight"])
        if "name" in pp:
            pillar["name"] = pp["name"]
        if "description" in pp:
            pillar["description"] = pp["description"]

    for ph in patch.get("holdings", []):
        holding = next((h for h in data["holdings"] if h["ticker"] == ph["ticker"]), None)
        if not holding:
            sys.exit(f"ERROR: ticker '{ph['ticker']}' not found in thesis holdings")
        if "targetWeight" in ph:
            holding["targetWeight"] = float(ph["targetWeight"])
        if "pillarId" in ph:
            valid_pillar_ids = {p["id"] for p in data["pillars"]}
            if ph["pillarId"] not in valid_pillar_ids:
                sys.exit(f"ERROR: pillar id '{ph['pillarId']}' does not exist — valid: {sorted(valid_pillar_ids)}")
            holding["pillarId"] = ph["pillarId"]
        if "role" in ph:
            if ph["role"] not in VALID_ROLES:
                sys.exit(f"ERROR: role '{ph['role']}' invalid — must be one of {sorted(VALID_ROLES)}")
            holding["role"] = ph["role"]
        if "thesisForInclusion" in ph:
            holding["thesisForInclusion"] = ph["thesisForInclusion"]
        if "thesisBreakers" in ph:
            holding["thesisBreakers"] = ph["thesisBreakers"]

    return data


def validate_breaker(breaker: dict) -> list[str]:
    """Validate a thesisBreakers entry before it's written to target-portfolio.json.

    Args:
        breaker: A single breaker dict (auto or manual — see spec §2.1).

    Returns:
        List of human-readable error strings; empty if valid.
    """
    errors: list[str] = []
    if not breaker.get("id"):
        errors.append("breaker missing 'id'")
    if breaker.get("type") not in ("auto", "manual"):
        errors.append(f"breaker 'type' must be 'auto' or 'manual', got {breaker.get('type')!r}")
    if breaker.get("type") == "auto" and breaker.get("metric") not in AUTO_METRICS:
        errors.append(f"auto breaker 'metric' must be one of {sorted(AUTO_METRICS)}, got {breaker.get('metric')!r}")
    if breaker.get("operator") not in VALID_OPERATORS:
        errors.append(f"'operator' must be one of {sorted(VALID_OPERATORS)}, got {breaker.get('operator')!r}")
    if breaker.get("operator") == "in" and not isinstance(breaker.get("threshold"), list):
        errors.append("operator 'in' requires 'threshold' to be a list")
    if breaker.get("type") == "manual":
        if breaker.get("status") not in VALID_STATUSES:
            errors.append(f"manual breaker 'status' must be one of {sorted(VALID_STATUSES)}, got {breaker.get('status')!r}")
        if not breaker.get("statusSetAt"):
            errors.append("manual breaker missing 'statusSetAt'")
        if not breaker.get("reviewCadenceDays"):
            errors.append("manual breaker missing 'reviewCadenceDays'")
    return errors


def set_breaker(holding: dict, breaker: dict) -> None:
    """Add a new breaker to a holding's thesisBreakers list.

    Args:
        holding: The holding dict from target-portfolio.json (mutated in place).
        breaker: The breaker to add — validated before insertion.

    Raises:
        ValueError: If the breaker fails validate_breaker(), or its id
            already exists on this holding.
    """
    errors = validate_breaker(breaker)
    if errors:
        raise ValueError(f"Invalid breaker: {'; '.join(errors)}")
    existing = holding.setdefault("thesisBreakers", [])
    if any(b["id"] == breaker["id"] for b in existing):
        raise ValueError(f"breaker id '{breaker['id']}' already exists on {holding.get('ticker')}")
    existing.append(breaker)


def set_breaker_status(holding: dict, breaker_id: str, status: str, note: str | None) -> None:
    """Update a manual breaker's status.

    Args:
        holding: The holding dict (mutated in place).
        breaker_id: id of the breaker to update.
        status: New status — must be one of VALID_STATUSES.
        note: Optional note appended to the breaker's 'note' field.

    Raises:
        ValueError: If the breaker isn't found, or isn't type "manual".
    """
    breaker = next((b for b in holding.get("thesisBreakers", []) if b["id"] == breaker_id), None)
    if breaker is None:
        raise ValueError(f"breaker id '{breaker_id}' not found on {holding.get('ticker')}")
    if breaker["type"] != "manual":
        raise ValueError(f"breaker '{breaker_id}' is type '{breaker['type']}' — status can only be set on manual breakers")
    breaker["status"] = status
    breaker["statusSetAt"] = datetime.now(timezone.utc).date().isoformat()
    if note:
        breaker["note"] = note


def remove_breaker(holding: dict, breaker_id: str) -> None:
    """Remove a breaker from a holding's thesisBreakers list.

    Args:
        holding: The holding dict (mutated in place).
        breaker_id: id of the breaker to remove.

    Raises:
        ValueError: If no breaker with that id exists on this holding.
    """
    existing = holding.get("thesisBreakers", [])
    remaining = [b for b in existing if b["id"] != breaker_id]
    if len(remaining) == len(existing):
        raise ValueError(f"breaker id '{breaker_id}' not found on {holding.get('ticker')}")
    holding["thesisBreakers"] = remaining


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Update target weights in thesis.json. All changes are validated before write.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set INTC holding weight to 8%
  python3 update_thesis.py --holding INTC --target 8.0

  # Set ai-compute pillar to 45%
  python3 update_thesis.py --pillar ai-compute --target 45.0

  # Preview changes without writing
  python3 update_thesis.py --holding AVGO --target 8.0 --dry-run

  # Batch update from a patch file
  python3 update_thesis.py --patch /tmp/formula_changes.json --note "2026-05-02 strategic review"

Patch file format (JSON):
  {
    "pillars": [{"id": "ai-compute", "targetWeight": 45.0}],
    "holdings": [{"ticker": "INTC", "targetWeight": 8.0}]
  }
        """,
    )
    parser.add_argument("--pillar",  help="Pillar id to update (e.g. 'ai-compute')")
    parser.add_argument("--holding", help="Ticker to update (e.g. 'INTC')")
    parser.add_argument("--target",  type=float, help="New target weight (percent)")
    parser.add_argument("--role",    choices=sorted(VALID_ROLES), help="Update holding role")
    parser.add_argument("--thesis",  help="Update thesisForInclusion text for the holding")
    parser.add_argument("--patch",   help="Path to a JSON patch file for batch updates")
    parser.add_argument("--set-breaker", help="JSON breaker object to add to --holding's thesisBreakers")
    parser.add_argument("--set-breaker-status", metavar="BREAKER_ID", help="Breaker id whose status to update (manual breakers only)")
    parser.add_argument("--status", choices=sorted(VALID_STATUSES), help="New status for --set-breaker-status")
    parser.add_argument("--remove-breaker", metavar="BREAKER_ID", help="Breaker id to remove from --holding's thesisBreakers")
    parser.add_argument("--note",    help="Change note recorded in changeLog")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print diff but do not write")
    parser.add_argument("--list",    action="store_true", help="Print current thesis summary and exit")
    args = parser.parse_args()

    data = load_thesis()

    if args.list:
        print(f"\nThesis: {data['name']}  (v{data['version']})")
        print(f"Thesis doc: {THESIS_DOC}\n")
        print(f"{'PILLAR':<32} {'TARGET':>7}")
        print("─" * 42)
        for p in sorted(data["pillars"], key=lambda x: -x["targetWeight"]):
            print(f"  {p['id']:<30} {p['targetWeight']:>6.2f}%")
        print()
        print(f"{'TICKER':<12} {'PILLAR':<22} {'ROLE':<14} {'TARGET':>7}")
        print("─" * 58)
        for h in sorted(data["holdings"], key=lambda x: -x["targetWeight"]):
            print(f"  {h['ticker']:<10} {h.get('pillarId', 'other'):<22} {h.get('role','core'):<14} {h['targetWeight']:>6.2f}%")
        print()
        return

    before = copy.deepcopy(data)

    if args.patch:
        patch_path = Path(args.patch)
        if not patch_path.exists():
            sys.exit(f"ERROR: patch file not found: {patch_path}")
        with open(patch_path) as f:
            patch = json.load(f)
        data = apply_patch(data, patch)

    if args.pillar:
        if args.target is None:
            sys.exit("ERROR: --pillar requires --target")
        pillar = next((p for p in data["pillars"] if p["id"] == args.pillar), None)
        if not pillar:
            available = [p["id"] for p in data["pillars"]]
            sys.exit(f"ERROR: pillar '{args.pillar}' not found. Available: {available}")
        pillar["targetWeight"] = args.target

    if args.holding:
        holding = next((h for h in data["holdings"] if h["ticker"] == args.holding), None)
        if not holding:
            available = [h["ticker"] for h in data["holdings"]]
            sys.exit(f"ERROR: ticker '{args.holding}' not found. Holdings: {available}")
        if args.target is not None:
            holding["targetWeight"] = args.target
        if args.role:
            holding["role"] = args.role
        if args.thesis:
            holding["thesisForInclusion"] = args.thesis
        if args.set_breaker:
            breaker = json.loads(args.set_breaker)
            set_breaker(holding, breaker)
        if args.set_breaker_status:
            if not args.status:
                sys.exit("ERROR: --set-breaker-status requires --status")
            set_breaker_status(holding, args.set_breaker_status, args.status, args.note)
        if args.remove_breaker:
            remove_breaker(holding, args.remove_breaker)

    if not args.patch and not args.pillar and not args.holding and not args.list:
        parser.print_help()
        sys.exit(0)

    print_diff(before, data)

    errors = validate_weights(data)
    if errors:
        print("❌  Validation failed:")
        for e in errors:
            print(f"    • {e}")
        print("\n⚠️   Weights do not sum to 100%. Adjust other pillars/holdings to compensate.")
        print("     Use --list to see current weights, then re-run with corrected values.")
        sys.exit(1)

    save_thesis(data, args.dry_run, args.note)


if __name__ == "__main__":
    main()
