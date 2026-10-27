#!/usr/bin/env python3
"""
update_thesis.py (Python Service)
=====================================

Purpose:
    CLI tool for modifying target weights, roles, thesis text, pillar targets and thesis
    breakers in domain_model.sqlite. Enforces strict validation (holding and pillar weights
    must sum to 100%) and records one portfolio_change_log entry for every write.
    Nothing is written with --dry-run or when validation fails.

Layer: Backend / Python Services / Strategy Configuration

Usage Examples:
    # Update a pillar's target weight (pillar weights must still sum to 100)
    python3 update_thesis.py --patch pillars.json            # {"pillars": [{"id": "ai", "targetWeight": 45}, ...]}

    # Update a holding's target weight (holding weights must still sum to 100)
    python3 update_thesis.py --holding INTC --target 8.0 --patch other_weights.json

    # Update holding role (accumulate, trim, exit, initiate, watchlist)
    python3 update_thesis.py --holding OKLO --role trim

    # Update holding thesis-for-inclusion text
    python3 update_thesis.py --holding CRWV --thesis "CoreWeave: pure-play GPU cloud for hyperscaler overflow"

    # Batch update from a JSON patch file (input only; never written)
    python3 update_thesis.py --patch /tmp/formula_changes.json --note "Strategic review: increase AVGO"

    # Thesis breakers
    python3 update_thesis.py --holding NBIS --set-breaker '{"id": "rsi-low", "type": "auto", ...}'
    python3 update_thesis.py --holding NBIS --set-breaker-status ndr-floor --status TRIGGERED --note "Q2 NDR 108%"
    python3 update_thesis.py --holding NBIS --remove-breaker rsi-low

    # Preview without writing
    python3 update_thesis.py --holding INTC --role exit --dry-run

Key Functions (Index):
    - load_thesis(): pillars and holdings (with breakers) from SQLite as one dict
    - apply_patch(): apply a JSON patch to the in-memory thesis
    - validate_weights(): hard gate on pillar and holding weight sums
    - set_breaker() / set_breaker_status() / remove_breaker(): in-memory breaker edits
    - save_thesis(): persist the differences through the repositories and record the change
    - main(): command line

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (--db): pillars, holdings, breakers
    - Optional JSON patch file (--patch), read only

Key Output Dependencies:
    - investment.* thesis fields, strategy_pillar.target_weight, thesis_breaker rows,
      portfolio_change_log (one entry per write)
"""

import argparse
import copy
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = REPO_ROOT / "investment_screener" / "backend" / "data" / "domain_model.sqlite"
THESIS_DOC = REPO_ROOT / "plugins" / "portfolio-advisor" / "references" / "investment_thesis.md"

sys.path.insert(0, str(REPO_ROOT / "investment_screener" / "backend" / "py_services"))
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.investment_repository import resolve_investment, update_investment_fields  # noqa: E402
from domain_model.pillar_repository import list_pillars, resolve_pillar  # noqa: E402
from domain_model.portfolio_change_log_repository import record_change  # noqa: E402
from domain_model.thesis_breaker_repository import (  # noqa: E402,F401
    AUTO_METRICS,
    VALID_OPERATORS,
    VALID_STATUSES,
    delete_breaker,
    upsert_breaker,
    validate_breaker,
)
from portfolio_io import LIFECYCLE_STATUSES, load_thesis_holdings, validate_lifecycle_status  # noqa: E402

VALID_ROLES = LIFECYCLE_STATUSES


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_thesis(db_path: Path = DB_PATH) -> dict:
    """The thesis from domain_model.sqlite: {"pillars": [...], "holdings": [...]}.

    Pillars are {id, name, targetWeight}; holdings are the portfolio_io.load_thesis_holdings
    dicts (ticker, pillarId, targetWeight, role, thesisForInclusion, thesisBreakers, ...).
    Exits with an error when the database does not exist.
    """
    if not Path(db_path).exists():
        sys.exit(f"ERROR: database not found at {db_path}")
    conn = initialize_db(str(db_path))
    try:
        pillars = [
            {"id": p["pillar_id"], "name": p["name"], "targetWeight": p["target_weight"]}
            for p in list_pillars(conn)
        ]
    finally:
        conn.close()
    return {"pillars": pillars, "holdings": load_thesis_holdings(str(db_path))}


def _changes(before: dict, after: dict) -> list[str]:
    """Human-readable list of what differs between two thesis dicts (used for the default note)."""
    out = []
    before_p = {p["id"]: p for p in before["pillars"]}
    for p in after["pillars"]:
        if before_p.get(p["id"], {}).get("targetWeight") != p["targetWeight"]:
            out.append(f"pillar {p['id']} -> {p['targetWeight']}%")
    before_h = {h["ticker"]: h for h in before["holdings"]}
    for h in after["holdings"]:
        old = before_h.get(h["ticker"], {})
        for key, label in (("targetWeight", "weight"), ("pillarId", "pillar"), ("role", "role")):
            if old.get(key) != h.get(key):
                out.append(f"{h['ticker']} {label} -> {h.get(key)}")
        if old.get("thesisForInclusion") != h.get("thesisForInclusion"):
            out.append(f"{h['ticker']} thesis text")
        if old.get("thesisBreakers") != h.get("thesisBreakers"):
            out.append(f"{h['ticker']} breakers")
    return out


def _save_holding_fields(conn, old: dict, h: dict) -> None:
    """Write the changed investment columns of one holding."""
    fields = {}
    if old.get("targetWeight") != h.get("targetWeight"):
        fields["target_weight"] = h["targetWeight"]
    if old.get("pillarId") != h.get("pillarId"):
        fields["pillar_id"] = h["pillarId"]
    if old.get("role") != h.get("role"):
        fields["lifecycle_status"] = validate_lifecycle_status(h["role"])
    if old.get("thesisForInclusion") != h.get("thesisForInclusion"):
        fields["thesis_for_inclusion"] = h["thesisForInclusion"]
    if fields:
        update_investment_fields(conn, resolve_investment(conn, h["ticker"]), **fields)


def _save_breakers(conn, old: dict, h: dict) -> None:
    """Delete removed breakers and upsert added or changed ones for one holding."""
    before = {b["id"]: b for b in old.get("thesisBreakers", [])}
    after = {b["id"]: b for b in h.get("thesisBreakers", [])}
    for breaker_id in before.keys() - after.keys():
        delete_breaker(conn, h["ticker"], breaker_id)
    for breaker_id, breaker in after.items():
        if before.get(breaker_id) != breaker:
            upsert_breaker(conn, h["ticker"], breaker)


def save_thesis(before: dict, after: dict, db_path: Path, note: str | None, dry_run: bool) -> None:
    """Persist what changed between ``before`` and ``after`` and record one change-log entry.

    Writes pillar targets through ``pillar_repository``, holding fields through
    ``investment_repository``, breakers through ``thesis_breaker_repository`` and then calls
    ``record_change``. With ``dry_run`` nothing is written.

    Raises:
        ValueError: a role is not in the lifecycle vocabulary, or a breaker is invalid.
    """
    summary = _changes(before, after)
    if dry_run:
        print("\n── DRY RUN — nothing written ──")
        print("  Would record:", note or ("update_thesis.py: " + "; ".join(summary)))
        return
    if not summary:
        print("No changes to save.")
        return
    conn = initialize_db(str(db_path))
    try:
        before_p = {p["id"]: p for p in before["pillars"]}
        for p in after["pillars"]:
            if before_p.get(p["id"], {}).get("targetWeight") != p["targetWeight"]:
                resolve_pillar(conn, p["id"], p["name"], p["targetWeight"])
        before_h = {h["ticker"]: h for h in before["holdings"]}
        for h in after["holdings"]:
            old = before_h.get(h["ticker"], {})
            _save_holding_fields(conn, old, h)
            _save_breakers(conn, old, h)
        record_change(conn, note or ("update_thesis.py: " + "; ".join(summary)))
    finally:
        conn.close()
    print(f"✅  Saved {len(summary)} change(s) to {db_path}")
    refresh = Path(__file__).parent / "refresh_all.py"
    if Path(db_path) == DB_PATH and refresh.exists():
        # Refresh all thesis pages and role fields after a write to the real database.
        subprocess.run([sys.executable, str(refresh)], check=False)


def validate_weights(data: dict) -> list[str]:
    """Errors when holding weights (and pillar weights, if any are set) do not sum to 100 ± 0.5."""
    errors = []
    if any(p["targetWeight"] is not None for p in data["pillars"]):
        pillar_sum = sum(p["targetWeight"] or 0 for p in data["pillars"])
        if abs(pillar_sum - 100) > 0.5:
            errors.append(f"Pillar weights sum to {pillar_sum:.2f}% (must be 100%)")
    holding_sum = sum(h["targetWeight"] or 0 for h in data["holdings"])
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
# Patch file format (JSON, input only):
# {
#   "pillars": [{"id": "ai-compute", "targetWeight": 45.0}],
#   "holdings": [{"ticker": "INTC", "targetWeight": 8.0, "role": "trim"}]
# }

def apply_patch(data: dict, patch: dict) -> dict:
    for pp in patch.get("pillars", []):
        pillar = next((p for p in data["pillars"] if p["id"] == pp["id"]), None)
        if not pillar:
            sys.exit(f"ERROR: pillar id '{pp['id']}' not found")
        if "targetWeight" in pp:
            pillar["targetWeight"] = float(pp["targetWeight"])
        if "name" in pp:
            pillar["name"] = pp["name"]
        if "description" in pp:
            pillar["description"] = pp["description"]

    for ph in patch.get("holdings", []):
        holding = next((h for h in data["holdings"] if h["ticker"] == ph["ticker"]), None)
        if not holding:
            sys.exit(f"ERROR: ticker '{ph['ticker']}' not found")
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


def set_breaker(holding: dict, breaker: dict) -> None:
    """Add a new breaker to a holding's thesisBreakers list.

    Args:
        holding: The holding dict from load_thesis() (mutated in place).
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
        note: Optional note appended to the breaker's 'note' field. If the
            breaker already has a note (e.g. the original condition rationale
            for a manual breaker), the new note is appended after a dated
            separator rather than overwriting it.

    Raises:
        ValueError: If the breaker isn't found, or isn't type "manual".
    """
    breaker = next((b for b in holding.get("thesisBreakers", []) if b["id"] == breaker_id), None)
    if breaker is None:
        raise ValueError(f"breaker id '{breaker_id}' not found on {holding.get('ticker')}")
    if breaker["type"] != "manual":
        raise ValueError(f"breaker '{breaker_id}' is type '{breaker['type']}' — status can only be set on manual breakers")
    today = datetime.now(timezone.utc).date().isoformat()
    breaker["status"] = status
    breaker["statusSetAt"] = today
    if note:
        if breaker.get("note"):
            breaker["note"] = f"{breaker['note']} | status update {today}: {note}"
        else:
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

def _list(data: dict) -> None:
    """Print the pillar and holding tables."""
    print(f"\nThesis document: {THESIS_DOC}\n")
    print(f"{'PILLAR':<32} {'TARGET':>7}")
    print("─" * 42)
    for p in sorted(data["pillars"], key=lambda x: -(x["targetWeight"] or 0)):
        print(f"  {p['id']:<30} {(p['targetWeight'] or 0):>6.2f}%  {p['name']}")
    print()
    print(f"{'TICKER':<12} {'PILLAR':<22} {'ROLE':<14} {'TARGET':>7}")
    print("─" * 58)
    for h in sorted(data["holdings"], key=lambda x: -(x["targetWeight"] or 0)):
        print(f"  {h['ticker']:<10} {h.get('pillarId', 'other'):<22} {h.get('role', 'watchlist'):<14} {h['targetWeight']:>6.2f}%")
    print()


def _edit_holding(data: dict, args) -> None:
    """Apply the --holding options to one holding, exiting with a message on invalid input."""
    holding = next((h for h in data["holdings"] if h["ticker"] == args.holding), None)
    if not holding:
        sys.exit(f"ERROR: ticker '{args.holding}' not found. Holdings: {[h['ticker'] for h in data['holdings']]}")
    if args.target is not None:
        holding["targetWeight"] = args.target
    if args.role:
        holding["role"] = args.role
    if args.thesis:
        holding["thesisForInclusion"] = args.thesis
    try:
        if args.set_breaker:
            set_breaker(holding, json.loads(args.set_breaker))
        if args.set_breaker_status:
            if not args.status:
                sys.exit("ERROR: --set-breaker-status requires --status")
            set_breaker_status(holding, args.set_breaker_status, args.status, args.note)
        if args.remove_breaker:
            remove_breaker(holding, args.remove_breaker)
    except ValueError as e:
        sys.exit(f"ERROR: {e}")


def main():
    """Command line entry point."""
    parser = argparse.ArgumentParser(
        description="Update the thesis in domain_model.sqlite. All changes are validated before write.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--pillar",  help="Pillar id to update (e.g. 'ai-compute')")
    parser.add_argument("--holding", help="Ticker to update (e.g. 'INTC')")
    parser.add_argument("--target",  type=float, help="New target weight (percent)")
    parser.add_argument("--role",    choices=sorted(VALID_ROLES), help="Update holding role")
    parser.add_argument("--thesis",  help="Update thesisForInclusion text for the holding")
    parser.add_argument("--patch",   help="Path to a JSON patch file for batch updates (read only)")
    parser.add_argument("--set-breaker", help="JSON breaker object to add to --holding's thesisBreakers")
    parser.add_argument("--set-breaker-status", metavar="BREAKER_ID", help="Breaker id whose status to update (manual breakers only)")
    parser.add_argument("--status", choices=sorted(VALID_STATUSES), help="New status for --set-breaker-status")
    parser.add_argument("--remove-breaker", metavar="BREAKER_ID", help="Breaker id to remove from --holding's thesisBreakers")
    parser.add_argument("--note",    help="Change note recorded in portfolio_change_log")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print diff but do not write")
    parser.add_argument("--list",    action="store_true", help="Print current thesis summary and exit")
    parser.add_argument("--db",      default=str(DB_PATH), help="Path to domain_model.sqlite")
    args = parser.parse_args()
    db_path = Path(args.db)

    data = load_thesis(db_path)
    if args.list:
        _list(data)
        return
    if not (args.patch or args.pillar or args.holding):
        parser.print_help()
        sys.exit(0)

    before = copy.deepcopy(data)

    if args.patch:
        patch_path = Path(args.patch)
        if not patch_path.exists():
            sys.exit(f"ERROR: patch file not found: {patch_path}")
        data = apply_patch(data, json.loads(patch_path.read_text()))

    if args.pillar:
        if args.target is None:
            sys.exit("ERROR: --pillar requires --target")
        pillar = next((p for p in data["pillars"] if p["id"] == args.pillar), None)
        if not pillar:
            sys.exit(f"ERROR: pillar '{args.pillar}' not found. Available: {[p['id'] for p in data['pillars']]}")
        pillar["targetWeight"] = args.target

    if args.holding:
        _edit_holding(data, args)

    print_diff(before, data)

    errors = validate_weights(data)
    if errors:
        print("❌  Validation failed:")
        for e in errors:
            print(f"    • {e}")
        print("\n⚠️   Weights do not sum to 100%. Adjust other pillars/holdings to compensate.")
        print("     Use --list to see current weights, then re-run with corrected values.")
        sys.exit(1)

    try:
        save_thesis(before, data, db_path, args.note, args.dry_run)
    except ValueError as e:
        sys.exit(f"ERROR: {e}")


if __name__ == "__main__":
    main()
