#!/usr/bin/env python3
"""
update_thesis.py — CLI tool to update target weights in the portfolio thesis JSON.

Reads: investment_screener/backend/data/theses/target_portfolio.json
Writes: same file (after --dry-run validation pass)

Aligns with investment thesis document:
  plugins/thesis-balancer/references/investment_thesis.md

Usage examples:
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

  # Batch update from a JSON patch file (see --help for format)
  python3 update_thesis.py --patch /tmp/formula_changes.json

  # Preview without writing
  python3 update_thesis.py --holding INTC --target 8.0 --dry-run

  # Bump version and write a change note
  python3 update_thesis.py --holding AVGO --target 8.0 --note "Strategic review 2026-05-02: increase weight per SA 13F conviction"
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
THESIS_PATH = REPO_ROOT / "investment_screener" / "backend" / "data" / "theses" / "target_portfolio.json"
THESIS_DOC  = REPO_ROOT / "docs" / "InvestmentThesis" / "investment_thesis.md"

VALID_ROLES = {"core", "hedge", "speculative", "reserve"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_thesis() -> dict:
    if not THESIS_PATH.exists():
        sys.exit(f"ERROR: thesis file not found at {THESIS_PATH}")
    with open(THESIS_PATH) as f:
        return json.load(f)


def save_thesis(data: dict, dry_run: bool, note: str | None) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    data["updatedAt"] = now
    data["version"] = data.get("version", 1) + 1
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
        if bh.get("pillarId") != h["pillarId"]:
            changes.append(f"pillar {bh.get('pillarId', '—')} → {h['pillarId']}")
        if bh.get("role") != h["role"]:
            changes.append(f"role {bh.get('role', '—')} → {h['role']}")
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
            print(f"  {h['ticker']:<10} {h['pillarId']:<22} {h.get('role','core'):<14} {h['targetWeight']:>6.2f}%")
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
